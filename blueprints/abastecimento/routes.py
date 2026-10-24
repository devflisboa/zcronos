from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from extensions import db
from models import Abastecimento
from services.veiculo_helper import get_veiculo_ativo

abastecimento_bp = Blueprint('abastecimento', __name__)


@abastecimento_bp.route('/cadastrar')
@login_required
def cadastrar_abastecimento():
    return render_template('cadastrar_abastecimento.html')


@abastecimento_bp.route('/add', methods=['POST'])
@login_required
def add_abastecimento():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Nenhum veículo ativo. Selecione um veículo primeiro.', 'danger')
        return redirect(url_for('veiculo.index'))
    try:
        novo = Abastecimento(
            veiculo_id=veiculo.id,
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
    veiculo = get_veiculo_ativo()
    abastecimento = db.session.get(Abastecimento, id)
    if not abastecimento or (veiculo and abastecimento.veiculo_id != veiculo.id):
        flash('Registro não encontrado.', 'danger')
        return redirect(url_for('main.index'))
    try:
        db.session.delete(abastecimento)
        db.session.commit()
        flash('Abastecimento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))
