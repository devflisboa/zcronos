from services.plano_service import requer_plano
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from services.veiculo_helper import get_veiculo_ativo
from services.uber_corrida_service import get_estatisticas_corridas
from services.uber_semanal_service import get_estatisticas_semanais

uber_bp = Blueprint('uber', __name__)


@uber_bp.route('/estatisticas')
@login_required
@requer_plano('pro')
def estatisticas():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        return redirect(url_for('veiculo.index'))
    return render_template('estatistica.html', **get_estatisticas_corridas(veiculo.id))


@uber_bp.route('/estatistica_semanal')
@login_required
@requer_plano('pro')
def estatistica_semanal():
    return render_template('estatistica_semanal.html', stats=get_estatisticas_semanais(current_user.id))
