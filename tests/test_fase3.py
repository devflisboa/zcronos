import os
os.environ.setdefault('SECRET_KEY', 'chave-exclusiva-dos-testes-locais')

import base64
import hashlib
import io
import json
import re
import tempfile
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, Mock

import cbor2
from PIL import Image
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from app import create_app
from extensions import db
from models import (User, Veiculo, Condutor, Assinatura, Fatura, EventoGateway, FotoVeiculo,
    PreferenciaAlerta, EnvioAlerta, WebAuthnDesafio, WebAuthnCredential)
from services.alerta_service import listar_alertas, processar_alertas, validar_subscription
from services.assinatura_service import iniciar_trial, plano_efetivo, sincronizar_fatura, criar_assinatura, GatewayIndisponivel


def b64(valor):
    return base64.urlsafe_b64encode(valor).decode().rstrip('=')


def foto_bytes():
    dados = io.BytesIO()
    Image.new('RGB', (800, 600), '#223355').save(dados, 'JPEG')
    dados.seek(0)
    return dados


class Fase3Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app('development', start_scheduler=False, test_config={
            'TESTING': True, 'DEBUG': False, 'SECRET_KEY': 'teste-fase3',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'RATELIMIT_ENABLED': False,
            'SESSION_PROTECTION': None, 'BCRYPT_LOG_ROUNDS': 4, 'VEICULO_UPLOAD_ROOT': self.tmp.name,
            'WEBAUTHN_RP_ID': 'autoviu.test', 'WEBAUTHN_ORIGIN': 'https://autoviu.test',
            'ASAAS_API_KEY': 'chave-teste', 'ASAAS_WEBHOOK_TOKEN': 'segredo-webhook-exclusivo-de-testes-123',
            'GOOGLE_CLIENT_ID': '', 'GOOGLE_CLIENT_SECRET': '',
            'OPENAI_API_KEY': '', 'OPENAI_VISION_MODEL': '', 'VAPID_PUBLIC_KEY': '',
            'ALERTAS_AUTOMATICOS': False, 'FROTA_PRECO': '', 'FROTA_LIMITE': None})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = User(nome='Usuário A', email='a@example.test', plano='free', status='ativo', ativo=True, email_confirmado=True)
        self.user.set_password('senha-local-segura')
        self.outro = User(nome='Usuário B', email='b@example.test', plano='free', status='ativo', ativo=True, email_confirmado=True)
        self.outro.set_password('senha-local-segura')
        db.session.add_all([self.user, self.outro])
        db.session.flush()
        self.v = Veiculo(user_id=self.user.id, marca='Marca', modelo='Modelo', ano=2024, ativo=True, km_atual=10000)
        self.vb = Veiculo(user_id=self.outro.id, marca='Outra', modelo='Privado', ano=2023, ativo=True)
        db.session.add_all([self.v, self.vb])
        db.session.commit()
        self.client = self.app.test_client()
        self.network = patch('requests.sessions.Session.request', side_effect=AssertionError('Teste tentou acessar rede')).start()
        self.smtp = patch('smtplib.SMTP', side_effect=AssertionError('Teste tentou enviar e-mail')).start()

    def tearDown(self):
        patch.stopall()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        self.tmp.cleanup()

    def login(self, user=None):
        from flask import g
        g.pop('_login_user', None)
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str((user or self.user).id)
            sess['_fresh'] = True

    def token(self, path='/auth/login'):
        response = self.client.get(path)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        if match is None:
            match = re.search(r'name="csrf-token" content="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match, response.get_data(as_text=True)[:1000])
        return match[1]

    def post(self, path, data=None, json_data=None):
        token = self.token('/condutor/' if self.user.is_authenticated and self._logged() else '/auth/login')
        if json_data is not None:
            return self.client.post(path, json=json_data, headers={'X-CSRFToken': token})
        return self.client.post(path, data={**(data or {}), 'csrf_token': token})

    def _logged(self):
        with self.client.session_transaction() as sess:
            return '_user_id' in sess

    def assinatura(self, **kwargs):
        campos = dict(user_id=self.user.id, plano='pro', status='pendente', valor=Decimal('14.90'),
                      data_inicio=date.today(), gateway_id='sub_local')
        campos.update(kwargs)
        obj = Assinatura(**campos)
        db.session.add(obj)
        db.session.commit()
        return obj

    def pagamento(self, **kwargs):
        campos = dict(id='pay_local', subscription='sub_local', value=14.9, status='CONFIRMED',
                      dueDate=date.today().isoformat(), confirmedDate=date.today().isoformat(),
                      invoiceUrl='https://www.asaas.com/i/local')
        campos.update(kwargs)
        return campos

    def test_telas_integradas(self):
        self.user.plano = 'pro'
        db.session.commit()
        self.login()
        for rota in ['/condutor/', '/alertas/', '/plano', '/auth/seguranca', '/veiculos/',
                     '/veiculos/novo', f'/veiculos/{self.v.id}/fotos']:
            response = self.client.get(rota)
            self.assertEqual(response.status_code, 200, rota)
            self.assertIn('no-store', response.headers['Cache-Control'])

    def test_perfil_valida_cpf_e_isola_veiculos(self):
        self.login()
        response = self.post('/condutor/', {'nome': 'Condutor Teste', 'cpf': '11111111111'})
        self.assertEqual(response.status_code, 400)
        response = self.post('/condutor/', {'nome': 'Condutor Teste', 'cpf': '529.982.247-25', 'cnh_categoria':'AB', 'veiculos':str(self.vb.id)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Condutor.query.count(), 0)
        response = self.post('/condutor/', {'nome': 'Condutor Teste', 'cpf': '529.982.247-25', 'cnh_categoria':'AB', 'veiculos':str(self.v.id)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.v.condutor_id, Condutor.query.one().id)
        self.assertIsNone(self.vb.condutor_id)

    def test_documentacao_veiculo_salva_campos_revisados(self):
        self.login()
        response = self.post(f'/veiculos/{self.v.id}/editar', {'marca':'Marca', 'modelo':'Modelo',
            'ano_fabricacao':'2023', 'chassi':'9BWZZZ377VT004251', 'renavam':'12345678901',
            'crlv_validade':'2026-12-31', 'seguro_validade':'2026-11-30'})
        self.assertEqual(response.status_code, 302)
        db.session.refresh(self.v)
        self.assertEqual(self.v.ano_fabricacao, 2023)
        self.assertEqual(self.v.crlv_validade, date(2026,12,31))

    def test_trial_e_expiracao_preservam_veiculos(self):
        iniciar_trial(self.user)
        db.session.commit()
        self.assertEqual(self.user.plano, 'free')
        self.assertEqual(self.user.plano_efetivo, 'pro')
        a = Assinatura.query.one()
        self.assertEqual(plano_efetivo(self.user, a.data_renovacao), 'free')
        self.assertEqual(Veiculo.query.filter_by(user_id=self.user.id).count(), 1)
        iniciar_trial(self.user)
        db.session.commit()
        self.assertEqual(Assinatura.query.count(), 1)

    def test_webhook_token_obrigatorio(self):
        self.assertEqual(self.client.post('/webhooks/asaas', json={'id':'evt1'}).status_code, 401)

    def test_webhook_consulta_estado_atual_e_idempotente(self):
        assinatura = self.assinatura()
        headers = {'asaas-access-token':self.app.config['ASAAS_WEBHOOK_TOKEN']}
        with patch('blueprints.assinatura.routes.asaas', return_value=self.pagamento()) as gateway:
            response = self.client.post('/webhooks/asaas', json={'id':'evt1','event':'PAYMENT_CONFIRMED','payment':{'id':'pay_local','value':1}}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.user.plano_efetivo, 'pro')
            self.assertEqual(Fatura.query.one().valor, Decimal('14.90'))
            self.client.post('/webhooks/asaas', json={'id':'evt1','event':'PAYMENT_CONFIRMED','payment':{'id':'pay_local'}}, headers=headers)
            self.assertEqual(gateway.call_count, 1)
        self.assertEqual(EventoGateway.query.count(), 1)

    def test_webhook_reembolso_remove_beneficio_sem_apagar_dados(self):
        assinatura = self.assinatura()
        sincronizar_fatura(assinatura, self.pagamento())
        db.session.commit()
        sincronizar_fatura(assinatura, self.pagamento(status='REFUNDED'))
        db.session.commit()
        self.assertEqual(self.user.plano_efetivo, 'free')
        self.assertEqual(Veiculo.query.count(), 2)

    def test_valor_divergente_nao_libera_acesso(self):
        assinatura = self.assinatura()
        with self.assertRaises(ValueError):
            sincronizar_fatura(assinatura, self.pagamento(value=1))
        self.assertEqual(self.user.plano_efetivo, 'free')

    def test_contratacao_timeout_nao_repete_cobranca(self):
        with patch('services.assinatura_service.asaas', side_effect=GatewayIndisponivel('simulado')) as gateway:
            with self.assertRaises(GatewayIndisponivel):
                criar_assinatura(self.user, 'pro', '52998224725', 'PIX')
            self.assertEqual(Assinatura.query.one().status, 'incerta')
            with self.assertRaises(ValueError):
                criar_assinatura(self.user, 'pro', '52998224725', 'PIX')
            self.assertEqual(gateway.call_count, 1)

    def test_cobranca_criada_nao_libera_plano(self):
        respostas = [{'data':[]}, {'id':'cus_local'}, {'id':'sub_local'},
                     {'id':'sub_local', 'customer':'cus_local', 'status':'ACTIVE'},
                     {'data':[self.pagamento(status='PENDING', confirmedDate=None)]}]
        with patch('services.assinatura_service.asaas', side_effect=respostas):
            criar_assinatura(self.user, 'pro', '52998224725', 'UNDEFINED')
        self.assertEqual(self.user.plano_efetivo, 'free')
        self.assertEqual(Fatura.query.one().status, 'PENDING')

    def test_admin_e_assinaturas_isolados(self):
        a = self.assinatura()
        self.login(self.outro)
        self.assertEqual(self.client.get('/admin/assinaturas').status_code, 403)
        response = self.post(f'/plano/{a.id}/cancelar', {'confirmar':'sim'})
        self.assertEqual(response.status_code, 404)
        self.outro.plano = 'superadmin'
        db.session.commit()
        self.assertEqual(self.client.get('/admin/assinaturas').status_code, 200)

    def test_upload_foto_e_acesso_privado(self):
        self.login()
        response = self.post(f'/veiculos/{self.v.id}/fotos', {'fotos':(foto_bytes(),'carro.jpg','image/jpeg')})
        self.assertEqual(response.status_code, 201)
        foto = FotoVeiculo.query.one()
        url = f'/veiculos/{self.v.id}/fotos/{foto.id}/imagem'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.get(f'/static/uploads/veiculos/{self.v.id}/{foto.filename}').status_code, 404)
        self.assertEqual(self.client.get(f'/static/x/../uploads/veiculos/{self.v.id}/{foto.filename}').status_code, 404)
        with Image.open(Path(self.tmp.name)/str(self.v.id)/foto.filename) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertFalse(image.getexif())
        self.login(self.outro)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.post(f'/veiculos/{self.v.id}/fotos/{foto.id}/remover', json_data={}).status_code, 404)

    def test_foto_mime_invalido_e_limite(self):
        self.login()
        response = self.post(f'/veiculos/{self.v.id}/fotos', {'fotos':(io.BytesIO(b'nao-imagem'),'carro.jpg','image/jpeg')})
        self.assertEqual(response.status_code, 400)
        for i in range(20):
            db.session.add(FotoVeiculo(veiculo_id=self.v.id, filename=str(i)+'.jpg', ordem=i))
        db.session.commit()
        response = self.post(f'/veiculos/{self.v.id}/fotos', {'fotos':(foto_bytes(),'carro.jpg','image/jpeg')})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FotoVeiculo.query.count(), 20)

    def test_ordenacao_rejeita_fotos_de_outro_usuario(self):
        self.login()
        db.session.add(FotoVeiculo(veiculo_id=self.v.id, filename='1.jpg', ordem=0))
        db.session.commit()
        self.assertEqual(self.post(f'/veiculos/{self.v.id}/fotos/ordenar', json_data={'ordem':[999]}).status_code, 400)
        foto = FotoVeiculo.query.one()
        self.assertEqual(self.post(f'/veiculos/{self.v.id}/fotos/ordenar', json_data={'ordem':[foto.id]}).status_code, 200)

    def test_ocr_exige_consentimento_e_credenciais(self):
        self.login()
        self.assertEqual(self.post('/documentos/cnh', {'documentos':(foto_bytes(),'cnh.jpg','image/jpeg')}).status_code, 400)
        self.assertEqual(self.post('/documentos/cnh', {'consentimento':'sim','documentos':(foto_bytes(),'cnh.jpg','image/jpeg')}).status_code, 503)
        self.network.assert_not_called()

    def test_ocr_resposta_estruturada_sem_persistencia(self):
        self.login()
        self.app.config.update(OPENAI_API_KEY='chave-teste', OPENAI_VISION_MODEL='modelo-teste')
        campos = dict(nome='Nome Extraído', cpf=None, data_nascimento=None, cnh_numero=None,
                      cnh_categoria='B', cnh_validade='2027-01-01', cnh_primeira_habilitacao=None)
        retorno = Mock()
        retorno.json.return_value = {'status':'completed', 'output':[{'content':[{'type':'output_text','text':json.dumps(campos)}]}]}
        with patch('services.documento_service.requests.post', return_value=retorno) as gateway:
            response = self.post('/documentos/cnh', {'consentimento':'sim','documentos':(foto_bytes(),'cnh.jpg','image/jpeg')})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['campos']['nome'], 'Nome Extraído')
            self.assertFalse(gateway.call_args.kwargs['json']['store'])
        self.assertEqual(Condutor.query.count(), 0)
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_ocr_mime_forjado_rejeitado(self):
        self.login()
        self.app.config.update(OPENAI_API_KEY='chave-teste', OPENAI_VISION_MODEL='modelo-teste')
        response = self.post('/documentos/crlv', {'consentimento':'sim','documentos':(foto_bytes(),'falso.png','image/png')})
        self.assertEqual(response.status_code, 400)
        self.network.assert_not_called()

    def test_alertas_cnh_crlv_seguro_e_isolamento(self):
        hoje = date(2026,10,24)
        db.session.add(Condutor(user_id=self.user.id, nome='Condutor', cnh_validade=hoje+timedelta(days=60)))
        self.v.crlv_validade = hoje+timedelta(days=15)
        self.v.seguro_validade = hoje-timedelta(days=1)
        db.session.commit()
        alertas = listar_alertas(self.user.id, hoje)
        self.assertEqual(len(alertas),3)
        self.assertEqual(listar_alertas(self.outro.id, hoje),[])
        self.assertEqual(listar_alertas(self.user.id, hoje)[0]['chave'], alertas[0]['chave'])

    def test_envio_alerta_opt_in_e_deduplicacao(self):
        self.user.plano = 'pro'
        db.session.add(Condutor(user_id=self.user.id, nome='Condutor', cnh_validade=date.today()+timedelta(days=15)))
        db.session.commit()
        with patch('services.email_service.enviar_email') as sender:
            self.assertEqual(processar_alertas(),0)
            db.session.add(PreferenciaAlerta(user_id=self.user.id, email=True))
            db.session.commit()
            self.assertEqual(processar_alertas(),1)
            self.assertEqual(processar_alertas(),0)
            sender.assert_called_once()
        self.assertEqual(EnvioAlerta.query.one().status, 'enviado')

    def test_push_rejeita_destinos_internos(self):
        for endpoint in ('http://localhost/', 'https://127.0.0.1/', 'https://fcm.googleapis.com@127.0.0.1/'):
            with self.assertRaises(ValueError):
                validar_subscription({'endpoint':endpoint,'keys':{'p256dh':'x'*20,'auth':'x'*20}})

    def test_google_nao_vincula_conta_sem_posse_local(self):
        token = {'userinfo':{'sub':'google-sub','email':self.user.email,'email_verified':True,'name':'Nome'}}
        with patch('blueprints.auth.google.oauth') as oauth:
            oauth.google.authorize_access_token.return_value = token
            response = self.client.get('/auth/google/callback')
            self.assertEqual(response.status_code,302)
            self.assertIsNone(self.user.google_id)
        self.assertFalse(self._logged())

    def test_google_cria_conta_sem_senha_e_trial(self):
        token = {'userinfo':{'sub':'google-sub','email':'novo@example.test','email_verified':True,'name':'Novo'}}
        with patch('blueprints.auth.google.oauth') as oauth:
            oauth.google.authorize_access_token.return_value = token
            self.assertEqual(self.client.get('/auth/google/callback').status_code,302)
        user = User.query.filter_by(google_id='google-sub').one()
        self.assertFalse(user.check_password('qualquer'))
        self.assertTrue(user.email_confirmado)
        self.assertEqual(user.plano_efetivo,'pro')

    def test_google_rejeita_email_nao_verificado(self):
        with patch('blueprints.auth.google.oauth') as oauth:
            oauth.google.authorize_access_token.return_value = {'userinfo':{'sub':'g','email':'novo@example.test','email_verified':False}}
            self.client.get('/auth/google/callback')
        self.assertEqual(User.query.count(),2)
        self.assertFalse(self._logged())

    def _registrar_passkey(self, origem='https://autoviu.test'):
        self.login()
        options = self.post('/auth/webauthn/register/begin', json_data={}).json
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        public = self.private_key.public_key().public_numbers()
        self.credential_id = b'credencial-testes-autoviu'
        cose = cbor2.dumps({1:2,3:-7,-1:1,-2:public.x.to_bytes(32,'big'),-3:public.y.to_bytes(32,'big')})
        auth_data = hashlib.sha256(b'autoviu.test').digest()+bytes([0x45])+(0).to_bytes(4,'big')+bytes(16)+len(self.credential_id).to_bytes(2,'big')+self.credential_id+cose
        client_data = json.dumps({'type':'webauthn.create','challenge':options['challenge'],'origin':origem,'crossOrigin':False}).encode()
        credential = {'id':b64(self.credential_id),'rawId':b64(self.credential_id),'type':'public-key',
            'response':{'clientDataJSON':b64(client_data),'attestationObject':b64(cbor2.dumps({'fmt':'none','attStmt':{},'authData':auth_data}))}}
        return self.post('/auth/webauthn/register/finish', json_data={'credential':credential,'nome':'Dispositivo Teste'})

    def test_passkey_registro_e_login_com_assinatura_real(self):
        self.assertEqual(self._registrar_passkey().status_code,200)
        self.assertEqual(WebAuthnCredential.query.count(),1)
        self.client.get('/auth/logout')
        options = self.post('/auth/webauthn/login/begin', json_data={}).json
        client_data = json.dumps({'type':'webauthn.get','challenge':options['challenge'],'origin':'https://autoviu.test','crossOrigin':False}).encode()
        auth_data = hashlib.sha256(b'autoviu.test').digest()+bytes([0x05])+(1).to_bytes(4,'big')
        signature = self.private_key.sign(auth_data+hashlib.sha256(client_data).digest(),ec.ECDSA(hashes.SHA256()))
        credential = {'id':b64(self.credential_id),'rawId':b64(self.credential_id),'type':'public-key',
            'response':{'clientDataJSON':b64(client_data),'authenticatorData':b64(auth_data),
                        'signature':b64(signature),'userHandle':b64(str(self.user.id).encode())}}
        response = self.post('/auth/webauthn/login/finish', json_data=credential)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(WebAuthnCredential.query.one().sign_count,1)
        self.assertEqual(self.post('/auth/webauthn/login/finish', json_data=credential).status_code,400)

    def test_passkey_rejeita_origem_incorreta(self):
        self.assertEqual(self._registrar_passkey('https://falso.test').status_code,400)
        self.assertEqual(WebAuthnCredential.query.count(),0)

    def test_passkey_desafio_expira_e_remocao_exige_senha(self):
        self.login()
        self.post('/auth/webauthn/register/begin', json_data={})
        WebAuthnDesafio.query.update({'expira_em':datetime.utcnow()-timedelta(seconds=1)})
        db.session.commit()
        self.assertEqual(self.post('/auth/webauthn/register/finish',json_data={}).status_code,400)
        self.assertEqual(self._registrar_passkey().status_code,200)
        cred = WebAuthnCredential.query.one()
        self.assertEqual(self.post(f'/auth/webauthn/{cred.id}/remover',json_data={'senha':'errada'}).status_code,400)
        self.assertEqual(self.post(f'/auth/webauthn/{cred.id}/remover',json_data={'senha':'senha-local-segura'}).status_code,200)

    def test_csrf_novas_rotas(self):
        self.login()
        for rota in ['/condutor/', '/alertas/', '/documentos/cnh', f'/veiculos/{self.v.id}/fotos', '/plano/contratar', '/auth/webauthn/register/begin']:
            self.assertEqual(self.client.post(rota,data={}).status_code,400,rota)


if __name__ == '__main__':
    unittest.main()
