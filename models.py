from datetime import datetime, date
from flask_login import UserMixin
from extensions import db, bcrypt

PLANO_LIMITES = {'free': 1, 'pro': 3, 'frota': 9999, 'superadmin': 9999}


class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id               = db.Column(db.Integer, primary_key=True)
    email            = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash    = db.Column(db.String(255), nullable=False)
    nome             = db.Column(db.String(100), nullable=False)
    plano            = db.Column(db.String(20), default='free')
    status           = db.Column(db.String(20), default='ativo')
    email_confirmado = db.Column(db.Boolean, default=False)
    ativo            = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at    = db.Column(db.DateTime)
    auth_version     = db.Column(db.Integer, nullable=False, default=0)
    google_id        = db.Column(db.String(100))
    __table_args__ = (db.Index('uq_usuarios_google_id', 'google_id', unique=True),)
    avatar_url       = db.Column(db.String(300))

    veiculos = db.relationship('Veiculo', backref='dono', lazy='dynamic',
                               foreign_keys='Veiculo.user_id')

    def set_password(self, senha):
        if self.password_hash:
            self.auth_version = (self.auth_version or 0) + 1
        self.password_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    def check_password(self, senha):
        if not self.password_hash:
            return False
        try:
            return bcrypt.check_password_hash(self.password_hash, senha)
        except (ValueError, TypeError):
            return False

    def get_id(self):
        return f'{self.id}:{self.auth_version or 0}'

    def pode_adicionar_veiculo(self, bloquear=False):
        from flask import current_app
        plano = self.plano_efetivo
        limite = PLANO_LIMITES.get(plano, 1)
        limite_configurado = current_app.config.get('FROTA_LIMITE')
        if plano == 'frota' and type(limite_configurado) is int and limite_configurado >= 0:
            limite = limite_configurado
            if limite == 0:
                return True
        query = self.veiculos.filter_by(ativo=True)
        quantidade = len(query.with_for_update().all()) if bloquear else query.count()
        return quantidade < limite

    @property
    def plano_efetivo(self):
        from services.assinatura_service import plano_efetivo
        return plano_efetivo(self)


class Veiculo(db.Model):
    __tablename__ = 'veiculo'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    ativo       = db.Column(db.Boolean, default=True)
    marca       = db.Column(db.String(50))
    modelo      = db.Column(db.String(50))
    versao      = db.Column(db.String(100))
    motor       = db.Column(db.String(100))
    ano         = db.Column(db.Integer)
    placa       = db.Column(db.String(10))
    cor         = db.Column(db.String(50))
    km_atual    = db.Column(db.Integer, default=0)
    data_compra = db.Column(db.Date)
    valor_compra = db.Column(db.Float)
    valor_atual  = db.Column(db.Float)
    ano_fabricacao = db.Column(db.Integer)
    chassi = db.Column(db.String(17))
    renavam = db.Column(db.String(11))
    proprietario = db.Column(db.String(120))
    condutor_id = db.Column(db.Integer, db.ForeignKey('condutor.id'), nullable=True)
    crlv_validade = db.Column(db.Date)
    seguro_validade = db.Column(db.Date)
    fipe_tipo = db.Column(db.String(20))
    fipe_marca_id = db.Column(db.String(20))
    fipe_modelo_id = db.Column(db.String(20))
    fipe_ano_id = db.Column(db.String(20))
    fipe_codigo = db.Column(db.String(12))
    fipe_referencia = db.Column(db.String(60))
    fipe_valor = db.Column(db.Numeric(12, 2))
    fipe_consultado_em = db.Column(db.DateTime)

    fotos = db.relationship('FotoVeiculo', order_by='FotoVeiculo.ordem', lazy='select')

    abastecimentos = db.relationship('Abastecimento', backref='veiculo', lazy='dynamic')
    despesas       = db.relationship('Despesa', backref='veiculo', lazy='dynamic')
    manutencoes    = db.relationship('Manutencao', backref='veiculo', lazy='dynamic')
    corridas       = db.relationship('CorridaUber', backref='veiculo', lazy='dynamic')

    def to_dict(self):
        return {
            'marca': self.marca, 'modelo': self.modelo, 'versao': self.versao,
            'motor': self.motor, 'ano': self.ano, 'placa': self.placa,
            'cor': self.cor, 'km_atual': self.km_atual,
            'data_compra': self.data_compra.strftime('%d/%m/%Y') if self.data_compra else '—',
            'valor_compra': self.valor_compra, 'valor_atual': self.valor_atual,
        }


