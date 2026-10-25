import secrets
from datetime import datetime
from flask import Blueprint, current_app, redirect, url_for, flash, session
from flask_login import login_user, current_user, login_fresh
from sqlalchemy.exc import IntegrityError
from authlib.integrations.flask_client import OAuth
from extensions import db, limiter
from models import User
from services.public_url import public_base_url
from services.cadastro_service import destino_inicial

google_bp = Blueprint('google', __name__)
oauth = OAuth()


def init_google(app):
    oauth.init_app(app)
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register('google', client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile', 'timeout': 10})


@google_bp.route('/google')
@limiter.limit('20/hour')
def login():
    if not current_app.config.get('GOOGLE_CLIENT_ID') or not current_app.config.get('GOOGLE_CLIENT_SECRET'):
        flash('Login com Google ainda não configurado.', 'info')
        return redirect(url_for('auth.login'))
    try:
        callback = public_base_url() + '/auth/google/callback'
        return oauth.google.authorize_redirect(callback)
    except Exception:
        current_app.logger.warning('Não foi possível iniciar autenticação Google')
        flash('Não foi possível acessar o Google. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))


@google_bp.route('/google/callback')
@limiter.limit('30/hour')
def callback():
    try:
        # Authlib valida state, nonce, emissor, assinatura, expiração e audience do ID token.
        token = oauth.google.authorize_access_token()
        dados = token.get('userinfo')
        if not dados or dados.get('email_verified') is not True:
            raise ValueError('E-mail não verificado')
        subject = dados.get('sub')
        email = str(dados.get('email', '')).strip().lower()
        if not isinstance(subject, str) or not subject or len(subject) > 100 or not email or len(email) > 120:
            raise ValueError('Identidade inválida')
        novo = False
        user = User.query.filter_by(google_id=subject).first()
        if user is None:
            user = User.query.filter_by(email=email).first()
            if user is not None:
                # Em contas existentes, exige posse da conta local antes de vincular.
                if not current_user.is_authenticated or current_user.id != user.id or user.google_id:
                    flash('Entre com sua senha e use Vincular Google em Segurança para conectar esta conta.', 'info')
                    return redirect(url_for('auth.login'))
                if not login_fresh():
                    return redirect(url_for('auth.reautenticar', next='/auth/google'))
                user.google_id = subject
            else:
                user = User(email=email, nome=str(dados.get('name') or email)[:100], password_hash='',
                            google_id=subject, plano='free', status='ativo', ativo=True, email_confirmado=True)
                db.session.add(user)
                db.session.flush()
                novo = True
        if not user.ativo or user.status not in ('ativo', 'pendente'):
            raise ValueError('Conta indisponível')
        if current_user.is_authenticated and current_user.id != user.id:
            raise ValueError('Identidade diferente da sessão atual')
        user.email_confirmado = True
        if user.status == 'pendente':
            user.status = 'ativo'
        picture = str(dados.get('picture') or '')
        user.avatar_url = picture[:300] if picture.startswith('https://') else None
        user.last_login_at = datetime.utcnow()
        if novo:
            from services.assinatura_service import iniciar_trial
            iniciar_trial(user)
        db.session.commit()
        session.pop('veiculo_ativo_id', None)
        login_user(user, fresh=True)
        return redirect(destino_inicial(user))
    except Exception as erro:
        db.session.rollback()
        current_app.logger.warning('Falha na autenticação Google: %s', type(erro).__name__)
        flash('Não foi possível autenticar com Google. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))
