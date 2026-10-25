from flask import session, url_for

from models import Condutor, Veiculo


def destino_inicial(user):
    """Retoma o cadastro sem guardar documentos ou dados pessoais na sessão."""
    if Veiculo.query.filter_by(user_id=user.id, ativo=True).first():
        return url_for('main.index')
    tem_condutor = Condutor.query.filter_by(user_id=user.id).first() is not None
    if not tem_condutor and session.get('cadastro_condutor_pulado') != user.id:
        return url_for('condutor.perfil', cadastro=1)
    return url_for('veiculo.novo')
