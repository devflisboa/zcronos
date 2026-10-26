from flask_login import current_user
import calendar
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from extensions import db
from models import Despesa, Abastecimento, Manutencao, Veiculo, Categoria


def _mes_ano():
    n = datetime.now()
    return n.month, n.year


def get_custo_mes(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    d = db.session.query(func.sum(Despesa.valor)).filter(
        Despesa.veiculo_id == veiculo_id,
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a,
    ).scalar() or 0
    c = db.session.query(func.sum(Abastecimento.valor_total)).filter(
        Abastecimento.veiculo_id == veiculo_id,
        extract('month', Abastecimento.data) == m,
        extract('year', Abastecimento.data) == a,
    ).scalar() or 0
    return round(float(d) + float(c), 2)


def get_custo_ano(veiculo_id, ano=None):
    a = ano or _mes_ano()[1]
    d = db.session.query(func.sum(Despesa.valor)).filter(
        Despesa.veiculo_id == veiculo_id,
        extract('year', Despesa.data) == a,
    ).scalar() or 0
    c = db.session.query(func.sum(Abastecimento.valor_total)).filter(
        Abastecimento.veiculo_id == veiculo_id,
        extract('year', Abastecimento.data) == a,
    ).scalar() or 0
    return round(float(d) + float(c), 2)


def get_media_mensal(veiculo_id):
    mes_atual = datetime.now().month
    total = get_custo_ano(veiculo_id)
    return round(total / mes_atual, 2) if mes_atual > 0 else 0


def get_custo_por_km(veiculo_id):
    a = datetime.now().year
    total = get_custo_ano(veiculo_id, a)
    registros = Abastecimento.query.filter(
        Abastecimento.veiculo_id == veiculo_id,
        extract('year', Abastecimento.data) == a,
    ).order_by(Abastecimento.quilometragem).all()
    if len(registros) < 2:
        return 0
    km_rodados = registros[-1].quilometragem - registros[0].quilometragem
    return round(total / km_rodados, 2) if km_rodados > 0 else 0


def get_gastos_combustivel_mes(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    v = db.session.query(func.sum(Abastecimento.valor_total)).filter(
        Abastecimento.veiculo_id == veiculo_id,
        extract('month', Abastecimento.data) == m,
        extract('year', Abastecimento.data) == a,
    ).scalar() or 0
    return round(float(v), 2)


def get_gastos_manutencao_mes(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    cats = ['Troca de Óleo', 'Revisão', 'Pneus', 'Peças', 'Reparo', 'Bateria', 'Filtro']
    v = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Despesa.veiculo_id == veiculo_id,
        Categoria.nome.in_(cats),
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a,
    ).scalar() or 0
    return round(float(v), 2)


def get_gastos_por_mes(veiculo_id, ultimos=12):
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
        total = get_custo_mes(veiculo_id, m, a)
        resultado.append({'mes': calendar.month_abbr[m], 'ano': a, 'total': total})
    return resultado


def get_gastos_por_categoria(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    rows = db.session.query(
        Categoria.nome, func.sum(Despesa.valor).label('total')
    ).join(Despesa.categoria).filter(
        Despesa.veiculo_id == veiculo_id,
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a,
    ).group_by(Categoria.nome).all()
    resultado = [{'categoria': r.nome, 'total': round(float(r.total), 2)} for r in rows]
    comb = get_gastos_combustivel_mes(veiculo_id, m, a)
    if comb > 0:
        resultado.append({'categoria': 'Combustível', 'total': comb})
    resultado.sort(key=lambda x: x['total'], reverse=True)
    return resultado


def get_consumo_medio(veiculo_id):
    abast = Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(
        Abastecimento.quilometragem
    ).all()
    if len(abast) < 2:
        return 0
    medias = []
    for i in range(1, len(abast)):
        km = abast[i].quilometragem - abast[i - 1].quilometragem
        litros = abast[i - 1].litros_abastecidos
        if litros > 0:
            medias.append(km / litros)
    return round(sum(medias) / len(medias), 2) if medias else 0


def get_km_por_dia(veiculo_id):
    abast = Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(
        Abastecimento.data, Abastecimento.quilometragem
    ).all()
    if len(abast) < 2:
        return None
    delta_days = (abast[-1].data - abast[0].data).days
    delta_km = abast[-1].quilometragem - abast[0].quilometragem
    if delta_days <= 0 or delta_km <= 0:
        return None
    return round(delta_km / delta_days, 1)


def get_preco_medio_litro(veiculo_id):
    v = db.session.query(func.avg(Abastecimento.preco_combustivel)).filter(
        Abastecimento.veiculo_id == veiculo_id
    ).scalar()
    return round(float(v), 3) if v else 0


def get_abastecimentos_com_consumo(veiculo_id):
    abast = Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(
        Abastecimento.quilometragem
    ).all()
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
            'tipo_combustivel': a.tipo_combustivel or '',
            'observacao': a.observacao or '',
            'latitude': a.latitude,
            'longitude': a.longitude,
        })
    return list(reversed(resultado))


def get_alertas_manutencao(veiculo_id):
    hoje = date.today()
    alertas = []
    for m in Manutencao.query.filter_by(veiculo_id=veiculo_id).filter(
        Manutencao.status != 'realizada'
    ).all():
        st = m.status_calculado
        if st in ('atrasada', 'proxima'):
            alertas.append({
                'id': m.id, 'tipo': m.tipo, 'descricao': m.descricao,
                'status': st,
                'data_prevista': m.data_prevista.strftime('%d/%m/%Y') if m.data_prevista else None,
                'km_previsto': m.km_previsto,
            })
    return alertas


def get_comparativo_mes(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    atual = get_custo_mes(veiculo_id, m, a)
    m_ant = m - 1 if m > 1 else 12
    a_ant = a if m > 1 else a - 1
    anterior = get_custo_mes(veiculo_id, m_ant, a_ant)
    delta = round(((atual - anterior) / anterior) * 100, 1) if anterior > 0 else 0
    return {'atual': atual, 'anterior': anterior, 'delta': delta}


def get_combustivel_por_mes(veiculo_id, ultimos=6):
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
        total = get_gastos_combustivel_mes(veiculo_id, m, a)
        litros = db.session.query(func.sum(Abastecimento.litros_abastecidos)).filter(
            Abastecimento.veiculo_id == veiculo_id,
            extract('month', Abastecimento.data) == m,
            extract('year', Abastecimento.data) == a,
        ).scalar() or 0
        preco_medio = db.session.query(func.avg(Abastecimento.preco_combustivel)).filter(
            Abastecimento.veiculo_id == veiculo_id,
            extract('month', Abastecimento.data) == m,
            extract('year', Abastecimento.data) == a,
        ).scalar()
        resultado.append({
            'mes': calendar.month_abbr[m],
            'valor': total,
            'litros': round(float(litros), 2),
            'preco_medio': round(float(preco_medio), 3) if preco_medio else None,
        })
    return resultado


def get_projecao_ano(veiculo_id, ano=None):
    """Projeta o gasto total do ano com base na média mensal até o mês atual."""
    hoje = date.today()
    a = ano or hoje.year
    custo_ate_agora = get_custo_ano(veiculo_id, a)
    meses_passados = hoje.month
    if meses_passados == 0 or custo_ate_agora == 0:
        return 0
    media = custo_ate_agora / meses_passados
    meses_restantes = 12 - meses_passados
    return round(custo_ate_agora + media * meses_restantes, 2)


def get_custo_historico(veiculo_id):
    d = db.session.query(func.sum(Despesa.valor)).filter(Despesa.veiculo_id == veiculo_id).scalar() or 0
    c = db.session.query(func.sum(Abastecimento.valor_total)).filter(Abastecimento.veiculo_id == veiculo_id).scalar() or 0
    return round(float(d) + float(c), 2)


def get_ultimo_abastecimento(veiculo_id):
    return Abastecimento.query.filter_by(veiculo_id=veiculo_id).order_by(
        Abastecimento.data.desc()
    ).first()


def get_gastos_fixos_vs_variaveis(veiculo_id, mes=None, ano=None):
    m, a = mes or _mes_ano()[0], ano or _mes_ano()[1]
    fixo = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Despesa.veiculo_id == veiculo_id,
        Categoria.tipo == 'fixo',
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a,
    ).scalar() or 0
    variavel = db.session.query(func.sum(Despesa.valor)).join(Categoria).filter(
        Despesa.veiculo_id == veiculo_id,
        Categoria.tipo == 'variavel',
        extract('month', Despesa.data) == m,
        extract('year', Despesa.data) == a,
    ).scalar() or 0
    comb = get_gastos_combustivel_mes(veiculo_id, m, a)
    return {'fixo': round(float(fixo), 2), 'variavel': round(float(variavel) + comb, 2)}


def get_dashboard_data(veiculo_id, mes=None, ano=None):
    veiculo = Veiculo.query.filter_by(id=veiculo_id, user_id=current_user.id, ativo=True).first_or_404()
    m_ref, a_ref = mes or _mes_ano()[0], ano or _mes_ano()[1]
    comp = get_comparativo_mes(veiculo_id, m_ref, a_ref)
    return {
        'veiculo': veiculo,
        'custo_mes': comp['atual'],
        'custo_mes_anterior': comp['anterior'],
        'custo_mes_delta': comp['delta'],
        'custo_ano': get_custo_ano(veiculo_id, a_ref),
        'media_mensal': get_media_mensal(veiculo_id),
        'custo_por_km': get_custo_por_km(veiculo_id),
        'gastos_combustivel_mes': get_gastos_combustivel_mes(veiculo_id, m_ref, a_ref),
        'gastos_manutencao_mes': get_gastos_manutencao_mes(veiculo_id, m_ref, a_ref),
        'consumo_medio': get_consumo_medio(veiculo_id),
        'preco_medio_litro': get_preco_medio_litro(veiculo_id),
        'km_atual': veiculo.km_atual if veiculo else 0,
        'gastos_por_mes': get_gastos_por_mes(veiculo_id, 12),
        'gastos_por_categoria': get_gastos_por_categoria(veiculo_id),
        'combustivel_por_mes': get_combustivel_por_mes(veiculo_id, 6),
        'fixo_vs_variavel': get_gastos_fixos_vs_variaveis(veiculo_id, m_ref, a_ref),
        'periodo_mes': m_ref,
        'periodo_ano': a_ref,
        'custo_historico': get_custo_historico(veiculo_id),
        'projecao_ano': get_projecao_ano(veiculo_id, a_ref),
        'ultimo_abastecimento': get_ultimo_abastecimento(veiculo_id),
        'alertas': get_alertas_manutencao(veiculo_id),
        'km_por_dia': get_km_por_dia(veiculo_id),
        'abastecimentos': get_abastecimentos_com_consumo(veiculo_id),
        'despesas': Despesa.query.filter_by(veiculo_id=veiculo_id).order_by(
            Despesa.data.desc()
        ).all(),
        'categorias': Categoria.query.order_by(Categoria.nome).all(),
        'manutencoes': Manutencao.query.filter_by(veiculo_id=veiculo_id).order_by(
            Manutencao.data_prevista
        ).all(),
    }
