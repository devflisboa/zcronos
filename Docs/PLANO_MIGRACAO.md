# zCronos — Plano de Migração para SaaS

> Como transformar o app mono-tenant em multi-tenant preservando dados existentes.  
> Data: 2026-10-23 | Versão: 1.0

---

## Premissas

- Os dados da produção atual (veículo, abastecimentos, manutenções, despesas) pertencem ao Felipe e devem ser preservados.
- A migração deve ser **incremental e reversível** — nenhum dado é deletado sem backup.
- O banco MySQL 8.0 será mantido (não migrar para PostgreSQL nesta fase).
- O app ficará online durante toda a migração (sem janela de manutenção necessária inicialmente).

---

## Fase 1 — Backup antes de qualquer coisa

```bash
# No servidor, antes de qualquer alteração no schema:
ssh -p 64622 -i ~/.ssh/id_casakek felipe@casakek.duckdns.org

# Dentro do container MySQL
docker exec zcronos_db_1 mysqldump \
  -u root -pSEU_PASSWORD \
  --single-transaction \
  --routines \
  --triggers \
  car_management > /home/felipe/backup_zcronos_pre_saas_$(date +%Y%m%d).sql

# Copiar backup para local
scp -P 64622 -i ~/.ssh/id_casakek \
  felipe@casakek.duckdns.org:/home/felipe/backup_zcronos_pre_saas_*.sql \
  "D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\.VERUS\DASHBOARDCARRO\backups\"
```

---

## Fase 2 — Instalar Alembic (substituir migrações manuais)

### 2.1 Adicionar dependências

```
# requirements.txt — adicionar:
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Bcrypt==1.0.1
Flask-Limiter==3.8.0
alembic==1.13.1
```

### 2.2 Inicializar Alembic

```bash
# Na raiz do projeto local:
alembic init migrations
```

### 2.3 Configurar `migrations/env.py`

```python
from app import create_app
from extensions import db

app = create_app('production')

with app.app_context():
    target_metadata = db.metadata
```

### 2.4 Remover `_run_migrations()` do `app.py`

O bloco `_run_migrations()` atual faz `ALTER TABLE` manual — substituir por Alembic completamente.

---

## Fase 3 — Migração de schema (incremental)

### Script de migração Alembic (gerado manualmente para dados existentes)

