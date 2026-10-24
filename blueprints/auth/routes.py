from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import User, Veiculo

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar') == 'on'

        user = User.query.filter_by(email=email, ativo=True).first()

        if user and user.check_password(senha):
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=lembrar)

            veiculo = Veiculo.query.filter_by(user_id=user.id, ativo=True).first()
            if veiculo:
                session['veiculo_ativo_id'] = veiculo.id

            destino = request.args.get('next')
            return redirect(destino or url_for('main.index'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('veiculo_ativo_id', None)
    logout_user()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('auth.login'))
