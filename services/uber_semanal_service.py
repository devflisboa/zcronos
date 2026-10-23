from sqlalchemy import func
from extensions import db
from models import SemanalUber


def total_ganhos():
    val = db.session.query(func.sum(SemanalUber.ganhos)).scalar()
    return float(val) if val else 0.0


def total_despesas_semanal():
    val = db.session.query(func.sum(SemanalUber.despesas_reembolsos)).scalar()
    return float(val) if val else 0.0


def media_ganhos_semanal():
    val = db.session.query(func.avg(SemanalUber.ganhos)).scalar()
    return float(val) if val else 0.0


def ganho_liquido_semanal():
    return total_ganhos() - total_despesas_semanal()


def total_taxas():
    taxas = db.session.query(SemanalUber.resumo_taxas).all()
    total = 0.0
    for (valor,) in taxas:
        if valor and 'Valor pago à plataforma da Uber:' in valor:
            try:
                total += float(valor.split(': ')[1])
            except (IndexError, ValueError):
                continue
    return total


def media_taxa_semanal():
    val = db.session.query(
        func.avg(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'taxa R$') + 7),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val is not None else 0.0


def media_promocoes_semanal():
    val = db.session.query(
        func.avg(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'promoção R$') + 10),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val is not None else 0.0


def ganho_dinamico():
    val = db.session.query(
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'dinâmico R$') + 9),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val else 0.0


def ganho_espera():
    val = db.session.query(
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'espera R$') + 7),
                db.Float
            )
        ).label('total_espera')
    ).scalar()
    return float(val) if val is not None else 0.0


def ganho_extras():
    val = db.session.query(
        func.sum(
            func.cast(
                func.substr(SemanalUber.detalhamento_ganhos,
                            func.instr(SemanalUber.detalhamento_ganhos, 'Extras R$') + 7),
                db.Float
            )
        )
    ).scalar()
    return float(val) if val else 0.0


def total_transferencias():
    val = db.session.query(func.sum(SemanalUber.transferencias)).scalar()
    return float(val) if val else 0.0


def saldo_medio_semanal():
    val = db.session.query(func.avg(SemanalUber.saldo_final)).scalar()
    return float(val) if val else 0.0


def proporcao_ganho_base():
    ganhos = total_ganhos()
    if ganhos <= 0:
        return 0.0
    ganho_base = ganhos - (ganho_dinamico() + ganho_espera() + ganho_extras())
    return round((ganho_base / ganhos) * 100, 2)


def get_estatisticas_semanais():
    return {
        'total_ganhos': total_ganhos(),
        'total_despesas': total_despesas_semanal(),
        'media_ganhos_semanal': media_ganhos_semanal(),
        'ganho_liquido': ganho_liquido_semanal(),
        'total_taxas': total_taxas(),
        'media_taxa_semanal': media_taxa_semanal(),
        'total_promocoes': 0,
        'media_promocoes_semanal': media_promocoes_semanal(),
        'ganho_dinamico': ganho_dinamico(),
        'ganho_espera': ganho_espera(),
        'ganho_extras': ganho_extras(),
        'proporcao_ganho_base': proporcao_ganho_base(),
        'total_transferencias': total_transferencias(),
        'saldo_medio_semanal': saldo_medio_semanal(),
    }
