from models import MetaGasto
from services.dashboard_service import (
    get_custo_mes, get_gastos_combustivel_mes, get_gastos_por_categoria
)


def get_metas_progresso(veiculo_id, mes, ano):
    metas = MetaGasto.query.filter_by(veiculo_id=veiculo_id).all()
    if not metas:
        return []

    custo_total = get_custo_mes(veiculo_id, mes, ano)
    custo_comb = get_gastos_combustivel_mes(veiculo_id, mes, ano)
    por_cat = {item['categoria']: item['total'] for item in get_gastos_por_categoria(veiculo_id, mes, ano)}

    resultado = []
    for m in metas:
        if m.tipo == 'total':
            gasto = custo_total
            rotulo = 'Total do Mês'
        elif m.tipo == 'combustivel':
            gasto = custo_comb
            rotulo = 'Combustível'
        else:
            nome_cat = m.categoria.nome if m.categoria else ''
            gasto = por_cat.get(nome_cat, 0)
            rotulo = f'{m.categoria.icone} {nome_cat}' if m.categoria else '—'

        pct = min(round(gasto / m.valor_limite * 100, 1), 999) if m.valor_limite > 0 else 0
        resultado.append({
            'id': m.id,
            'rotulo': rotulo,
            'tipo': m.tipo,
            'limite': m.valor_limite,
            'gasto': round(gasto, 2),
            'pct': pct,
            'status': 'danger' if pct >= 100 else ('warn' if pct >= 80 else 'ok'),
        })
    return resultado
