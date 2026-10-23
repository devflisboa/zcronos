from datetime import date, timedelta
from flask import Flask
from flask_apscheduler import APScheduler
from sqlalchemy import text

from config import config
from extensions import db

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


def _run_migrations(app):
    with app.app_context():
        for col, typ in [
            ('quilometragem', 'INT NULL'),
            ('forma_pagamento', 'VARCHAR(50) NULL'),
            ('observacoes', 'TEXT NULL'),
        ]:
            try:
                db.session.execute(text(f'ALTER TABLE despesas ADD COLUMN {col} {typ}'))
                db.session.commit()
            except Exception:
                db.session.rollback()

        for col, typ in [
            ('icone', "VARCHAR(10) NULL DEFAULT ''"),
            ('tipo', "VARCHAR(20) NULL DEFAULT 'variavel'"),
        ]:
            try:
                db.session.execute(text(f'ALTER TABLE categorias ADD COLUMN {col} {typ}'))
                db.session.commit()
            except Exception:
                db.session.rollback()


def _seed(app):
    from models import Veiculo, Categoria, Manutencao
    with app.app_context():
        if not Veiculo.query.first():
            db.session.add(Veiculo(
                marca='Fiat', modelo='Cronos', versao='Drive 1.3 Manual',
                motor='Firefly 1.3 Flex 109 CV', ano=2021, placa='RGE7D41',
                cor='Branco Banchisa', km_atual=63248,
                data_compra=date(2021, 3, 15),
                valor_compra=72990.0, valor_atual=68000.0,
            ))
            db.session.commit()

        if not Categoria.query.first():
            for nome, icone, tipo in CATEGORIAS_SEED:
                db.session.add(Categoria(nome=nome, icone=icone, tipo=tipo))
            db.session.commit()

        if not Manutencao.query.first():
            hoje = date.today()
            db.session.add_all([
                Manutencao(tipo='oleo', descricao='Troca de óleo e filtro',
                           data_realizada=date(2026, 3, 10), km_realizada=58000,
                           data_prevista=date(2026, 9, 10), km_previsto=68000,
                           custo=280, status='pendente'),
                Manutencao(tipo='revisao', descricao='Revisão dos 65.000 km',
                           data_prevista=date(2026, 10, 1), km_previsto=65000,
                           status='pendente'),
                Manutencao(tipo='pneu', descricao='Rodízio de pneus',
                           data_realizada=date(2026, 1, 20), km_realizada=55000,
                           data_prevista=date(2026, 9, 20), km_previsto=65000,
                           custo=60, status='pendente'),
                Manutencao(tipo='freio', descricao='Pastilhas de freio dianteiro',
                           data_prevista=(hoje + timedelta(days=45)), km_previsto=66000,
                           status='pendente'),
            ])
            db.session.commit()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.start()

    from blueprints.main.routes import main_bp
    from blueprints.abastecimento.routes import abastecimento_bp
    from blueprints.despesa.routes import despesa_bp
    from blueprints.uber.routes import uber_bp
    from blueprints.manutencao.routes import manutencao_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(abastecimento_bp, url_prefix='/abastecimento')
    app.register_blueprint(despesa_bp, url_prefix='/despesa')
    app.register_blueprint(uber_bp)
    app.register_blueprint(manutencao_bp, url_prefix='/manutencao')

    with app.app_context():
        db.create_all()

    _run_migrations(app)
    _seed(app)

    return app


if __name__ == '__main__':
    create_app('development').run(debug=True, host='0.0.0.0')
