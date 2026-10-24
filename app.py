from datetime import datetime
from flask import Flask
from flask_apscheduler import APScheduler
from sqlalchemy import text

from config import config
from extensions import db, login_manager, csrf, bcrypt, limiter

scheduler = APScheduler()

CATEGORIAS_SEED = [
    ('Troca de Óleo', '🛢️', 'variavel'), ('Revisão', '🔧', 'variavel'),
    ('Pneus', '🔄', 'variavel'), ('Bateria', '⚡', 'variavel'),
    ('Filtros', '🌬️', 'variavel'), ('Pastilhas de Freio', '🛑', 'variavel'),
    ('Seguro', '🛡️', 'fixo'), ('IPVA', '📋', 'fixo'),
    ('Licenciamento', '📄', 'fixo'), ('Lavagem', '🚿', 'variavel'),
    ('Estacionamento', '🅿️', 'variavel'), ('Pedágio', '🛣️', 'variavel'),
    ('Multa', '⚠️', 'variavel'), ('Peças', '⚙️', 'variavel'),
    ('Reparo', '🔨', 'variavel'), ('Outros', '📦', 'variavel'),
]


def _seed_categorias(app):
    from models import Categoria
    with app.app_context():
        if not Categoria.query.first():
            for nome, icone, tipo in CATEGORIAS_SEED:
                db.session.add(Categoria(nome=nome, icone=icone, tipo=tipo))
            db.session.commit()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar essa página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.start()

    from blueprints.auth.routes import auth_bp
    from blueprints.main.routes import main_bp
    from blueprints.abastecimento.routes import abastecimento_bp
    from blueprints.despesa.routes import despesa_bp
    from blueprints.uber.routes import uber_bp
    from blueprints.manutencao.routes import manutencao_bp
    from blueprints.veiculo.routes import veiculo_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(abastecimento_bp, url_prefix='/abastecimento')
    app.register_blueprint(despesa_bp, url_prefix='/despesa')
    app.register_blueprint(uber_bp)
    app.register_blueprint(manutencao_bp, url_prefix='/manutencao')
    app.register_blueprint(veiculo_bp, url_prefix='/veiculos')

    with app.app_context():
        db.create_all()

    _seed_categorias(app)

    return app


if __name__ == '__main__':
    create_app('development').run(debug=True, host='0.0.0.0')
