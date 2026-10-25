import re

_ANTIGA = re.compile(r'^[A-Z]{3}[0-9]{4}$')          # ABC1234 → gravada como ABC-1234
_MERCOSUL = re.compile(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$')  # ABC1D23


def normalizar_placa(valor):
    """Normaliza a placa para o formato de gravação.

    'abc1234' / 'ABC-1234' → 'ABC-1234' (padrão antigo)
    'abc1d23'              → 'ABC1D23'  (Mercosul)
    vazio/None             → None
    Levanta ValueError se não for placa antiga nem Mercosul.
    """
    bruto = re.sub(r'[^A-Za-z0-9]', '', valor or '').upper()
    if not bruto:
        return None
    if _ANTIGA.match(bruto):
        return f'{bruto[:3]}-{bruto[3:]}'
    if _MERCOSUL.match(bruto):
        return bruto
    raise ValueError('Placa inválida. Use ABC-1234 ou ABC1D23 (Mercosul).')
