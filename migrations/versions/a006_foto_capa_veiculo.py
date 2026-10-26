"""Adiciona foto_capa ao veículo.

Revision ID: a006
Revises: a005
"""
from alembic import op
import sqlalchemy as sa

revision = 'a006'
down_revision = 'a005'
branch_labels = None
depends_on = None


def upgrade():
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('veiculo')}
    if 'foto_capa' not in cols:
        op.add_column('veiculo', sa.Column('foto_capa', sa.String(200)))


def downgrade():
    try:
        op.drop_column('veiculo', 'foto_capa')
    except Exception:
        pass
