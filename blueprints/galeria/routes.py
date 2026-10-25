from flask import Blueprint, render_template, request, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from extensions import db, limiter
from models import Veiculo, FotoVeiculo
from services.dashboard_service import get_custo_por_km, get_consumo_medio
from services.foto_service import preparar_foto, salvar_foto, remover_foto, pasta_fotos

galeria_bp = Blueprint('galeria', __name__)


def _veiculo(id, bloquear=False):
    query = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True)
    return (query.with_for_update() if bloquear else query).first_or_404()


@galeria_bp.route('/<int:id>/fotos')
@login_required
def index(id):
    veiculo = _veiculo(id)
    return render_template('veiculos/galeria.html', veiculo=veiculo,
        custo=get_custo_por_km(id), consumo=get_consumo_medio(id),
        fotos=FotoVeiculo.query.filter_by(veiculo_id=id).order_by(FotoVeiculo.ordem, FotoVeiculo.id).all())


@galeria_bp.route('/<int:id>/fotos', methods=['POST'])
@login_required
@limiter.limit('60/hour', key_func=lambda: str(current_user.id))
def upload(id):
    _veiculo(id)
    arquivos = request.files.getlist('fotos')
    if not 1 <= len(arquivos) <= 20:
        return jsonify(erro='Selecione de 1 a 20 fotos.'), 400
    salvos = []
    try:
        preparadas = [preparar_foto(a) for a in arquivos]
        _veiculo(id, bloquear=True)
        existentes = len(FotoVeiculo.query.filter_by(veiculo_id=id).with_for_update().all())
        if existentes + len(preparadas) > 20:
            raise ValueError('O limite é de 20 fotos por veículo.')
        for posicao, preparada in enumerate(preparadas, existentes):
            filename = salvar_foto(id, preparada)
            salvos.append(filename)
            db.session.add(FotoVeiculo(veiculo_id=id, filename=filename, ordem=posicao))
        db.session.commit()
        return jsonify(ok=True), 201
    except ValueError as erro:
        db.session.rollback()
        return jsonify(erro=str(erro)), 400
    except (OSError, SQLAlchemyError):
        db.session.rollback()
        for filename in salvos:
            remover_foto(id, filename)
        return jsonify(erro='Não foi possível salvar as fotos. Tente novamente.'), 503


@galeria_bp.route('/<int:id>/fotos/<int:foto_id>/imagem')
@login_required
def imagem(id, foto_id):
    _veiculo(id)
    foto = FotoVeiculo.query.filter_by(id=foto_id, veiculo_id=id).first_or_404()
    nome = foto.filename[:-4] + '_thumb.jpg' if request.args.get('thumb') == '1' else foto.filename
    arquivo = pasta_fotos(id) / nome
    if not arquivo.is_file():
        abort(404)
    resposta = send_file(arquivo, mimetype='image/jpeg', max_age=0)
    resposta.headers['Cache-Control'] = 'private, no-store'
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    return resposta


@galeria_bp.route('/<int:id>/fotos/<int:foto_id>', methods=['POST'])
@login_required
def atualizar(id, foto_id):
    _veiculo(id, bloquear=True)
    foto = FotoVeiculo.query.filter_by(id=foto_id, veiculo_id=id).first_or_404()
    dados = request.get_json(silent=True) or {}
    if not isinstance(dados, dict):
        return jsonify(erro='Envie um objeto JSON válido.'), 400
    legenda = dados.get('legenda', '')
    if not isinstance(legenda, str) or len(legenda) > 200:
        return jsonify(erro='A legenda deve ter até 200 caracteres.'), 400
    foto.legenda = legenda.strip()
    db.session.commit()
    return jsonify(ok=True)


@galeria_bp.route('/<int:id>/fotos/ordenar', methods=['POST'])
@login_required
def ordenar(id):
    _veiculo(id, bloquear=True)
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(erro='Envie um objeto JSON válido.'), 400
    ordem = dados.get('ordem')
    fotos = FotoVeiculo.query.filter_by(veiculo_id=id).all()
    if not isinstance(ordem, list) or any(type(i) is not int for i in ordem) or len(ordem) != len(fotos) or set(ordem) != {f.id for f in fotos}:
        return jsonify(erro='Envie cada foto do veículo uma única vez.'), 400
    for foto in fotos:
        foto.ordem = ordem.index(foto.id)
    db.session.commit()
    return jsonify(ok=True)


@galeria_bp.route('/<int:id>/fotos/<int:foto_id>/remover', methods=['POST'])
@login_required
def remover(id, foto_id):
    _veiculo(id, bloquear=True)
    foto = FotoVeiculo.query.filter_by(id=foto_id, veiculo_id=id).first_or_404()
    filename = foto.filename
    db.session.delete(foto)
    db.session.commit()
    try:
        remover_foto(id, filename)
    except OSError:
        current_app.logger.error('Falha na limpeza de foto removida')
    fotos = FotoVeiculo.query.filter_by(veiculo_id=id).order_by(FotoVeiculo.ordem, FotoVeiculo.id).all()
    for ordem, item in enumerate(fotos):
        item.ordem = ordem
    db.session.commit()
    return jsonify(ok=True)
