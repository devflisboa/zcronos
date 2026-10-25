from urllib.parse import urlsplit
from flask import current_app


def validar_origem(origem, exigir_https=False):
    origem = (origem or '').rstrip('/')
    try:
        url = urlsplit(origem)
        url.port
        valida = (url.scheme in (('https',) if exigir_https else ('http', 'https'))
                  and url.hostname and url.path in ('', '/') and not url.query
                  and not url.fragment and not url.username and not url.password)
    except ValueError:
        valida = False
    if not valida:
        raise ValueError('Informe uma origem válida' + (' com HTTPS.' if exigir_https else '.'))
    return origem


def public_base_url():
    try:
        return validar_origem(current_app.config.get('PUBLIC_BASE_URL'), exigir_https=not current_app.debug)
    except ValueError:
        raise ValueError('Configure PUBLIC_BASE_URL com a origem pública válida do aplicativo, usando HTTPS em produção.') from None
