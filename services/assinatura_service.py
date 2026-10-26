import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests
from flask import current_app
from extensions import db
from models import Assinatura, ContaCobranca, Fatura, User

PAGOS = ('RECEIVED', 'CONFIRMED', 'RECEIVED_IN_CASH')
STATUS_ASSINATURA = {
    'trial': 'Período de experiência', 'criando': 'Contratação em andamento',
    'incerta': 'Aguardando conciliação', 'pendente': 'Aguardando pagamento',
    'ativo': 'Recorrência ativa', 'cancelado': 'Recorrência cancelada',
    'suspenso': 'Recorrência suspensa', 'expirado': 'Recorrência encerrada',
    'rejeitado': 'Contratação não concluída',
}
STATUS_FATURA = {
    'PENDING': 'Aguardando pagamento', 'RECEIVED': 'Recebida', 'CONFIRMED': 'Confirmada',
    'RECEIVED_IN_CASH': 'Recebida', 'OVERDUE': 'Vencida', 'REFUNDED': 'Reembolsada',
    'REFUND_REQUESTED': 'Reembolso solicitado', 'REFUND_IN_PROGRESS': 'Reembolso em processamento',
    'CHARGEBACK_REQUESTED': 'Contestação solicitada', 'CHARGEBACK_DISPUTE': 'Em contestação',
    'AWAITING_CHARGEBACK_REVERSAL': 'Aguardando decisão da contestação',
    'DUNNING_REQUESTED': 'Cobrança em recuperação', 'DUNNING_RECEIVED': 'Recuperada',
    'AWAITING_RISK_ANALYSIS': 'Em análise', 'CANCELED': 'Cancelada',
}


class GatewayIndisponivel(Exception):
    pass


class GatewayRequisicaoRejeitada(GatewayIndisponivel):
    def __init__(self, mensagem, status_code=None):
        super().__init__(mensagem)
        self.status_code = status_code


def catalogo():
    planos = {'free': {'nome': 'Gratuito', 'valor': Decimal('0.00'), 'limite': 1},
              'pro': {'nome': 'Pro', 'valor': Decimal('14.90'), 'limite': 3}}
    # O plano Frota só é colocado à venda quando a divergência comercial for resolvida.
    valor = current_app.config.get('FROTA_PRECO')
    limite = current_app.config.get('FROTA_LIMITE')
    if valor and limite is not None:
        try:
            preco = Decimal(str(valor))
            if (not preco.is_finite() or not 0 < preco <= Decimal('9999999999.99')
                    or preco != preco.quantize(Decimal('0.01'))
                    or type(limite) is not int or limite < 0):
                raise ValueError()
        except (ValueError, InvalidOperation):
            current_app.logger.warning('Venda Frota desabilitada: configuração comercial inválida.')
        else:
            planos['frota'] = {'nome': 'Frota', 'valor': preco, 'limite': limite}
    return planos


def plano_efetivo(user, hoje=None):
    hoje = hoje or date.today()
    if user.plano == 'superadmin':
        return 'superadmin'
    assinaturas = Assinatura.query.filter_by(user_id=user.id).order_by(Assinatura.id.desc()).all()
    for assinatura in assinaturas:
        if assinatura.status in ('ativo', 'cancelado', 'suspenso', 'expirado', 'trial') and assinatura.data_renovacao and assinatura.data_renovacao > hoje:
            return assinatura.plano
    # Planos administrados anteriormente por script não são revogados por esta entrega.
    if not assinaturas:
        return user.plano or 'free'
    return 'free'


def iniciar_trial(user):
    if user.plano == 'free' and not Assinatura.query.filter_by(user_id=user.id).first():
        db.session.add(Assinatura(user_id=user.id, plano='pro', status='trial', valor=0,
            data_inicio=date.today(), data_renovacao=date.today() + timedelta(days=14)))


