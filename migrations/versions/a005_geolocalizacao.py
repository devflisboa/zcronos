"""Adiciona geolocalização e campos extras em abastecimento e despesa.

Revision ID: a005
Revises: a004
"""
from alembic import op
import sqlalchemy as sa

revision = 'a005'
down_revision = 'a004'
branch_labels = None
depends_on = None


def upgrade():
    cols_abast = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('abastecimentos')}
    novos_abast = [
        sa.Column('tipo_combustivel', sa.String(30)),
        sa.Column('observacao', sa.String(200)),
        sa.Column('latitude', sa.Float),
        sa.Column('longitude', sa.Float),
    ]
    for col in novos_abast:
        if col.name not in cols_abast:
            op.add_column('abastecimentos', col)

    cols_desp = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('despesas')}
    novos_desp = [
        sa.Column('latitude', sa.Float),
        sa.Column('longitude', sa.Float),
    ]
    for col in novos_desp:
        if col.name not in cols_desp:
            op.add_column('despesas', col)


def downgrade():
    for col in ('tipo_combustivel', 'observacao', 'latitude', 'longitude'):
        try:
            op.drop_column('abastecimentos', col)
        except Exception:
            pass
    for col in ('latitude', 'longitude'):
        try:
            op.drop_column('despesas', col)
        except Exception:
            pass
