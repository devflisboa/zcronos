from sqlalchemy import func
from extensions import db
from models import Despesa, Categoria


def get_estatisticas_despesas():
    total_despesas = db.session.query(func.sum(Despesa.valor)).scalar() or 0
    total_categorias = db.session.query(func.count(Categoria.id)).scalar() or 0
    media_despesa_categoria = total_despesas / total_categorias if total_categorias > 0 else 0
    maior_despesa = db.session.query(func.max(Despesa.valor)).scalar() or 0
    menor_despesa = db.session.query(func.min(Despesa.valor)).scalar() or 0
    despesa_media = db.session.query(func.avg(Despesa.valor)).scalar() or 0
    return {
        'total_despesas': total_despesas,
        'total_categorias': total_categorias,
        'media_despesa_categoria': media_despesa_categoria,
        'maior_despesa': maior_despesa,
        'menor_despesa': menor_despesa,
        'despesa_media': despesa_media,
    }