```python
# migrations/versions/001_add_multi_tenant.py
"""add multi-tenant support"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Criar tabela usuarios
    op.create_table('usuarios',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('plano', sa.Enum('free','pro','frota'), default='free'),
        sa.Column('status', sa.Enum('ativo','suspenso','cancelado'), default='ativo'),
        sa.Column('email_confirmado', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime),
    )
    op.create_index('idx_email', 'usuarios', ['email'])
    
    # 2. Inserir usuário Felipe (owner dos dados atuais)
    op.execute("""
        INSERT INTO usuarios (email, password_hash, nome, plano, status, email_confirmado)
        VALUES (
            'felipe.lisboa@gmail.com',
            '$2b$12$TROQUE_APOS_MIGRAR',  -- rodar: bcrypt.generate_password_hash('senha') 
            'Felipe Lisboa',
            'frota',
            'ativo',
            TRUE
        )
    """)
    
    # 3. Adicionar user_id e ativo ao veiculo
    op.add_column('veiculo', sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id')))
    op.add_column('veiculo', sa.Column('ativo', sa.Boolean, default=True))
    
    # 4. Vincular veiculo existente ao Felipe (user_id=1)
    op.execute("UPDATE veiculo SET user_id = 1, ativo = TRUE")
    
    # 5. Tornar user_id obrigatório após preencher dados
    op.alter_column('veiculo', 'user_id', nullable=False)
    
    # 6. Adicionar veiculo_id às tabelas transacionais
    for tabela in ['abastecimentos', 'despesas', 'manutencoes', 'corrida_uber']:
        op.add_column(tabela, sa.Column('veiculo_id', sa.Integer, sa.ForeignKey('veiculo.id')))
        op.execute(f"UPDATE {tabela} SET veiculo_id = (SELECT id FROM veiculo LIMIT 1)")
        op.alter_column(tabela, 'veiculo_id', nullable=False)
    
    # 7. Adicionar user_id ao semanal_uber
    op.add_column('semanal_uber', sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id')))
    op.execute("UPDATE semanal_uber SET user_id = 1")
    
    # 8. Criar índices de performance
    for tabela in ['abastecimentos', 'despesas', 'manutencoes', 'corrida_uber']:
        op.create_index(f'idx_{tabela}_veiculo', tabela, ['veiculo_id'])
    
    # 9. Criar tabela de telemetria OBD (vazia, para futura integração)
    op.create_table('telemetria_obd',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('veiculo_id', sa.Integer, sa.ForeignKey('veiculo.id'), nullable=False),
        sa.Column('registrado_em', sa.DateTime, server_default=sa.func.now()),
        sa.Column('rpm', sa.SmallInteger),
        sa.Column('velocidade_kmh', sa.SmallInteger),
        sa.Column('temp_liquido_c', sa.SmallInteger),
        sa.Column('carga_motor_pct', sa.SmallInteger),
        sa.Column('nivel_comb_pct', sa.SmallInteger),
        sa.Column('dtc_codes', sa.JSON),
    )
    op.create_index('idx_obd_veiculo_ts', 'telemetria_obd', ['veiculo_id', 'registrado_em'])
    
    # 10. Criar tabela de assinaturas
    op.create_table('assinaturas',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('plano', sa.Enum('free','pro','frota'), nullable=False),
        sa.Column('status', sa.Enum('ativo','cancelado','trial'), default='trial'),
        sa.Column('data_inicio', sa.Date, nullable=False),
        sa.Column('data_renovacao', sa.Date),
        sa.Column('gateway_id', sa.String(100)),
    )

def downgrade():
    # Reverter na ordem inversa
    op.drop_table('assinaturas')
    op.drop_table('telemetria_obd')
    for tabela in ['abastecimentos', 'despesas', 'manutencoes', 'corrida_uber']:
        op.drop_index(f'idx_{tabela}_veiculo')
        op.drop_column(tabela, 'veiculo_id')
    op.drop_column('semanal_uber', 'user_id')
    op.drop_column('veiculo', 'user_id')
    op.drop_column('veiculo', 'ativo')
    op.drop_table('usuarios')
```

---

## Fase 4 — Atualizar modelos Python

### models.py — mudanças necessárias

```python
# 1. Novo modelo User
class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome          = db.Column(db.String(100), nullable=False)
    plano         = db.Column(db.Enum('free','pro','frota'), default='free')
    status        = db.Column(db.Enum('ativo','suspenso','cancelado'), default='ativo')
    email_confirmado = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    veiculos      = db.relationship('Veiculo', backref='dono', lazy='dynamic')

# 2. Veiculo — adicionar FKs
class Veiculo(db.Model):
    # ... campos existentes mantidos ...
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ativo   = db.Column(db.Boolean, default=True)
    abastecimentos = db.relationship('Abastecimento', backref='veiculo', lazy='dynamic')
    despesas       = db.relationship('Despesa', backref='veiculo', lazy='dynamic')
    manutencoes    = db.relationship('Manutencao', backref='veiculo', lazy='dynamic')

# 3. Todas as tabelas transacionais — adicionar veiculo_id
class Abastecimento(db.Model):
    # ... campos existentes ...
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)

# Mesma mudança para: Despesa, Manutencao, CorridaUber
# SemanalUber → adicionar user_id (não veiculo_id)
```

---

## Fase 5 — Atualizar todas as queries (isolamento de dados)

### Padrão de atualização obrigatória para cada blueprint

