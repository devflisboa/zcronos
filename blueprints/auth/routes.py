import re
from datetime import datetime
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user, fresh_login_required, confirm_login
from extensions import db, limiter
from models import User, Veiculo
from services.email_service import enviar_confirmacao, ler_token_confirmacao
from services.cadastro_service import destino_inicial

auth_bp = Blueprint('auth', __name__)


@auth_bp.after_request
def proteger_resposta_auth(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute", methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar') == 'on'

        user = User.query.filter_by(email=email, ativo=True).first()

        if user and user.check_password(senha):
            if user.status == 'pendente' and not user.email_confirmado:
                flash('Confirme seu e-mail antes de entrar. Você pode solicitar um novo link.', 'info')
                return redirect(url_for('auth.reenviar_confirmacao'))
            if user.status != 'ativo':
                flash('E-mail ou senha incorretos.', 'danger')
                return render_template('auth/login.html')
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=lembrar)

            veiculo = Veiculo.query.filter_by(user_id=user.id, ativo=True).first()
            if veiculo:
                session['veiculo_ativo_id'] = veiculo.id

            destino = request.args.get('next')
            if not destino or not destino.startswith('/') or destino.startswith('//') or '\\' in destino or urlsplit(destino).netloc:
                destino = destino_inicial(user)
            return redirect(destino)

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('veiculo_ativo_id', None)
    session.pop('cadastro_condutor_pulado', None)
    logout_user()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('auth.login'))


_MENSAGEM_ENVIO = 'Se o endereço estiver apto para confirmação, você receberá um link por e-mail. Verifique também o spam.'


def _enviar_sem_expor_dados(user):
    try:
        enviar_confirmacao(user)
    except Exception as erro:
        # Não registrar endereço, credenciais SMTP ou token.
        current_app.logger.error('Falha no envio de confirmação: %s', type(erro).__name__)