def asaas(method, recurso, **kwargs):
    config = current_app.config
    token = config.get('ASAAS_API_KEY')
    if not token:
        raise GatewayIndisponivel('Cobrança ainda não configurada.')
    base = 'https://api.asaas.com/v3' if config.get('ASAAS_ENV') == 'production' else 'https://api-sandbox.asaas.com/v3'
    try:
        response = requests.request(method, base + recurso,
            headers={'access_token': token, 'User-Agent': 'AUTOVIU/1.0'}, timeout=(5, 20),
            allow_redirects=False, **kwargs)
        response.raise_for_status()
        dados = response.json()
        if not isinstance(dados, dict):
            raise ValueError('Resposta inesperada')
        return dados
    except requests.HTTPError as erro:
        if erro.response is not None and erro.response.status_code in (400, 401, 403, 404, 422):
            raise GatewayRequisicaoRejeitada('A solicitação não foi aceita pelo serviço de pagamentos. Confira os dados ou tente novamente mais tarde.', erro.response.status_code) from None
        raise GatewayIndisponivel('Não foi possível confirmar a operação de cobrança. Atualize a situação antes de tentar novamente.') from None
    except (requests.RequestException, ValueError):
        raise GatewayIndisponivel('Não foi possível consultar a cobrança. Tente novamente mais tarde.') from None


def url_fatura(valor):
    if not isinstance(valor, str) or len(valor) > 500:
        return None
    url = urlsplit(valor)
    if url.scheme == 'https' and url.hostname in ('www.asaas.com', 'asaas.com', 'sandbox.asaas.com', 'www.sandbox.asaas.com') and not url.username and not url.password:
        return valor
    return None


def criar_assinatura(user, plano, cpf, forma):
    if not current_app.config.get('ASAAS_API_KEY'):
        raise GatewayIndisponivel('Cobrança ainda não configurada.')
    planos = catalogo()
    if plano not in planos or plano == 'free' or forma not in ('UNDEFINED', 'PIX', 'BOLETO'):
        raise ValueError('Plano ou forma de pagamento inválidos.')
    if user.plano == 'superadmin':
        raise ValueError('Conta administrativa não precisa contratar assinatura.')
    User.query.filter_by(id=user.id).with_for_update().one()
    existente = Assinatura.query.filter(Assinatura.user_id == user.id,
        Assinatura.status.in_(('pendente', 'criando', 'incerta', 'ativo', 'suspenso')),
        Assinatura.gateway_id.isnot(None)).order_by(Assinatura.id.desc()).with_for_update().first()
    if existente:
        raise ValueError('Já existe uma assinatura. Use o histórico ou a alteração de plano.')
    if Assinatura.query.filter(Assinatura.user_id == user.id, Assinatura.status.in_(('criando', 'incerta'))).with_for_update().first():
        raise ValueError('A contratação anterior está em conciliação. Não repita a cobrança.')
    assinatura = Assinatura(user_id=user.id, plano=plano, status='criando', valor=planos[plano]['valor'], data_inicio=date.today())
    db.session.add(assinatura)
    db.session.commit()
    referencia = 'autoviu:' + str(user.id)
    try:
        conta = db.session.get(ContaCobranca, user.id)
        if conta is None:
            conta = ContaCobranca(user_id=user.id)
            db.session.add(conta)
        if not conta.customer_id:
            clientes = asaas('GET', '/customers', params={'externalReference': referencia}).get('data', [])
            cliente = clientes[0] if clientes else asaas('POST', '/customers', json={
                'name': user.nome, 'email': user.email, 'cpfCnpj': cpf, 'externalReference': referencia,
                'notificationDisabled': True})
            conta.customer_id = cliente['id']
            db.session.commit()
        resultado = asaas('POST', '/subscriptions', json={
            'customer': conta.customer_id, 'billingType': forma, 'value': float(assinatura.valor),
            'nextDueDate': date.today().isoformat(), 'cycle': 'MONTHLY',
            'description': 'ΛUTOVIU — ' + planos[plano]['nome'],
            'externalReference': 'autoviu-assinatura:' + str(assinatura.id)})
        assinatura.gateway_id = resultado['id']
        assinatura.status = 'pendente'
        db.session.commit()
        conciliar_assinatura(assinatura.id, user.id)
        return assinatura
    except Exception as erro:
        db.session.rollback()
        assinatura = db.session.get(Assinatura, assinatura.id)
        if not assinatura.gateway_id:
            assinatura.status = 'rejeitado' if isinstance(erro, GatewayRequisicaoRejeitada) else 'incerta'
            db.session.commit()
        current_app.logger.warning('Contratação %s não concluída: %s', assinatura.id, type(erro).__name__)
        if assinatura.status == 'rejeitado':
            raise GatewayIndisponivel('A contratação não foi concluída e nenhuma assinatura foi confirmada. Confira os dados e tente novamente mais tarde.') from None
        raise GatewayIndisponivel('A contratação está aguardando confirmação do gateway. Consulte o histórico antes de tentar novamente.') from None


