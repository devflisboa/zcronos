from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required
from extensions import db
from models import Abastecimento
from services.veiculo_helper import get_veiculo_ativo

abastecimento_bp = Blueprint('abastecimento', __name__)


@abastecimento_bp.route('/cadastrar')
@login_required
def cadastrar_abastecimento():
    veiculo = get_veiculo_ativo()
    return render_template('cadastrar_abastecimento.html', veiculo=veiculo, hoje=date.today())


@abastecimento_bp.route('/add', methods=['POST'])
@login_required
def add_abastecimento():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Nenhum veículo ativo. Selecione um veículo primeiro.', 'danger')
        return redirect(url_for('veiculo.index'))
    try:
        data_str = request.form.get('data')
        def _float(v): return float(v) if v else None
        novo = Abastecimento(
            veiculo_id=veiculo.id,
            quilometragem=int(request.form.get('quilometragem') or 0),
            litros_abastecidos=float(request.form.get('litros_abastecidos') or 0),
            valor_total=float(request.form.get('valor_total') or 0),
            posto=request.form.get('posto') or '',
            preco_combustivel=float(request.form.get('preco_combustivel') or 0),
            data=date.fromisoformat(data_str) if data_str else None,
            tipo_combustivel=request.form.get('tipo_combustivel') or None,
            observacao=request.form.get('observacao') or None,
            latitude=_float(request.form.get('latitude')),
            longitude=_float(request.form.get('longitude')),
        )
        db.session.add(novo)
        db.session.commit()
        flash('Abastecimento adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))


@abastecimento_bp.route('/mapa')
@login_required
def mapa():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        flash('Selecione um veículo para ver o mapa.', 'info')
        return redirect(url_for('veiculo.index'))
    return render_template('mapa_abastecimentos.html', veiculo=veiculo)


@abastecimento_bp.route('/mapa/pontos.json')
@login_required
def mapa_pontos():
    veiculo = get_veiculo_ativo()
    if not veiculo:
        return jsonify([])
    registros = Abastecimento.query.filter(
        Abastecimento.veiculo_id == veiculo.id,
        Abastecimento.latitude.isnot(None),
        Abastecimento.longitude.isnot(None),
    ).order_by(Abastecimento.data.desc()).all()
    pontos = [{
        'lat': r.latitude,
        'lng': r.longitude,
        'data': r.data.strftime('%d/%m/%Y'),
        'posto': r.posto or '—',
        'litros': r.litros_abastecidos,
        'valor': r.valor_total,
        'preco_litro': r.preco_combustivel,
        'tipo': r.tipo_combustivel or '',
    } for r in registros]
    return jsonify(pontos)


@abastecimento_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_abastecimento(id):
    veiculo = get_veiculo_ativo()
    abastecimento = db.session.get(Abastecimento, id)
    if not abastecimento or not veiculo or abastecimento.veiculo_id != veiculo.id:
        abort(404)
    if request.method == 'POST':
        try:
            data_str = request.form.get('data')
            def _float(v): return float(v) if v else None
            abastecimento.quilometragem = int(request.form.get('quilometragem') or 0)
            abastecimento.litros_abastecidos = float(request.form.get('litros_abastecidos') or 0)
            abastecimento.valor_total = float(request.form.get('valor_total') or 0)
            abastecimento.posto = request.form.get('posto') or ''
            abastecimento.preco_combustivel = float(request.form.get('preco_combustivel') or 0)
            abastecimento.data = date.fromisoformat(data_str) if data_str else abastecimento.data
            abastecimento.tipo_combustivel = request.form.get('tipo_combustivel') or None
            abastecimento.observacao = request.form.get('observacao') or None
            lat = _float(request.form.get('latitude'))
            lng = _float(request.form.get('longitude'))
            if lat is not None and lng is not None:
                abastecimento.latitude = lat
                abastecimento.longitude = lng
            db.session.commit()
            flash('Abastecimento atualizado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar abastecimento: {e}', 'danger')
        return redirect(url_for('main.index'))
    return render_template('editar_abastecimento.html', a=abastecimento, veiculo=veiculo)


@abastecimento_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_abastecimento(id):
    veiculo = get_veiculo_ativo()
    abastecimento = db.session.get(Abastecimento, id)
    if not abastecimento or not veiculo or abastecimento.veiculo_id != veiculo.id:
        abort(404)
    try:
        db.session.delete(abastecimento)
        db.session.commit()
        flash('Abastecimento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir abastecimento: {e}', 'danger')
    return redirect(url_for('main.index'))
