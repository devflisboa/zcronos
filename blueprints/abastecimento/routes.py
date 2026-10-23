from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from datetime import datetime
from extensions import db
from models import Abastecimento

abastecimento_bp = Blueprint('abastecimento', __name__)


@abastecimento_bp.route('/cadastrar')
@login_required
def cadastrar_abastecimento():
    return render_template('cadastrar_abastecimento.html')


@abastecimento_bp.route('/add', methods=['POST'])
@login_required
def add_abastecimento():
    try:
        novo = Abastecimento(
            quilometragem=request.form.get('quilometragem'),
            litros_abastecidos=request.form.get('litros_abastecidos'),
            valor_total=request.form.get('valor_total'),
            posto=request.form.get('posto'),
            preco_combustivel=request.form.get('preco_combustivel'),
            data=request.form.get('data'),
        )
        db.session.add(novo)
        db.session.commit()
        flash('Abastecimento adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))


@abastecimento_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_abastecimento(id):
    abastecimento = db.session.get(Abastecimento, id)
    try:
        db.session.delete(abastecimento)
        db.session.commit()
        flash('Abastecimento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))
