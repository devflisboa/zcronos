from flask import Blueprint, render_template
from services.uber_corrida_service import get_estatisticas_corridas
from services.uber_semanal_service import get_estatisticas_semanais

uber_bp = Blueprint('uber', __name__)


@uber_bp.route('/estatisticas')
def estatisticas():
    return render_template('estatistica.html', **get_estatisticas_corridas())


@uber_bp.route('/estatistica_semanal')
def estatistica_semanal():
    return render_template('estatistica_semanal.html', stats=get_estatisticas_semanais())
