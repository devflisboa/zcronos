import smtplib
import ssl
from email.message import EmailMessage
from services.public_url import public_base_url

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


_SALT = 'autoviu-confirmacao-email-v1'


def gerar_token_confirmacao(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'id': user.id, 'email': user.email}, salt=_SALT)


def ler_token_confirmacao(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(token, salt=_SALT,
                                max_age=current_app.config['EMAIL_CONFIRM_MAX_AGE'])
    except (BadSignature, SignatureExpired):
        return None


def enviar_confirmacao(user):
    config = current_app.config
    origem = public_base_url()
    if not config.get('MAIL_SERVER') or not config.get('MAIL_DEFAULT_SENDER'):
        raise RuntimeError('SMTP não configurado')
    link = origem + '/auth/confirmar/' + gerar_token_confirmacao(user)
    mensagem = EmailMessage()
    mensagem['Subject'] = 'Confirme seu e-mail — AUTOVIU'
    mensagem['From'] = config['MAIL_DEFAULT_SENDER']
    mensagem['To'] = user.email
    mensagem.set_content(
        'Bem-vindo ao AUTOVIU!\n\n'
        'Para confirmar seu cadastro, abra o link e clique em Confirmar e-mail:\n'
        + link + '\n\nEste link expira em 24 horas. '
        'Se você não solicitou o cadastro, ignore esta mensagem.'
    )
    enviar_mensagem(mensagem)


def enviar_email(destinatario, assunto, texto):
    config = current_app.config
    if not config.get('MAIL_SERVER') or not config.get('MAIL_DEFAULT_SENDER'):
        raise RuntimeError('SMTP não configurado')
    mensagem = EmailMessage()
    mensagem['Subject'] = assunto
    mensagem['From'] = config['MAIL_DEFAULT_SENDER']
    mensagem['To'] = destinatario
    mensagem.set_content(texto)
    enviar_mensagem(mensagem)


def enviar_mensagem(mensagem):
    config = current_app.config
    with smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT'], timeout=10) as smtp:
        smtp.ehlo()
        if config['MAIL_USE_TLS']:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if config.get('MAIL_USERNAME'):
            smtp.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
        smtp.send_message(mensagem)


def gerar_token_senha(user):
    import hashlib
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    versao = hashlib.sha256(user.password_hash.encode()).hexdigest()
    return serializer.dumps({'id': user.id, 'email': user.email, 'versao': versao}, salt='autoviu-reset-senha-v1')


def ler_token_senha(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(token, salt='autoviu-reset-senha-v1', max_age=3600)
    except (BadSignature, SignatureExpired):
        return None


def enviar_recuperacao(user):
    link = public_base_url() + '/auth/redefinir-senha/' + gerar_token_senha(user)
    enviar_email(user.email, 'Redefinir senha — AUTOVIU',
        'Para definir uma nova senha, abra o link abaixo. Ele expira em 1 hora e funciona uma única vez.\n\n'
        + link + '\n\nSe você não solicitou, ignore esta mensagem.')
