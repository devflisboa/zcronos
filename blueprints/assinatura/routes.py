import hmac
import re
from datetime import date
from decimal import InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, abort
from flask_login import current_user, login_required, fresh_login_required
from sqlalchemy import func, extract
from sqlalchemy.exc import IntegrityError
from extensions import db, csrf, limiter
from models import User, Assinatura, Fatura, EventoGateway
from services.condutor_service import validar_cpf
from services.assinatura_service import (catalogo, criar_assinatura, sincronizar_fatura,
    asaas, GatewayIndisponivel, PAGOS, conciliar_assinatura, cancelar_assinatura,
    consultar_assinatura_remota, STATUS_ASSINATURA, STATUS_FATURA)

assinatura_bp = Blueprint('assinatura', __name__)


@assinatura_bp.route('/plano')
@login_required
def planos():
    assinaturas = Assinatura.query.filter_by(user_id=current_user.id).order_by(Assinatura.id.desc()).all()
    ids = [a.id for a in assinaturas]
    faturas = Fatura.query.filter(Fatura.assinatura_id.in_(ids)).order_by(Fatura.vencimento.desc()).all() if ids else []
    return render_template('assinatura/planos.html', planos=catalogo(), assinaturas=assinaturas,
        faturas=faturas, atual=current_user.plano_efetivo, hoje=date.today(),
        status_assinatura=STATUS_ASSINATURA, status_fatura=STATUS_FATURA,
        tem_recorrencia=any(a.status in ('criando', 'incerta', 'pendente', 'ativo', 'suspenso') for a in assinaturas),
        configurado=bool(current_app.config.get('ASAAS_API_KEY')))


@assinatura_bp.route('/plano/<int:id>/atualizar', methods=['POST'])
@login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def atualizar(id):
    Assinatura.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    try:
        conciliar_assinatura(id, current_user.id)
        flash('Assinatura e faturas atualizadas com o gateway.', 'success')
    except (GatewayIndisponivel, ValueError, KeyError, TypeError, InvalidOperation) as erro:
        db.session.rollback()
        current_app.logger.warning('Falha na atualização de assinatura %s: %s', id, type(erro).__name__)
        flash(str(erro) if isinstance(erro, GatewayIndisponivel) else 'Não foi possível atualizar a assinatura. Tente novamente mais tarde.', 'danger')
    return redirect(url_for('assinatura.planos'))


@assinatura_bp.route('/plano/contratar', methods=['POST'])
@fresh_login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def contratar():
    try:
        cpf = validar_cpf(request.form.get('cpf'))
        if not cpf:
            raise ValueError('Informe um CPF válido para a cobrança.')
        if request.form.get('aceite') != 'sim':
            raise ValueError('Confirme a contratação recorrente antes de continuar.')
        criar_assinatura(current_user, request.form.get('plano'), cpf, request.form.get('forma', 'UNDEFINED'))
        flash('Assinatura criada. Abra a fatura no histórico para concluir o pagamento.', 'success')
    except (ValueError, GatewayIndisponivel) as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    return redirect(url_for('assinatura.planos'))


@assinatura_bp.route('/plano/<int:id>/alterar', methods=['POST'])
@fresh_login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def alterar(id):
    assinatura = Assinatura.query.filter_by(id=id, user_id=current_user.id, status='ativo').with_for_update().first_or_404()
    plano = request.form.get('plano')
    planos = catalogo()
    if plano not in planos or plano == 'free' or not assinatura.gateway_id:
        abort(400)
    try:
        asaas('PUT', '/subscriptions/' + assinatura.gateway_id,
              json={'value': float(planos[plano]['valor']), 'updatePendingPayments': False})
        assinatura.plano_solicitado = plano
        assinatura.valor_solicitado = planos[plano]['valor']
        db.session.commit()
        flash('Plano agendado para a próxima cobrança gerada pelo gateway. O pagamento confirma a alteração.', 'info')
    except GatewayIndisponivel as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    return redirect(url_for('assinatura.planos'))


@assinatura_bp.route('/plano/<int:id>/cancelar', methods=['POST'])
@fresh_login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def cancelar(id):
    assinatura = Assinatura.query.filter_by(id=id, user_id=current_user.id).with_for_update().first_or_404()
    if request.form.get('confirmar') != 'sim':
        abort(400)
    try:
        cancelar_assinatura(assinatura)
        db.session.commit()
        flash('Recorrência cancelada. O período já pago permanece disponível; seus dados serão preservados.', 'info')
    except (GatewayIndisponivel, ValueError) as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    return redirect(url_for('assinatura.planos'))


