import os
from datetime import timedelta


class Config:
    ENVIRONMENT = 'production'
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY não definida no ambiente — configure o .env')

    DEBUG = False

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.environ.get('DB_USER', 'admin')}:"
        f"{os.environ.get('DB_PASSWORD', 'admin')}@"
        f"{os.environ.get('DB_HOST', 'localhost:3306')}/"
        f"{os.environ.get('DB_NAME', 'car_management')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Sessão segura
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    MAX_CONTENT_LENGTH = 12 * 1024 * 1024
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_VISION_MODEL = os.environ.get('OPENAI_VISION_MODEL', '')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID', '')
    WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', '')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
    VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', '')
    ALERTAS_AUTOMATICOS = os.environ.get('ALERTAS_AUTOMATICOS', 'false').lower() == 'true'
    ASAAS_API_KEY = os.environ.get('ASAAS_API_KEY', '')
    ASAAS_WEBHOOK_TOKEN = os.environ.get('ASAAS_WEBHOOK_TOKEN', '')
    ASAAS_ENV = os.environ.get('ASAAS_ENV', 'sandbox')
    FROTA_PRECO = os.environ.get('FROTA_PRECO', '')
    FROTA_LIMITE = int(os.environ['FROTA_LIMITE']) if os.environ.get('FROTA_LIMITE') else None
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    FIPE_API_TOKEN = os.environ.get('FIPE_API_TOKEN', '')
    FIPE_CACHE_SECONDS = int(os.environ.get('FIPE_CACHE_SECONDS', '3600'))

    # Cadastro público e e-mail transacional
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', '')
    EMAIL_CONFIRM_MAX_AGE = 86400
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')


class DevelopmentConfig(Config):
    ENVIRONMENT = 'development'
    DEBUG = True
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    # NPM (Nginx Proxy Manager) não repassa o Referer header em HTTPS → desabilita
    # só a checagem de Referer, mantendo a proteção CSRF intacta
    WTF_CSRF_SSL_STRICT = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
