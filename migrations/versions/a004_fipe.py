"""Identificação e última referência FIPE confirmada pelo proprietário.

Revision ID: a004
Revises: a003
"""
from alembic import op
import sqlalchemy as sa

revision = 'a004'
down_revision = 'a003'
branch_labels = None
depends_on = None


def upgrade():
    existentes = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('veiculo')}
    for coluna in (
        sa.Column('fipe_tipo', sa.String(20)),
        sa.Column('fipe_marca_id', sa.String(20)),
        sa.Column('fipe_modelo_id', sa.String(20)),
        sa.Column('fipe_ano_id', sa.String(20)),
        sa.Column('fipe_codigo', sa.String(12)),
        sa.Column('fipe_referencia', sa.String(60)),
        sa.Column('fipe_valor', sa.Numeric(12, 2)),
        sa.Column('fipe_consultado_em', sa.DateTime),
    ):
        if coluna.name not in existentes:
            op.add_column('veiculo', coluna)


def downgrade():
    with op.batch_alter_table('veiculo') as batch:
        for nome in ('fipe_consultado_em', 'fipe_valor', 'fipe_referencia', 'fipe_codigo',
                     'fipe_ano_id', 'fipe_modelo_id', 'fipe_marca_id', 'fipe_tipo'):
            batch.drop_column(nome)
