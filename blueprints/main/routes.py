import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db, limiter
from models import Despesa, Categoria, Abastecimento, Manutencao, Veiculo
from services.dashboard_service import get_dashboard_data
from services.veiculo_helper import get_veiculo_ativo
from services.placa import normalizar_placa
from services.cadastro_service import destino_inicial
from services.manutencao_service import validar_quilometragem
from sqlalchemy.exc import SQLAlchemyError

main_bp = Blueprint('main', __name__)


@main_bp.route('/sw.js')
@limiter.exempt
def service_worker():
    """Service worker do PWA — servido na raiz para ter escopo '/'."""
    resp = send_from_directory(current_app.static_folder, 'sw.js', mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@main_bp.route('/')
@login_required
def index():
    return renderizar_dashboard()


def renderizar_dashboard(**contexto):
    veiculo = get_veiculo_ativo()
    if not veiculo:
        return redirect(destino_inicial(current_user))
    data = get_dashboard_data(veiculo.id)
    data['gastos_por_mes_json'] = json.dumps(data['gastos_por_mes'])
    data['gastos_por_categoria_json'] = json.dumps(data['gastos_por_categoria'])
    data['combustivel_por_mes_json'] = json.dumps(data['combustivel_por_mes'])
    data['consumo_json'] = json.dumps([
        {'data': a['data'], 'consumo': a['consumo'], 'posto': a['posto'] or ''}
        for a in reversed(data['abastecimentos']) if a['consumo'] is not None
    ])
    data['current_date'] = datetime.now().strftime('%d/%m/%Y')
    data.update(contexto)
    return render_template('index.html', **data)


@main_bp.route('/veiculo/editar', methods=['POST'])
@login_required
def editar_veiculo():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Nenhum veículo ativo selecionado.', 'danger')
        return redirect(url_for('veiculo.index'))
    try:
        from services.veiculo_service import validar_veiculo
        for campo, valor in validar_veiculo(request.form, veiculo).items():
            setattr(veiculo, campo, valor)
        db.session.commit()
        flash('Veículo atualizado!', 'success')
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    except Exception as erro:
        db.session.rollback()
        current_app.logger.error('Falha ao atualizar veículo: %s', type(erro).__name__)
        flash('Não foi possível atualizar o veículo. Tente novamente.', 'danger')
    return redirect(url_for('main.index'))


@main_bp.route('/km/atualizar', methods=['POST'])
@login_required
def atualizar_km():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Selecione um veículo para atualizar a quilometragem.', 'info')
        return redirect(url_for('veiculo.index'))
    try:
        novo_km = validar_quilometragem(request.form.get('km_atual'), obrigatorio=True)
        veiculo.km_atual = novo_km
        db.session.commit()
        flash('Quilometragem atualizada!', 'success')
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), 'danger')
    except SQLAlchemyError as erro:
        db.session.rollback()
        current_app.logger.warning('Falha ao atualizar quilometragem: %s', type(erro).__name__)
        flash('Não foi possível atualizar a quilometragem. Tente novamente.', 'danger')
    return redirect(url_for('main.index'))
