import json
from datetime import date
from urllib.parse import urlsplit

from flask import current_app
from sqlalchemy.exc import IntegrityError
from extensions import db
from services.plano_service import tem_plano
from models import (User, Condutor, Veiculo, Manutencao, PreferenciaAlerta,
                    PushSubscription, EnvioAlerta)


def listar_alertas(user_id, hoje=None):
    hoje = hoje or date.today()
    alertas = []
    def adicionar(chave, titulo, texto, prioridade='atenção', destino=None, veiculo_id=None):
        alertas.append(dict(chave=chave, titulo=titulo, texto=texto,
                            prioridade=prioridade, destino=destino, veiculo_id=veiculo_id))
    def vencimento(tipo, ident, prazo, titulo, janelas=(30,), veiculo_id=None):
        if prazo is None:
            return
        dias = (prazo - hoje).days
        if dias <= max(janelas):
            janela = 'vencido' if dias < 0 else str(min(j for j in janelas if dias <= j))
            texto = 'Vencido em ' if dias < 0 else ('Vence hoje: ' if dias == 0 else 'Vence em ')
            if dias > 0:
                texto += f'{dias} dia(s), em '
            adicionar(f'{tipo}:{ident}:{prazo}:{janela}', titulo, texto + prazo.strftime('%d/%m/%Y'),
                      'urgente' if dias <= 0 else 'atenção',
                      'veiculo' if veiculo_id else 'condutor', veiculo_id)
    condutor = Condutor.query.filter_by(user_id=user_id).first()
    if condutor:
        vencimento('cnh', condutor.id, condutor.cnh_validade, 'Validade da CNH', (30, 60))
    veiculos = Veiculo.query.filter_by(user_id=user_id, ativo=True).all()
    # Uma consulta para a agenda dos veículos do proprietário, em vez de uma por veículo.
    agendas = {}
    ids = [v.id for v in veiculos]
    if ids:
        for manutencao in Manutencao.query.filter(
                Manutencao.veiculo_id.in_(ids), Manutencao.status != 'realizada').all():
            agendas.setdefault(manutencao.veiculo_id, []).append(manutencao)
    for veiculo in veiculos:
        nome = f'{veiculo.marca} {veiculo.modelo}'
        vencimento('crlv', veiculo.id, veiculo.crlv_validade, 'Licenciamento — ' + nome, veiculo_id=veiculo.id)
        vencimento('seguro', veiculo.id, veiculo.seguro_validade, 'Seguro — ' + nome, veiculo_id=veiculo.id)
        if hoje.month == 1:
            texto = 'Confira o calendário e os valores oficiais do seu estado.'
            if veiculo.valor_atual:
                texto += ' Valor estimado do veículo: R$ ' + f'{veiculo.valor_atual:.2f}'
            adicionar(f'ipva:{veiculo.id}:{hoje.year}', 'Planeje o IPVA — ' + nome, texto,
                      'informativo', 'veiculo', veiculo.id)
        for manutencao in agendas.get(veiculo.id, []):
            atingido = manutencao.km_previsto is not None and (veiculo.km_atual or 0) >= manutencao.km_previsto
            proximo = manutencao.data_prevista and (manutencao.data_prevista - hoje).days <= 30
            if atingido or proximo:
                detalhes = [manutencao.descricao or manutencao.tipo or 'Revisão programada.']
                if manutencao.data_prevista:
                    dias = (manutencao.data_prevista - hoje).days
                    prazo = manutencao.data_prevista.strftime('%d/%m/%Y')
                    detalhes.append(f'Data prevista: {prazo}.' + (
                        f' Atrasada há {-dias} dia(s).' if dias < 0 else
                        ' Prazo hoje.' if dias == 0 else f' Faltam {dias} dia(s).'))
                if manutencao.km_previsto is not None:
                    restante = manutencao.km_previsto - (veiculo.km_atual or 0)
                    detalhes.append(f'Quilometragem prevista: {manutencao.km_previsto:,} km.'.replace(',', '.') + (
                        f' Limite ultrapassado em {-restante:,} km.'.replace(',', '.') if restante < 0 else
                        ' Quilometragem atingida.' if restante == 0 else
                        f' Faltam {restante:,} km.'.replace(',', '.')))
                adicionar(f'manutencao:{manutencao.id}:{manutencao.km_previsto}:{manutencao.data_prevista}',
                          'Revisão — ' + nome, ' '.join(detalhes),
                          'urgente' if atingido or (proximo and manutencao.data_prevista <= hoje) else 'atenção',
                          'agenda', veiculo.id)
    ordem = {'urgente': 0, 'atenção': 1, 'informativo': 2}
    return sorted(alertas, key=lambda alerta: ordem[alerta['prioridade']])


def validar_subscription(dados):
    if not isinstance(dados, dict):
        raise ValueError('Assinatura push inválida.')
    endpoint = dados.get('endpoint', '')
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        raise ValueError('Endpoint push inválido.')
    url = urlsplit(endpoint)
    hosts = ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com')
    if url.scheme != 'https' or url.hostname not in hosts or url.username or url.password or url.port not in (None, 443):
        raise ValueError('Serviço de push não suportado.')
    keys = dados.get('keys', {})
    if not isinstance(keys, dict) or any(not isinstance(keys.get(k), str) or not 16 <= len(keys[k]) <= 200 for k in ('p256dh', 'auth')):
        raise ValueError('Chaves de push inválidas.')
    return {'endpoint': endpoint, 'keys': {k: keys[k] for k in ('p256dh', 'auth')}}


def processar_alertas():
    from services.email_service import enviar_email
    from pywebpush import webpush, WebPushException
    enviados = 0
    for user in User.query.filter_by(ativo=True, status='ativo').all():
        preferencia = db.session.get(PreferenciaAlerta, user.id)
        subscriptions = PushSubscription.query.filter_by(user_id=user.id).all()
        for alerta in listar_alertas(user.id):
            canais = ['email'] if preferencia and preferencia.email and user.email_confirmado and tem_plano(user, 'pro') else []
            if subscriptions and current_app.config.get('VAPID_PRIVATE_KEY'):
                canais.append('push')
            for canal in canais:
                envio = EnvioAlerta(user_id=user.id, chave=alerta['chave'], canal=canal)
                db.session.add(envio)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    continue
                try:
                    entregas = 0
                    if canal == 'email':
                        enviar_email(user.email, alerta['titulo'] + ' — AUTOVIU', alerta['texto'])
                        entregas = 1
                    else:
                        for sub in subscriptions[:]:
                            try:
                                # Nunca colocar dados de CNH/CPF na tela bloqueada.
                                webpush(subscription_info=sub.dados,
                                    data=json.dumps({'title': 'AUTOVIU', 'body': 'Você tem alertas para revisar no aplicativo.'}),
                                    vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
                                    vapid_claims={'sub': current_app.config['VAPID_SUBJECT']}, timeout=10)
                                entregas += 1
                            except WebPushException as erro:
                                if erro.response is not None and erro.response.status_code in (404, 410):
                                    db.session.delete(sub)
                                    subscriptions.remove(sub)
                                else:
                                    raise
                    envio.status = 'enviado' if entregas else 'sem_destino'
                    if entregas:
                        enviados += 1
                except Exception as erro:
                    envio.status = 'falhou'
                    current_app.logger.error('Falha no envio de alerta: %s', type(erro).__name__)
                db.session.commit()
    return enviados
