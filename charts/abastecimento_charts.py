import plotly.graph_objects as go


def gerar_grafico_consumo(quilometragens, litros_abastecidos, valores_totais):
    if len(quilometragens) < 2:
        return None
    medias = [
        (quilometragens[i] - quilometragens[i - 1]) / litros_abastecidos[i - 1]
        for i in range(1, len(quilometragens))
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quilometragens[1:], y=medias, mode='lines+markers', name='Média de Consumo (Km/L)'))
    fig.add_trace(go.Scatter(x=quilometragens, y=valores_totais, mode='lines+markers',
                             line=dict(color='green'), name='Valor (R$)'))
    fig.update_layout(
        title='Média de Consumo e Valor por Quilometragem',
        xaxis_title='Quilometragem', yaxis_title='Consumo (Km/L) e Valor (R$)',
        template='plotly_dark', width=1110, height=450,
    )
    return fig


def gerar_grafico_custo_por_litro(quilometragens, precos_combustivel):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quilometragens, y=precos_combustivel, mode='lines+markers', name='Preço por Litro (R$)'))
    fig.update_layout(
        title='Preço por Litro de Combustível',
        xaxis_title='Quilometragem', yaxis_title='Preço por Litro (R$)',
        template='plotly_dark', width=1110, height=450,
    )
    return fig


def gerar_grafico_custo_por_km(quilometragens, valores_totais):
    custos_por_km = [
        valores_totais[i] / (quilometragens[i] - quilometragens[i - 1])
        for i in range(1, len(quilometragens))
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quilometragens[1:], y=custos_por_km, mode='lines+markers', name='Custo por Km (R$)'))
    fig.update_layout(
        title='Custo por Quilômetro',
        xaxis_title='Quilometragem', yaxis_title='Custo por Km (R$)',
        template='plotly_dark', width=1110, height=450,
    )
    return fig
