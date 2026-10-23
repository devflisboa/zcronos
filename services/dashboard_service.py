import calendar
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from extensions import db
from models import Despesa, Abastecimento, Manutencao, Veiculo, Categoria


def _mes_ano():
    n = datetime.now()
    return n.month, n.year


def get_custo_mes(mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    d = db.session.query(func.sum(Despesa.valor)).filter(
        extract('month', Despesa.data) == m, extract('year', Despesa.data) == a
    ).scalar() or 0
    c = db.session.query(func.sum(Abastecimento.valor_total)).filter(
        extract('month', Abastecimento.data) == m, extract('year', Abastecimento.data) == a
    ).scalar() or 0
    return round(float(d) + float(c), 2)


def get_custo_ano(ano=None):
    a = ano or _mes_ano()[1]
    d = db.session.query(func.sum(Despesa.valor)).filter(extract('year', Despesa.data) == a).scalar() or 0
    c = db.session.query(func.sum(Abastecimento.valor_total)).filter(extract('year', Abastecimento.data) == a).scalar() or 0
    return round(float(d) + float(c), 2)


def get_media_mensal():
    mes_atual = datetime.now().month
    total = get_custo_ano()
    return round(total / mes_atual, 2) if mes_atual > 0 else 0


def get_custo_por_km():
    a = datetime.now().year
    total = get_custo_ano(a)
    registros = Abastecimento.query.filter(
        extract('year', Abastecimento.data) == a
    ).order_by(Abastecimento.quilometragem).all()
    if len(registros) < 2:
        return 0
    km_rodados = registros[-1].quilometragem - registros[0].quilometragem
    return round(total / km_rodados, 2) if km_rodados > 0 else 0


def get_gastos_combustivel_mes(mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    v = db.session.query(func.sum(Abastecimento.valor_total)).filter(
        extract('month', Abastecimento.data) == m, extract('year', Abastecimento.data) == a
    ).scalar() or 0
    return round(float(v), 2)


def get_gastos_manutencao_mes(mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    cats = ['Troca de Óleo', 'Revisão', 'Pneus', 'Peças', 'Reparo', 'Bateria', 'Filtro']
    v = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Categoria.nome.in_(cats),
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a
    ).scalar() or 0
    return round(float(v), 2)


def get_gastos_por_mes(ultimos=12):
    hoje = datetime.now()
    resultado = []
    for i in range(ultimos - 1, -1, -1):
        total_meses = hoje.month - i
        if total_meses <= 0:
            m = total_meses + 12
            a = hoje.year - 1
        else:
            m = total_meses
            a = hoje.year
        total = get_custo_mes(m, a)
        resultado.append({'mes': calendar.month_abbr[m], 'ano': a, 'total': total})
    return resultado


def get_gastos_por_categoria(mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    rows = db.session.query(
        Categoria.nome, func.sum(Despesa.valor).label('total')
    ).join(Despesa.categoria).filter(
        extract('month', Despesa.data) == m, extract('year', Despesa.data) == a
    ).group_by(Categoria.nome).all()
    resultado = [{'categoria': r.nome, 'total': round(float(r.total), 2)} for r in rows]
    comb = get_gastos_combustivel_mes(m, a)
    if comb > 0:
        resultado.append({'categoria': 'Combustível', 'total': comb})
    resultado.sort(key=lambda x: x['total'], reverse=True)
    return resultado


def get_consumo_medio():
    abast = Abastecimento.query.order_by(Abastecimento.quilometragem).all()
    if len(abast) < 2:
        return 0
    medias = []
    for i in range(1, len(abast)):
        km = abast[i].quilometragem - abast[i - 1].quilometragem
        litros = abast[i - 1].litros_abastecidos
        if litros > 0:
            medias.append(km / litros)
    return round(sum(medias) / len(medias), 2) if medias else 0


def get_preco_medio_litro():
    v = db.session.query(func.avg(Abastecimento.preco_combustivel)).scalar()
    return round(float(v), 3) if v else 0


def get_abastecimentos_com_consumo():
    abast = Abastecimento.query.order_by(Abastecimento.quilometragem).all()
    resultado = []
    for i, a in enumerate(abast):
        consumo = None
        if i > 0:
            km = a.quilometragem - abast[i - 1].quilometragem
            lt = abast[i - 1].litros_abastecidos
            consumo = round(km / lt, 2) if lt > 0 else None
        resultado.append({
            'id': a.id, 'data': a.data.strftime('%d/%m/%Y'),
            'quilometragem': a.quilometragem, 'litros': a.litros_abastecidos,
            'valor': a.valor_total, 'preco_litro': a.preco_combustivel,
            'posto': a.posto, 'consumo': consumo,
        })
    return list(reversed(resultado))


def get_alertas_manutencao():
    hoje = date.today()
    veiculo = Veiculo.query.first()
    km_atual = veiculo.km_atual if veiculo else 0
    alertas = []
    for m in Manutencao.query.filter(Manutencao.status != 'realizada').all():
        st = m.status_calculado
        if st in ('atrasada', 'proxima'):
            alertas.append({
                'id': m.id, 'tipo': m.tipo, 'descricao': m.descricao,
                'status': st,
                'data_prevista': m.data_prevista.strftime('%d/%m/%Y') if m.data_prevista else None,
                'km_previsto': m.km_previsto,
            })
    return alertas


def get_comparativo_mes():
    agora = datetime.now()
    atual = get_custo_mes(agora.month, agora.year)
    m_ant = agora.month - 1 if agora.month > 1 else 12
    a_ant = agora.year if agora.month > 1 else agora.year - 1
    anterior = get_custo_mes(m_ant, a_ant)
    delta = round(((atual - anterior) / anterior) * 100, 1) if anterior > 0 else 0
    return {'atual': atual, 'anterior': anterior, 'delta': delta}


def get_combustivel_por_mes(ultimos=6):
    hoje = datetime.now()
    resultado = []
    for i in range(ultimos - 1, -1, -1):
        total_meses = hoje.month - i
        if total_meses <= 0:
            m = total_meses + 12
            a = hoje.year - 1
        else:
            m = total_meses
            a = hoje.year
        total = get_gastos_combustivel_mes(m, a)
        litros = db.session.query(func.sum(Abastecimento.litros_abastecidos)).filter(
            extract('month', Abastecimento.data) == m,
            extract('year', Abastecimento.data) == a
        ).scalar() or 0
        resultado.append({'mes': calendar.month_abbr[m], 'valor': total, 'litros': round(float(litros), 2)})
    return resultado


def get_gastos_fixos_vs_variaveis(mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    fixo = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Categoria.tipo == 'fixo',
        extract('month', Despesa.data) == m, extract('year', Despesa.data) == a
    ).scalar() or 0
    variavel = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Categoria.tipo == 'variavel',
        extract('month', Despesa.data) == m, extract('year', Despesa.data) == a
    ).scalar() or 0
    comb = get_gastos_combustivel_mes(m, a)
    return {'fixo': round(float(fixo), 2), 'variavel': round(float(variavel) + comb, 2)}


def get_dashboard_data():
    veiculo = Veiculo.query.first()
    comp = get_comparativo_mes()
    return {
        'veiculo': veiculo,
        'custo_mes': comp['atual'],
        'custo_mes_anterior': comp['anterior'],
        'custo_mes_delta': comp['delta'],
        'custo_ano': get_custo_ano(),
        'media_mensal': get_media_mensal(),
        'custo_por_km': get_custo_por_km(),
        'gastos_combustivel_mes': get_gastos_combustivel_mes(),
        'gastos_manutencao_mes': get_gastos_manutencao_mes(),
        'consumo_medio': get_consumo_medio(),
        'preco_medio_litro': get_preco_medio_litro(),
        'km_atual': veiculo.km_atual if veiculo else 0,
        'gastos_por_mes': get_gastos_por_mes(12),
        'gastos_por_categoria': get_gastos_por_categoria(),
        'combustivel_por_mes': get_combustivel_por_mes(6),
        'fixo_vs_variavel': get_gastos_fixos_vs_variaveis(),
        'alertas': get_alertas_manutencao(),
        'abastecimentos': get_abastecimentos_com_consumo(),
        'despesas': Despesa.query.order_by(Despesa.data.desc()).all(),
        'categorias': Categoria.query.order_by(Categoria.nome).all(),
        'manutencoes': Manutencao.query.order_by(Manutencao.data_prevista).all(),
    }
