"""Testes isolados: SQLite em memória e e-mail simulado, sem produção."""
import os
os.environ.setdefault('SECRET_KEY', 'chave-exclusiva-dos-testes-de-cadastro')

import re
import unittest
from unittest.mock import patch
from flask import Flask
from extensions import db, bcrypt, csrf, login_manager, limiter
from models import User
from blueprints.auth.routes import auth_bp
from services.email_service import gerar_token_confirmacao, enviar_confirmacao


class RegistroTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder='../templates', static_folder='../static')
        self.app.config.update(TESTING=True, SECRET_KEY='teste-local',
            SQLALCHEMY_DATABASE_URI='sqlite://', WTF_CSRF_ENABLED=True,
            RATELIMIT_ENABLED=True, RATELIMIT_STORAGE_URI='memory://', BCRYPT_LOG_ROUNDS=4,
            EMAIL_CONFIRM_MAX_AGE=86400)
        for extension in (db, bcrypt, csrf, login_manager, limiter):
            extension.init_app(self.app)
        self.app.register_blueprint(auth_bp, url_prefix='/auth')
        self.app.add_url_rule('/sw.js', endpoint='main.service_worker', view_func=lambda: '')
        self.app.add_url_rule('/', endpoint='main.index', view_func=lambda: 'dashboard')
        self.app.add_url_rule('/veiculos/', endpoint='veiculo.index', view_func=lambda: 'veiculos')
        self.app.add_url_rule('/veiculos/novo', endpoint='veiculo.novo', view_func=lambda: 'novo')
        self.app.add_url_rule('/condutor/', endpoint='condutor.perfil', view_func=lambda: 'condutor')
        @self.app.context_processor
        def contexto():
            from datetime import datetime
            return {'now': datetime.utcnow()}
        @login_manager.user_loader
        def load_user(user_id):
            ident, _, versao = user_id.partition(':')
            user = db.session.get(User, int(ident))
            return user if user and (user.auth_version or 0) == int(versao or 0) else None
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.sender = patch('blueprints.auth.routes.enviar_confirmacao').start()

    def tearDown(self):
        patch.stopall()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def post(self, path, data=None):
        response = self.client.get(path)
        token = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(token)
        return self.client.post(path, data={**(data or {}), 'csrf_token': token[1]})

    def register(self, **kwargs):
        return self.post('/auth/registro', dict(nome='Pessoa Teste', email='novo@example.com',
            senha='senha-segura-123', confirmar_senha='senha-segura-123', **kwargs))

    def test_fluxo_completo_sem_login_antes_de_confirmar(self):
        response = self.register()
        self.assertEqual(response.status_code, 302)
        user = User.query.one()
        self.assertEqual((user.plano, user.status, user.email_confirmado), ('free', 'pendente', False))
        self.assertTrue(user.check_password('senha-segura-123'))
        self.assertNotEqual(user.password_hash, 'senha-segura-123')
        self.sender.assert_called_once()
        response = self.post('/auth/login', {'email': user.email, 'senha': 'senha-segura-123'})
        self.assertIn('reenviar-confirmacao', response.location)
        with self.client.session_transaction() as sess:
            self.assertNotIn('_user_id', sess)
        token = gerar_token_confirmacao(user)
        url = '/auth/confirmar/' + token
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(user.email_confirmado)
        self.assertEqual(self.post(url).status_code, 302)
        self.assertTrue(user.email_confirmado)
        self.assertEqual(user.status, 'ativo')
        self.assertIn('reenviar-confirmacao', self.client.get(url).location)
        response = self.post('/auth/login', {'email': user.email, 'senha': 'senha-segura-123'})
        self.assertTrue(response.location.endswith('/condutor/?cadastro=1'))

    def test_csrf_obrigatorio(self):
        self.assertEqual(self.client.post('/auth/registro', data={}).status_code, 400)
        self.assertEqual(User.query.count(), 0)

    def test_entrada_invalida(self):
        for campo, valor in [('nome', 'A'), ('email', 'invalido'), ('senha', 'curta'),
                             ('confirmar_senha', 'diferente'), ('senha', 'á' * 40)]:
            dados = dict(nome='Pessoa Teste', email='novo@example.com',
                         senha='senha-segura-123', confirmar_senha='senha-segura-123')
            dados[campo] = valor
            self.assertEqual(self.post('/auth/registro', dados).status_code, 400)
        self.assertEqual(User.query.count(), 0)

    def test_duplicado_nao_altera_conta(self):
        self.register()
        user = User.query.one()
        original = user.password_hash
        self.register()
        self.assertEqual(User.query.count(), 1)
        self.assertEqual(user.password_hash, original)
        self.assertEqual(self.sender.call_count, 1)

    def test_reenvio_e_endereco_inexistente(self):
        self.register()
        response = self.post('/auth/reenviar-confirmacao', {'email': 'novo@example.com'})
        self.assertEqual(self.sender.call_count, 2)
        unknown = self.post('/auth/reenviar-confirmacao', {'email': 'ninguem@example.com'})
        self.assertEqual(response.location, unknown.location)
        self.assertEqual(self.sender.call_count, 2)

    def test_token_invalido_expirado_e_csrf_confirmacao(self):
        self.register()
        user = User.query.one()
        token = gerar_token_confirmacao(user)
        self.assertEqual(self.client.post('/auth/confirmar/' + token).status_code, 400)
        self.assertEqual(self.client.get('/auth/confirmar/adulterado').status_code, 302)
        self.app.config['EMAIL_CONFIRM_MAX_AGE'] = -1
        self.assertEqual(self.client.get('/auth/confirmar/' + token).status_code, 302)
        self.assertFalse(user.email_confirmado)

    def test_falha_smtp_mantem_conta_pendente(self):
        self.sender.side_effect = OSError('simulacao')
        self.assertEqual(self.register().status_code, 302)
        user = User.query.one()
        self.assertEqual(user.status, 'pendente')
        self.assertFalse(user.email_confirmado)

    def test_conta_existente_preservada_e_redirect_externo_bloqueado(self):
        user = User(nome='Legado', email='legado@example.com', plano='free',
                    status='ativo', ativo=True, email_confirmado=False)
        user.set_password('senha-segura-123')
        db.session.add(user)
        db.session.commit()
        response = self.post('/auth/login?next=https://externo.example',
                             {'email': user.email, 'senha': 'senha-segura-123'})
        self.assertTrue(response.location.endswith('/condutor/?cadastro=1'))


    def test_envio_smtp_com_url_confiavel(self):
        self.register()
        self.app.config.update(PUBLIC_BASE_URL='https://autoviu.example',
            MAIL_SERVER='smtp.example', MAIL_PORT=587, MAIL_USE_TLS=True,
            MAIL_DEFAULT_SENDER='contato@autoviu.example',
            MAIL_USERNAME='usuario', MAIL_PASSWORD='segredo')
        with patch('services.email_service.smtplib.SMTP') as smtp:
            enviar_confirmacao(User.query.one())
            connection = smtp.return_value.__enter__.return_value
            connection.starttls.assert_called_once()
            connection.login.assert_called_once_with('usuario', 'segredo')
            message = connection.send_message.call_args.args[0]
            self.assertIn('https://autoviu.example/auth/confirmar/', message.get_content())
            self.assertEqual(message['To'], 'novo@example.com')
        self.app.config['PUBLIC_BASE_URL'] = 'http://autoviu.example'
        with self.assertRaises(ValueError):
            enviar_confirmacao(User.query.one())

    def test_limite_de_reenvio(self):
        for tentativa in range(4):
            response = self.post('/auth/reenviar-confirmacao', {'email': 'ninguem@example.com'})
            self.assertEqual(response.status_code, 302 if tentativa < 3 else 429)

    def test_resposta_auth_nao_cacheavel(self):
        response = self.client.get('/auth/registro')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')


if __name__ == '__main__':
    unittest.main()
