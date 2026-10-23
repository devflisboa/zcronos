from models import Abastecimento


def obter_dados_abastecimento():
    abastecimentos = Abastecimento.query.all()
    quilometragens = [a.quilometragem for a in abastecimentos]
    litros_abastecidos = [a.litros_abastecidos for a in abastecimentos]
    valores_totais = [a.valor_total for a in abastecimentos]
    postos = [a.posto for a in abastecimentos]
    precos_combustivel = [a.preco_combustivel for a in abastecimentos]
    return quilometragens, litros_abastecidos, valores_totais, postos, precos_combustivel, abastecimentos


def calcular_media_consumo(quilometragens, litros_abastecidos):
    return [
        (quilometragens[i] - quilometragens[i - 1]) / litros_abastecidos[i - 1]
        for i in range(1, len(quilometragens))
    ]
