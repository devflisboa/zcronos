from datetime import date
from decimal import Decimal, InvalidOperation

from services.condutor_service import validar_documentacao_veiculo, campo_data
from services.placa import normalizar_placa


def validar_veiculo(dados, existente=None):
    campos = {}
    for campo, limite in (('marca', 50), ('modelo', 50), ('versao', 100), ('motor', 100), ('cor', 50)):
        valor = str(dados.get(campo, getattr(existente, campo, '') or '')).strip()
        if len(valor) > limite or (campo in ('marca', 'modelo') and not valor):
            raise ValueError(f'Informe {campo} válido (até {limite} caracteres).')
        campos[campo] = valor or None
    for campo in ('ano', 'km_atual'):
        valor = dados.get(campo, getattr(existente, campo, None))
        try:
            numero = int(valor) if valor not in (None, '') else (0 if campo == 'km_atual' else None)
        except (ValueError, TypeError):
            raise ValueError(f'Valor inválido: {campo}.') from None
        if campo == 'ano' and (numero is None or not 1900 <= numero <= date.today().year + 1):
            raise ValueError('Informe um ano válido para o veículo.')
        if campo == 'km_atual' and not 0 <= numero <= 2147483647:
            raise ValueError('Quilometragem inválida.')
        campos[campo] = numero
    for campo in ('valor_compra', 'valor_atual'):
        valor = dados.get(campo, getattr(existente, campo, None))
        try:
            numero = Decimal(str(valor)) if valor not in (None, '') else None
            if numero is not None and (not numero.is_finite() or not 0 <= numero <= Decimal('9999999999.99')):
                raise InvalidOperation()
        except (ValueError, InvalidOperation):
            raise ValueError(f'Valor inválido: {campo.replace("_", " ")}.') from None
        campos[campo] = float(numero) if numero is not None else None
    if 'placa' in dados or existente is None:
        campos['placa'] = normalizar_placa(dados.get('placa'))
    if 'data_compra' in dados:
        campos['data_compra'] = campo_data(dados, 'data_compra')
    campos.update(validar_documentacao_veiculo(dados))
    if existente and any(campos.get(campo) != getattr(existente, campo)
                         for campo in ('marca', 'modelo', 'versao', 'ano')):
        # A identificação de outra versão/ano não pode continuar vinculada ao carro editado.
        for campo in ('fipe_tipo', 'fipe_marca_id', 'fipe_modelo_id', 'fipe_ano_id',
                      'fipe_codigo', 'fipe_referencia', 'fipe_valor', 'fipe_consultado_em'):
            campos[campo] = None
    return campos