def sincronizar_fatura(assinatura, pagamento, recalcular=True):
    if pagamento.get('subscription') != assinatura.gateway_id:
        raise ValueError('Cobrança não pertence à assinatura.')
    valor = Decimal(str(pagamento['value']))
    fatura = Fatura.query.filter_by(gateway_id=pagamento['id']).first()
    if valor not in (assinatura.valor, assinatura.valor_solicitado, fatura.valor if fatura else None):
        raise ValueError('Valor da cobrança divergente.')
    if fatura is None:
        fatura = Fatura(assinatura_id=assinatura.id, gateway_id=pagamento['id'],
            plano=assinatura.plano_solicitado if assinatura.plano_solicitado and valor == assinatura.valor_solicitado else assinatura.plano)
        db.session.add(fatura)
    elif fatura.assinatura_id != assinatura.id:
        raise ValueError('Identificador de cobrança já utilizado.')
    fatura.valor = valor
    fatura.status = 'CANCELED' if pagamento.get('deleted') else pagamento['status']
    fatura.vencimento = date.fromisoformat(pagamento['dueDate'])
    confirmacao = pagamento.get('confirmedDate') or pagamento.get('paymentDate')
    fatura.confirmacao = date.fromisoformat(confirmacao[:10]) if confirmacao else None
    fatura.url = None if fatura.status == 'CANCELED' else url_fatura(pagamento.get('invoiceUrl'))
    db.session.flush()
    if recalcular:
        _recalcular_assinatura(assinatura)


def _recalcular_assinatura(assinatura):
    pagas = Fatura.query.filter(Fatura.assinatura_id == assinatura.id, Fatura.status.in_(PAGOS)).all()
    if pagas:
        recente = max(pagas, key=lambda f: f.vencimento)
        ano, mes = recente.vencimento.year, recente.vencimento.month + 1
        if mes == 13:
            ano, mes = ano + 1, 1
        assinatura.data_renovacao = date(ano, mes, min(recente.vencimento.day, calendar.monthrange(ano, mes)[1]))
        if assinatura.plano_solicitado and recente.valor == assinatura.valor_solicitado:
            assinatura.plano = assinatura.plano_solicitado
            assinatura.valor = assinatura.valor_solicitado
            assinatura.plano_solicitado = None
            assinatura.valor_solicitado = None
        assinatura.plano = recente.plano
        if assinatura.status not in ('cancelado', 'suspenso', 'expirado'):
            assinatura.status = 'ativo'
        user = db.session.get(User, assinatura.user_id)
        if user.plano != 'superadmin' and assinatura.data_renovacao > date.today():
            user.plano = assinatura.plano
    else:
        assinatura.data_renovacao = None
        if assinatura.status not in ('cancelado', 'suspenso', 'expirado'):
            assinatura.status = 'pendente'


def _listar_assinatura_remota(assinatura):
    referencia = 'autoviu-assinatura:' + str(assinatura.id)
    resposta = asaas('GET', '/subscriptions', params={
        'externalReference': referencia, 'includeDeleted': 'true', 'limit': 100})
    registros = resposta.get('data')
    if not isinstance(registros, list):
        raise GatewayIndisponivel('Resposta de conciliação inválida. Tente novamente mais tarde.')
    encontrados = [item for item in registros if isinstance(item, dict)
                   and item.get('externalReference') == referencia
                   and (not assinatura.gateway_id or item.get('id') == assinatura.gateway_id)]
    if not encontrados:
        raise GatewayIndisponivel('A contratação ainda não foi localizada. Não repita a cobrança; aguarde a conciliação.')
    if len(encontrados) != 1 or resposta.get('hasMore'):
        raise GatewayIndisponivel('A contratação exige revisão administrativa antes de continuar.')
    remoto = encontrados[0]
    conta = db.session.get(ContaCobranca, assinatura.user_id)
    if not conta or not conta.customer_id or remoto.get('customer') != conta.customer_id:
        raise GatewayIndisponivel('Não foi possível confirmar o pagador da assinatura.')
    return remoto


