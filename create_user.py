"""
Script para criar usuário manualmente (admin ou owner).
Rodar no servidor após o deploy:

    docker exec -it zcronos_web_1 python create_user.py
"""
import os
import sys

email = os.environ.get('ADMIN_EMAIL') or input('E-mail: ').strip().lower()
nome  = os.environ.get('ADMIN_NOME')  or input('Nome: ').strip()
senha = os.environ.get('ADMIN_SENHA') or input('Senha: ').strip()
plano = os.environ.get('ADMIN_PLANO') or input('Plano (free/pro/frota) [frota]: ').strip() or 'frota'

if len(senha) < 8:
    print('Senha deve ter pelo menos 8 caracteres.')
    sys.exit(1)

if plano not in ('free', 'pro', 'frota'):
    print('Plano inválido. Use: free, pro ou frota.')
    sys.exit(1)

from app import create_app
from extensions import db
from models import User

app = create_app('production')

with app.app_context():
    if User.query.filter_by(email=email).first():
        print(f'Usuário {email} já existe.')
        sys.exit(0)

    user = User(
        email=email,
        nome=nome,
        ativo=True,
        plano=plano,
        status='ativo',
        email_confirmado=True,
    )
    user.set_password(senha)
    db.session.add(user)
    db.session.commit()
    print(f'Usuário criado: {email} | plano={plano} | id={user.id}')
