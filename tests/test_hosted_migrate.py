"""Explicit hosted migration CLI: no implicit startup, credentials or overwrite."""
from contextlib import redirect_stdout
import os
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from tools import hosted_migrate as migration


class Raw:
    autocommit = True
    info = SimpleNamespace(transaction_status=0)

    def __init__(self, inventories, ledger=(), fail=None):
        self.inventories = iter(inventories)
        self.ledger = ledger
        self.fail = fail
        self.statements = []
        self.committed = False
        self.rolled_back = False

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if self.fail and self.fail in sql:
            raise RuntimeError('secret-dsn-and-password')
        if sql == migration.INVENTORY:
            result = next(self.inventories)
        elif sql.startswith('SELECT migration_id'):
            result = self.ledger
        else:
            result = []
        return SimpleNamespace(fetchall=lambda: result)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class HostedMigrateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backup = Path(self.tmp.name) / 'new-private-inventory.json'
        self.sql = migration.SQL_PATH.read_text(encoding='utf-8')
        self.digest = migration.digest(self.sql)
        self.expected = migration.expected_columns(self.sql)
        self.installed = [('relation', name, 'r') for name in self.expected]
        self.installed += [('column', name + '.' + column, kind)
            for name, columns in self.expected.items() for column, kind in columns.items()]
        self.installed += [('relation', migration.LEDGER, 'r')]
        self.installed.sort()

    def test_check_empty_is_read_only_without_backup_or_ddl(self):
        raw = Raw([[]])
        result = migration.run(raw, apply=False)
        self.assertEqual(result['status'], 'empty')
        self.assertFalse(self.backup.exists())
        self.assertFalse(any('CREATE TABLE' in sql for sql, _ in raw.statements))
        self.assertIn('READ ONLY', raw.statements[0][0])

    def test_apply_empty_backs_up_before_ddl_and_commits_schema_with_ledger(self):
        raw = Raw([[], self.installed])
        original = raw.execute
        def execute(sql, params=()):
            if 'CREATE TABLE' in sql:
                self.assertTrue(self.backup.exists())
                self.assertEqual(json.loads(self.backup.read_text())['inventory'], [])
            return original(sql, params)
        raw.execute = execute
        result = migration.run(raw, apply=True, backup=self.backup)
        self.assertEqual(result['status'], 'applied')
        self.assertTrue(raw.committed)
        self.assertFalse(raw.rolled_back)
        self.assertEqual(len([sql for sql, _ in raw.statements if sql.startswith('BEGIN')]), 1)
        ddl = next(sql for sql, _ in raw.statements if 'CREATE TABLE public.workflow_items' in sql)
        self.assertFalse(ddl.lstrip().startswith('BEGIN;'))
        self.assertFalse(ddl.rstrip().endswith('COMMIT;'))
        self.assertTrue(any(sql.startswith('INSERT INTO public.' + migration.LEDGER) for sql, _ in raw.statements))

    def test_existing_schema_unrelated_relation_and_existing_backup_refused(self):
        for inventory in ([('relation', 'workflow_items', 'r')], [('relation', 'unrelated', 'v')]):
            raw = Raw([inventory])
            with self.assertRaises(migration.MigrationError) as error:
                migration.run(raw, apply=True, backup=self.backup)
            self.assertEqual(error.exception.code, 'schema_not_empty')
            self.assertFalse(self.backup.exists())
        self.backup.write_text('preserve')
        raw = Raw([[]])
        with self.assertRaises(migration.MigrationError):
            migration.run(raw, apply=True, backup=self.backup)
        self.assertEqual(self.backup.read_text(), 'preserve')
        self.assertFalse(any('CREATE TABLE' in sql for sql, _ in raw.statements))

    def test_exact_replay_is_noop_but_hash_inventory_columns_and_ledger_drift_refuse(self):
        ledger = [(migration.MIGRATION_ID, self.digest, json.dumps(self.installed))]
        raw = Raw([self.installed], ledger)
        self.assertEqual(migration.run(raw, apply=True, backup=self.backup)['status'], 'already_applied')
        self.assertFalse(self.backup.exists())
        for inventory, records in ((self.installed, [(migration.MIGRATION_ID, 'wrong', json.dumps(self.installed))]),
                (self.installed + [('trigger', 'unexpected', 'definition')], ledger),
                ([row for row in self.installed if row[:2] != ('column', 'workflow_items.title')], ledger),
                (self.installed, ledger + ledger), (self.installed, [])):
            with self.subTest(records=len(records)), self.assertRaises(migration.MigrationError):
                migration.run(Raw([inventory], records), apply=False)

    def test_failure_rolls_back_and_retains_preflight_backup_without_secret_error(self):
        raw = Raw([[]], fail='CREATE TABLE public.workflow_items')
        with self.assertRaises(migration.MigrationError) as error:
            migration.run(raw, apply=True, backup=self.backup)
        self.assertEqual(error.exception.code, 'migration_failed')
        self.assertNotIn('secret', str(error.exception))
        self.assertTrue(raw.rolled_back)
        self.assertFalse(raw.committed)
        self.assertTrue(self.backup.exists())

    def test_invalid_schema_transaction_envelope_and_untrusted_backup_paths_refused(self):
        for schema in ('other', 'public; DROP SCHEMA public', 'cm_verify_wrong'):
            raw = Raw([[]])
            with self.assertRaises(migration.MigrationError):
                migration.run(raw, apply=True, backup=self.backup, schema=schema)
            self.assertEqual(raw.statements, [])
        for value in ('BEGIN; SELECT 1;', 'SELECT 1; COMMIT;', 'BEGIN; SELECT 1; COMMIT; SELECT 2;'):
            with self.assertRaises(migration.MigrationError):
                migration.body(value)
        with self.assertRaises(migration.MigrationError):
            migration.run(Raw([[]]), apply=True, backup=Path('relative.json'))

    def test_cli_configuration_and_driver_failures_are_redacted_no_dotenv_read(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(migration, 'parse_hosted_configuration',
                side_effect=RuntimeError('secret-password')):
            code = migration.main(['check'])
        self.assertEqual(code, 1)
        self.assertNotIn('secret', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['code'], 'migration_failed')


@unittest.skipUnless(os.getenv('CONTENT_MACHINE_LIVE_POSTGRES') == '1', 'explicit live PostgreSQL opt-in required')
class LiveHostedMigrateTest(unittest.TestCase):
    def setUp(self):
        import psycopg
        from dotenv import dotenv_values
        values = dict(dotenv_values(migration.ROOT / '.env'))
        if os.getenv('CONTENT_MACHINE_DATABASE_URL'):
            values['CONTENT_MACHINE_DATABASE_URL'] = os.environ['CONTENT_MACHINE_DATABASE_URL']
        config = migration.parse_hosted_configuration(values)
        try:
            self.conn = psycopg.connect(config.database_url, autocommit=True, connect_timeout=10)
        except Exception:
            raise RuntimeError('Verification connection unavailable; details redacted.') from None
        self.addCleanup(self.conn.close)
        self.schema = 'cm_verify_' + uuid.uuid4().hex
        self.conn.execute('CREATE SCHEMA ' + self.schema)
        self.addCleanup(lambda: self.conn.execute('DROP SCHEMA ' + self.schema + ' CASCADE'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backup = Path(self.tmp.name) / 'new-private-inventory.json'

    def test_actual_generated_schema_apply_replay_rls_and_drift_refusal(self):
        self.assertEqual(migration.run(self.conn, schema=self.schema)['status'], 'empty')
        self.assertEqual(migration.run(self.conn, apply=True, backup=self.backup, schema=self.schema)['status'], 'applied')
        self.assertEqual(migration.run(self.conn, apply=True, backup=self.backup, schema=self.schema)['status'], 'already_applied')
        inventory = json.loads(self.backup.read_text())
        self.assertEqual(inventory['inventory'], [])
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM ' + self.schema + '.' + migration.LEDGER).fetchone()[0], 1)
        self.assertFalse(self.conn.execute('SELECT has_table_privilege(%s,%s,%s)',
            ('authenticated', self.schema + '.' + migration.LEDGER, 'SELECT')).fetchone()[0])
        self.conn.execute('ALTER TABLE ' + self.schema + '.workflow_items ALTER COLUMN title DROP NOT NULL')
        with self.assertRaises(migration.MigrationError) as error:
            migration.run(self.conn, schema=self.schema)
        self.assertEqual(error.exception.code, 'schema_drift')

    def test_actual_ddl_failure_rolls_back_ledger_and_all_foundation_objects(self):
        changed = Path(self.tmp.name) / 'broken-migration.sql'
        changed.write_text(migration.SQL_PATH.read_text().replace('CREATE TABLE public.workflow_versions',
            'SELECT unknown_column_for_rollback;\nCREATE TABLE public.workflow_versions'), encoding='utf-8')
        with patch.object(migration, 'SQL_PATH', changed):
            with self.assertRaises(migration.MigrationError) as error:
                migration.run(self.conn, apply=True, backup=self.backup, schema=self.schema)
        self.assertEqual(error.exception.code, 'migration_failed')
        self.assertTrue(self.backup.exists())
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n '
            'ON n.oid=c.relnamespace WHERE n.nspname=%s', (self.schema,)).fetchone()[0], 0)
        self.assertEqual(migration.run(self.conn, schema=self.schema)['status'], 'empty')


if __name__ == '__main__':
    unittest.main()
