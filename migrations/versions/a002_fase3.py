"""Perfil, documentos, galeria, alertas e autenticação da Fase 3.

Revision ID: a002
Revises: a001
"""
from alembic import op
import sqlalchemy as sa

revision = 'a002'
down_revision = 'a001'
branch_labels = None
depends_on = None


def _add(table, column):
    if column.name not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}:
        op.add_column(table, column)


def _create(name, *columns):
    if not sa.inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns)


def upgrade():
    _add('usuarios', sa.Column('auth_version', sa.Integer, nullable=False, server_default='0'))
    _add('usuarios', sa.Column('google_id', sa.String(100), nullable=True))
    _add('usuarios', sa.Column('avatar_url', sa.String(300), nullable=True))
    insp = sa.inspect(op.get_bind())
    uniques = insp.get_unique_constraints('usuarios') + insp.get_indexes('usuarios')
    if not any(item.get('column_names') == ['google_id'] for item in uniques):
        op.create_index('uq_usuarios_google_id', 'usuarios', ['google_id'], unique=True)
    _create('condutor',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False, unique=True),
        sa.Column('nome', sa.String(120), nullable=False), sa.Column('cpf', sa.String(11)),
        sa.Column('data_nascimento', sa.Date), sa.Column('cnh_numero', sa.String(20)),
        sa.Column('cnh_categoria', sa.String(5)), sa.Column('cnh_validade', sa.Date),
        sa.Column('cnh_primeira_habilitacao', sa.Date))
    for col in (sa.Column('ano_fabricacao', sa.Integer), sa.Column('chassi', sa.String(17)),
                sa.Column('renavam', sa.String(11)), sa.Column('proprietario', sa.String(120)),
                sa.Column('condutor_id', sa.Integer), sa.Column('crlv_validade', sa.Date),
                sa.Column('seguro_validade', sa.Date)):
        _add('veiculo', col)
    insp = sa.inspect(op.get_bind())
    if not any(fk.get('constrained_columns') == ['condutor_id'] for fk in insp.get_foreign_keys('veiculo')):
        with op.batch_alter_table('veiculo') as batch:
            batch.create_foreign_key('fk_veiculo_condutor', 'condutor', ['condutor_id'], ['id'])
    _create('foto_veiculo', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('veiculo_id', sa.Integer, sa.ForeignKey('veiculo.id'), nullable=False, index=True),
        sa.Column('filename', sa.String(200), nullable=False), sa.Column('legenda', sa.String(200)),
        sa.Column('ordem', sa.Integer, nullable=False, server_default='0'), sa.Column('criado_em', sa.DateTime))
    _create('preferencia_alerta', sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), primary_key=True),
        sa.Column('email', sa.Boolean, nullable=False, server_default=sa.false()))
    _create('push_subscription', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False, index=True),
        sa.Column('endpoint_hash', sa.String(64), nullable=False, unique=True), sa.Column('dados', sa.JSON, nullable=False))
    _create('envio_alerta', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('chave', sa.String(160), nullable=False), sa.Column('canal', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='processando'),
        sa.Column('criado_em', sa.DateTime), sa.UniqueConstraint('user_id', 'chave', 'canal', name='uq_envio_alerta'))
    _create('webauthn_credential', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False, index=True),
        sa.Column('credential_id', sa.String(1400), nullable=False),
        sa.Column('credential_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('public_key', sa.LargeBinary, nullable=False),
        sa.Column('sign_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('device_name', sa.String(100), nullable=False), sa.Column('criado_em', sa.DateTime))
    _create('webauthn_desafio', sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id')),
        sa.Column('tipo', sa.String(20), nullable=False), sa.Column('challenge', sa.LargeBinary, nullable=False),
        sa.Column('expira_em', sa.DateTime, nullable=False), sa.Column('consumido', sa.Boolean, nullable=False, server_default=sa.false()))
    for col in (sa.Column('valor', sa.Numeric(10, 2), nullable=False, server_default='0'),
                sa.Column('plano_solicitado', sa.String(20)), sa.Column('valor_solicitado', sa.Numeric(10, 2))):
        _add('assinaturas', col)
    _create('conta_cobranca', sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), primary_key=True),
        sa.Column('customer_id', sa.String(100)))
    _create('fatura', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('assinatura_id', sa.Integer, sa.ForeignKey('assinaturas.id'), nullable=False, index=True),
        sa.Column('plano', sa.String(20), nullable=False),
        sa.Column('gateway_id', sa.String(100), nullable=False, unique=True),
        sa.Column('valor', sa.Numeric(10, 2), nullable=False), sa.Column('status', sa.String(30), nullable=False),
        sa.Column('vencimento', sa.Date, nullable=False), sa.Column('confirmacao', sa.Date), sa.Column('url', sa.String(500)))
    _create('evento_gateway', sa.Column('id', sa.String(100), primary_key=True), sa.Column('criado_em', sa.DateTime))


def downgrade():
    for table in ('evento_gateway', 'fatura', 'conta_cobranca'):
        op.drop_table(table)
    for col in ('valor_solicitado', 'plano_solicitado', 'valor'):
        op.drop_column('assinaturas', col)
    for table in ('webauthn_desafio', 'webauthn_credential', 'envio_alerta', 'push_subscription', 'preferencia_alerta', 'foto_veiculo'):
        op.drop_table(table)
    with op.batch_alter_table('veiculo') as batch:
        batch.drop_constraint('fk_veiculo_condutor', type_='foreignkey')
        for col in ('ano_fabricacao', 'chassi', 'renavam', 'proprietario', 'condutor_id', 'crlv_validade', 'seguro_validade'):
            batch.drop_column(col)
    op.drop_table('condutor')
    with op.batch_alter_table('usuarios') as batch:
        batch.drop_index('uq_usuarios_google_id')
        batch.drop_column('google_id')
        batch.drop_column('avatar_url')
        batch.drop_column('auth_version')
