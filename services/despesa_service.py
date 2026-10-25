from sqlalchemy import func
from extensions import db
from flask_login import current_user
from models import Despesa, Categoria, Veiculo


def get_estatisticas_despesas(veiculo_id):
    total_despesas = _query(veiculo_id, func.sum(Despesa.valor)).scalar() or 0
    total_categorias = db.session.query(func.count(Categoria.id)).scalar() or 0
    media_despesa_categoria = total_despesas / total_categorias if total_categorias > 0 else 0
    maior_despesa = _query(veiculo_id, func.max(Despesa.valor)).scalar() or 0
    menor_despesa = _query(veiculo_id, func.min(Despesa.valor)).scalar() or 0
    despesa_media = _query(veiculo_id, func.avg(Despesa.valor)).scalar() or 0
    return {
        'total_despesas': total_despesas,
        'total_categorias': total_categorias,
        'media_despesa_categoria': media_despesa_categoria,
        'maior_despesa': maior_despesa,
        'menor_despesa': menor_despesa,
        'despesa_media': despesa_media,
    }


def _query(veiculo_id, *columns):
    return db.session.query(*columns).select_from(Despesa).join(Veiculo).filter(Veiculo.user_id == current_user.id, Veiculo.id == veiculo_id, Veiculo.ativo.is_(True))
