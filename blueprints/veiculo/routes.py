from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, send_file, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models import Veiculo, User, Condutor
from services.veiculo_helper import get_veiculo_ativo
from services.veiculo_service import validar_veiculo
from services.foto_service import preparar_foto_capa, pasta_fotos

veiculo_bp = Blueprint('veiculo', __name__)


@veiculo_bp.route('/')
@login_required
def index():
    veiculos = Veiculo.query.filter_by(user_id=current_user.id, ativo=True).order_by(Veiculo.id).all()
    ativo = get_veiculo_ativo()
    return render_template('veiculos/index.html', veiculos=veiculos,
        veiculo_ativo_id=ativo.id if ativo else None, pode_adicionar=current_user.pode_adicionar_veiculo())


@veiculo_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    condutor = Condutor.query.filter_by(user_id=current_user.id).first()
    cadastro = not Veiculo.query.filter_by(user_id=current_user.id, ativo=True).first()
    if request.method == 'POST':
        User.query.filter_by(id=current_user.id).with_for_update().one()
    if not current_user.pode_adicionar_veiculo(bloquear=request.method == 'POST'):
        flash('Limite de veículos atingido para o seu plano.', 'danger')
        return redirect(url_for('veiculo.index'))
    if request.method == 'POST':
        try:
            v = Veiculo(user_id=current_user.id, ativo=True, **validar_veiculo(request.form))
            if condutor and request.form.get('vincular_condutor') == 'sim':
                v.condutor_id = condutor.id
            db.session.add(v)
            db.session.commit()
            session['veiculo_ativo_id'] = v.id
            flash(f'{v.marca} {v.modelo} cadastrado com sucesso!', 'success')
            return redirect(url_for('main.index'))
        except ValueError as erro:
            db.session.rollback()
            flash(str(erro), 'danger')
        except SQLAlchemyError as erro:
            db.session.rollback()
            current_app.logger.error('Falha ao cadastrar veículo: %s', type(erro).__name__)
            flash('Não foi possível cadastrar o veículo. Tente novamente.', 'danger')
        return render_template('veiculos/form.html', veiculo=None, condutor=condutor, cadastro=cadastro), 400
    return render_template('veiculos/form.html', veiculo=None, condutor=condutor, cadastro=cadastro)


@veiculo_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    condutor = Condutor.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        try:
            for campo, valor in validar_veiculo(request.form, v).items():
                setattr(v, campo, valor)
            if condutor:
                v.condutor_id = condutor.id if request.form.get('vincular_condutor') == 'sim' else None
            # Foto capa — processada separadamente para não bloquear o form em caso de erro
            arquivo_capa = request.files.get('foto_capa')
            if arquivo_capa and arquivo_capa.filename:
                try:
                    png_bytes = preparar_foto_capa(arquivo_capa)
                    pasta = pasta_fotos(v.id)
                    pasta.mkdir(parents=True, exist_ok=True)
                    nome_capa = f'capa_{v.id}.png'
                    (pasta / nome_capa).write_bytes(png_bytes)
                    v.foto_capa = nome_capa
                except ValueError as e:
                    flash(str(e), 'warning')
                except Exception:
                    current_app.logger.exception('Falha ao processar foto capa')
                    flash('Não foi possível processar a foto. Dados do veículo foram salvos.', 'warning')
            db.session.commit()
            flash('Veículo atualizado!', 'success')
            return redirect(url_for('veiculo.index'))
        except ValueError as erro:
            db.session.rollback()
            flash(str(erro), 'danger')
        except SQLAlchemyError as erro:
            db.session.rollback()
            current_app.logger.error('Falha ao editar veículo: %s', type(erro).__name__)
            flash('Não foi possível salvar o veículo. Tente novamente.', 'danger')
        return render_template('veiculos/form.html', veiculo=v, condutor=condutor, cadastro=False), 400
    return render_template('veiculos/form.html', veiculo=v, condutor=condutor, cadastro=False)


@veiculo_bp.route('/<int:id>/capa')
@login_required
def capa(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    if not v.foto_capa:
        abort(404)
    arquivo = pasta_fotos(id) / v.foto_capa
    if not arquivo.is_file():
        abort(404)
    resp = send_file(arquivo, mimetype='image/png', max_age=0)
    resp.headers['Cache-Control'] = 'private, no-store'
    return resp


@veiculo_bp.route('/<int:id>/selecionar', methods=['POST'])
@login_required
def selecionar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    session['veiculo_ativo_id'] = v.id
    flash(f'{v.marca} {v.modelo} selecionado.', 'success')
    return redirect(url_for('main.index'))


@veiculo_bp.route('/<int:id>/deletar', methods=['POST'])
@login_required
def deletar(id):
    v = Veiculo.query.filter_by(id=id, user_id=current_user.id, ativo=True).first_or_404()
    if session.get('veiculo_ativo_id') == v.id:
        flash('Não é possível remover o veículo ativo. Selecione outro primeiro.', 'danger')
        return redirect(url_for('veiculo.index'))
    v.ativo = False
    db.session.commit()
    flash(f'{v.marca} {v.modelo} removido.', 'success')
    return redirect(url_for('veiculo.index'))