def consultar_assinatura_remota(assinatura):
    if not assinatura.gateway_id:
        return _listar_assinatura_remota(assinatura)
    try:
        remoto = asaas('GET', '/subscriptions/' + assinatura.gateway_id)
    except GatewayRequisicaoRejeitada as erro:
        if erro.status_code != 404:
            raise
        # A listagem com includeDeleted permite localizar uma recorrência removida.
        remoto = _listar_assinatura_remota(assinatura)
    if not isinstance(remoto, dict) or remoto.get('id') != assinatura.gateway_id:
        raise GatewayIndisponivel('Resposta de conciliação inválida.')
    conta = db.session.get(ContaCobranca, assinatura.user_id)
    if conta and conta.customer_id and remoto.get('customer') != conta.customer_id:
        raise GatewayIndisponivel('Não foi possível confirmar o pagador da assinatura.')
    return remoto


def conciliar_assinatura(assinatura_id, user_id):
    """Consulta o gateway e atualiza apenas a assinatura do proprietário informado."""
    assinatura = Assinatura.query.filter_by(id=assinatura_id, user_id=user_id).with_for_update().first()
    if assinatura is None:
        raise ValueError('Assinatura não encontrada.')
    if assinatura.status == 'trial':
        return assinatura
    remoto = consultar_assinatura_remota(assinatura)
    if not assinatura.gateway_id:
        assinatura.gateway_id = remoto['id']
        assinatura.status = 'pendente'
    situacao_remota = ('cancelado' if remoto.get('deleted') else
                       'suspenso' if remoto.get('status') == 'INACTIVE' else
                       'expirado' if remoto.get('status') == 'EXPIRED' else None)
    if situacao_remota:
        assinatura.status = situacao_remota
        assinatura.plano_solicitado = None
        assinatura.valor_solicitado = None
    elif remoto.get('status') == 'ACTIVE' and assinatura.status in ('suspenso', 'expirado'):
        assinatura.status = 'pendente'
    offset = 0
    for _ in range(100):
        resposta = asaas('GET', '/subscriptions/' + assinatura.gateway_id + '/payments',
                        params={'offset': offset, 'limit': 100})
        pagamentos = resposta.get('data')
        if not isinstance(pagamentos, list):
            raise GatewayIndisponivel('Não foi possível obter o histórico completo.')
        for pagamento in pagamentos:
            if not isinstance(pagamento, dict):
                raise GatewayIndisponivel('O gateway retornou uma cobrança inválida.')
            sincronizar_fatura(assinatura, pagamento, recalcular=False)
        if not resposta.get('hasMore'):
            break
        if not pagamentos:
            raise GatewayIndisponivel('O histórico retornou uma página incompleta. Tente novamente.')
        offset += len(pagamentos)
    else:
        raise GatewayIndisponivel('O histórico excede o limite desta atualização. Solicite revisão administrativa.')
    if remoto.get('deleted'):
        _cancelar_faturas_pendentes(assinatura)
    _recalcular_assinatura(assinatura)
    db.session.commit()
    return assinatura


def _cancelar_faturas_pendentes(assinatura):
    Fatura.query.filter(Fatura.assinatura_id == assinatura.id,
                       Fatura.status.in_(('PENDING', 'OVERDUE'))).update(
        {'status': 'CANCELED', 'url': None}, synchronize_session='fetch')
    db.session.flush()


def cancelar_assinatura(assinatura):
    if assinatura.status == 'cancelado':
        return
    if assinatura.status in ('criando', 'incerta') and not assinatura.gateway_id:
        raise ValueError('Atualize a contratação antes de cancelar. O resultado anterior ainda não foi confirmado.')
    if assinatura.gateway_id:
        resultado = asaas('DELETE', '/subscriptions/' + assinatura.gateway_id)
        if not isinstance(resultado, dict) or resultado.get('deleted') is not True:
            raise GatewayIndisponivel('O cancelamento ainda não foi confirmado. Atualize a assinatura antes de tentar novamente.')
        _cancelar_faturas_pendentes(assinatura)
    assinatura.status = 'cancelado'
    assinatura.plano_solicitado = None
    assinatura.valor_solicitado = None


def reconciliar_pendentes():
    total = 0
    registros = db.session.query(Assinatura.id, Assinatura.user_id).filter(
        Assinatura.status.in_(('criando', 'incerta', 'pendente', 'ativo', 'cancelado', 'suspenso', 'expirado'))).all()
    for assinatura_id, user_id in registros:
        try:
            conciliar_assinatura(assinatura_id, user_id)
            total += 1
        except (GatewayIndisponivel, ValueError, KeyError, TypeError, InvalidOperation) as erro:
            db.session.rollback()
            current_app.logger.warning('Falha na conciliação de assinatura %s: %s',
                                       assinatura_id, type(erro).__name__)
    return total
