from datetime import datetime
import posixpath
import click
from flask import Flask, request, abort
from flask_apscheduler import APScheduler
from werkzeug.middleware.proxy_fix import ProxyFix

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


def create_app(config_name='default', *, test_config=None, initialize_database=True, start_scheduler=True):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if test_config:
        app.config.update(test_config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.refresh_view = 'auth.reautenticar'
    login_manager.needs_refresh_message = 'Confirme sua identidade para continuar.'
    login_manager.needs_refresh_message_category = 'info'
    login_manager.login_message = 'Faça login para acessar essa página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        try:
            ident, _, versao = user_id.partition(':')
            user = db.session.get(User, int(ident))
            versao = int(versao or 0)
        except (ValueError, TypeError, AttributeError):
            return None
        return user if user and user.ativo and user.status == 'ativo' and (user.auth_version or 0) == versao else None

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    app.config['SCHEDULER_API_ENABLED'] = False
    if start_scheduler:
        scheduler.init_app(app)
        if app.config.get('ALERTAS_AUTOMATICOS'):
            def enviar_alertas_programados():
                from services.alerta_service import processar_alertas
                with app.app_context():
                    processar_alertas()
            scheduler.add_job(id='alertas_fase3', func=enviar_alertas_programados,
                              trigger='interval', hours=24, max_instances=1, replace_existing=True)
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
    from blueprints.fipe.routes import fipe_bp
    app.register_blueprint(fipe_bp, url_prefix='/fipe')

    from blueprints.relatorio.routes import relatorio_bp
    app.register_blueprint(relatorio_bp, url_prefix='/relatorios')
    from blueprints.condutor.routes import condutor_bp
    from blueprints.documento.routes import documento_bp
    from blueprints.galeria.routes import galeria_bp
    from blueprints.alerta.routes import alerta_bp
    from blueprints.assinatura.routes import assinatura_bp
    from blueprints.auth.google import google_bp, init_google
    from blueprints.auth.seguranca import seguranca_bp
    app.register_blueprint(condutor_bp, url_prefix='/condutor')
    app.register_blueprint(documento_bp, url_prefix='/documentos')
    app.register_blueprint(galeria_bp, url_prefix='/veiculos')
    app.register_blueprint(alerta_bp, url_prefix='/alertas')
    app.register_blueprint(assinatura_bp)
    app.register_blueprint(google_bp, url_prefix='/auth')
    app.register_blueprint(seguranca_bp, url_prefix='/auth')
    init_google(app)

    @app.before_request
    def proteger_uploads():
        if request.endpoint == 'static':
            filename = posixpath.normpath((request.view_args or {}).get('filename', '').replace('\\', '/'))
            if filename == 'uploads' or filename.startswith('uploads/'):
                abort(404)

    @app.after_request
    def proteger_dados_privados(response):
        from flask_login import current_user
        if current_user.is_authenticated:
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    @app.cli.command('configuracao-diagnosticar')
    @click.option('--json', 'saida_json', is_flag=True, help='Emitir somente nomes de serviços e pendências em JSON.')
    def configuracao_diagnosticar(saida_json):
        from services.configuracao_service import diagnosticar_configuracao
        resultados = diagnosticar_configuracao(app.config)
        if saida_json:
            import json
            click.echo(json.dumps({'escopo': 'presença e formato, sem homologação', 'servicos': resultados}, ensure_ascii=False))
            return
        click.echo('Diagnóstico local: presença e formato. Não comprova funcionamento das integrações.')
        for item in resultados:
            click.echo(f"{item['servico']}: {item['estado']}")
            for pendencia in item['pendencias']:
                click.echo('  - ' + pendencia)
            if item['observacao']:
                click.echo('  ' + item['observacao'])

    @app.cli.command('dados-auditar')
    def dados_auditar():
        import sqlalchemy as sa
        vinculos = [('veiculo', 'user_id', 'usuarios'), ('abastecimentos', 'veiculo_id', 'veiculo'),
                    ('despesas', 'veiculo_id', 'veiculo'), ('manutencoes', 'veiculo_id', 'veiculo'),
                    ('corrida_uber', 'veiculo_id', 'veiculo'), ('semanal_uber', 'user_id', 'usuarios')]
        for tabela, campo, pai in vinculos:
            meta = sa.MetaData()
            filha = sa.Table(tabela, meta, autoload_with=db.engine)
            parent = sa.Table(pai, meta, autoload_with=db.engine, extend_existing=True)
            total = db.session.execute(sa.select(sa.func.count()).select_from(filha)).scalar()
            invalidos = db.session.execute(sa.select(sa.func.count()).select_from(
                filha.outerjoin(parent, filha.c[campo] == parent.c.id)).where(
                sa.or_(filha.c[campo].is_(None), parent.c.id.is_(None)))).scalar()
            click.echo(f'{tabela}: {total} registros; {invalidos} vínculos inválidos')

    @app.cli.command('alertas-enviar')
    def alertas_enviar():
        from services.alerta_service import processar_alertas
        click.echo(f'Alertas enviados: {processar_alertas()}')

    @app.cli.command('assinaturas-reconciliar')
    def assinaturas_reconciliar():
        from services.assinatura_service import reconciliar_pendentes
        click.echo(f'Assinaturas conciliadas: {reconciliar_pendentes()}')

    if initialize_database:
        with app.app_context():
            db.create_all()
        _seed_categorias(app)

    return app


if __name__ == '__main__':
    create_app('development').run(debug=True, host='0.0.0.0')
