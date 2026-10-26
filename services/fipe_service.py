import copy
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import requests
from flask import current_app

FONTE = 'FipeAPI / Parallelum'
FONTE_URL = 'https://fipe.api.br/docs/comece-aqui'
TIPOS = {'cars': 'Carro', 'motorcycles': 'Moto', 'trucks': 'Caminhão'}
MESES = ('janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')
_cache = OrderedDict()
_lock = threading.Lock()


class FipeIndisponivel(Exception):
    pass


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


def codigo(valor, ano=False):
    valor = str(valor or '')
    if not re.fullmatch(r'\d{4,5}-\d{1,2}' if ano else r'\d{1,12}', valor):
        raise ValueError('Seleção FIPE inválida. Escolha uma opção da lista.')
    return valor


def _consultar(recurso, referencia=None):
    agora = datetime.now(timezone.utc)
    token = current_app.config.get('FIPE_API_TOKEN', '')
    # O mês faz parte da chave: uma virada de mês nunca reutiliza cache do mês anterior.
    chave = (agora.strftime('%Y-%m'), recurso, referencia, token)
    ttl = max(1, min(int(current_app.config.get('FIPE_CACHE_SECONDS', 3600)), 86400))
    with _lock:
        item = _cache.get(chave)
        if item and item[0] > time.monotonic():
            _cache.move_to_end(chave)
            return copy.deepcopy(item[1]), item[2]
    try:
        resposta = requests.get('https://fipe.parallelum.com.br/api/v2' + recurso,
            params={'reference': referencia} if referencia else None,
            headers={'X-Subscription-Token': token} if token else {},
            timeout=(4, 12), allow_redirects=False)
        if resposta.status_code == 429:
            raise FipeIndisponivel('O limite de consultas do serviço foi atingido. Tente novamente mais tarde.')
        if resposta.status_code == 404:
            raise FipeIndisponivel('Não foi encontrado valor para essa seleção. Confira versão, ano e combustível.')
        resposta.raise_for_status()
        if resposta.status_code != 200:
            raise ValueError('Resposta inesperada')
        dados = resposta.json()
        if not isinstance(dados, (list, dict)):
            raise ValueError('Resposta inválida')
    except (requests.RequestException, ValueError):
        raise FipeIndisponivel('A consulta FIPE está indisponível no momento. Seus dados foram mantidos.') from None
    consultado = agora.isoformat()
    with _lock:
        _cache[chave] = (time.monotonic() + ttl, copy.deepcopy(dados), consultado)
        _cache.move_to_end(chave)
        while len(_cache) > 512:
            _cache.popitem(last=False)
    return dados, consultado


def _opcoes(recurso, referencia=None):
    dados, _ = _consultar(recurso, referencia)
    if not isinstance(dados, list):
        raise FipeIndisponivel('A lista FIPE não pôde ser carregada. Tente novamente.')
    resultado = []
    for item in dados:
        if isinstance(item, dict) and isinstance(item.get('name'), str) and item.get('code') is not None:
            resultado.append({'code': str(item['code']), 'name': item['name'][:200]})
    return resultado


def referencia_atual():
    dados, _ = _consultar('/references')
    if not isinstance(dados, list):
        raise FipeIndisponivel('Não foi possível identificar o mês de referência da FIPE.')
    referencias = [r for r in dados if isinstance(r, dict) and str(r.get('code', '')).isdigit() and isinstance(r.get('month'), str)]
    if not referencias:
        raise FipeIndisponivel('O serviço não informou uma referência FIPE válida.')
    referencia = max(referencias, key=lambda r: int(r['code']))
    return {'code': str(referencia['code']), 'month': referencia['month'][:60]}


def marcas(tipo, referencia):
    if tipo not in TIPOS:
        raise ValueError('Selecione o tipo do veículo.')
    return _opcoes('/' + tipo + '/brands', codigo(referencia))


def modelos(tipo, marca, referencia):
    if tipo not in TIPOS:
        raise ValueError('Selecione o tipo do veículo.')
    return _opcoes(f'/{tipo}/brands/{codigo(marca)}/models', codigo(referencia))


def anos(tipo, marca, modelo, referencia):
    if tipo not in TIPOS:
        raise ValueError('Selecione o tipo do veículo.')
    return _opcoes(f'/{tipo}/brands/{codigo(marca)}/models/{codigo(modelo)}/years', codigo(referencia))


def referencia_vigente(referencia):
    texto = normalizar(referencia)
    ano = re.search(r'\b(20\d{2})\b', texto)
    mes = next((i + 1 for i, nome in enumerate(MESES) if nome in texto.split()), None)
    hoje = datetime.now(timezone.utc)
    return bool(ano and mes and (int(ano[1]), mes) == (hoje.year, hoje.month))


