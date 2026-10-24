from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from datetime import datetime
from extensions import db
from models import Despesa, Categoria
from services.veiculo_helper import get_veiculo_ativo

despesa_bp = Blueprint('despesa', __name__)


@despesa_bp.route('/cadastrar')
@login_required
def cadastrar_despesa():
    categorias = Categoria.query.all()
    return render_template('cadastrar_despesas.html', categorias=categorias)


@despesa_bp.route('/add', methods=['POST'])
@login_required
def add_despesa():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Nenhum veículo ativo. Selecione um veículo primeiro.', 'danger')
        return redirect(url_for('veiculo.index'))

    categoria_id = request.form.get('categoria_id')
    if not categoria_id:
        flash('Categoria não selecionada.', 'danger')
        return redirect(url_for('despesa.cadastrar_despesa'))

    try:
        categoria = Categoria.query.get(int(categoria_id))
        if not categoria:
            flash('Categoria inválida.', 'danger')
            return redirect(url_for('despesa.cadastrar_despesa'))

        nova = Despesa(
            veiculo_id=veiculo.id,
            descricao=request.form.get('descricao'),
            valor=request.form.get('valor'),
            data=datetime.strptime(request.form.get('data'), '%Y-%m-%d'),
            categoria=categoria,
        )
        db.session.add(nova)
        db.session.commit()
        flash('Despesa adicionada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar despesa: {e}', 'danger')
    return redirect(url_for('main.index'))


@despesa_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_despesa(id):
    veiculo = get_veiculo_ativo()
    despesa = db.session.get(Despesa, id)
    if not despesa or (veiculo and despesa.veiculo_id != veiculo.id):
        flash('Registro não encontrado.', 'danger')
        return redirect(url_for('main.index'))
    try:
        db.session.delete(despesa)
        db.session.commit()
        flash('Despesa excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir despesa: {e}', 'danger')
    return redirect(url_for('main.index'))
