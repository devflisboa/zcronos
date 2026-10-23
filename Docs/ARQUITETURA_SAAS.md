# zCronos — Arquitetura SaaS

> Documento técnico para transformação do app mono-tenant em plataforma multi-tenant.  
> Data: 2026-10-23 | Versão: 1.0

---

## 1. Estado atual (baseline)

### Stack existente
- **Backend:** Flask 3.0.3 + SQLAlchemy 2.0 + PyMySQL (MySQL 8.0)
- **Frontend:** Jinja2 templates + Chart.js + Plotly
- **Infra:** Docker + Gunicorn (gthread) + DuckDNS + Nginx Proxy Manager
- **Produção:** `zcronos.duckdns.org` → porta 5012 no servidor `casakek.duckdns.org:64622`

### Modelos existentes (sem user_id / tenant_id)

| Modelo | Tabela | Problema |
|---|---|---|
| `Veiculo` | `veiculo` | Singleton — `Veiculo.query.first()` hardcoded em toda view |
| `Abastecimento` | `abastecimentos` | Sem FK para Veiculo ou User |
| `Categoria` | `categorias` | Sem FK (compartilhado — OK para SaaS) |
| `Despesa` | `despesas` | FK apenas para Categoria |
| `Manutencao` | `manutencoes` | Sem FK para Veiculo ou User |
| `CorridaUber` | `corrida_uber` | Sem FK |
| `SemanalUber` | `semanal_uber` | Sem FK |

### Problemas críticos de segurança
1. **Zero autenticação** — todas as rotas são públicas
2. **Zero autorização** — qualquer um deleta qualquer registro via `POST /despesa/delete/<id>`
3. **Zero CSRF** — todos os forms POST desprotegidos
4. **Sem multi-tenancy** — dados globais, sem `user_id` ou `tenant_id`
5. **SECRET_KEY padrão fraca** — `'minha_chave_secreta_default'` no config.py
6. **Migrações manuais** — `ALTER TABLE` em SQL bruto no `app.py`
7. **Seed com dados reais** — placa `RGE7D41`, km, valor do carro gravados no código

---

## 2. Arquitetura SaaS alvo

### Modelo de dados multi-tenant

A estratégia adotada é **shared database, shared schema com `user_id`** — mais simples de operar, suficiente para o volume esperado. Row-Level Security no PostgreSQL pode ser adicionado na Fase 3.

```
User
 ├── id (PK)
 ├── email (unique)
 ├── password_hash
 ├── nome
 ├── plano (free | pro | frota)
 ├── status (ativo | suspenso | cancelado)
 ├── created_at
 └── last_login_at
      │
      ├──► Veiculo (user_id FK)
      │     ├── id
      │     ├── user_id  ← NOVO
      │     ├── marca, modelo, versao, motor, ano
      │     ├── placa, cor
      │     ├── km_atual, data_compra, valor_compra
      │     └── ativo (bool)
      │          │
      │          ├──► Abastecimento (veiculo_id FK)
      │          ├──► Despesa (veiculo_id FK)
      │          ├──► Manutencao (veiculo_id FK)
      │          └──► CorridaUber (veiculo_id FK)
      │
      └──► SemanalUber (user_id FK, sem vínculo de veículo)

Categoria (sem user_id — catálogo global compartilhado)
```

### Limites por plano

| Recurso | Gratuito | Pro (R$14,90/mês) | Frota (R$49,90/mês) |
|---|---|---|---|
| Veículos | 1 | 3 | 15 |
| Histórico | 12 meses | Ilimitado | Ilimitado |
| Export CSV | ✗ | ✓ | ✓ |
| API OBD-II | ✗ | ✓ | ✓ |
| Gestão equipe | ✗ | ✗ | ✓ |
| Relatórios PDF | ✗ | ✓ | ✓ |

### Camadas da arquitetura SaaS

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Jinja2 → migrar gradualmente para componentes)   │
│  Login | Dashboard | Veículos | Abastecimento | Manutenção  │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / REST
┌───────────────────────▼─────────────────────────────────────┐
│  Flask App (blueprints)                                     │
│  auth_bp | dashboard_bp | veiculo_bp | abastecimento_bp ... │
│  + @login_required decorator em TODAS as rotas             │
│  + @plan_required(min='pro') para features pagas           │
│  + CSRF protection (Flask-WTF)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │ SQLAlchemy + Alembic
┌───────────────────────▼─────────────────────────────────────┐
│  MySQL 8.0 (manter) ou PostgreSQL (upgrade futuro)         │
│  Schema com user_id + veiculo_id em todas as tabelas       │
│  Indexes: user_id, veiculo_id, data                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Novos componentes a criar

### 3.1 Blueprint de autenticação (`blueprints/auth/`)

