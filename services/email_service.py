import smtplib
import ssl
from email.message import EmailMessage
from services.public_url import public_base_url

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


_SALT = 'autoviu-confirmacao-email-v1'

_HTML_BASE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0A0A0C;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0A0A0C">
<tr><td align="center" style="padding:40px 16px">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="max-width:560px;background:#111113;border-radius:12px;border:1px solid #2a2a2d;overflow:hidden">
<!-- cabeçalho -->
<tr><td style="padding:28px 32px;border-bottom:1px solid #2a2a2d;text-align:center">
  <span style="font-size:22px;font-weight:700;color:#c9a84c;letter-spacing:3px;font-family:Arial,sans-serif">&#923;UTOVIU</span>
</td></tr>
<!-- corpo -->
<tr><td style="padding:32px">
  {body}
</td></tr>
<!-- rodapé -->
<tr><td style="padding:20px 32px;border-top:1px solid #2a2a2d;text-align:center">
  <p style="color:#555;font-size:12px;margin:0;line-height:1.5">
    &#923;UTOVIU &mdash; Gest&atilde;o Automotiva Inteligente<br>
    <span style="color:#444">Voc&ecirc; recebeu este e-mail pois realizou uma a&ccedil;&atilde;o na plataforma.</span>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

_BTN = ('<table cellpadding="0" cellspacing="0" border="0" style="margin-top:24px">'
        '<tr><td style="background:#c9a84c;border-radius:8px;padding:14px 28px;text-align:center">'
        '<a href="{link}" style="color:#000;font-weight:700;text-decoration:none;font-size:14px;'
        'font-family:Arial,sans-serif">{label}</a></td></tr></table>')

_LINK_FALLBACK = ('<p style="margin:16px 0 0;font-size:12px;color:#666;word-break:break-all">'
                  'Se o bot&atilde;o n&atilde;o funcionar, copie e cole este link:<br>'
                  '<a href="{link}" style="color:#c9a84c">{link}</a></p>')


def _html(titulo, paragrafos, link=None, label_btn=None, nota_expiracao=None):
    p_tags = ''.join(
        f'<p style="color:#b0b8c2;font-size:14px;line-height:1.6;margin:0 0 12px">{p}</p>'
        for p in paragrafos
    )
    body = (
        f'<h1 style="color:#f0f0f0;font-size:18px;font-weight:700;margin:0 0 16px;'
        f'font-family:Arial,sans-serif">{titulo}</h1>'
        + p_tags
    )
    if link and label_btn:
        body += _BTN.format(link=link, label=label_btn)
        body += _LINK_FALLBACK.format(link=link)
    if nota_expiracao:
        body += (f'<p style="margin-top:20px;font-size:12px;color:#555;line-height:1.5">'
                 f'{nota_expiracao}</p>')
    return _HTML_BASE.replace('{body}', body)


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
    texto = (
        'Bem-vindo ao ΛUTOVIU!\n\n'
        'Para confirmar seu cadastro, abra o link e clique em Confirmar e-mail:\n'
        + link + '\n\nEste link expira em 24 horas. '
        'Se você não solicitou o cadastro, ignore esta mensagem.'
    )
    html = _html(
        'Confirme seu e-mail',
        ['Bem-vindo ao &#923;UTOVIU! Estamos felizes em ter voc&ecirc; por aqui.',
         'Clique no bot&atilde;o abaixo para ativar sua conta. Se voc&ecirc; n&atilde;o '
         'solicitou o cadastro, ignore esta mensagem.'],
        link=link,
        label_btn='Confirmar e-mail',
        nota_expiracao='Este link expira em <strong>24 horas</strong> e funciona uma &uacute;nica vez.',
    )
    mensagem = EmailMessage()
    mensagem['Subject'] = 'Confirme seu e-mail — ΛUTOVIU'
    mensagem['From'] = config['MAIL_DEFAULT_SENDER']
    mensagem['To'] = user.email
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype='html')
    enviar_mensagem(mensagem)


def enviar_email(destinatario, assunto, texto):
    config = current_app.config
    if not config.get('MAIL_SERVER') or not config.get('MAIL_DEFAULT_SENDER'):
        raise RuntimeError('SMTP não configurado')
    # Texto simples → HTML básico sem botão de link
    paragrafos = [linha for linha in texto.split('\n') if linha.strip()]
    html = _html(assunto, paragrafos)
    mensagem = EmailMessage()
    mensagem['Subject'] = assunto
    mensagem['From'] = config['MAIL_DEFAULT_SENDER']
    mensagem['To'] = destinatario
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype='html')
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
    return serializer.dumps({'id': user.id, 'email': user.email, 'versao': versao},
                            salt='autoviu-reset-senha-v1')


def ler_token_senha(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(token, salt='autoviu-reset-senha-v1', max_age=3600)
    except (BadSignature, SignatureExpired):
        return None


def enviar_recuperacao(user):
    link = public_base_url() + '/auth/redefinir-senha/' + gerar_token_senha(user)
    texto = (
        'Para definir uma nova senha, abra o link abaixo. '
        'Ele expira em 1 hora e funciona uma única vez.\n\n'
        + link + '\n\nSe você não solicitou, ignore esta mensagem.'
    )
    html = _html(
        'Redefinir sua senha',
        ['Recebemos uma solicita&ccedil;&atilde;o para redefinir a senha da sua conta &#923;UTOVIU.',
         'Clique no bot&atilde;o abaixo para criar uma nova senha. '
         'Se voc&ecirc; n&atilde;o solicitou, ignore esta mensagem.'],
        link=link,
        label_btn='Redefinir senha',
        nota_expiracao='Este link expira em <strong>1 hora</strong> e funciona uma &uacute;nica vez.',
    )
    mensagem = EmailMessage()
    mensagem['Subject'] = 'Redefinir senha — ΛUTOVIU'
    mensagem['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    mensagem['To'] = user.email
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype='html')
    enviar_mensagem(mensagem)
