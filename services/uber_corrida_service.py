from sqlalchemy import func, Float, cast, text
from extensions import db
from models import CorridaUber


def total_corridas():
    return db.session.query(func.count(CorridaUber.id)).scalar() or 0


def quilometros_percorridos():
    val = db.session.query(func.sum(CorridaUber.distancia_km)).scalar()
    return float(val) if val else 0.0


def ganho_bruto():
    val = db.session.query(func.sum(CorridaUber.ganho_bruto)).scalar()
    return float(val) if val else 0.0


def ganho_liquido():
    val = db.session.query(func.sum(CorridaUber.ganho_liquido)).scalar()
    return float(val) if val else 0.0


def pontos_ganhos():
    val = db.session.query(func.sum(CorridaUber.pontos_ganhos)).scalar()
    return float(val) if val else 0.0


def pago_usuarios():
    val = db.session.query(func.sum(CorridaUber.total_pago_usuario)).scalar()
    return float(val) if val else 0.0


def corridas_por_tipo():
    return db.session.query(CorridaUber.tipo_corrida, func.count(CorridaUber.id)).group_by(CorridaUber.tipo_corrida).all()


def quilometros_por_tipo():
    rows = db.session.query(CorridaUber.tipo_corrida, func.sum(CorridaUber.distancia_km)).group_by(CorridaUber.tipo_corrida).all()
    return [(tipo, float(dist) if dist else 0.0) for tipo, dist in rows]


def corridas_por_local_partida():
    return db.session.query(CorridaUber.local_partida, func.count(CorridaUber.id)).group_by(CorridaUber.local_partida).all()


def corridas_por_local_destino():
    return db.session.query(CorridaUber.local_destino, func.count(CorridaUber.id)).group_by(CorridaUber.local_destino).all()


def top_5_corridas_lucrativas():
    return db.session.query(
        text("DATE_FORMAT(data_corrida, '%d/%m/%Y') AS data_corrida"),
        text("TIME_FORMAT(hora_corrida, '%H:%i') AS hora_corrida"),
        CorridaUber.local_destino,
        CorridaUber.ganho_liquido
    ).order_by(CorridaUber.ganho_liquido.desc()).limit(5).all()


def top_5_dias_movimentados():
    dias_da_semana = {
        0: 'Domingo', 1: 'Segunda-feira', 2: 'Terça-feira',
        3: 'Quarta-feira', 4: 'Quinta-feira', 5: 'Sexta-feira', 6: 'Sábado',
    }
    rows = db.session.query(
        func.dayofweek(CorridaUber.data_corrida).label('dia'),
        func.count(CorridaUber.id).label('total_corridas')
    ).group_by('dia').order_by(func.count(CorridaUber.id).desc()).limit(5).all()
    return [(dias_da_semana[dia - 1], total) for dia, total in rows]


def top_5_locais_frequentados():
    return db.session.query(CorridaUber.local_partida, func.count(CorridaUber.id)).group_by(
        CorridaUber.local_partida).order_by(func.count(CorridaUber.id).desc()).limit(5).all()


def media_ganho_bruto():
    val = db.session.query(func.avg(CorridaUber.ganho_bruto)).scalar()
    return float(val) if val else 0.0


def media_ganho_liquido():
    val = db.session.query(func.avg(CorridaUber.ganho_liquido)).scalar()
    return float(val) if val else 0.0


def taxa_servico_media():
    val = db.session.query(func.avg(CorridaUber.taxa_servico)).scalar()
    return float(val) if val else 0.0


def total_promocoes():
    val = db.session.query(func.count(CorridaUber.promocao_aplicada)).filter(
        CorridaUber.promocao_aplicada.isnot(None)).scalar()
    return val or 0


def velocidade_media():
    quilometros = float(db.session.query(func.sum(cast(CorridaUber.distancia_km, Float))).scalar() or 0.0)
    duracao = float(db.session.query(func.sum(cast(CorridaUber.duracao, Float))).scalar() or 0.0)
    return (quilometros / (duracao / 60)) if duracao > 0 else 0.0


def tempo_medio():
    val = db.session.query(func.avg(CorridaUber.duracao)).scalar()
    return float(val) if val else 0.0


def distancia_media():
    val = db.session.query(func.avg(CorridaUber.distancia_km)).scalar()
    return float(val) if val else 0.0


def get_estatisticas_corridas():
    return {
        'total_corridas': total_corridas(),
        'quilometros_percorridos': quilometros_percorridos(),
        'ganho_bruto': ganho_bruto(),
        'ganho_liquido': ganho_liquido(),
        'pontos_ganhos': pontos_ganhos(),
        'pago_usuarios': pago_usuarios(),
        'corridas_por_tipo': corridas_por_tipo(),
        'quilometros_por_tipo': quilometros_por_tipo(),
        'corridas_por_local_partida': corridas_por_local_partida(),
        'corridas_por_local_destino': corridas_por_local_destino(),
        'top_5_corridas_lucrativas': top_5_corridas_lucrativas(),
        'top_5_dias_movimentados': top_5_dias_movimentados(),
        'top_5_locais_frequentados': top_5_locais_frequentados(),
        'media_ganho_bruto': media_ganho_bruto(),
        'media_ganho_liquido': media_ganho_liquido(),
        'taxa_servico_media': taxa_servico_media(),
        'total_promocoes': total_promocoes(),
        'velocidade_media': velocidade_media(),
        'tempo_medio': tempo_medio(),
        'distancia_media': distancia_media(),
    }