```python
# Rotas:
GET  /auth/login           # Tela de login
POST /auth/login           # Processa login (bcrypt verify)
GET  /auth/registro        # Tela de cadastro
POST /auth/registro        # Cria conta + envia e-mail de confirmação
GET  /auth/logout          # Invalida sessão
GET  /auth/confirmar/<token>  # Confirma e-mail
GET  /auth/recuperar       # Formulário de recuperação de senha
POST /auth/recuperar       # Envia link de reset
GET  /auth/reset/<token>   # Formulário nova senha
POST /auth/reset/<token>   # Grava nova senha
```

**Bibliotecas:**
- `Flask-Login` — sessão/current_user
- `Flask-WTF` — forms com CSRF automático
- `bcrypt` (via `Flask-Bcrypt`) — hash de senha
- `itsdangerous` — tokens de confirmação de e-mail (já incluso no Flask)

### 3.2 Blueprint de veículos (`blueprints/veiculo/`)

```python
GET  /veiculos                    # Lista veículos do usuário
GET  /veiculos/novo               # Form cadastro
POST /veiculos/novo               # Cria veículo
GET  /veiculos/<id>/editar        # Form edição
POST /veiculos/<id>/editar        # Atualiza
POST /veiculos/<id>/deletar       # Soft delete (ativo=False)
POST /veiculos/<id>/selecionar    # Seta veiculo_ativo na sessão
```

### 3.3 Modelo `User`

```python
class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nome          = db.Column(db.String(100), nullable=False)
    plano         = db.Column(db.Enum('free','pro','frota'), default='free')
    status        = db.Column(db.Enum('ativo','suspenso','cancelado'), default='ativo')
    email_confirmado = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    
    veiculos      = db.relationship('Veiculo', backref='dono', lazy='dynamic')
    
    def set_password(self, senha):
        self.password_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
    
    def check_password(self, senha):
        return bcrypt.check_password_hash(self.password_hash, senha)
    
    def pode_adicionar_veiculo(self):
        limites = {'free': 1, 'pro': 3, 'frota': 15}
        return self.veiculos.filter_by(ativo=True).count() < limites[self.plano]
```

### 3.4 Decorator de plano

```python
from functools import wraps
from flask_login import current_user
from flask import abort

PLANO_ORDEM = {'free': 0, 'pro': 1, 'frota': 2}

def plano_minimo(plano):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if PLANO_ORDEM.get(current_user.plano, 0) < PLANO_ORDEM[plano]:
                abort(403)  # ou redirect para página de upgrade
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### 3.5 Filtro de segurança em todas as queries

**Padrão obrigatório após multi-tenancy:**

```python
# ANTES (inseguro — global):
abastecimentos = Abastecimento.query.order_by(Abastecimento.data.desc()).all()

# DEPOIS (seguro — filtrado por veículo do usuário):
veiculo_id = session.get('veiculo_ativo_id')
veiculo = Veiculo.query.filter_by(
    id=veiculo_id,
    user_id=current_user.id  # dupla verificação
).first_or_404()

abastecimentos = Abastecimento.query.filter_by(
    veiculo_id=veiculo.id
).order_by(Abastecimento.data.desc()).all()
```

---

## 4. Segurança — checklist de implementação

### Flask-WTF (CSRF)
```python
# extensions.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

# app.py — init
csrf.init_app(app)

