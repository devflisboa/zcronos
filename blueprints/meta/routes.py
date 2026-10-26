from flask import Blueprint, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import MetaGasto, Veiculo, Categoria
from services.veiculo_helper import get_veiculo_ativo

meta_bp = Blueprint('meta', __name__)


@meta_bp.route('/add', methods=['POST'])
@login_required
def add_meta():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Selecione um veículo.', 'info')
        return redirect(url_for('veiculo.index'))
    tipo = request.form.get('tipo', 'categoria')
    if tipo not in ('total', 'combustivel', 'categoria'):
        flash('Tipo inválido.', 'danger')
        return redirect(url_for('main.index'))
    try:
        valor = float(request.form.get('valor_limite', 0))
        if valor <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash('Valor limite inválido.', 'danger')
        return redirect(url_for('main.index'))
    categoria_id = None
    if tipo == 'categoria':
        try:
            categoria_id = int(request.form.get('categoria_id', 0))
            cat = Categoria.query.get(categoria_id)
            if not cat:
                raise ValueError
        except (ValueError, TypeError):
            flash('Categoria inválida.', 'danger')
            return redirect(url_for('main.index'))
    meta = MetaGasto(veiculo_id=veiculo.id, tipo=tipo, valor_limite=valor, categoria_id=categoria_id)
    db.session.add(meta)
    db.session.commit()
    flash('Meta adicionada!', 'success')
    return redirect(url_for('main.index') + '#sec-analise')


@meta_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_meta(id):
    meta = MetaGasto.query.get_or_404(id)
    veiculo = Veiculo.query.filter_by(id=meta.veiculo_id, user_id=current_user.id, ativo=True).first()
    if not veiculo:
        abort(404)
    db.session.delete(meta)
    db.session.commit()
    flash('Meta removida.', 'success')
    return redirect(url_for('main.index') + '#sec-analise')
