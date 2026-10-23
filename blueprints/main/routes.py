import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from extensions import db
from models import Despesa, Categoria, Abastecimento, Manutencao, Veiculo
from services.dashboard_service import get_dashboard_data

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    data = get_dashboard_data()
    data['gastos_por_mes_json'] = json.dumps(data['gastos_por_mes'])
    data['gastos_por_categoria_json'] = json.dumps(data['gastos_por_categoria'])
    data['combustivel_por_mes_json'] = json.dumps(data['combustivel_por_mes'])
    data['current_date'] = datetime.now().strftime('%d/%m/%Y')
    return render_template('index.html', **data)


@main_bp.route('/veiculo/editar', methods=['POST'])
@login_required
def editar_veiculo():
    veiculo = Veiculo.query.first()
    if not veiculo:
        veiculo = Veiculo()
        db.session.add(veiculo)
    veiculo.marca = request.form.get('marca', veiculo.marca)
    veiculo.modelo = request.form.get('modelo', veiculo.modelo)
    veiculo.versao = request.form.get('versao', veiculo.versao)
    veiculo.motor = request.form.get('motor', veiculo.motor)
    veiculo.ano = request.form.get('ano', veiculo.ano)
    veiculo.placa = request.form.get('placa', veiculo.placa)
    veiculo.cor = request.form.get('cor', veiculo.cor)
    veiculo.km_atual = request.form.get('km_atual', veiculo.km_atual)
    veiculo.valor_compra = request.form.get('valor_compra', veiculo.valor_compra)
    veiculo.valor_atual = request.form.get('valor_atual', veiculo.valor_atual)
    try:
        db.session.commit()
        flash('Veículo atualizado!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {e}', 'danger')
    return redirect(url_for('main.index'))


@main_bp.route('/km/atualizar', methods=['POST'])
@login_required
def atualizar_km():
    veiculo = Veiculo.query.first()
    if veiculo:
        novo_km = request.form.get('km_atual')
        if novo_km:
            veiculo.km_atual = int(novo_km)
            db.session.commit()
            flash('Quilometragem atualizada!', 'success')
    return redirect(url_for('main.index'))
