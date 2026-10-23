from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from datetime import datetime
from extensions import db
from models import Despesa, Categoria

despesa_bp = Blueprint('despesa', __name__)


@despesa_bp.route('/cadastrar')
@login_required
def cadastrar_despesa():
    categorias = Categoria.query.all()
    return render_template('cadastrar_despesas.html', categorias=categorias)


@despesa_bp.route('/add', methods=['POST'])
@login_required
def add_despesa():
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
    despesa = db.session.get(Despesa, id)
    try:
        db.session.delete(despesa)
        db.session.commit()
        flash('Despesa excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir despesa: {e}', 'danger')
    return redirect(url_for('main.index'))
