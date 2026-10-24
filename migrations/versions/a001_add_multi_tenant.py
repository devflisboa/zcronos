"""Adiciona suporte multi-tenant: plano/status em usuarios, user_id em veiculo,
veiculo_id nas tabelas transacionais, tabelas telemetria_obd e assinaturas.

Revision ID: a001
Revises:
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c['name'] for c in sa.inspect(bind).get_columns(table)}


def _idx_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    return index in {i['name'] for i in sa.inspect(bind).get_indexes(table)}


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    # ── 1. usuarios — adicionar plano / status / email_confirmado ───────────
    if not _col_exists('usuarios', 'plano'):
        op.add_column('usuarios', sa.Column('plano', sa.String(20), nullable=True,
                                             server_default='free'))
    if not _col_exists('usuarios', 'status'):
        op.add_column('usuarios', sa.Column('status', sa.String(20), nullable=True,
                                             server_default='ativo'))
    if not _col_exists('usuarios', 'email_confirmado'):
        op.add_column('usuarios', sa.Column('email_confirmado', sa.Boolean,
                                             nullable=True, server_default=sa.text('TRUE')))

    # Proprietário original vira plano frota
    op.execute(
        "UPDATE usuarios SET plano='frota', status='ativo', email_confirmado=TRUE "
        "WHERE plano IS NULL OR plano=''"
    )

    # ── 2. veiculo — user_id e ativo ────────────────────────────────────────
    if not _col_exists('veiculo', 'user_id'):
        op.add_column('veiculo', sa.Column('user_id', sa.Integer, nullable=True))
    if not _col_exists('veiculo', 'ativo'):
        op.add_column('veiculo', sa.Column('ativo', sa.Boolean, nullable=True,
                                           server_default=sa.text('TRUE')))

    op.execute(
        "UPDATE veiculo SET user_id = (SELECT id FROM usuarios ORDER BY id LIMIT 1), "
        "ativo = TRUE WHERE user_id IS NULL"
    )

    try:
        op.create_foreign_key('fk_veiculo_user', 'veiculo', 'usuarios',
                              ['user_id'], ['id'])
    except Exception:
        pass

    if not _idx_exists('veiculo', 'idx_veiculo_user'):
        op.create_index('idx_veiculo_user', 'veiculo', ['user_id'])

    # ── 3. tabelas transacionais — veiculo_id ───────────────────────────────
    for tabela in ('abastecimentos', 'despesas', 'manutencoes', 'corrida_uber'):
        if not _table_exists(tabela):
            continue
        if not _col_exists(tabela, 'veiculo_id'):
            op.add_column(tabela, sa.Column('veiculo_id', sa.Integer, nullable=True))
            op.execute(
                f"UPDATE {tabela} SET veiculo_id = (SELECT id FROM veiculo ORDER BY id LIMIT 1) "
                f"WHERE veiculo_id IS NULL"
            )
            try:
                op.create_foreign_key(f'fk_{tabela}_veiculo', tabela, 'veiculo',
                                      ['veiculo_id'], ['id'])
            except Exception:
                pass
            idx = f'idx_{tabela}_veiculo'
            if not _idx_exists(tabela, idx):
                op.create_index(idx, tabela, ['veiculo_id'])

    # ── 4. semanal_uber — user_id ────────────────────────────────────────────
    if _table_exists('semanal_uber') and not _col_exists('semanal_uber', 'user_id'):
        op.add_column('semanal_uber', sa.Column('user_id', sa.Integer, nullable=True))
        op.execute(
            "UPDATE semanal_uber SET user_id = (SELECT id FROM usuarios ORDER BY id LIMIT 1) "
            "WHERE user_id IS NULL"
        )
        try:
            op.create_foreign_key('fk_semanal_uber_user', 'semanal_uber', 'usuarios',
                                  ['user_id'], ['id'])
        except Exception:
            pass

    # ── 5. telemetria_obd ────────────────────────────────────────────────────
    if not _table_exists('telemetria_obd'):
        op.create_table(
            'telemetria_obd',
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
        op.create_index('idx_obd_veiculo_ts', 'telemetria_obd',
                        ['veiculo_id', 'registrado_em'])

    # ── 6. assinaturas ───────────────────────────────────────────────────────
    if not _table_exists('assinaturas'):
        op.create_table(
            'assinaturas',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id'), nullable=False),
            sa.Column('plano', sa.String(20), nullable=False),
            sa.Column('status', sa.String(20), server_default='trial'),
            sa.Column('data_inicio', sa.Date, nullable=False),
            sa.Column('data_renovacao', sa.Date),
            sa.Column('gateway_id', sa.String(100)),
        )
        op.create_index('idx_assinaturas_user', 'assinaturas', ['user_id'])


def downgrade() -> None:
    for tabela in ('abastecimentos', 'despesas', 'manutencoes', 'corrida_uber'):
        for idx in (f'idx_{tabela}_veiculo',):
            try:
                op.drop_index(idx, table_name=tabela)
            except Exception:
                pass
        try:
            op.drop_constraint(f'fk_{tabela}_veiculo', tabela, type_='foreignkey')
        except Exception:
            pass
        try:
            op.drop_column(tabela, 'veiculo_id')
        except Exception:
            pass

    for item in (
        ('idx_veiculo_user', 'veiculo'),
    ):
        try:
            op.drop_index(item[0], table_name=item[1])
        except Exception:
            pass
    try:
        op.drop_constraint('fk_veiculo_user', 'veiculo', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('veiculo', 'user_id')
        op.drop_column('veiculo', 'ativo')
    except Exception:
        pass

    try:
        op.drop_constraint('fk_semanal_uber_user', 'semanal_uber', type_='foreignkey')
        op.drop_column('semanal_uber', 'user_id')
    except Exception:
        pass

    for col in ('plano', 'status', 'email_confirmado'):
        try:
            op.drop_column('usuarios', col)
        except Exception:
            pass

    try:
        op.drop_table('assinaturas')
    except Exception:
        pass
    try:
        op.drop_table('telemetria_obd')
    except Exception:
        pass