class Abastecimento(db.Model):
    __tablename__ = 'abastecimentos'
    id                  = db.Column(db.Integer, primary_key=True)
    veiculo_id          = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False, index=True)
    data                = db.Column(db.Date, default=datetime.utcnow)
    quilometragem       = db.Column(db.Integer, nullable=False)
    litros_abastecidos  = db.Column(db.Float, nullable=False)
    valor_total         = db.Column(db.Float, nullable=False)
    preco_combustivel   = db.Column(db.Float, nullable=False)
    posto               = db.Column(db.String(250), nullable=False)
    tipo_combustivel    = db.Column(db.String(30))
    observacao          = db.Column(db.String(200))
    latitude            = db.Column(db.Float)
    longitude           = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id, 'quilometragem': self.quilometragem,
            'litros_abastecidos': self.litros_abastecidos,
            'valor_total': self.valor_total,
            'data': self.data.strftime('%Y-%m-%d'),
            'preco_combustivel': self.preco_combustivel,
            'posto': self.posto,
            'tipo_combustivel': self.tipo_combustivel or '',
            'observacao': self.observacao or '',
            'latitude': self.latitude,
            'longitude': self.longitude,
        }


class Categoria(db.Model):
    __tablename__ = 'categorias'
    id    = db.Column(db.Integer, primary_key=True)
    nome  = db.Column(db.String(50), nullable=False, unique=True)
    icone = db.Column(db.String(10), default='📦')
    tipo  = db.Column(db.String(20), default='variavel')  # fixo | variavel

    def __repr__(self):
        return f'<Categoria {self.nome}>'


class Despesa(db.Model):
    __tablename__ = 'despesas'
    id              = db.Column(db.Integer, primary_key=True)
    veiculo_id      = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=True, index=True)
    data            = db.Column(db.Date, default=datetime.utcnow)
    descricao       = db.Column(db.String(100), nullable=False)
    valor           = db.Column(db.Float, nullable=False)
    quilometragem   = db.Column(db.Integer)
    forma_pagamento = db.Column(db.String(50))
    observacoes     = db.Column(db.Text)
    latitude        = db.Column(db.Float)
    longitude       = db.Column(db.Float)
    categoria_id    = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    categoria       = db.relationship('Categoria', backref='despesas')

    def to_dict(self):
        return {
            'id': self.id, 'data': self.data.strftime('%d/%m/%Y'),
            'descricao': self.descricao, 'valor': self.valor,
            'quilometragem': self.quilometragem,
            'forma_pagamento': self.forma_pagamento or '—',
            'observacoes': self.observacoes or '',
            'categoria_id': self.categoria_id,
            'categoria_nome': self.categoria.nome,
            'categoria_icone': self.categoria.icone,
        }


class Manutencao(db.Model):
    __tablename__ = 'manutencoes'
    id             = db.Column(db.Integer, primary_key=True)
    veiculo_id     = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=True, index=True)
    tipo           = db.Column(db.String(50))
    descricao      = db.Column(db.String(200))
    data_realizada = db.Column(db.Date)
    km_realizada   = db.Column(db.Integer)
    data_prevista  = db.Column(db.Date)
    km_previsto    = db.Column(db.Integer)
    custo          = db.Column(db.Float, default=0)
    status         = db.Column(db.String(20), default='pendente')
    observacoes    = db.Column(db.Text)

    @property
    def status_calculado(self):
        hoje = date.today()
        km_atual = self.veiculo.km_atual if self.veiculo else 0
        if self.status == 'realizada':
            return 'realizada'
        atrasada = (self.data_prevista and self.data_prevista < hoje) or \
                   (self.km_previsto and km_atual > self.km_previsto)
        if atrasada:
            return 'atrasada'
        proxima_data = self.data_prevista and (self.data_prevista - hoje).days <= 30
        proxima_km = self.km_previsto and (self.km_previsto - km_atual) <= 800
        if proxima_data or proxima_km:
            return 'proxima'
        return 'ok'

    def to_dict(self):
        return {
            'id': self.id, 'tipo': self.tipo, 'descricao': self.descricao,
            'data_realizada': self.data_realizada.strftime('%d/%m/%Y') if self.data_realizada else None,
            'km_realizada': self.km_realizada,
            'data_prevista': self.data_prevista.strftime('%d/%m/%Y') if self.data_prevista else None,
            'km_previsto': self.km_previsto,
            'custo': self.custo, 'status': self.status_calculado,
            'observacoes': self.observacoes,
        }


