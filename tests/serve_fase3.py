"""Servidor descartável para Cypress: apenas dados sintéticos e SQLite em memória."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SECRET_KEY'] = 'chave-local-exclusiva-da-auditoria-visual'
from app import create_app
from extensions import db
from models import User, Veiculo, Condutor

uploads = tempfile.TemporaryDirectory(prefix='autoviu-visual-')
app = create_app('development', start_scheduler=False, test_config={
    'SQLALCHEMY_DATABASE_URI':'sqlite://', 'SECRET_KEY':'chave-local-visual', 'DEBUG':False,
    'BCRYPT_LOG_ROUNDS':4, 'VEICULO_UPLOAD_ROOT':uploads.name,
    'GOOGLE_CLIENT_ID':'', 'GOOGLE_CLIENT_SECRET':'', 'OPENAI_API_KEY':'',
    'ASAAS_API_KEY':'', 'VAPID_PRIVATE_KEY':'', 'VAPID_PUBLIC_KEY':'',
    'WEBAUTHN_RP_ID':'', 'ALERTAS_AUTOMATICOS':False, 'PUBLIC_BASE_URL':'http://127.0.0.1:5087'})
with app.app_context():
    user = User(nome='Demonstração', email='visual@example.test', plano='pro', status='ativo', ativo=True, email_confirmado=True)
    user.set_password('VisualLocal123!')
    db.session.add(user)
    db.session.flush()
    db.session.add(Veiculo(user_id=user.id, marca='Fiat', modelo='Cronos', ano=2024, ativo=True, placa='ABC1D23', km_atual=12000))
    db.session.add(Condutor(user_id=user.id, nome='Condutor de demonstração', cnh_categoria='B'))
    db.session.commit()
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5087, debug=False, use_reloader=False, threaded=False)
