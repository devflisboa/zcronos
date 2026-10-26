from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required
from datetime import datetime
from extensions import db
from models import Despesa, Categoria
from services.veiculo_helper import get_veiculo_ativo

despesa_bp = Blueprint('despesa', __name__)


@despesa_bp.route('/cadastrar')
@login_required
def cadastrar_despesa():
    from datetime import date
    categorias = Categoria.query.all()
    veiculo = get_veiculo_ativo()
    return render_template('cadastrar_despesas.html', categorias=categorias, veiculo=veiculo, hoje=date.today())


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

        def _float(v): return float(v) if v else None
        km_str = request.form.get('km_na_despesa')
        nova = Despesa(
            veiculo_id=veiculo.id,
            descricao=request.form.get('descricao'),
            valor=request.form.get('valor'),
            data=datetime.strptime(request.form.get('data'), '%Y-%m-%d'),
            categoria=categoria,
            quilometragem=int(km_str) if km_str else None,
            forma_pagamento=request.form.get('forma_pagamento') or None,
            observacoes=request.form.get('observacao') or None,
            latitude=_float(request.form.get('latitude')),
            longitude=_float(request.form.get('longitude')),
        )
        db.session.add(nova)
        if nova.quilometragem and (not veiculo.km_atual or nova.quilometragem > veiculo.km_atual):
            veiculo.km_atual = nova.quilometragem
        db.session.commit()
        flash('Despesa adicionada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar despesa: {e}', 'danger')
    return redirect(url_for('main.index'))


@despesa_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_despesa(id):
    from datetime import date as date_type
    veiculo = get_veiculo_ativo()
    despesa = db.session.get(Despesa, id)
    if not despesa or not veiculo or despesa.veiculo_id != veiculo.id:
        abort(404)
    categorias = Categoria.query.order_by(Categoria.nome).all()
    if request.method == 'POST':
        try:
            categoria_id = request.form.get('categoria_id')
            categoria = Categoria.query.get(int(categoria_id)) if categoria_id else None
            if not categoria:
                flash('Categoria inválida.', 'danger')
                return redirect(url_for('despesa.editar_despesa', id=id))
            def _float(v): return float(v) if v else None
            km_str = request.form.get('km_na_despesa')
            data_str = request.form.get('data')
            despesa.descricao = request.form.get('descricao')
            despesa.valor = float(request.form.get('valor') or 0)
            despesa.data = datetime.strptime(data_str, '%Y-%m-%d') if data_str else despesa.data
            despesa.categoria = categoria
            despesa.quilometragem = int(km_str) if km_str else None
            despesa.forma_pagamento = request.form.get('forma_pagamento') or None
            despesa.observacoes = request.form.get('observacao') or None
            lat = _float(request.form.get('latitude'))
            lng = _float(request.form.get('longitude'))
            if lat is not None and lng is not None:
                despesa.latitude = lat
                despesa.longitude = lng
            db.session.commit()
            flash('Despesa atualizada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar despesa: {e}', 'danger')
        return redirect(url_for('main.index'))
    return render_template('editar_despesa.html', d=despesa, veiculo=veiculo, categorias=categorias)


@despesa_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_despesa(id):
    veiculo = get_veiculo_ativo()
    despesa = db.session.get(Despesa, id)
    if not despesa or not veiculo or despesa.veiculo_id != veiculo.id:
        abort(404)
    try:
        db.session.delete(despesa)
        db.session.commit()
        flash('Despesa excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir despesa: {e}', 'danger')
    return redirect(url_for('main.index'))
