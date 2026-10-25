"""Migração a002 sobre um schema legado sintético, sem banco externo."""
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


class MigracaoFase3Test(unittest.TestCase):
    def test_upgrade_idempotente_downgrade_preserva_legado(self):
        engine = sa.create_engine('sqlite://')
        meta = sa.MetaData()
        usuarios = sa.Table('usuarios', meta, sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('email', sa.String(120), nullable=False))
        veiculo = sa.Table('veiculo', meta, sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id')),
            sa.Column('marca', sa.String(50)))
        sa.Table('assinaturas', meta, sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('usuarios.id')),
            sa.Column('plano', sa.String(20)), sa.Column('status', sa.String(20)),
            sa.Column('data_inicio', sa.Date), sa.Column('data_renovacao', sa.Date),
            sa.Column('gateway_id', sa.String(100)))
        meta.create_all(engine)
        arquivo = Path(__file__).resolve().parents[1] / 'migrations/versions/a002_fase3.py'
        spec = importlib.util.spec_from_file_location('migration_fase3', arquivo)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with engine.begin() as conn:
            conn.execute(usuarios.insert().values(id=1, email='legado@example.test'))
            conn.execute(veiculo.insert().values(id=1, user_id=1, marca='Preservado'))
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                module.upgrade()
                module.upgrade()
                insp = sa.inspect(conn)
                self.assertIn('fatura', insp.get_table_names())
                self.assertIn('condutor_id', [col['name'] for col in insp.get_columns('veiculo')])
                module.downgrade()
            self.assertEqual(conn.execute(sa.select(usuarios.c.email)).scalar(), 'legado@example.test')
            self.assertEqual(conn.execute(sa.select(veiculo.c.marca)).scalar(), 'Preservado')
            self.assertNotIn('condutor', sa.inspect(conn).get_table_names())
        engine.dispose()
