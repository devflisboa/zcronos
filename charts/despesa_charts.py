import plotly.graph_objects as go
from markupsafe import Markup
from sqlalchemy import func
from extensions import db
from models import Despesa, Categoria


def gerar_grafico_despesas():
    rows = db.session.query(
        Categoria.nome.label('categoria'),
        func.sum(Despesa.valor).label('total')
    ).join(Despesa.categoria).group_by(Categoria.nome).all()

    if not rows:
        return Markup("<p class='text-center'>Nenhuma despesa encontrada para exibir o gráfico.</p>")

    fig = go.Figure(data=go.Bar(
        x=[r.categoria for r in rows],
        y=[r.total for r in rows],
        marker_color='orange',
    ))
    fig.update_layout(
        title='Despesas por Categoria',
        xaxis_title='Categoria', yaxis_title='Total (R$)',
        template='plotly_dark', width=1110, height=450,
    )
    return Markup(fig.to_html(full_html=False))