@auth_bp.route('/registro', methods=['GET', 'POST'])
@limiter.limit('5/hour', methods=['POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('veiculo.index'))
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        erro = None
        if not 2 <= len(nome) <= 100:
            erro = 'Informe seu nome com 2 a 100 caracteres.'
        elif len(email) > 120 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or any(c in email for c in '\r\n'):
            erro = 'Informe um e-mail válido com até 120 caracteres.'
        elif not 12 <= len(senha) <= 128 or len(senha.encode('utf-8')) > 72:
            erro = 'Use uma senha com pelo menos 12 caracteres e no máximo 72 bytes.'
        elif senha != request.form.get('confirmar_senha', ''):
            erro = 'As senhas não conferem.'
        if erro:
            flash(erro, 'danger')
            return render_template('auth/registro.html'), 400
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(nome=nome, email=email, plano='free', status='pendente',
                        ativo=True, email_confirmado=False)
            user.set_password(senha)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                user = None
            if user is not None:
                _enviar_sem_expor_dados(user)
        # Cadastro repetido não altera senha nem envia mensagens não solicitadas.
        flash(_MENSAGEM_ENVIO, 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/registro.html')


@auth_bp.route('/confirmar/<token>', methods=['GET', 'POST'])
@limiter.limit('30/hour', methods=['POST'])
def confirmar_email(token):
    dados = ler_token_confirmacao(token)
    user = None
    if isinstance(dados, dict):
        user = User.query.filter_by(id=dados.get('id'), email=dados.get('email'),
                                    ativo=True, status='pendente',
                                    email_confirmado=False).first()
    if user is None:
        flash('Link inválido, expirado ou já utilizado. Solicite um novo link se necessário.', 'info')
        return redirect(url_for('auth.reenviar_confirmacao'))
    if request.method == 'POST':
        user.email_confirmado = True
        user.status = 'ativo'
        from services.assinatura_service import iniciar_trial
        iniciar_trial(user)
        db.session.commit()
        flash('E-mail confirmado! Entre para completar seu cadastro e adicionar o veículo.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/confirmar_email.html', token=token)


@auth_bp.route('/reenviar-confirmacao', methods=['GET', 'POST'])
@limiter.limit('3/hour', methods=['POST'])
def reenviar_confirmacao():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, status='pendente',
                                    email_confirmado=False, ativo=True).first()
        if user is not None:
            _enviar_sem_expor_dados(user)
        flash(_MENSAGEM_ENVIO, 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reenviar_confirmacao.html')


@auth_bp.route('/reautenticar', methods=['GET', 'POST'])
@login_required
@limiter.limit('10/minute', methods=['POST'])
def reautenticar():
    if request.method == 'POST':
        if current_user.check_password(request.form.get('senha', '')):
            confirm_login()
            destino = request.args.get('next', '')
            if not destino.startswith('/') or destino.startswith('//') or '\\' in destino or urlsplit(destino).netloc:
                destino = url_for('seguranca.index')
            return redirect(destino)
        flash('Senha incorreta. Contas sem senha devem autenticar novamente pelo Google.', 'danger')
    return render_template('auth/reautenticar.html')


@auth_bp.route('/senha', methods=['POST'])
@fresh_login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def alterar_senha():
    if not current_user.password_hash:
        flash('Esta conta utiliza Google e não possui senha local.', 'info')
    elif not current_user.check_password(request.form.get('senha_atual', '')):
        flash('Senha atual incorreta.', 'danger')
    else:
        senha = request.form.get('nova_senha', '')
        if len(senha) < 12 or len(senha.encode('utf-8')) > 72 or senha != request.form.get('confirmar_senha'):
            flash('Use senhas iguais, com pelo menos 12 caracteres e até 72 bytes.', 'danger')
        else:
            current_user.set_password(senha)
            db.session.commit()
            login_user(current_user._get_current_object(), fresh=True)
            flash('Senha atualizada.', 'success')
    return redirect(url_for('seguranca.index'))


@auth_bp.route('/recuperar-senha', methods=['GET', 'POST'])
@limiter.limit('3/hour', methods=['POST'])
def recuperar_senha():
    if request.method == 'POST':
        from services.email_service import enviar_recuperacao
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, ativo=True, status='ativo').first()
        if user and user.password_hash:
            try:
                enviar_recuperacao(user)
            except Exception as erro:
                current_app.logger.error('Falha no envio de recuperação: %s', type(erro).__name__)
        flash('Se o endereço possuir uma conta com senha, enviaremos um link de recuperação. Verifique também o spam.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/recuperar_senha.html')


@auth_bp.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
@limiter.limit('10/hour', methods=['POST'])
def redefinir_senha(token):
    import hashlib
    import hmac
    from services.email_service import ler_token_senha
    dados = ler_token_senha(token)
    user = None
    if isinstance(dados, dict):
        consulta = User.query.filter_by(id=dados.get('id'), email=dados.get('email'), ativo=True, status='ativo')
        user = (consulta.with_for_update() if request.method == 'POST' else consulta).first()
    versao = dados.get('versao') if isinstance(dados, dict) else None
    if not user or not user.password_hash or not isinstance(versao, str) or not hmac.compare_digest(hashlib.sha256(user.password_hash.encode()).hexdigest(), versao):
        flash('Link inválido, expirado ou já utilizado. Solicite um novo link.', 'info')
        return redirect(url_for('auth.recuperar_senha'))
    if request.method == 'POST':
        senha = request.form.get('senha', '')
        if len(senha) < 12 or len(senha.encode('utf-8')) > 72 or senha != request.form.get('confirmar_senha'):
            flash('Use senhas iguais, com ao menos 12 caracteres e até 72 bytes.', 'danger')
            return render_template('auth/redefinir_senha.html', token=token), 400
        user.set_password(senha)
        user.email_confirmado = True
        db.session.commit()
        logout_user()
        session.pop('veiculo_ativo_id', None)
        flash('Senha redefinida. Entre novamente com a nova senha.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/redefinir_senha.html', token=token)
