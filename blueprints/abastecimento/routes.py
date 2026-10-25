from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
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
        data_str = request.form.get('data')
        novo = Abastecimento(
            veiculo_id=veiculo.id,
            quilometragem=int(request.form.get('quilometragem') or 0),
            litros_abastecidos=float(request.form.get('litros_abastecidos') or 0),
            valor_total=float(request.form.get('valor_total') or 0),
            posto=request.form.get('posto') or '',
            preco_combustivel=float(request.form.get('preco_combustivel') or 0),
            data=date.fromisoformat(data_str) if data_str else None,
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
    if not abastecimento or not veiculo or abastecimento.veiculo_id != veiculo.id:
        abort(404)
    try:
        db.session.delete(abastecimento)
        db.session.commit()
        flash('Abastecimento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))
