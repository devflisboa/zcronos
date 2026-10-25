"""Regressões dos serviços acrescentados hoje; SQLite e rede estritamente simulada."""
import importlib.util
import unittest
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, Mock

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
import test_fase3 as base
from extensions import db
from models import Manutencao, Veiculo, Condutor, PushSubscription, EnvioAlerta
from services.alerta_service import processar_alertas, listar_alertas
from services import fipe_service as fipe
from services.manutencao_service import validar_manutencao, validar_quilometragem
from services.configuracao_service import diagnosticar_configuracao
from services.public_url import validar_origem
from services.assinatura_service import catalogo


class EntregasHojeTest(unittest.TestCase):
    setUp = base.Fase3Test.setUp
    tearDown = base.Fase3Test.tearDown
    login = base.Fase3Test.login
    token = base.Fase3Test.token
    post = base.Fase3Test.post
    _logged = base.Fase3Test._logged

    def cotacao(self):
        hoje = datetime.now(timezone.utc)
        mes = f'{fipe.MESES[hoje.month-1]} de {hoje.year}'
        return {'price':'R$ 100.000,00','brand':'Toyota','model':'Corolla XEi',
                'modelYear':2022,'fuel':'Gasolina','codeFipe':'002001-1','referenceMonth':mes}, {'code':'999','month':mes}

    def test_manutencao_valores_invalidos(self):
        for campo, valor in [('custo','NaN'),('custo','Infinity'),('custo','-1'),('custo','1.001'),
                              ('km_previsto','-1'),('km_previsto','1.5'),('km_previsto','2147483648'),
                              ('status','x'),('tipo','x'),('data_prevista','2026-02-30')]:
            with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                validar_manutencao({'tipo':'oleo','descricao':'Revisão',campo:valor})

    def test_manutencao_zero_e_campos_omitidos(self):
        m = Manutencao(custo=150, km_realizada=2000)
        self.assertEqual(validar_manutencao({'custo':'0','km_realizada':'0'},m)['custo'],0)
        self.assertEqual(validar_manutencao({},m)['custo'],150)
        self.assertEqual(validar_quilometragem('0'),0)
        with self.assertRaises(ValueError):
            validar_quilometragem('',obrigatorio=True)

    def test_cadastro_manutencao_invalido_nao_persiste(self):
        self.login()
        response = self.post('/manutencao/add',{'tipo':'oleo','descricao':'Não gravar','custo':'NaN'})
        self.assertEqual(response.status_code,422)
        self.assertEqual(Manutencao.query.count(),0)
        self.assertIn('Não gravar',response.get_data(as_text=True))

    def test_diagnostico_nao_expoe_segredos_e_perfil_nao_depende_debug(self):
        config = dict(self.app.config, DEBUG=False, ENVIRONMENT='development',
                      ASAAS_API_KEY='SEGREDO-QUE-NAO-PODE-APARECER',PUBLIC_BASE_URL='http://localhost:5087')
        resultado = diagnosticar_configuracao(config)
        self.assertNotIn('SEGREDO-QUE-NAO-PODE-APARECER',str(resultado))
        self.assertEqual(next(r for r in resultado if r['servico']=='Origem pública')['estado'],'presente')

    def test_origens_invalidas_sao_recusadas(self):
        for origem in ('https://user:senha@dominio.test','https://dominio.test/caminho',
                       'https://dominio.test?query=1','https://dominio.test#fragmento','https://dominio.test:invalida'):
            with self.subTest(origem=origem), self.assertRaises(ValueError):
                validar_origem(origem,exigir_https=True)

    def test_frota_invalida_nao_derruba_catalogo(self):
        for preco, limite in [('NaN',0),('Infinity',0),('-1',1),('0',0),('1.001',0),('39.90',-1)]:
            with self.subTest(preco=preco,limite=limite):
                self.app.config.update(FROTA_PRECO=preco,FROTA_LIMITE=limite)
                self.assertEqual(set(catalogo()),{'free','pro'})
        self.app.config.update(FROTA_PRECO='39.90',FROTA_LIMITE=0)
        self.assertEqual(catalogo()['frota']['valor'],Decimal('39.90'))

    def test_fipe_perguntas_sem_estimativa_por_ia(self):
        self.assertEqual(fipe.interpretar_pergunta('Quanto meu carro tá valendo?'),('meu',''))
        self.assertEqual(fipe.interpretar_pergunta('quanto aquele carro Toyota Corolla 2022 tá valendo?'),('outro','toyota corolla 2022'))
        with self.assertRaises(ValueError):
            fipe.interpretar_pergunta('a'*181)

    def test_fipe_cache_e_metadados(self):
        dados, referencia = self.cotacao()
        fipe._cache.clear()
        with patch('services.fipe_service.requests.get',return_value=Mock(status_code=200,json=lambda:dados)) as rede:
            primeira = fipe.consultar_valor('cars','1','101','2022-1',referencia)
            segunda = fipe.consultar_valor('cars','1','101','2022-1',referencia)
            self.assertEqual(rede.call_count,1)
            self.assertEqual(primeira['consultado_em'],segunda['consultado_em'])
            self.assertEqual(primeira['valor'],'100000.00')
            self.assertTrue(primeira['vigente'])

    def test_fipe_cotacoes_inconsistentes(self):
        original, referencia = self.cotacao()
        for campo, valor in [('price','NaN'),('price','R$ -1,00'),('modelYear',2021),
                             ('referenceMonth','janeiro de 2000'),('codeFipe','invalido')]:
            dados = dict(original,**{campo:valor})
            fipe._cache.clear()
            with self.subTest(campo=campo), patch('services.fipe_service.requests.get',
                    return_value=Mock(status_code=200,json=lambda:dados)), self.assertRaises(fipe.FipeIndisponivel):
                fipe.consultar_valor('cars','1','101','2022-1',referencia)

    def test_fipe_token_de_outro_usuario_recusado(self):
        from blueprints.fipe.routes import _serializer, _identidade
        self.login()
        dados = {'user_id':self.outro.id,'veiculo_id':self.v.id,'identidade':_identidade(self.v),'cotacao':{}}
        token = _serializer().dumps(dados)
        self.post(f'/fipe/{self.v.id}/confirmar',{'confirmar':'sim','cotacao_token':token})
        self.assertIsNone(db.session.get(Veiculo,self.v.id).fipe_codigo)

    def test_fipe_confirmacao_expirada(self):
        from blueprints.fipe.routes import _serializer, _identidade
        self.login()
        dados = {'user_id':self.user.id,'veiculo_id':self.v.id,'identidade':_identidade(self.v),'cotacao':{}}
        with patch('time.time',return_value=(datetime.now(timezone.utc)-timedelta(hours=1)).timestamp()):
            token = _serializer().dumps(dados)
        response = self.post(f'/fipe/{self.v.id}/confirmar',{'confirmar':'sim','cotacao_token':token})
        self.assertEqual(response.status_code,302)
        self.assertIsNone(db.session.get(Veiculo,self.v.id).fipe_codigo)

    def test_cache_fipe_nao_cruza_mes(self):
        fipe._cache.clear()
        with patch('services.fipe_service.datetime') as relogio, patch('services.fipe_service.requests.get',
                return_value=Mock(status_code=200,json=lambda:[])) as rede:
            relogio.now.side_effect=[datetime(2026,1,31,tzinfo=timezone.utc),datetime(2026,2,1,tzinfo=timezone.utc)]
            fipe._consultar('/references')
            fipe._consultar('/references')
            self.assertEqual(rede.call_count,2)

    def test_alertas_urgentes_e_janelas_cnh(self):
        condutor=Condutor(user_id=self.user.id,nome='Sintético',cnh_validade=date.today()+timedelta(days=60))
        db.session.add(condutor)
        db.session.commit()
        self.assertIn(':60',listar_alertas(self.user.id)[0]['chave'])
        condutor.cnh_validade=date.today()
        self.v.crlv_validade=date.today()+timedelta(days=20)
        db.session.commit()
        alertas=listar_alertas(self.user.id)
        self.assertEqual(alertas[0]['prioridade'],'urgente')
        self.assertIn('hoje',alertas[0]['texto'])

    def test_push_todos_destinos_expirados_nao_marca_como_enviado(self):
        from pywebpush import WebPushException
        import requests
        self.app.config['VAPID_PRIVATE_KEY']='mock'
        db.session.add(Condutor(user_id=self.user.id,nome='Sintético',cnh_validade=date.today()))
        db.session.add(PushSubscription(user_id=self.user.id,endpoint_hash='a'*64,dados={'endpoint':'https://fcm.googleapis.com/sintetico'}))
        db.session.commit()
        resposta=requests.Response()
        resposta.status_code=410
        with patch('pywebpush.webpush',side_effect=WebPushException('expirado',response=resposta)):
            self.assertEqual(processar_alertas(),0)
        self.assertEqual(EnvioAlerta.query.one().status,'sem_destino')
        self.assertEqual(PushSubscription.query.count(),0)


class MigracaoFipeTest(unittest.TestCase):
    def test_upgrade_idempotente_e_downgrade_preservam_valores(self):
        engine=sa.create_engine('sqlite://')
        meta=sa.MetaData()
        veiculo=sa.Table('veiculo',meta,sa.Column('id',sa.Integer,primary_key=True),sa.Column('valor_atual',sa.Float))
        meta.create_all(engine)
        spec=importlib.util.spec_from_file_location('migracao_fipe',Path(__file__).resolve().parents[1]/'migrations/versions/a004_fipe.py')
        modulo=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        with engine.begin() as conn:
            conn.execute(veiculo.insert().values(id=1,valor_atual=90000))
            with Operations.context(MigrationContext.configure(conn)):
                modulo.upgrade()
                modulo.upgrade()
                self.assertIn('fipe_codigo',{c['name'] for c in sa.inspect(conn).get_columns('veiculo')})
                modulo.downgrade()
            self.assertEqual(conn.execute(sa.select(veiculo.c.valor_atual)).scalar(),90000)
        engine.dispose()
