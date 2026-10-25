import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadData
from sqlalchemy.exc import SQLAlchemyError
from extensions import db, limiter
from models import Veiculo
from services.veiculo_helper import get_veiculo_ativo
from services import fipe_service as fipe

fipe_bp = Blueprint('fipe', __name__)


def _identidade(veiculo):
    dados = [veiculo.marca, veiculo.modelo, veiculo.versao, veiculo.ano]
    return hashlib.sha256(json.dumps(dados, ensure_ascii=False).encode()).hexdigest()


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='autoviu-fipe-v1')


def _veiculo(modo):
    if modo != 'meu':
        return None
    ident = request.args.get('veiculo_id')
    if ident is not None:
        return Veiculo.query.filter_by(id=ident, user_id=current_user.id, ativo=True).first_or_404()
    return get_veiculo_ativo()


@fipe_bp.route('/')
@login_required
@limiter.limit('60/hour', key_func=lambda: str(current_user.id))
def index():
    pergunta = request.args.get('pergunta', '').strip()
    modo = request.args.get('modo')
    alvo = ''
    erro = None
    if pergunta:
        try:
            intencao, alvo = fipe.interpretar_pergunta(pergunta)
            modo = modo or intencao
        except ValueError as exc:
            erro = str(exc)
    modo = modo or 'outro'
    if modo not in ('meu', 'outro'):
        modo, erro = 'outro', 'Escolha consultar seu carro ou outro veículo.'
    veiculo = _veiculo(modo)
    tipo = request.args.get('tipo', veiculo.fipe_tipo if veiculo else 'cars') or 'cars'
    marca = request.args.get('marca', '')
    modelo = request.args.get('modelo', '')
    ano = request.args.get('ano', '')
    # Seleções salvas só são retomadas quando a consulta não trouxe novos filtros.
    if veiculo and not any(c in request.args for c in ('tipo', 'marca', 'modelo', 'ano')):
        marca, modelo, ano = veiculo.fipe_marca_id or '', veiculo.fipe_modelo_id or '', veiculo.fipe_ano_id or ''
    referencia = cotacao = token = None
    marcas, modelos, anos = [], [], []
    consulta = request.args.get('busca', alvo or (veiculo.modelo if veiculo else '') or '').strip()[:100]
    if modo == 'meu' and not veiculo:
        erro = 'Selecione ou cadastre seu veículo para consultar seu carro. Você também pode consultar outro veículo sem cadastrá-lo.'
    if not erro:
        try:
            referencia = fipe.referencia_atual()
            marcas = fipe.marcas(tipo, referencia['code'])
            if not marca:
                nome_marca = fipe.normalizar(veiculo.marca) if veiculo else ''
                candidatas = [m for m in marcas if nome_marca and (fipe.normalizar(m['name']) == nome_marca or fipe.normalizar(m['name'].split(' - ')[0]) == nome_marca)]
                if not candidatas and alvo:
                    texto_alvo = ' ' + fipe.normalizar(alvo) + ' '
                    candidatas = [m for m in marcas if any(' ' + nome + ' ' in texto_alvo for nome in (
                        fipe.normalizar(m['name']), fipe.normalizar(m['name'].split(' - ')[0])))]
                if len(candidatas) == 1:
                    marca = candidatas[0]['code']
            if marca:
                if marca not in {m['code'] for m in marcas}:
                    raise ValueError('Marca não encontrada na referência atual. Selecione novamente.')
                modelos = fipe.modelos(tipo, marca, referencia['code'])
                if modelo:
                    if modelo not in {m['code'] for m in modelos}:
                        raise ValueError('Modelo não encontrado para a marca selecionada.')
                    anos = fipe.anos(tipo, marca, modelo, referencia['code'])
                    if ano:
                        if ano not in {a['code'] for a in anos}:
                            raise ValueError('Ano/combustível não encontrado para essa versão.')
                        cotacao = fipe.consultar_valor(tipo, marca, modelo, ano, referencia)
                        cotacao['consulta_formatada'] = datetime.fromisoformat(cotacao['consultado_em']).strftime('%d/%m/%Y %H:%M UTC')
                        if veiculo:
                            token = _serializer().dumps({'user_id':current_user.id, 'veiculo_id':veiculo.id,
                                'identidade':_identidade(veiculo), 'cotacao':cotacao})
        except (ValueError, fipe.FipeIndisponivel) as exc:
            erro = str(exc)
    # O filtro é local: não percorre marcas nem dispara dezenas de consultas externas.
    termos = [t for t in fipe.normalizar(consulta).split() if not re.fullmatch(r'(19|20)\d{2}', t)]
    marcas_no_alvo = {termo for m in marcas if m['code'] == marca for termo in fipe.normalizar(m['name']).split()}
    termos = [t for t in termos if t not in marcas_no_alvo]
    filtrados = [m for m in modelos if all(t in fipe.normalizar(m['name']) for t in termos)] if termos else modelos
    return render_template('fipe/index.html', modo=modo, veiculo=veiculo, pergunta=pergunta,
        tipos=fipe.TIPOS, tipo=tipo, marca=marca, modelo=modelo, ano=ano, busca=consulta,
        marcas=marcas, modelos=modelos, filtrados=filtrados, anos=anos, erro=erro,
        referencia=referencia, cotacao=cotacao, cotacao_token=token)


