import plotly.graph_objects as go
from markupsafe import Markup


def gerar_grafico_ganhos(titulo, labels, data, largura=1110, altura=900):
    grouped_data = {}
    for label, value in zip(labels, data):
        grouped_data[label] = grouped_data.get(label, 0) + value

    text_values = [None] * len(data)
    for i in range(len(labels) - 1, -1, -1):
        if text_values[i] is None and labels[i] in grouped_data:
            text_values[i] = f"{grouped_data[labels[i]]}"
            grouped_data.pop(labels[i])

    fig = go.Figure(data=[go.Bar(
        name='Ganhos Brutos',
        y=labels,
        x=data,
        text=text_values,
        textposition='outside',
        orientation='h',
        marker=dict(color='green', opacity=0.8, line=dict(color='black', width=1.5)),
    )])
    fig.update_layout(
        title=titulo,
        xaxis_title='Ganhos Brutos', yaxis_title='Data',
        template='plotly_dark', font=dict(color='white'),
        width=largura, height=altura,
        margin=dict(t=80), bargap=0.15,
    )
    return fig.to_html(full_html=False)


def gerar_e_formatar_grafico(titulo, labels, data, largura=1110, altura=900):
    return Markup(gerar_grafico_ganhos(titulo, labels, data, largura, altura))
