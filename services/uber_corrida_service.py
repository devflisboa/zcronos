from flask_login import current_user
from sqlalchemy import func, Float, cast, text
from extensions import db
from models import CorridaUber, Veiculo


def total_corridas(veiculo_id):
    return _query(veiculo_id, func.count(CorridaUber.id)).scalar() or 0


def quilometros_percorridos(veiculo_id):
    val = _query(veiculo_id, func.sum(CorridaUber.distancia_km)).scalar()
    return float(val) if val else 0.0


def ganho_bruto(veiculo_id):
    val = _query(veiculo_id, func.sum(CorridaUber.ganho_bruto)).scalar()
    return float(val) if val else 0.0


def ganho_liquido(veiculo_id):
    val = _query(veiculo_id, func.sum(CorridaUber.ganho_liquido)).scalar()
    return float(val) if val else 0.0


def pontos_ganhos(veiculo_id):
    val = _query(veiculo_id, func.sum(CorridaUber.pontos_ganhos)).scalar()
    return float(val) if val else 0.0


def pago_usuarios(veiculo_id):
    val = _query(veiculo_id, func.sum(CorridaUber.total_pago_usuario)).scalar()
    return float(val) if val else 0.0


def corridas_por_tipo(veiculo_id):
    return _query(veiculo_id, CorridaUber.tipo_corrida, func.count(CorridaUber.id)).group_by(CorridaUber.tipo_corrida).all()


def quilometros_por_tipo(veiculo_id):
    rows = _query(veiculo_id, CorridaUber.tipo_corrida, func.sum(CorridaUber.distancia_km)).group_by(CorridaUber.tipo_corrida).all()
    return [(tipo, float(dist) if dist else 0.0) for tipo, dist in rows]


def corridas_por_local_partida(veiculo_id):
    return _query(veiculo_id, CorridaUber.local_partida, func.count(CorridaUber.id)).group_by(CorridaUber.local_partida).all()


def corridas_por_local_destino(veiculo_id):
    return _query(veiculo_id, CorridaUber.local_destino, func.count(CorridaUber.id)).group_by(CorridaUber.local_destino).all()


def top_5_corridas_lucrativas(veiculo_id):
    return _query(veiculo_id, 
        text("DATE_FORMAT(data_corrida, '%d/%m/%Y') AS data_corrida"),
        text("TIME_FORMAT(hora_corrida, '%H:%i') AS hora_corrida"),
        CorridaUber.local_destino,
        CorridaUber.ganho_liquido
    ).order_by(CorridaUber.ganho_liquido.desc()).limit(5).all()


def top_5_dias_movimentados(veiculo_id):
    dias_da_semana = {
        0: 'Domingo', 1: 'Segunda-feira', 2: 'Terça-feira',
        3: 'Quarta-feira', 4: 'Quinta-feira', 5: 'Sexta-feira', 6: 'Sábado',
    }
    rows = _query(veiculo_id, 
        func.dayofweek(CorridaUber.data_corrida).label('dia'),
        func.count(CorridaUber.id).label('total_corridas')
    ).group_by('dia').order_by(func.count(CorridaUber.id).desc()).limit(5).all()
    return [(dias_da_semana[dia - 1], total) for dia, total in rows]


def top_5_locais_frequentados(veiculo_id):
    return _query(veiculo_id, CorridaUber.local_partida, func.count(CorridaUber.id)).group_by(
        CorridaUber.local_partida).order_by(func.count(CorridaUber.id).desc()).limit(5).all()


def media_ganho_bruto(veiculo_id):
    val = _query(veiculo_id, func.avg(CorridaUber.ganho_bruto)).scalar()
    return float(val) if val else 0.0


def media_ganho_liquido(veiculo_id):
    val = _query(veiculo_id, func.avg(CorridaUber.ganho_liquido)).scalar()
    return float(val) if val else 0.0


def taxa_servico_media(veiculo_id):
    val = _query(veiculo_id, func.avg(CorridaUber.taxa_servico)).scalar()
    return float(val) if val else 0.0


def total_promocoes(veiculo_id):
    val = _query(veiculo_id, func.count(CorridaUber.promocao_aplicada)).filter(
        CorridaUber.promocao_aplicada.isnot(None)).scalar()
    return val or 0


def velocidade_media(veiculo_id):
    quilometros = float(_query(veiculo_id, func.sum(cast(CorridaUber.distancia_km, Float))).scalar() or 0.0)
    duracao = float(_query(veiculo_id, func.sum(cast(CorridaUber.duracao, Float))).scalar() or 0.0)
    return (quilometros / (duracao / 60)) if duracao > 0 else 0.0


def tempo_medio(veiculo_id):
    val = _query(veiculo_id, func.avg(CorridaUber.duracao)).scalar()
    return float(val) if val else 0.0


def distancia_media(veiculo_id):
    val = _query(veiculo_id, func.avg(CorridaUber.distancia_km)).scalar()
    return float(val) if val else 0.0


def get_estatisticas_corridas(veiculo_id):
    return {
        'total_corridas': total_corridas(veiculo_id),
        'quilometros_percorridos': quilometros_percorridos(veiculo_id),
        'ganho_bruto': ganho_bruto(veiculo_id),
        'ganho_liquido': ganho_liquido(veiculo_id),
        'pontos_ganhos': pontos_ganhos(veiculo_id),
        'pago_usuarios': pago_usuarios(veiculo_id),
        'corridas_por_tipo': corridas_por_tipo(veiculo_id),
        'quilometros_por_tipo': quilometros_por_tipo(veiculo_id),
        'corridas_por_local_partida': corridas_por_local_partida(veiculo_id),
        'corridas_por_local_destino': corridas_por_local_destino(veiculo_id),
        'top_5_corridas_lucrativas': top_5_corridas_lucrativas(veiculo_id),
        'top_5_dias_movimentados': top_5_dias_movimentados(veiculo_id),
        'top_5_locais_frequentados': top_5_locais_frequentados(veiculo_id),
        'media_ganho_bruto': media_ganho_bruto(veiculo_id),
        'media_ganho_liquido': media_ganho_liquido(veiculo_id),
        'taxa_servico_media': taxa_servico_media(veiculo_id),
        'total_promocoes': total_promocoes(veiculo_id),
        'velocidade_media': velocidade_media(veiculo_id),
        'tempo_medio': tempo_medio(veiculo_id),
        'distancia_media': distancia_media(veiculo_id),
    }


def _query(veiculo_id, *columns):
    return db.session.query(*columns).select_from(CorridaUber).join(Veiculo, CorridaUber.veiculo_id == Veiculo.id).filter(
        Veiculo.user_id == current_user.id, Veiculo.ativo.is_(True), CorridaUber.veiculo_id == veiculo_id)