# templates — cada form
<form method="POST">
    {{ form.hidden_tag() }}  {# ou: <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"> #}
    ...
</form>
```

### Cookies seguros
```python
# config.py
SESSION_COOKIE_SECURE    = True   # apenas HTTPS
SESSION_COOKIE_HTTPONLY  = True   # inacessível via JS
SESSION_COOKIE_SAMESITE  = 'Lax' # proteção extra CSRF
PERMANENT_SESSION_LIFETIME = timedelta(days=30)
REMEMBER_COOKIE_SECURE   = True
REMEMBER_COOKIE_HTTPONLY = True
```

### Rate limiting
```python
# pip install Flask-Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/day", "50/hour"])

# nas rotas sensíveis:
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
def login():
    ...
```

### Headers de segurança (via Nginx ou Flask-Talisman)
```nginx
# Adicionar no bloco location do Nginx Proxy Manager:
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Content-Security-Policy "default-src 'self'; script-src 'self' cdn.jsdelivr.net; style-src 'self' cdn.jsdelivr.net;";
```

---

## 5. Integração OBD-II (módulo experimental)

### Fluxo de dados

```
Adaptador ELM327 (Bluetooth)
         │
         │ RFCOMM / Serial BT
         ▼
App Android (OBD2 Monitor / Torque)
  ou Script Python no celular (python-obd)
         │
         │ POST HTTP → /api/v1/obd/telemetria
         │ Authorization: Bearer <token>
         ▼
Flask API endpoint (novo blueprint api_bp)
         │
         │ SQLAlchemy
         ▼
Tabela telemetria_obd (nova)
  ├── id
  ├── veiculo_id
  ├── timestamp
  ├── rpm
  ├── velocidade_kmh
  ├── temp_liquido_c
  ├── carga_motor_pct
  ├── pressao_combustivel
  └── dtc_codes (JSON)
         │
         │ Server-Sent Events (SSE) ou polling 5s
         ▼
Dashboard real-time (gauge charts via Chart.js / Plotly)
```

### Endpoint da API OBD

```python
# blueprints/api/routes.py
@api_bp.route('/v1/obd/telemetria', methods=['POST'])
@token_required  # JWT ou API key simples
def receber_telemetria():
    data = request.get_json()
    registro = TelemetriaOBD(
        veiculo_id = data['veiculo_id'],
        rpm        = data.get('rpm'),
        velocidade = data.get('velocidade'),
        temp_liquido = data.get('temp_liquido'),
        carga_motor  = data.get('carga_motor'),
        dtc_codes    = json.dumps(data.get('dtc', [])),
    )
    db.session.add(registro)
    db.session.commit()
    return jsonify({'status': 'ok'}), 201
```

### Dados OBD-II mapeados (ELM327 padrão)

| PID | Descrição | Unidade | Protocolo |
|---|---|---|---|
| 0x0C | RPM | rpm | Todos |
| 0x0D | Velocidade | km/h | Todos |
| 0x05 | Temp. líquido arrefecimento | °C | Todos |
| 0x04 | Carga calculada do motor | % | Todos |
| 0x03 | Status sistema de combustível | enum | Todos |
| 0x2F | Nível de combustível | % | CAN |
| 0x33 | Pressão barométrica | kPa | CAN |
| 0x1C | Norma OBD suportada | enum | Todos |
| 0x01 | DTCs ativos | lista | Todos |

---

## 6. APIs externas (roadmap)

| API | Finalidade | Integração |
|---|---|---|
| **Preço de combustível ANP** | Preço médio por estado/município | GET com parsing CSV semanal |
| **ViaCEP / Google Geocoding** | Autocompletar posto de abastecimento | GET no form |
| **FIPE** | Valor de mercado do veículo | GET na tela do veículo |
| **Mercado Pago / Asaas** | Cobrança de assinaturas | Webhooks POST |
| **SendGrid / Resend** | E-mail transacional (confirmação, alertas) | SDK |
| **Telegram Bot API** | Alertas de manutenção próxima | POST via Alfred |

---

## 7. Banco de dados — novas tabelas

```sql
-- Adicionadas via Alembic (não ALTER manual)

CREATE TABLE usuarios (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    email            VARCHAR(120) UNIQUE NOT NULL,
    password_hash    VARCHAR(255) NOT NULL,
    nome             VARCHAR(100) NOT NULL,
    plano            ENUM('free','pro','frota') DEFAULT 'free',
    status           ENUM('ativo','suspenso','cancelado') DEFAULT 'ativo',
    email_confirmado BOOLEAN DEFAULT FALSE,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at    DATETIME,
    INDEX idx_email (email)
);

-- Adicionar user_id aos veículos
ALTER TABLE veiculo ADD COLUMN user_id INT REFERENCES usuarios(id);
ALTER TABLE veiculo ADD COLUMN ativo BOOLEAN DEFAULT TRUE;

-- Adicionar veiculo_id às tabelas transacionais
ALTER TABLE abastecimentos ADD COLUMN veiculo_id INT REFERENCES veiculo(id);
ALTER TABLE despesas       ADD COLUMN veiculo_id INT REFERENCES veiculo(id);
ALTER TABLE manutencoes    ADD COLUMN veiculo_id INT REFERENCES veiculo(id);
ALTER TABLE corrida_uber   ADD COLUMN veiculo_id INT REFERENCES veiculo(id);
ALTER TABLE semanal_uber   ADD COLUMN user_id    INT REFERENCES usuarios(id);

-- Telemetria OBD (novo)
CREATE TABLE telemetria_obd (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    veiculo_id      INT NOT NULL REFERENCES veiculo(id),
    registrado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    rpm             SMALLINT UNSIGNED,
    velocidade_kmh  TINYINT UNSIGNED,
    temp_liquido_c  TINYINT,
    carga_motor_pct TINYINT UNSIGNED,
    nivel_comb_pct  TINYINT UNSIGNED,
    dtc_codes       JSON,
    INDEX idx_veiculo_ts (veiculo_id, registrado_em)
);

-- Planos e assinaturas
CREATE TABLE assinaturas (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES usuarios(id),
    plano            ENUM('free','pro','frota') NOT NULL,
    status           ENUM('ativo','cancelado','trial') DEFAULT 'trial',
    data_inicio      DATE NOT NULL,
    data_renovacao   DATE,
    gateway_id       VARCHAR(100),  -- ID no Mercado Pago / Asaas
    INDEX idx_user (user_id)
);
```
