from datetime import date
from decimal import Decimal, InvalidOperation

from services.condutor_service import campo_data, campo_texto

TIPOS = ('oleo', 'revisao', 'pneu', 'freio', 'bateria', 'filtro', 'outro')


def validar_quilometragem(valor, obrigatorio=False):
    if valor in (None, ''):
        if obrigatorio:
            raise ValueError('Informe a quilometragem.')
        return None
    try:
        texto = str(valor).strip()
        if not texto.isascii() or not texto.isdecimal():
            raise ValueError()
        numero = int(texto)
        if not 0 <= numero <= 2147483647:
            raise ValueError()
        return numero
    except (ValueError, TypeError):
        raise ValueError('Informe uma quilometragem inteira entre 0 e 2147483647 km.') from None


def _custo(valor):
    try:
        numero = Decimal(str(valor)) if valor not in (None, '') else Decimal('0')
        if not numero.is_finite() or not 0 <= numero <= Decimal('9999999999.99'):
            raise InvalidOperation()
        if numero != numero.quantize(Decimal('0.01')):
            raise InvalidOperation()
        return float(numero)
    except (ValueError, InvalidOperation):
        raise ValueError('Informe um custo válido, não negativo, com até duas casas decimais.') from None


def validar_manutencao(dados, existente=None):
    if existente is not None:
        campos = {'status': 'realizada'}
        campos['data_realizada'] = campo_data(dados, 'data_realizada') or date.today()
        km = dados.get('km_realizada')
        campos['km_realizada'] = validar_quilometragem(km) if km not in (None, '') else existente.km_realizada
        custo = dados.get('custo')
        campos['custo'] = _custo(custo) if custo not in (None, '') else existente.custo
    else:
        tipo = campo_texto(dados, 'tipo', 50, True)
        status = dados.get('status', 'pendente')
        if tipo not in TIPOS or status not in ('pendente', 'realizada'):
            raise ValueError('Selecione um tipo e um status válidos para a manutenção.')
        campos = dict(tipo=tipo, status=status,
                      descricao=campo_texto(dados, 'descricao', 200, True),
                      observacoes=campo_texto(dados, 'observacoes', 5000),
                      data_realizada=campo_data(dados, 'data_realizada'),
                      data_prevista=campo_data(dados, 'data_prevista'),
                      km_realizada=validar_quilometragem(dados.get('km_realizada')),
                      km_previsto=validar_quilometragem(dados.get('km_previsto')),
                      custo=_custo(dados.get('custo')))
        if status == 'realizada' and campos['data_realizada'] is None:
            campos['data_realizada'] = date.today()
    if campos['data_realizada'] and campos['data_realizada'] > date.today():
        raise ValueError('A data de realização não pode estar no futuro. Use a data prevista para agendar.')
    return campos