@fipe_bp.route('/<int:id>/confirmar', methods=['POST'])
@login_required
@limiter.limit('20/hour', key_func=lambda: str(current_user.id))
def confirmar(id):
    veiculo = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).with_for_update().first_or_404()
    try:
        dados = _serializer().loads(request.form.get('cotacao_token', ''), max_age=900)
        if not isinstance(dados, dict) or dados.get('user_id') != current_user.id or dados.get('veiculo_id') != id or dados.get('identidade') != _identidade(veiculo):
            raise ValueError('A consulta não corresponde ao veículo atual. Consulte novamente.')
        if request.form.get('confirmar') != 'sim':
            raise ValueError('Confirme a versão do veículo antes de salvar a referência.')
        cotacao = dados['cotacao']
        if request.form.get('atualizar_valor') == 'sim' and not fipe.referencia_vigente(cotacao['referencia']):
            raise ValueError('A referência não é do mês atual. O valor estimado foi preservado.')
        veiculo.fipe_tipo = cotacao['tipo']
        veiculo.fipe_marca_id = cotacao['marca_id']
        veiculo.fipe_modelo_id = cotacao['modelo_id']
        veiculo.fipe_ano_id = cotacao['ano_id']
        veiculo.fipe_codigo = cotacao['codigo']
        veiculo.fipe_referencia = cotacao['referencia']
        veiculo.fipe_valor = Decimal(cotacao['valor'])
        veiculo.fipe_consultado_em = datetime.fromisoformat(cotacao['consultado_em']).astimezone(timezone.utc).replace(tzinfo=None)
        atualizar = request.form.get('atualizar_valor') == 'sim'
        if atualizar:
            veiculo.valor_atual = float(cotacao['valor'])
        db.session.commit()
        flash('Referência FIPE salva.' + (' Valor estimado atualizado.' if atualizar else ' Seu valor estimado foi mantido.'), 'success')
    except BadData:
        db.session.rollback()
        flash('A confirmação expirou ou é inválida. Consulte novamente antes de salvar.', 'danger')
    except (ValueError, KeyError, TypeError) as exc:
        db.session.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else 'Não foi possível confirmar a cotação.', 'danger')
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.warning('Falha ao salvar referência FIPE: %s', type(exc).__name__)
        flash('Não foi possível salvar a referência. Tente novamente.', 'danger')
    return redirect(url_for('fipe.index', modo='meu', veiculo_id=id))
