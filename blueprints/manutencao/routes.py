from flask import Blueprint, redirect, url_for, request, flash, abort, current_app, jsonify
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models import Manutencao
from services.veiculo_helper import get_veiculo_ativo
from services.manutencao_service import validar_manutencao

manutencao_bp = Blueprint('manutencao', __name__)


def _responder(mensagem, categoria='success', status=200, destino='main.index', formulario=None):
    if request.accept_mimetypes.best == 'application/json':
        return jsonify(ok=status < 400, mensagem=mensagem, destino=url_for(destino)), status
    if status == 422 and formulario:
        from blueprints.main.routes import renderizar_dashboard
        return renderizar_dashboard(formulario_manutencao=formulario,
                                   dados_manutencao=request.form,
                                   erro_manutencao=mensagem), status
    flash(mensagem, categoria)
    return redirect(url_for(destino))


@manutencao_bp.route('/add', methods=['POST'])
@login_required
def add_manutencao():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        return _responder('Selecione um veículo antes de registrar a manutenção.', 'danger', 409, 'veiculo.index')
    if request.form.get('veiculo_id') not in (None, str(veiculo.id)):
        return _responder('O veículo ativo mudou. Confira o veículo selecionado antes de registrar novamente.', 'danger', 409)
    try:
        m = Manutencao(veiculo_id=veiculo.id, **validar_manutencao(request.form))
        db.session.add(m)
        db.session.commit()
        return _responder('Manutenção registrada!')
    except ValueError as erro:
        db.session.rollback()
        return _responder(str(erro), 'danger', 422, formulario='nova')
    except SQLAlchemyError as erro:
        db.session.rollback()
        current_app.logger.warning('Falha ao cadastrar manutenção: %s', type(erro).__name__)
        return _responder('Não foi possível confirmar o registro. Confira a agenda antes de tentar novamente.', 'danger', 503)


@manutencao_bp.route('/concluir/<int:id>', methods=['POST'])
@login_required
def concluir_manutencao(id):
    veiculo = get_veiculo_ativo()
    if not veiculo:
        abort(404)
    if request.form.get('veiculo_id') not in (None, str(veiculo.id)):
        return _responder('O veículo ativo mudou. Confira o veículo selecionado antes de concluir.', 'danger', 409)
    m = Manutencao.query.filter_by(id=id, veiculo_id=veiculo.id).with_for_update().first_or_404()
    if m.status == 'realizada':
        return _responder('Esta manutenção já foi concluída.', 'info')
    try:
        campos = validar_manutencao(request.form, existente=m)
        for campo, valor in campos.items():
            setattr(m, campo, valor)
        db.session.commit()
        return _responder('Manutenção concluída!')
    except ValueError as erro:
        db.session.rollback()
        return _responder(str(erro), 'danger', 422, formulario=f'concluir-{id}')
    except SQLAlchemyError as erro:
        db.session.rollback()
        current_app.logger.warning('Falha ao concluir manutenção: %s', type(erro).__name__)
        return _responder('Não foi possível confirmar a conclusão. Confira a agenda antes de tentar novamente.', 'danger', 503)


@manutencao_bp.route('/editar/<int:id>', methods=['POST'])
@login_required
def editar_manutencao(id):
    veiculo = get_veiculo_ativo()
    m = db.session.get(Manutencao, id)
    if not m or not veiculo or m.veiculo_id != veiculo.id:
        abort(404)
    try:
        campos = validar_manutencao(request.form)
        for campo, valor in campos.items():
            setattr(m, campo, valor)
        db.session.commit()
        flash('Manutenção atualizada!', 'success')
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    except SQLAlchemyError as erro:
        db.session.rollback()
        current_app.logger.warning('Falha ao editar manutenção: %s', type(erro).__name__)
        flash('Não foi possível atualizar a manutenção. Tente novamente.', 'danger')
    return redirect(url_for('main.index'))


@manutencao_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_manutencao(id):
    veiculo = get_veiculo_ativo()
    m = db.session.get(Manutencao, id)
    if not m or not veiculo or m.veiculo_id != veiculo.id:
        abort(404)
    try:
        db.session.delete(m)
        db.session.commit()
        flash('Manutenção removida!', 'success')
    except SQLAlchemyError as erro:
        db.session.rollback()
        current_app.logger.warning('Falha ao remover manutenção: %s', type(erro).__name__)
        flash('Não foi possível remover a manutenção. Tente novamente.', 'danger')
    return redirect(url_for('main.index'))
