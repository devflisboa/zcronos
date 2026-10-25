from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import limiter
from services.documento_service import extrair_documento, DocumentoIndisponivel

documento_bp = Blueprint('documento', __name__)


@documento_bp.route('/<tipo>', methods=['POST'])
@login_required
@limiter.limit('5/hour', key_func=lambda: str(current_user.id))
def importar(tipo):
    if tipo not in ('cnh', 'crlv'):
        return jsonify(erro='Tipo de documento inválido.'), 404
    if request.form.get('consentimento') != 'sim':
        return jsonify(erro='Confirme o envio ao serviço de leitura de documentos.'), 400
    try:
        campos = extrair_documento(request.files.getlist('documentos'), tipo)
        return jsonify(campos=campos)
    except ValueError as erro:
        return jsonify(erro=str(erro)), 400
    except DocumentoIndisponivel as erro:
        return jsonify(erro=str(erro)), 503
