from datetime import datetime, date
from extensions import db


class Veiculo(db.Model):
    __tablename__ = 'veiculo'
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    versao = db.Column(db.String(100))
    motor = db.Column(db.String(100))
    ano = db.Column(db.Integer)
    placa = db.Column(db.String(10))
    cor = db.Column(db.String(50))
    km_atual = db.Column(db.Integer, default=0)
    data_compra = db.Column(db.Date)
    valor_compra = db.Column(db.Float)
    valor_atual = db.Column(db.Float)

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
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=datetime.utcnow)
    quilometragem = db.Column(db.Integer, nullable=False)
    litros_abastecidos = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    preco_combustivel = db.Column(db.Float, nullable=False)
    posto = db.Column(db.String(250), nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'quilometragem': self.quilometragem,
            'litros_abastecidos': self.litros_abastecidos,
            'valor_total': self.valor_total,
            'data': self.data.strftime('%Y-%m-%d'),
            'preco_combustivel': self.preco_combustivel,
            'posto': self.posto,
        }


class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    icone = db.Column(db.String(10), default='📦')
    tipo = db.Column(db.String(20), default='variavel')  # fixo | variavel

    def __repr__(self):
        return f'<Categoria {self.nome}>'


class Despesa(db.Model):
    __tablename__ = 'despesas'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=datetime.utcnow)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    quilometragem = db.Column(db.Integer)
    forma_pagamento = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    categoria = db.relationship('Categoria', backref='despesas')

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
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))
    descricao = db.Column(db.String(200))
    data_realizada = db.Column(db.Date)
    km_realizada = db.Column(db.Integer)
    data_prevista = db.Column(db.Date)
    km_previsto = db.Column(db.Integer)
    custo = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pendente')
    observacoes = db.Column(db.Text)

    @property
    def status_calculado(self):
        hoje = date.today()
        veiculo = Veiculo.query.first()
        km_atual = veiculo.km_atual if veiculo else 0
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
    id = db.Column(db.Integer, primary_key=True)
    data_corrida = db.Column(db.Date, nullable=False)
    hora_corrida = db.Column(db.Time, nullable=False)
    tipo_corrida = db.Column(db.String(50))
    duracao = db.Column(db.Time)
    distancia_km = db.Column(db.Numeric(5, 2))
    local_partida = db.Column(db.String(255))
    local_destino = db.Column(db.String(255))
    ganho_bruto = db.Column(db.Numeric(10, 2), nullable=False)
    taxa_servico = db.Column(db.Numeric(5, 2))
    ganho_liquido = db.Column(db.Numeric(10, 2))
    pontos_ganhos = db.Column(db.Integer)
    total_pago_usuario = db.Column(db.Numeric(10, 2))
    promocao_aplicada = db.Column(db.Numeric(10, 2))


class SemanalUber(db.Model):
    __tablename__ = 'semanal_uber'
    id = db.Column(db.Integer, primary_key=True)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_termino = db.Column(db.DateTime, nullable=False)
    nome_motorista = db.Column(db.String(255))
    contato = db.Column(db.String(255))
    saldo_inicial = db.Column(db.Numeric(10, 2))
    ganhos = db.Column(db.Numeric(10, 2))
    despesas_reembolsos = db.Column(db.Numeric(10, 2))
    transferencias = db.Column(db.Numeric(10, 2))
    saldo_final = db.Column(db.Numeric(10, 2))
    detalhamento_ganhos = db.Column(db.Text)
    resumo_taxas = db.Column(db.Text)
    transacoes_detalhadas = db.Column(db.Text)
    nome_arquivo = db.Column(db.String(255))
