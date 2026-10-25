from flask import session
from flask_login import current_user
from models import Veiculo


def get_veiculo_ativo():
    """Retorna o Veiculo ativo da sessão do usuário atual.

    Busca pelo id em session['veiculo_ativo_id'] e verifica a propriedade.
    Se não encontrar, pega o primeiro veículo ativo do usuário e grava na sessão.
    Retorna None se o usuário não tiver nenhum veículo cadastrado.
    """
    veiculo_id = session.get('veiculo_ativo_id')
    if veiculo_id:
        v = Veiculo.query.filter_by(
            id=veiculo_id, user_id=current_user.id, ativo=True
        ).first()
        if v:
            return v
    v = Veiculo.query.filter_by(user_id=current_user.id, ativo=True).order_by(Veiculo.id).first()
    if v:
        session['veiculo_ativo_id'] = v.id
    else:
        session.pop('veiculo_ativo_id', None)
    return v
