from flask import Blueprint, redirect, url_for, request, flash
from datetime import datetime
from extensions import db
from models import Manutencao

manutencao_bp = Blueprint('manutencao', __name__)


@manutencao_bp.route('/add', methods=['POST'])
def add_manutencao():
    try:
        m = Manutencao(
            tipo=request.form.get('tipo'),
            descricao=request.form.get('descricao'),
            data_realizada=datetime.strptime(request.form['data_realizada'], '%Y-%m-%d').date()
            if request.form.get('data_realizada') else None,
            km_realizada=request.form.get('km_realizada') or None,
            data_prevista=datetime.strptime(request.form['data_prevista'], '%Y-%m-%d').date()
            if request.form.get('data_prevista') else None,
            km_previsto=request.form.get('km_previsto') or None,
            custo=float(request.form.get('custo') or 0),
            status=request.form.get('status', 'pendente'),
            observacoes=request.form.get('observacoes'),
        )
        db.session.add(m)
        db.session.commit()
        flash('Manutenção registrada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {e}', 'danger')
    return redirect(url_for('main.index'))


@manutencao_bp.route('/concluir/<int:id>', methods=['POST'])
def concluir_manutencao(id):
    m = db.session.get(Manutencao, id)
    if m:
        m.status = 'realizada'
        m.data_realizada = datetime.strptime(request.form['data_realizada'], '%Y-%m-%d').date() \
            if request.form.get('data_realizada') else datetime.today().date()
        m.km_realizada = request.form.get('km_realizada') or m.km_realizada
        m.custo = float(request.form.get('custo') or m.custo or 0)
        db.session.commit()
        flash('Manutenção concluída!', 'success')
    return redirect(url_for('main.index'))


@manutencao_bp.route('/delete/<int:id>', methods=['POST'])
def delete_manutencao(id):
    m = db.session.get(Manutencao, id)
    if m:
        db.session.delete(m)
        db.session.commit()
        flash('Manutenção removida!', 'success')
    return redirect(url_for('main.index'))
