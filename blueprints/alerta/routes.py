import hashlib
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from extensions import db, limiter
from models import PreferenciaAlerta, PushSubscription
from services.plano_service import tem_plano
from services.alerta_service import listar_alertas, validar_subscription

alerta_bp = Blueprint('alerta', __name__)


@alerta_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    preferencia = db.session.get(PreferenciaAlerta, current_user.id)
    if request.method == 'POST':
        if request.form.get('email') == 'sim' and not tem_plano(current_user, 'pro'):
            flash('Alertas por e-mail exigem plano Pro ativo.', 'info')
            return redirect(url_for('assinatura.planos'))
        if preferencia is None:
            preferencia = PreferenciaAlerta(user_id=current_user.id)
            db.session.add(preferencia)
        preferencia.email = request.form.get('email') == 'sim'
        db.session.commit()
        flash('Preferência de alertas salva.', 'success')
        return redirect(url_for('alerta.index'))
    alertas = listar_alertas(current_user.id)
    for alerta in alertas:
        if alerta['destino'] == 'condutor':
            alerta['url'] = url_for('condutor.perfil')
            alerta['acao'] = 'Revisar dados da CNH'
        elif alerta['destino'] == 'veiculo':
            alerta['url'] = url_for('veiculo.editar', id=alerta['veiculo_id'])
            alerta['acao'] = 'Revisar dados do veículo'
        elif alerta['destino'] == 'agenda':
            alerta['url'] = url_for('veiculo.index')
            alerta['acao'] = 'Selecionar veículo para acessar a agenda'
    return render_template('alertas.html', alertas=alertas, preferencia=preferencia,
        vapid_public=current_app.config.get('VAPID_PUBLIC_KEY', ''))


@alerta_bp.route('/push', methods=['POST'])
@login_required
@limiter.limit('20/hour', key_func=lambda: str(current_user.id))
def push():
    if not current_app.config.get('VAPID_PUBLIC_KEY'):
        return jsonify(erro='Push ainda não configurado.'), 503
    try:
        dados = validar_subscription(request.get_json(silent=True))
    except ValueError as erro:
        return jsonify(erro=str(erro)), 400
    chave = hashlib.sha256(dados['endpoint'].encode()).hexdigest()
    sub = PushSubscription.query.filter_by(endpoint_hash=chave).first()
    if sub is not None and sub.user_id != current_user.id:
        return jsonify(erro='Este navegador está vinculado a outra conta. Desative as notificações na conta anterior.'), 409
    if sub is None:
        sub = PushSubscription(user_id=current_user.id, endpoint_hash=chave)
        db.session.add(sub)
    sub.dados = dados
    db.session.commit()
    return jsonify(ok=True)


@alerta_bp.route('/push/remover', methods=['POST'])
@login_required
def remover_push():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(erro='Envie um objeto JSON válido.'), 400
    endpoint = dados.get('endpoint', '')
    if not isinstance(endpoint, str):
        return jsonify(erro='Endpoint inválido.'), 400
    chave = hashlib.sha256(endpoint.encode()).hexdigest()
    PushSubscription.query.filter_by(user_id=current_user.id, endpoint_hash=chave).delete()
    db.session.commit()
    return jsonify(ok=True)
