from flask import Blueprint, render_template
from flask_login import login_required
from services.uber_corrida_service import get_estatisticas_corridas
from services.uber_semanal_service import get_estatisticas_semanais

uber_bp = Blueprint('uber', __name__)


@uber_bp.route('/estatisticas')
@login_required
def estatisticas():
    return render_template('estatistica.html', **get_estatisticas_corridas())


@uber_bp.route('/estatistica_semanal')
@login_required
def estatistica_semanal():
    return render_template('estatistica_semanal.html', stats=get_estatisticas_semanais())
