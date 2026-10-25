"""Torna vínculos de proprietário obrigatórios sem atribuição automática.

Revision ID: a003
Revises: a002
"""
from alembic import op
import sqlalchemy as sa

revision = 'a003'
down_revision = 'a002'
branch_labels = None
depends_on = None
VINCULOS = (
    ('veiculo', 'user_id', 'usuarios'),
    ('abastecimentos', 'veiculo_id', 'veiculo'),
    ('despesas', 'veiculo_id', 'veiculo'),
    ('manutencoes', 'veiculo_id', 'veiculo'),
    ('corrida_uber', 'veiculo_id', 'veiculo'),
    ('semanal_uber', 'user_id', 'usuarios'),
)


def upgrade():
    bind = op.get_bind()
    # Validar todos os vínculos antes de iniciar DDL, que pode efetuar commit no MySQL.
    problemas = []
    for tabela, campo, pai in VINCULOS:
        meta = sa.MetaData()
        filha = sa.Table(tabela, meta, autoload_with=bind)
        parent = sa.Table(pai, meta, autoload_with=bind, extend_existing=True)
        total = bind.execute(sa.select(sa.func.count()).select_from(
            filha.outerjoin(parent, filha.c[campo] == parent.c.id)).where(
                sa.or_(filha.c[campo].is_(None), parent.c.id.is_(None)))).scalar()
        if total:
            problemas.append(f'{tabela}.{campo}: {total} vínculo(s) inválido(s)')
    if problemas:
        raise RuntimeError('Migração interrompida para preservar dados. Faça backup e confirme o proprietário dos registros antes de corrigir os vínculos: ' + '; '.join(problemas))
    for tabela, campo, pai in VINCULOS:
        insp = sa.inspect(bind)
        col = next(c for c in insp.get_columns(tabela) if c['name'] == campo)
        existe_fk = any(f.get('constrained_columns') == [campo] for f in insp.get_foreign_keys(tabela))
        with op.batch_alter_table(tabela) as batch:
            if col['nullable']:
                batch.alter_column(campo, nullable=False, existing_type=sa.Integer())
            if not existe_fk:
                batch.create_foreign_key(f'fk_f123_{tabela}_{campo}', pai, [campo], ['id'])
        if not any(i.get('column_names') == [campo] for i in sa.inspect(bind).get_indexes(tabela)):
            op.create_index(f'ix_f123_{tabela}_{campo}', tabela, [campo])


def downgrade():
    for tabela, campo, _ in reversed(VINCULOS):
        insp = sa.inspect(op.get_bind())
        indice = f'ix_f123_{tabela}_{campo}'
        if any(i['name'] == indice for i in insp.get_indexes(tabela)):
            op.drop_index(indice, table_name=tabela)
        nome_fk = f'fk_f123_{tabela}_{campo}'
        with op.batch_alter_table(tabela) as batch:
            if any(f['name'] == nome_fk for f in insp.get_foreign_keys(tabela)):
                batch.drop_constraint(nome_fk, type_='foreignkey')
            batch.alter_column(campo, nullable=True, existing_type=sa.Integer())