def consultar_valor(tipo, marca, modelo, ano, referencia):
    if tipo not in TIPOS:
        raise ValueError('Selecione o tipo do veículo.')
    marca, modelo, ano = codigo(marca), codigo(modelo), codigo(ano, ano=True)
    dados, consultado = _consultar(f'/{tipo}/brands/{marca}/models/{modelo}/years/{ano}', codigo(referencia['code']))
    try:
        obrigatorios = ('price', 'brand', 'model', 'fuel', 'codeFipe', 'referenceMonth')
        if not isinstance(dados, dict) or any(not isinstance(dados.get(c), str) or not dados[c].strip() for c in obrigatorios):
            raise ValueError('Campos ausentes')
        if any(len(dados[c]) > 200 for c in obrigatorios) or len(dados['referenceMonth']) > 60:
            raise ValueError('Campo inesperado')
        if not re.fullmatch(r'\d{6}-\d', dados['codeFipe']):
            raise ValueError('Código FIPE inválido')
        preco = dados['price'].replace('R$', '').replace('.', '').replace(',', '.').strip()
        valor = Decimal(preco)
        if not valor.is_finite() or not 0 < valor <= Decimal('9999999999.99'):
            raise ValueError('Preço inválido')
        ano_modelo = int(dados['modelYear'])
        if ano_modelo != int(ano.split('-')[0]):
            raise ValueError('Ano divergente')
        if normalizar(dados['referenceMonth']).replace(' de ', ' ') != normalizar(referencia['month']).replace(' de ', ' '):
            raise ValueError('Referência divergente')
    except (ValueError, TypeError, KeyError, InvalidOperation):
        raise FipeIndisponivel('O serviço retornou uma cotação inconsistente. Nenhum valor foi aplicado ao cadastro.') from None
    return dict(tipo=tipo, marca_id=marca, modelo_id=modelo, ano_id=ano,
        marca=dados['brand'], modelo=dados['model'], ano_modelo=ano_modelo,
        combustivel=dados['fuel'], codigo=dados['codeFipe'], valor=str(valor.quantize(Decimal('0.01'))),
        valor_formatado='R$ ' + format(valor, ',.2f').replace(',', '#').replace('.', ',').replace('#', '.'),
        referencia=dados['referenceMonth'].strip(), referencia_codigo=referencia['code'],
        consultado_em=consultado, fonte=FONTE, fonte_url=FONTE_URL,
        vigente=referencia_vigente(dados['referenceMonth']))


def buscar_automatico(veiculo):
    """Tenta encontrar e buscar FIPE automaticamente pelos dados do veículo.

    Faz matching normalizado de marca → modelo → ano. Retorna dict de cotação
    (mesmo formato de consultar_valor) ou None se não for possível identificar
    de forma unívoca. Nunca lança exceção — falhas silenciosas.
    """
    tipo = 'cars'
    try:
        ref = referencia_atual()
        # ── Marca ──────────────────────────────────────────────────────────────
        lista_marcas = marcas(tipo, ref['code'])
        nome_marca = normalizar(veiculo.marca)
        candidatas_marca = [
            m for m in lista_marcas
            if normalizar(m['name']) == nome_marca
            or normalizar(m['name'].split(' - ')[0]) == nome_marca
            or nome_marca in normalizar(m['name'])
        ]
        if len(candidatas_marca) != 1:
            return None
        marca_id = candidatas_marca[0]['code']

        # ── Modelo ─────────────────────────────────────────────────────────────
        lista_modelos = modelos(tipo, marca_id, ref['code'])
        termos_modelo = normalizar(veiculo.modelo).split()
        candidatas_modelo = [
            m for m in lista_modelos
            if all(t in normalizar(m['name']) for t in termos_modelo)
        ]
        if not candidatas_modelo:
            return None
        if len(candidatas_modelo) > 1 and veiculo.versao:
            termos_versao = normalizar(veiculo.versao).split()
            refinados = [
                m for m in candidatas_modelo
                if any(t in normalizar(m['name']) for t in termos_versao)
            ]
            if refinados:
                candidatas_modelo = refinados
        # menor nome = versão mais genérica, menos risco de erro
        candidatas_modelo.sort(key=lambda m: len(m['name']))
        modelo_id = candidatas_modelo[0]['code']

        # ── Ano/combustível ────────────────────────────────────────────────────
        lista_anos = anos(tipo, marca_id, modelo_id, ref['code'])
        ano_str = str(veiculo.ano)
        candidatas_ano = [a for a in lista_anos if a['code'].startswith(ano_str + '-')]
        if not candidatas_ano:
            return None
        # prefere gasolina (-1), depois flex/etanol (-3), depois outros
        _pref = {'1': 0, '3': 1, '2': 2}
        candidatas_ano.sort(key=lambda a: _pref.get(a['code'].split('-')[-1], 9))
        ano_id = candidatas_ano[0]['code']

        return consultar_valor(tipo, marca_id, modelo_id, ano_id, ref)
    except Exception:
        return None


def interpretar_pergunta(pergunta):
    if len(pergunta) > 180:
        raise ValueError('Use uma pergunta com até 180 caracteres.')
    texto = normalizar(pergunta)
    if re.search(r'\b(meu|minha)\s+(carro|veiculo|moto|caminhao)\b', texto):
        return 'meu', ''
    alvo = re.sub(r'^(quanto|qual)\s+(vale|custa|e|o valor de|o valor do|o preco de|o preco do)?\s*', '', texto)
    alvo = re.sub(r'\b(esta|ta|vale|valendo|custa)\b.*$', '', alvo)
    alvo = re.sub(r'\b(o|a|aquele|aquela|carro|veiculo|modelo|um|uma|de|do|da|valor|preco|qual|e)\b', ' ', alvo)
    return 'outro', re.sub(r'\s+', ' ', alvo).strip()
