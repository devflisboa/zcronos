from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from extensions import db
from models import Veiculo
from services.veiculo_helper import get_veiculo_ativo

veiculo_bp = Blueprint('veiculo', __name__)


@veiculo_bp.route('/')
@login_required
def index():
    veiculos = Veiculo.query.filter_by(user_id=current_user.id, ativo=True).all()
    ativo = get_veiculo_ativo()
    return render_template(
        'veiculos/index.html',
        veiculos=veiculos,
        veiculo_ativo_id=ativo.id if ativo else None,
        pode_adicionar=current_user.pode_adicionar_veiculo(),
    )


@veiculo_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if not current_user.pode_adicionar_veiculo():
        flash('Limite de veículos atingido para o seu plano.', 'danger')
        return redirect(url_for('veiculo.index'))

    if request.method == 'POST':
        try:
            v = Veiculo(
                user_id=current_user.id,
                ativo=True,
                marca=request.form.get('marca'),
                modelo=request.form.get('modelo'),
                versao=request.form.get('versao') or None,
                motor=request.form.get('motor') or None,
                ano=int(request.form.get('ano')) if request.form.get('ano') else None,
                placa=(request.form.get('placa') or '').upper() or None,
                cor=request.form.get('cor') or None,
                km_atual=int(request.form.get('km_atual') or 0),
                valor_compra=float(request.form.get('valor_compra')) if request.form.get('valor_compra') else None,
                valor_atual=float(request.form.get('valor_atual')) if request.form.get('valor_atual') else None,
            )
            if request.form.get('data_compra'):
                v.data_compra = datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
            db.session.add(v)
            db.session.commit()
            session['veiculo_ativo_id'] = v.id
            flash(f'{v.marca} {v.modelo} cadastrado com sucesso!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar veículo: {e}', 'danger')

    return render_template('veiculos/form.html', veiculo=None)


@veiculo_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        try:
            v.marca = request.form.get('marca') or v.marca
            v.modelo = request.form.get('modelo') or v.modelo
            v.versao = request.form.get('versao') or v.versao
            v.motor = request.form.get('motor') or v.motor
            v.ano = int(request.form.get('ano')) if request.form.get('ano') else v.ano
            v.placa = (request.form.get('placa') or v.placa or '').upper() or None
            v.cor = request.form.get('cor') or v.cor
            v.km_atual = int(request.form.get('km_atual') or v.km_atual or 0)
            if request.form.get('valor_compra'):
                v.valor_compra = float(request.form['valor_compra'])
            if request.form.get('valor_atual'):
                v.valor_atual = float(request.form['valor_atual'])
            if request.form.get('data_compra'):
                v.data_compra = datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
            db.session.commit()
            flash('Veículo atualizado!', 'success')
            return redirect(url_for('veiculo.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('veiculos/form.html', veiculo=v)


@veiculo_bp.route('/<int:id>/selecionar', methods=['POST'])
@login_required
def selecionar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    session['veiculo_ativo_id'] = v.id
    flash(f'{v.marca} {v.modelo} selecionado.', 'success')
    return redirect(url_for('main.index'))


@veiculo_bp.route('/<int:id>/deletar', methods=['POST'])
@login_required
def deletar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if session.get('veiculo_ativo_id') == v.id:
        flash('Não é possível remover o veículo ativo. Selecione outro primeiro.', 'danger')
        return redirect(url_for('veiculo.index'))
    v.ativo = False
    db.session.commit()
    flash(f'{v.marca} {v.modelo} removido.', 'success')
    return redirect(url_for('veiculo.index'))
