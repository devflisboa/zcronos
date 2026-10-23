import os

class Config:
    # Configurações básicas do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'minha_chave_secreta_default')  # Usado para segurança de sessão
    DEBUG = False  # Modo de depuração desativado por padrão
    
    # Configurações de Banco de Dados
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.environ.get('DB_USER', 'admin')}:"
        f"{os.environ.get('DB_PASSWORD', 'admin')}@"
        f"{os.environ.get('DB_HOST', 'localhost:3306')}/"
        f"{os.environ.get('DB_NAME', 'car_management')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Desativa o monitoramento de mudanças no SQLAlchemy para melhorar o desempenho
    
    # Configurações de outros serviços (ex.: envio de e-mail, se necessário)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'seu_email@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'sua_senha_email')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'seu_email@example.com')

class DevelopmentConfig(Config):
    DEBUG = True  # Habilita o modo de depuração em desenvolvimento
    SQLALCHEMY_ECHO = True  # Exibe os comandos SQL no console para depuração

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False

# Dicionário para acessar diferentes configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