```python
# Antes (inseguro):
@main_bp.route('/')
def index():
    veiculo = Veiculo.query.first()
    abastecimentos = Abastecimento.query.all()

# Depois (seguro):
@main_bp.route('/')
@login_required
def index():
    veiculo_id = session.get('veiculo_ativo_id')
    veiculo = Veiculo.query.filter_by(
        id=veiculo_id,
        user_id=current_user.id
    ).first_or_404()
    
    abastecimentos = Abastecimento.query.filter_by(
        veiculo_id=veiculo.id
    ).all()
```

### Arquivos que precisam ser atualizados

| Arquivo | Mudanças |
|---|---|
| `blueprints/main/routes.py` | Adicionar `@login_required`, filtrar por `user_id` |
| `blueprints/abastecimento/routes.py` | Adicionar `@login_required`, `veiculo_id` nos inserts, verificar propriedade nos deletes |
| `blueprints/despesa/routes.py` | Idem |
| `blueprints/manutencao/routes.py` | Idem |
| `blueprints/uber/routes.py` | Idem |
| `services/dashboard_service.py` | Receber `veiculo_id` como parâmetro |
| `services/despesa_service.py` | Idem |
| `services/uber_corrida_service.py` | Receber `user_id` como parâmetro |
| `services/abastecimento_service.py` | Idem |

---

## Fase 6 — Atualizar app.py

```python
# app.py — remover _seed() com dados hardcoded do Cronos
# Manter apenas seed de Categorias (são globais)
# Remover _run_migrations() — substituído pelo Alembic

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para continuar.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.veiculo import veiculo_bp
    # ... demais blueprints ...
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(veiculo_bp, url_prefix='/veiculos')
    # ...
    
    with app.app_context():
        _seed_categorias()  # apenas categorias globais
    
    return app
```

---

## Fase 7 — Testes antes do deploy

### Checklist de testes manuais

- [ ] Cadastrar novo usuário → receber e-mail de confirmação
- [ ] Login com credenciais corretas → redirect ao dashboard
- [ ] Login com credenciais erradas → mensagem de erro, sem detalhes técnicos
- [ ] Dashboard de usuário A não mostra dados de usuário B
- [ ] DELETE `/despesa/delete/<id_do_usuario_B>` logado como usuário A → 403/404
- [ ] Cadastrar veículo respeitando limite do plano (Free: máx 1)
- [ ] Alembic rollback funciona (executa `downgrade()`)

### Testes automatizados (adicionar ao projeto)

```python
# tests/test_auth.py
def test_login_redirect(client):
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']

def test_data_isolation(client, user_a, user_b):
    despesa_b = criar_despesa(user=user_b)
    client.post('/auth/login', data={'email': user_a.email, 'password': 'senha'})
    resp = client.post(f'/despesa/delete/{despesa_b.id}')
    assert resp.status_code in (403, 404)
```

---

## Rollback de emergência

Se algo der errado após o deploy:

```bash
# 1. Restaurar backup
docker exec -i zcronos_db_1 mysql \
  -u root -pSEU_PASSWORD car_management \
  < /home/felipe/backup_zcronos_pre_saas_YYYYMMDD.sql

# 2. Reverter código para commit antes da migração
git revert HEAD~1  # ou git reset --hard <commit-hash>

# 3. Rebuild e restart
docker-compose -f docker-compose.prod.yml build web
docker ps -a --filter name=zcronos_web --format '{{.Names}}' | xargs -r docker rm -f
docker-compose -f docker-compose.prod.yml up -d --no-deps web
```

---

## Estimativa de esforço

| Fase | Esforço estimado | Dependências |
|---|---|---|
| Fase 1 — Backup | 15 min | Acesso SSH ao servidor |
| Fase 2 — Alembic install | 1h | — |
| Fase 3 — Script de migração | 2h | Fase 2 |
| Fase 4 — Atualizar modelos | 2h | Fase 3 |
| Fase 5 — Atualizar queries | 3h | Fase 4 |
| Fase 6 — Autenticação completa | 4h | Fase 4 |
| Fase 7 — Templates de auth | 3h | Fase 6 |
| Fase 8 — Testes e deploy | 2h | Todas |
| **Total** | **~17h de dev** | — |
