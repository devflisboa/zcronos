import hashlib
import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from flask import Blueprint, render_template, request, jsonify, session, current_app, abort
from flask_login import current_user, login_user, login_required, fresh_login_required
from sqlalchemy.exc import IntegrityError
from webauthn import (generate_registration_options, generate_authentication_options,
    verify_registration_response, verify_authentication_response, options_to_json, base64url_to_bytes)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, ResidentKeyRequirement,
    UserVerificationRequirement, PublicKeyCredentialDescriptor)
from extensions import db, limiter
from models import User, WebAuthnCredential, WebAuthnDesafio
from services.cadastro_service import destino_inicial

seguranca_bp = Blueprint('seguranca', __name__)


def parametros():
    origem = current_app.config.get('WEBAUTHN_ORIGIN', '')
    rp = current_app.config.get('WEBAUTHN_RP_ID', '')
    parsed = urlsplit(origem)
    if parsed.scheme != 'https' or not rp or not parsed.hostname or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username or parsed.password or not (parsed.hostname == rp or parsed.hostname.endswith('.' + rp)):
        abort(503, description='Passkeys aguardam configuração HTTPS do domínio.')
    return rp, origem.rstrip('/')


def criar_desafio(tipo, challenge, user_id=None):
    agora = datetime.utcnow()
    WebAuthnDesafio.query.filter(WebAuthnDesafio.expira_em < agora).delete()
    ident = secrets.token_hex(32)
    db.session.add(WebAuthnDesafio(id=ident, tipo=tipo, challenge=challenge,
        user_id=user_id, expira_em=agora + timedelta(seconds=60), consumido=False))
    db.session.commit()
    session['webauthn_' + tipo] = ident


def consumir_desafio(tipo):
    ident = session.pop('webauthn_' + tipo, None)
    query = WebAuthnDesafio.query.filter_by(id=ident, tipo=tipo, consumido=False)
    if tipo == 'registro':
        query = query.filter_by(user_id=current_user.id)
    desafio = query.filter(WebAuthnDesafio.expira_em >= datetime.utcnow()).first()
    if not desafio:
        raise ValueError('Desafio expirado ou já utilizado. Inicie novamente.')
    challenge = desafio.challenge
    if query.filter(WebAuthnDesafio.expira_em >= datetime.utcnow()).update({'consumido': True}, synchronize_session=False) != 1:
        db.session.rollback()
        raise ValueError('Desafio já utilizado.')
    db.session.commit()
    return challenge


@seguranca_bp.route('/seguranca')
@login_required
def index():
    return render_template('auth/seguranca.html', credenciais=WebAuthnCredential.query.filter_by(user_id=current_user.id).all())


@seguranca_bp.route('/webauthn/register/begin', methods=['POST'])
@fresh_login_required
@limiter.limit('10/hour', key_func=lambda: str(current_user.id))
def registro_inicio():
    rp, _ = parametros()
    existentes = WebAuthnCredential.query.filter_by(user_id=current_user.id).all()
    if len(existentes) >= 10:
        return jsonify(erro='Limite de 10 dispositivos atingido.'), 400
    options = generate_registration_options(rp_id=rp, rp_name='AUTOVIU',
        user_id=str(current_user.id).encode(), user_name=current_user.email,
        user_display_name=current_user.nome, timeout=60000,
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existentes],
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED))
    criar_desafio('registro', options.challenge, current_user.id)
    return jsonify(json.loads(options_to_json(options)))


@seguranca_bp.route('/webauthn/register/finish', methods=['POST'])
@fresh_login_required
@limiter.limit('10/hour', key_func=lambda: str(current_user.id))
def registro_fim():
    rp, origem = parametros()
    try:
        challenge = consumir_desafio('registro')
        dados = request.get_json(silent=True) or {}
        if not isinstance(dados, dict):
            raise ValueError('JSON inválido')
        nome = dados.get('nome', 'Meu dispositivo')
        if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 100:
            raise ValueError('Nome de dispositivo inválido.')
        verificado = verify_registration_response(credential=dados.get('credential', {}),
            expected_challenge=challenge, expected_rp_id=rp, expected_origin=origem, require_user_verification=True)
        # Bloqueia o usuário para serializar inclusão concorrente de credenciais.
        User.query.filter_by(id=current_user.id).with_for_update().one()
        if len(WebAuthnCredential.query.filter_by(user_id=current_user.id).with_for_update().all()) >= 10:
            raise ValueError('Limite de dispositivos atingido.')
        cid = bytes_to_base64url(verificado.credential_id)
        db.session.add(WebAuthnCredential(user_id=current_user.id, credential_id=cid,
            credential_hash=hashlib.sha256(verificado.credential_id).hexdigest(),
            public_key=verificado.credential_public_key, sign_count=verificado.sign_count, device_name=nome.strip()))
        db.session.commit()
        return jsonify(ok=True)
    except Exception:
        db.session.rollback()
        return jsonify(erro='Não foi possível registrar a passkey. Inicie novamente.'), 400


@seguranca_bp.route('/webauthn/login/begin', methods=['POST'])
@limiter.limit('10/minute')
def login_inicio():
    rp, _ = parametros()
    options = generate_authentication_options(rp_id=rp, timeout=60000,
        user_verification=UserVerificationRequirement.REQUIRED)
    criar_desafio('login', options.challenge)
    return jsonify(json.loads(options_to_json(options)))


@seguranca_bp.route('/webauthn/login/finish', methods=['POST'])
@limiter.limit('10/minute')
def login_fim():
    rp, origem = parametros()
    try:
        challenge = consumir_desafio('login')
        dados = request.get_json(silent=True) or {}
        if not isinstance(dados, dict):
            raise ValueError('JSON inválido')
        cid = base64url_to_bytes(dados.get('id', ''))
        credencial = WebAuthnCredential.query.filter_by(credential_hash=hashlib.sha256(cid).hexdigest()).with_for_update().first()
        if credencial is None:
            raise ValueError('Credencial desconhecida')
        user = db.session.get(User, credencial.user_id)
        if not user or not user.ativo or user.status != 'ativo':
            raise ValueError('Conta indisponível')
        user_handle = (dados.get('response') or {}).get('userHandle')
        if user_handle and base64url_to_bytes(user_handle) != str(user.id).encode():
            raise ValueError('Usuário divergente')
        verificado = verify_authentication_response(credential=dados, expected_challenge=challenge,
            expected_rp_id=rp, expected_origin=origem, credential_public_key=credencial.public_key,
            credential_current_sign_count=credencial.sign_count, require_user_verification=True)
        credencial.sign_count = verificado.new_sign_count
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        session.pop('veiculo_ativo_id', None)
        login_user(user, fresh=True)
        return jsonify(ok=True, destino=destino_inicial(user))
    except Exception:
        db.session.rollback()
        return jsonify(erro='Não foi possível autenticar com esta passkey. Tente novamente ou use sua senha.'), 400


@seguranca_bp.route('/webauthn/<int:id>/remover', methods=['POST'])
@fresh_login_required
@limiter.limit('10/hour', key_func=lambda: str(current_user.id))
def remover(id):
    credencial = WebAuthnCredential.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    dados = request.get_json(silent=True) or {}
    if not isinstance(dados, dict):
        return jsonify(erro='Envie um objeto JSON válido.'), 400
    if not current_user.check_password(dados.get('senha', '')):
        return jsonify(erro='Confirme a senha atual para remover o dispositivo.'), 400
    db.session.delete(credencial)
    db.session.commit()
    return jsonify(ok=True)
