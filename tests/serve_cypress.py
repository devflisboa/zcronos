"""Instância E2E descartável. Nunca importar pelo entrypoint de produção."""
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

if os.environ.get('AUTOVIU_E2E') != '1':
    raise RuntimeError('Inicie explicitamente com AUTOVIU_E2E=1.')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SECRET_KEY'] = 'segredo-sintetico-exclusivo-do-cypress'

import requests
from flask import jsonify, request
from app import create_app
from extensions import db, csrf
from models import User, Veiculo, Condutor, Manutencao, Despesa, Abastecimento, Assinatura, ContaCobranca, Fatura
from services.email_service import gerar_token_confirmacao, gerar_token_senha
from services.documento_service import CAMPOS
from services import fipe_service

temporario = tempfile.TemporaryDirectory(prefix='autoviu-cypress-')
estado = {}
app = create_app('development', initialize_database=False, start_scheduler=False, test_config={
    'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'DEBUG': False, 'TESTING': True,
    'BCRYPT_LOG_ROUNDS': 4, 'VEICULO_UPLOAD_ROOT': temporario.name,
    'SECRET_KEY': 'segredo-sintetico-exclusivo-do-cypress',
    'PUBLIC_BASE_URL': 'http://127.0.0.1:5087', 'SESSION_PROTECTION': None,
    'GOOGLE_CLIENT_ID': '', 'GOOGLE_CLIENT_SECRET': '',
    'OPENAI_API_KEY': 'mock', 'OPENAI_VISION_MODEL': 'mock',
    'ASAAS_API_KEY': 'mock', 'ASAAS_WEBHOOK_TOKEN': 'webhook-sintetico-cypress-1234567890',
    'VAPID_PRIVATE_KEY': '', 'VAPID_PUBLIC_KEY': '', 'WEBAUTHN_RP_ID': '',
    'ALERTAS_AUTOMATICOS': False, 'FROTA_PRECO': '', 'FROTA_LIMITE': None,
    'MAIL_SERVER': '', 'MAIL_DEFAULT_SENDER': 'teste@example.test',
})


