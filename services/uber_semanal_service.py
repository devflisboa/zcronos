from flask_login import current_user
from sqlalchemy import func
from extensions import db
from models import SemanalUber


def total_ganhos(user_id):
    val = _query(user_id, func.sum(SemanalUber.ganhos)).scalar()
    return float(val) if val else 0.0


def total_despesas_semanal(user_id):
    val = _query(user_id, func.sum(SemanalUber.despesas_reembolsos)).scalar()
    return float(val) if val else 0.0


def media_ganhos_semanal(user_id):
    val = _query(user_id, func.avg(SemanalUber.ganhos)).scalar()
    return float(val) if val else 0.0


def ganho_liquido_semanal(user_id):
    return total_ganhos(user_id) - total_despesas_semanal(user_id)


def total_taxas(user_id):
    taxas = _query(user_id, SemanalUber.resumo_taxas).all()
    total = 0.0
    for (valor,) in taxas:
        if valor and 'Valor pago à plataforma da Uber:' in valor:
            try:
                total += float(valor.split(': ')[1])
            except (IndexError, ValueError):
                continue
    return total


def media_taxa_semanal(user_id):
    val = _query(user_id, 
        func.avg(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'taxa R$') + 7),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val is not None else 0.0


def media_promocoes_semanal(user_id):
    val = _query(user_id, 
        func.avg(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'promoção R$') + 10),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val is not None else 0.0


def ganho_dinamico(user_id):
    val = _query(user_id, 
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'dinâmico R$') + 9),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val else 0.0


def ganho_espera(user_id):
    val = _query(user_id, 
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'espera R$') + 7),
                db.Float
            )
        ).label('total_espera')
    ).scalar()
    return float(val) if val is not None else 0.0


def ganho_extras(user_id):
    val = _query(user_id, 
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'Extras R$') + 7),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val else 0.0


def total_transferencias(user_id):
    val = _query(user_id, func.sum(SemanalUber.transferencias)).scalar()
    return float(val) if val else 0.0


def saldo_medio_semanal(user_id):
    val = _query(user_id, func.avg(SemanalUber.saldo_final)).scalar()
    return float(val) if val else 0.0


def proporcao_ganho_base(user_id):
    ganhos = total_ganhos(user_id)
    if ganhos <= 0:
        return 0.0
    ganho_base = ganhos - (ganho_dinamico(user_id) + ganho_espera(user_id) + ganho_extras(user_id))
    return round((ganho_base / ganhos) * 100, 2)


def get_estatisticas_semanais(user_id):
    return {
        'total_ganhos': total_ganhos(user_id),
        'total_despesas': total_despesas_semanal(user_id),
        'media_ganhos_semanal': media_ganhos_semanal(user_id),
        'ganho_liquido': ganho_liquido_semanal(user_id),
        'total_taxas': total_taxas(user_id),
        'media_taxa_semanal': media_taxa_semanal(user_id),
        'total_promocoes': 0,
        'media_promocoes_semanal': media_promocoes_semanal(user_id),
        'ganho_dinamico': ganho_dinamico(user_id),
        'ganho_espera': ganho_espera(user_id),
        'ganho_extras': ganho_extras(user_id),
        'proporcao_ganho_base': proporcao_ganho_base(user_id),
        'total_transferencias': total_transferencias(user_id),
        'saldo_medio_semanal': saldo_medio_semanal(user_id),
    }


def _query(user_id, *columns):
    return db.session.query(*columns).filter(SemanalUber.user_id == user_id, SemanalUber.user_id == current_user.id)
