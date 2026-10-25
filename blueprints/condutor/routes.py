from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models import Condutor, Veiculo
from services.condutor_service import validar_condutor, CATEGORIAS_CNH

condutor_bp = Blueprint('condutor', __name__)


@condutor_bp.route('/', methods=['GET', 'POST'])
@login_required
def perfil():
    condutor = Condutor.query.filter_by(user_id=current_user.id).first()
    cadastro = request.args.get('cadastro') == '1'
    if request.method == 'POST':
        try:
            campos = validar_condutor(request.form)
            if condutor is None:
                condutor = Condutor(user_id=current_user.id, **campos)
                db.session.add(condutor)
                db.session.flush()
            else:
                for campo, valor in campos.items():
                    setattr(condutor, campo, valor)
            selecionados = {int(item) for item in request.form.getlist('veiculos')}
            veiculos = Veiculo.query.filter_by(user_id=current_user.id, ativo=True).all()
            if not selecionados.issubset({v.id for v in veiculos}):
                raise ValueError('Veículo não disponível para vinculação.')
            for veiculo in veiculos:
                veiculo.condutor_id = condutor.id if veiculo.id in selecionados else None
            db.session.commit()
            session.pop('cadastro_condutor_pulado', None)
            flash('Perfil do condutor atualizado.', 'success')
            if cadastro:
                return redirect(url_for('veiculo.novo'))
            return redirect(url_for('condutor.perfil'))
        except ValueError as erro:
            db.session.rollback()
            flash(str(erro), 'danger')
        except SQLAlchemyError:
            db.session.rollback()
            flash('Não foi possível salvar. Tente novamente.', 'danger')
        return render_template('condutor/perfil.html', condutor=condutor, cadastro=cadastro,
            categorias=CATEGORIAS_CNH, veiculos=Veiculo.query.filter_by(user_id=current_user.id, ativo=True).all()), 400
    return render_template('condutor/perfil.html', condutor=condutor, cadastro=cadastro,
        categorias=CATEGORIAS_CNH, veiculos=Veiculo.query.filter_by(user_id=current_user.id, ativo=True).all())


@condutor_bp.route('/pular', methods=['POST'])
@login_required
def pular():
    session['cadastro_condutor_pulado'] = current_user.id
    return redirect(url_for('veiculo.novo'))
