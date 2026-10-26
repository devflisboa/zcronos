import csv
import io
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from models import Veiculo, Abastecimento, Despesa, Manutencao
from services.plano_service import requer_plano
from services.dashboard_service import get_custo_mes, get_custo_ano, get_consumo_medio

relatorio_bp = Blueprint('relatorio', __name__)


@relatorio_bp.route('/')
@login_required
@requer_plano('pro')
def index():
    veiculos = Veiculo.query.filter_by(user_id=current_user.id, ativo=True).order_by(Veiculo.id).all()
    linhas = [dict(veiculo=v, custo_mes=get_custo_mes(v.id), custo_ano=get_custo_ano(v.id), consumo=get_consumo_medio(v.id)) for v in veiculos]
    return render_template('relatorios.html', linhas=linhas)


@relatorio_bp.route('/<int:id>/exportar.csv')
@login_required
@requer_plano('pro')
def exportar(id):
    Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    tipo = request.args.get('tipo', 'abastecimentos')
    modelos = {'abastecimentos': (Abastecimento, ('data', 'posto', 'quilometragem', 'litros_abastecidos', 'valor_total', 'preco_combustivel', 'tipo_combustivel', 'observacao', 'latitude', 'longitude'), 'data'),
        'despesas': (Despesa, ('data', 'descricao', 'valor', 'quilometragem', 'forma_pagamento', 'observacoes', 'latitude', 'longitude'), 'data'),
        'manutencoes': (Manutencao, ('tipo', 'descricao', 'data_realizada', 'km_realizada', 'data_prevista', 'km_previsto', 'custo', 'status'), 'data_realizada')}
    if tipo not in modelos:
        from flask import abort
        abort(400)
    from datetime import date as date_type
    model, campos, campo_data = modelos[tipo]
    q = model.query.filter_by(veiculo_id=id)
    try:
        if request.args.get('de'):
            q = q.filter(getattr(model, campo_data) >= date_type.fromisoformat(request.args['de']))
        if request.args.get('ate'):
            q = q.filter(getattr(model, campo_data) <= date_type.fromisoformat(request.args['ate']))
    except (ValueError, AttributeError):
        pass
    registros = q.order_by(model.id).all()
    saida = io.StringIO(newline='')
    writer = csv.writer(saida, delimiter=';')
    writer.writerow(campos)
    def seguro(valor):
        if isinstance(valor, str) and valor.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + valor
        return valor if valor is not None else ''
    for registro in registros:
        writer.writerow([seguro(getattr(registro, campo)) for campo in campos])
    return Response(('\ufeff' + saida.getvalue()).encode('utf-8'), mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{tipo}-{id}.csv"', 'Cache-Control': 'private, no-store'})