def resposta(dados, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(dados).encode()
    result.headers['Content-Type'] = 'application/json'
    result.url = 'https://mock.example.test'
    return result


def transporte(_session, method, url, **kwargs):
    estado['chamadas'].append({'method': method.upper(), 'url': url})
    if 'fipe.parallelum.com.br/api/v2' in url:
        if estado.get('fipe_erro'):
            return resposta({}, estado['fipe_erro'])
        mes = fipe_service.MESES[date.today().month - 1]
        referencia = f'{mes} de {date.today().year}'
        if estado.get('fipe_historica'):
            referencia = 'janeiro de 2000'
        if url.endswith('/references'):
            return resposta([{'code': 999, 'month': referencia}])
        if url.endswith('/brands'):
            return resposta([{'code': '1', 'name': 'Toyota'}])
        if url.endswith('/models'):
            return resposta([{'code': '101', 'name': 'Corolla XEi 2.0 Flex'}, {'code': '102', 'name': 'Corolla GLi 1.8 Flex'}])
        if url.endswith('/years'):
            return resposta([{'code': '2022-1', 'name': '2022 Gasolina'}])
        return resposta({'price': 'R$ 100.000,00', 'brand': 'Toyota', 'model': 'Corolla XEi 2.0 Flex',
                         'modelYear': 2022, 'fuel': 'Gasolina', 'codeFipe': '002001-1', 'referenceMonth': referencia})
    if url == 'https://api.openai.com/v1/responses':
        if estado.get('ocr_erro'):
            return resposta({}, 503)
        schema = kwargs['json']['text']['format']['schema']['properties']
        dados = {campo: None for campo in schema}
        sinteticos = {'nome': 'Condutor Sintético', 'cpf': '52998224725', 'cnh_categoria': 'B',
                      'marca': 'Toyota', 'modelo': 'Corolla', 'ano': '2022', 'placa': 'ABC1D23'}
        dados.update({k: v for k, v in sinteticos.items() if k in dados})
        return resposta({'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(dados)}]}]})
    if 'asaas.com/v3' in url:
        if estado.get('asaas_sucesso'):
            pagamento = {'id':'pay_mock', 'subscription':'sub_mock', 'value':14.90,
                         'status':estado.get('pagamento_status','PENDING'), 'dueDate':date.today().isoformat(),
                         'confirmedDate':date.today().isoformat(), 'invoiceUrl':'https://sandbox.asaas.com/i/mock'}
            if url.endswith('/payments/pay_mock'):
                return resposta(pagamento)
            if url.endswith('/payments'):
                return resposta({'data':[pagamento], 'hasMore':False})
            if method.upper() == 'DELETE':
                estado['remoto_deletado'] = True
                return resposta({'deleted':True})
            if '/customers' in url:
                return resposta({'data':[{'id':'cus_mock'}]})
            return resposta({'id':'sub_mock','customer':'cus_mock','status':'ACTIVE',
                             'deleted':estado.get('remoto_deletado',False)})
        return resposta({'errors': [{'description': 'Rejeição sintética para testar preservação.'}]}, 400)
    raise AssertionError('Rede externa bloqueada no servidor E2E')


def resetar():
    db.session.remove()
    db.drop_all()
    db.create_all()
    from app import _seed_categorias
    _seed_categorias(app)
    estado.clear()
    estado.update(chamadas=[], emails=[])
    fipe_service._cache.clear()
    app.config.update(FROTA_PRECO='', FROTA_LIMITE=None, OPENAI_API_KEY='mock', OPENAI_VISION_MODEL='mock')
    for email, plano in [('teste@zcronos.local', 'superadmin'), ('b@example.test', 'free'),
                          ('vazio@example.test', 'free'), ('pro@example.test', 'pro')]:
        user = User(nome='Usuário sintético', email=email, plano=plano, ativo=True, status='ativo', email_confirmado=True)
        user.set_password('TesteSenha123!')
        db.session.add(user)
    db.session.flush()
    db.session.add_all([
        Veiculo(id=1, user_id=1, marca='Toyota', modelo='Corolla', ano=2022, ativo=True, km_atual=12000, valor_atual=90000, valor_compra=80000),
        Veiculo(id=2, user_id=1, marca='Honda', modelo='Civic', ano=2023, ativo=True, km_atual=20000),
        Veiculo(id=3, user_id=2, marca='Privado', modelo='Segredo do usuário B', ano=2023, ativo=True),
        Veiculo(id=4, user_id=4, marca='Toyota', modelo='Corolla', ano=2022, ativo=True),
        Condutor(user_id=1, nome='Condutor Cypress', cnh_validade=date.today() - timedelta(days=1)),
    ])
    db.session.flush()
    db.session.add_all([
        Manutencao(id=1, veiculo_id=1, tipo='oleo', descricao='Revisão sintética', km_previsto=10000, data_prevista=date.today(), status='pendente', custo=150),
        Manutencao(id=2, veiculo_id=3, tipo='freio', descricao='Manutenção privada B', status='pendente'),
        Despesa(id=1, veiculo_id=3, categoria_id=1, descricao='Despesa privada B', valor=120, data=date.today()),
        Abastecimento(id=1, veiculo_id=3, posto='Posto privado B', data=date.today(), quilometragem=1000, litros_abastecidos=10, valor_total=50, preco_combustivel=5),
    ])
    db.session.commit()
    shutil.rmtree(temporario.name)
    Path(temporario.name).mkdir()


@app.route('/__e2e/<acao>', methods=['GET', 'POST'])
@csrf.exempt
def controle(acao):
    if request.headers.get('X-E2E-Key') != 'somente-cypress-local':
        return jsonify(erro='Controle exclusivo E2E'), 403
    if acao == 'reset' and request.method == 'POST':
        resetar()
    elif acao == 'cenario' and request.method == 'POST':
        dados = request.get_json() or {}
        estado.update({k: v for k, v in dados.items() if k in ('fipe_erro', 'ocr_erro', 'asaas_sucesso', 'pagamento_status', 'fipe_historica')})
        fipe_service._cache.clear()
        if dados.get('ocr_desabilitado'):
            app.config['OPENAI_API_KEY'] = ''
        if dados.get('assinatura'):
            db.session.add(ContaCobranca(user_id=2,customer_id='cus_mock'))
            db.session.add(Assinatura(id=1,user_id=2,plano='pro',status='pendente',valor=14.90,
                                      gateway_id='sub_mock',data_inicio=date.today()))
            db.session.commit()
        if dados.get('trial_expirado'):
            db.session.add(Assinatura(user_id=2,plano='pro',status='trial',valor=0,
                                      data_inicio=date.today()-timedelta(days=16),data_renovacao=date.today()-timedelta(days=1)))
            db.session.commit()
    elif acao == 'tokens':
        user = User.query.filter_by(email=request.args.get('email')).first_or_404()
        return jsonify(confirmacao=gerar_token_confirmacao(user), senha=gerar_token_senha(user))
    elif acao != 'estado':
        return jsonify(erro='Ação inválida'), 404
    return jsonify(ambiente='autoviu-cypress-descartavel', chamadas=estado['chamadas'], emails=len(estado['emails']))


patch('requests.sessions.Session.request', transporte).start()
patch('smtplib.SMTP', side_effect=AssertionError('SMTP real bloqueado em E2E')).start()
patch('services.email_service.enviar_mensagem', lambda mensagem: estado['emails'].append(mensagem)).start()
with app.app_context():
    resetar()

if __name__ == '__main__':
    app.run(host=os.environ.get('E2E_BIND', '127.0.0.1'), port=int(os.environ.get('E2E_PORT', '5087')),
            debug=False, use_reloader=False, threaded=False)