@assinatura_bp.route('/webhooks/asaas', methods=['POST'])
@csrf.exempt
@limiter.exempt
def webhook():
    esperado = current_app.config.get('ASAAS_WEBHOOK_TOKEN', '')
    recebido = request.headers.get('asaas-access-token', '')
    if len(esperado) < 32 or not hmac.compare_digest(esperado, recebido):
        abort(401)
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not isinstance(dados.get('id'), str) or not 1 <= len(dados['id']) <= 100:
        return jsonify(erro='Evento inválido.'), 400
    if db.session.get(EventoGateway, dados['id']):
        return jsonify(ok=True)
    evento = dados.get('event', '')
    if not isinstance(evento, str):
        return jsonify(erro='Evento inválido.'), 400
    try:
        if evento.startswith('PAYMENT_'):
            recurso = dados.get('payment')
            if not isinstance(recurso, dict):
                return jsonify(erro='Cobrança inválida.'), 400
            pagamento_id = recurso.get('id', '')
            if not isinstance(pagamento_id, str) or not re.fullmatch(r'pay_[A-Za-z0-9]+', pagamento_id):
                return jsonify(erro='Cobrança inválida.'), 400
            # O payload não decide liberação de acesso. Consulta autenticada traz o estado atual.
            pagamento = asaas('GET', '/payments/' + pagamento_id)
            assinatura = Assinatura.query.filter_by(gateway_id=pagamento.get('subscription')).with_for_update().first() if pagamento.get('subscription') else None
            if assinatura:
                sincronizar_fatura(assinatura, pagamento)
        elif evento in ('SUBSCRIPTION_DELETED', 'SUBSCRIPTION_INACTIVATED'):
            remoto = dados.get('subscription')
            if not isinstance(remoto, dict):
                return jsonify(erro='Assinatura inválida.'), 400
            assinatura = Assinatura.query.filter_by(gateway_id=remoto.get('id')).with_for_update().first() if remoto.get('id') else None
            if assinatura:
                estado = consultar_assinatura_remota(assinatura)
                if estado.get('deleted'):
                    assinatura.status = 'cancelado'
                    Fatura.query.filter(Fatura.assinatura_id == assinatura.id,
                        Fatura.status.in_(('PENDING', 'OVERDUE'))).update(
                        {'status': 'CANCELED', 'url': None}, synchronize_session='fetch')
                elif estado.get('status') == 'INACTIVE':
                    assinatura.status = 'suspenso'
                if assinatura.status in ('cancelado', 'suspenso'):
                    assinatura.plano_solicitado = None
                    assinatura.valor_solicitado = None
        db.session.add(EventoGateway(id=dados['id']))
        db.session.commit()
        return jsonify(ok=True)
    except IntegrityError:
        db.session.rollback()
        if db.session.get(EventoGateway, dados['id']):
            return jsonify(ok=True)
        return jsonify(erro='Evento aguardando processamento.'), 503
    except (GatewayIndisponivel, ValueError, KeyError, TypeError, InvalidOperation):
        db.session.rollback()
        current_app.logger.warning('Falha na conciliação de evento de cobrança')
        return jsonify(erro='Evento aguardando conciliação.'), 503


@assinatura_bp.route('/admin/assinaturas')
@login_required
def admin():
    if current_user.plano != 'superadmin':
        abort(403)
    hoje = date.today()
    receita = db.session.query(func.sum(Fatura.valor)).filter(Fatura.status.in_(PAGOS),
        extract('year', Fatura.confirmacao) == hoje.year, extract('month', Fatura.confirmacao) == hoje.month).scalar() or 0
    page = max(1, request.args.get('page', 1, type=int))
    usuarios = User.query.order_by(User.id).paginate(page=page, per_page=50, error_out=False)
    pendentes = db.session.query(Assinatura, User.nome).join(User, Assinatura.user_id == User.id).filter(
        Assinatura.status.in_(('criando', 'incerta', 'pendente'))).order_by(Assinatura.id.desc()).limit(20).all()
    return render_template('assinatura/admin.html', usuarios=usuarios, receita=receita,
                           pendentes=pendentes, status_assinatura=STATUS_ASSINATURA)


@assinatura_bp.route('/admin/assinaturas/<int:id>/atualizar', methods=['POST'])
@fresh_login_required
@limiter.limit('10/hour', key_func=lambda: str(current_user.id))
def admin_atualizar(id):
    if current_user.plano != 'superadmin':
        abort(403)
    assinatura = db.session.get(Assinatura, id)
    if assinatura is None:
        abort(404)
    try:
        conciliar_assinatura(assinatura.id, assinatura.user_id)
        flash('Contratação conciliada com o gateway.', 'success')
    except (GatewayIndisponivel, ValueError, KeyError, TypeError, InvalidOperation) as erro:
        db.session.rollback()
        current_app.logger.warning('Falha na conciliação administrativa %s: %s', id, type(erro).__name__)
        flash(str(erro) if isinstance(erro, GatewayIndisponivel) else 'Não foi possível conciliar esta contratação.', 'danger')
    return redirect(url_for('assinatura.admin'))
