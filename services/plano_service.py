from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user

NIVEIS = {'free': 0, 'pro': 1, 'frota': 2, 'superadmin': 3}


def tem_plano(user, minimo='pro'):
    return user.is_authenticated and NIVEIS.get(user.plano_efetivo, 0) >= NIVEIS[minimo]


def requer_plano(minimo='pro'):
    def decorar(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            if not tem_plano(current_user, minimo):
                if request.is_json:
                    return jsonify(erro='Seu plano não permite acessar este recurso.'), 403
                flash('Este recurso exige plano ' + minimo.capitalize() + ' ativo. Seus dados foram preservados.', 'info')
                return redirect(url_for('assinatura.planos'))
            return funcao(*args, **kwargs)
        return executar
    return decorar
