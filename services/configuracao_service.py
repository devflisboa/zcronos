from urllib.parse import urlsplit
from services.public_url import validar_origem


def diagnosticar_configuracao(config):
    """Inspeciona configuração carregada, sem rede, banco ou exposição de valores."""
    resultados = []

    def grupo(nome, campos=(), pendencias=(), observacao=''):
        faltantes = [f'Configurar {campo}.' for campo in campos if not config.get(campo)]
        faltantes.extend(pendencias)
        resultados.append(dict(servico=nome, estado='pendente' if faltantes else 'presente',
                               pendencias=faltantes, observacao=observacao))

    def origem_valida(valor, https=False):
        try:
            validar_origem(valor, exigir_https=https)
            return True
        except ValueError:
            return False

    producao = config.get('ENVIRONMENT', 'production') == 'production'
    pendencias = []
    if len(str(config.get('SECRET_KEY') or '')) < 32:
        pendencias.append('Configurar SECRET_KEY com pelo menos 32 caracteres aleatórios.')
    if producao and not all(config.get(campo) for campo in ('SESSION_COOKIE_SECURE', 'REMEMBER_COOKIE_SECURE')):
        pendencias.append('Ativar cookies Secure no ambiente de produção (FLASK_ENV=production).')
    grupo('Sessão', pendencias=pendencias)

    publica_valida = origem_valida(config.get('PUBLIC_BASE_URL'), https=producao)
    grupo('Origem pública', pendencias=[] if publica_valida else ['Configurar PUBLIC_BASE_URL como origem válida, com HTTPS em produção.'])

    pendencias = []
    if config.get('MAIL_USERNAME') and not config.get('MAIL_PASSWORD'):
        pendencias.append('Configurar MAIL_PASSWORD para autenticação SMTP.')
    if not publica_valida:
        pendencias.append('Corrigir PUBLIC_BASE_URL para os links transacionais.')
    grupo('E-mail', ('MAIL_SERVER', 'MAIL_DEFAULT_SENDER'), pendencias,
          'Presença de configuração não comprova autenticação SMTP ou entrega.')
    grupo('OCR', ('OPENAI_API_KEY', 'OPENAI_VISION_MODEL'), observacao='Modelo e leitura de documentos ainda exigem homologação.')
    grupo('Google', ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'),
          [] if publica_valida else ['Corrigir PUBLIC_BASE_URL para o callback.'],
          'A decisão sobre vínculo de contas existente no roadmap continua pendente; o diagnóstico não autoriza habilitação.')

    origem = config.get('WEBAUTHN_ORIGIN', '')
    rp = config.get('WEBAUTHN_RP_ID', '')
    pendencias = []
    if origem and not origem_valida(origem, https=True):
        pendencias.append('Corrigir WEBAUTHN_ORIGIN para uma origem HTTPS.')
    elif origem and rp:
        host = urlsplit(origem).hostname
        if not (host == rp or host.endswith('.' + rp)):
            pendencias.append('Alinhar WEBAUTHN_RP_ID ao domínio de WEBAUTHN_ORIGIN.')
    grupo('Passkeys', ('WEBAUTHN_ORIGIN', 'WEBAUTHN_RP_ID'), pendencias,
          'Presença e formato não comprovam registro/autenticação em dispositivos reais.')
    grupo('Push', ('VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY', 'VAPID_SUBJECT'),
          observacao='Chaves não são decodificadas; permissão do dispositivo e entrega precisam de homologação.')

    pendencias = []
    if config.get('ASAAS_ENV') not in ('sandbox', 'production'):
        pendencias.append('Definir ASAAS_ENV como sandbox ou production.')
    if config.get('ASAAS_WEBHOOK_TOKEN') and len(config['ASAAS_WEBHOOK_TOKEN']) < 32:
        pendencias.append('Configurar ASAAS_WEBHOOK_TOKEN independente com pelo menos 32 caracteres.')
    grupo('Asaas', ('ASAAS_API_KEY', 'ASAAS_WEBHOOK_TOKEN'), pendencias,
          'Sem consulta de credenciais, cobrança, webhook ou conciliação; homologar primeiro em sandbox.')
    grupo('Limite de requisições', pendencias=(
        ['Configurar RATELIMIT_STORAGE_URI compartilhado antes de usar múltiplos workers.']
        if config.get('RATELIMIT_STORAGE_URI', 'memory://') == 'memory://' else []),
        observacao='A conexão ao armazenamento não é verificada.')
    grupo('FIPE', observacao='Token opcional; o diagnóstico não consulta preços nem valida quota do provedor.')
    grupo('Frota', pendencias=['Resolver preço e limite divergentes nos roadmaps antes de habilitar a venda.'],
          observacao='Nenhuma decisão comercial é inferida das variáveis presentes.')
    return resultados
