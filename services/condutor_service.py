import re
from datetime import date

CATEGORIAS_CNH = ('ACC', 'A', 'B', 'AB', 'C', 'AC', 'D', 'AD', 'E', 'AE')


def validar_cpf(valor):
    cpf = re.sub(r'[.\-\s]', '', valor or '')
    if not cpf:
        return None
    if not re.fullmatch(r'\d{11}', cpf) or len(set(cpf)) == 1:
        raise ValueError('CPF inválido.')
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            raise ValueError('CPF inválido.')
    return cpf


def campo_texto(dados, campo, limite, obrigatorio=False):
    valor = str(dados.get(campo) or '').strip()
    if len(valor) > limite or (obrigatorio and not valor):
        raise ValueError(f'Campo {campo.replace("_", " ")} inválido (máximo {limite} caracteres).')
    return valor or None


def campo_data(dados, campo):
    valor = dados.get(campo)
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except (ValueError, TypeError):
        raise ValueError(f'Data inválida: {campo.replace("_", " ")}.') from None


def validar_condutor(dados):
    campos = dict(nome=campo_texto(dados, 'nome', 120, True), cpf=validar_cpf(dados.get('cpf')),
                  cnh_numero=campo_texto(dados, 'cnh_numero', 20),
                  cnh_categoria=campo_texto(dados, 'cnh_categoria', 5))
    if campos['cnh_categoria'] and campos['cnh_categoria'] not in CATEGORIAS_CNH:
        raise ValueError('Categoria da CNH inválida.')
    if campos['cnh_numero'] and not campos['cnh_numero'].isdigit():
        raise ValueError('O registro da CNH deve conter apenas números.')
    for campo in ('data_nascimento', 'cnh_validade', 'cnh_primeira_habilitacao'):
        campos[campo] = campo_data(dados, campo)
    for campo in ('data_nascimento', 'cnh_primeira_habilitacao'):
        if campos[campo] and campos[campo] > date.today():
            raise ValueError('Nascimento e primeira habilitação não podem estar no futuro.')
    if campos['data_nascimento'] and campos['cnh_primeira_habilitacao'] and campos['cnh_primeira_habilitacao'] <= campos['data_nascimento']:
        raise ValueError('Primeira habilitação deve ser posterior ao nascimento.')
    return campos


def validar_documentacao_veiculo(dados):
    campos = {}
    if 'ano_fabricacao' in dados:
        valor = dados.get('ano_fabricacao')
        try:
            ano = int(valor) if valor else None
        except (ValueError, TypeError):
            raise ValueError('Ano de fabricação inválido.') from None
        if ano and not 1900 <= ano <= date.today().year + 1:
            raise ValueError('Ano de fabricação inválido.')
        campos['ano_fabricacao'] = ano
    for campo, limite in (('chassi', 17), ('renavam', 11), ('proprietario', 120)):
        if campo in dados:
            campos[campo] = campo_texto(dados, campo, limite)
    if campos.get('chassi'):
        campos['chassi'] = campos['chassi'].upper()
        if not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', campos['chassi']):
            raise ValueError('Chassi deve conter 17 caracteres válidos.')
    if campos.get('renavam') and not re.fullmatch(r'\d{11}', campos['renavam']):
        raise ValueError('Renavam deve conter 11 números.')
    for campo in ('crlv_validade', 'seguro_validade'):
        if campo in dados:
            campos[campo] = campo_data(dados, campo)
    return campos