class CorridaUber(db.Model):
    __tablename__ = 'corrida_uber'
    id                 = db.Column(db.Integer, primary_key=True)
    veiculo_id         = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=True, index=True)
    data_corrida       = db.Column(db.Date, nullable=False)
    hora_corrida       = db.Column(db.Time, nullable=False)
    tipo_corrida       = db.Column(db.String(50))
    duracao            = db.Column(db.Time)
    distancia_km       = db.Column(db.Numeric(5, 2))
    local_partida      = db.Column(db.String(255))
    local_destino      = db.Column(db.String(255))
    ganho_bruto        = db.Column(db.Numeric(10, 2), nullable=False)
    taxa_servico       = db.Column(db.Numeric(5, 2))
    ganho_liquido      = db.Column(db.Numeric(10, 2))
    pontos_ganhos      = db.Column(db.Integer)
    total_pago_usuario = db.Column(db.Numeric(10, 2))
    promocao_aplicada  = db.Column(db.Numeric(10, 2))


class SemanalUber(db.Model):
    __tablename__ = 'semanal_uber'
    id                    = db.Column(db.Integer, primary_key=True)
    user_id               = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    data_inicio           = db.Column(db.DateTime, nullable=False)
    data_termino          = db.Column(db.DateTime, nullable=False)
    nome_motorista        = db.Column(db.String(255))
    contato               = db.Column(db.String(255))
    saldo_inicial         = db.Column(db.Numeric(10, 2))
    ganhos                = db.Column(db.Numeric(10, 2))
    despesas_reembolsos   = db.Column(db.Numeric(10, 2))
    transferencias        = db.Column(db.Numeric(10, 2))
    saldo_final           = db.Column(db.Numeric(10, 2))
    detalhamento_ganhos   = db.Column(db.Text)
    resumo_taxas          = db.Column(db.Text)
    transacoes_detalhadas = db.Column(db.Text)
    nome_arquivo          = db.Column(db.String(255))


class Condutor(db.Model):
    __tablename__ = 'condutor'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(11))
    data_nascimento = db.Column(db.Date)
    cnh_numero = db.Column(db.String(20))
    cnh_categoria = db.Column(db.String(5))
    cnh_validade = db.Column(db.Date)
    cnh_primeira_habilitacao = db.Column(db.Date)


class FotoVeiculo(db.Model):
    __tablename__ = 'foto_veiculo'
    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False, index=True)
    filename = db.Column(db.String(200), nullable=False)
    legenda = db.Column(db.String(200))
    ordem = db.Column(db.Integer, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class PreferenciaAlerta(db.Model):
    __tablename__ = 'preferencia_alerta'
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    email = db.Column(db.Boolean, nullable=False, default=False)


class PushSubscription(db.Model):
    __tablename__ = 'push_subscription'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    endpoint_hash = db.Column(db.String(64), unique=True, nullable=False)
    dados = db.Column(db.JSON, nullable=False)


class EnvioAlerta(db.Model):
    __tablename__ = 'envio_alerta'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    chave = db.Column(db.String(160), nullable=False)
    canal = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processando')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'chave', 'canal', name='uq_envio_alerta'),)


class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credential'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    credential_id = db.Column(db.String(1400), nullable=False)
    credential_hash = db.Column(db.String(64), nullable=False, unique=True)
    public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, nullable=False, default=0)
    device_name = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class WebAuthnDesafio(db.Model):
    __tablename__ = 'webauthn_desafio'
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo = db.Column(db.String(20), nullable=False)
    challenge = db.Column(db.LargeBinary, nullable=False)
    expira_em = db.Column(db.DateTime, nullable=False)
    consumido = db.Column(db.Boolean, nullable=False, default=False)


class Assinatura(db.Model):
    __tablename__ = 'assinaturas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    plano = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='trial')
    data_inicio = db.Column(db.Date, nullable=False)
    data_renovacao = db.Column(db.Date)
    gateway_id = db.Column(db.String(100))
    valor = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    plano_solicitado = db.Column(db.String(20))
    valor_solicitado = db.Column(db.Numeric(10, 2))


class ContaCobranca(db.Model):
    __tablename__ = 'conta_cobranca'
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    customer_id = db.Column(db.String(100))


class Fatura(db.Model):
    __tablename__ = 'fatura'
    id = db.Column(db.Integer, primary_key=True)
    assinatura_id = db.Column(db.Integer, db.ForeignKey('assinaturas.id'), nullable=False, index=True)
    plano = db.Column(db.String(20), nullable=False)
    gateway_id = db.Column(db.String(100), nullable=False, unique=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    confirmacao = db.Column(db.Date)
    url = db.Column(db.String(500))


class EventoGateway(db.Model):
    __tablename__ = 'evento_gateway'
    id = db.Column(db.String(100), primary_key=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class MetaGasto(db.Model):
    __tablename__ = 'metas_gasto'
    id           = db.Column(db.Integer, primary_key=True)
    veiculo_id   = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False, index=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    tipo         = db.Column(db.String(20), default='categoria')  # total | combustivel | categoria
    valor_limite = db.Column(db.Float, nullable=False)

    categoria = db.relationship('Categoria', backref='metas')
