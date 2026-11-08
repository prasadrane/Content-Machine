"""Schema contract checks; real PostgreSQL checks are explicit and disposable.

Offline tests compare columns with an actual disposable SQLite runtime. They
cannot establish PostgreSQL transaction, RLS, or privilege behavior. Set BOTH
CM_POSTGRES_SCHEMA_TEST_DISPOSABLE=1 and CM_POSTGRES_SCHEMA_TEST_DSN to run the
real PostgreSQL class on a dedicated disposable database with Supabase roles.
"""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
import uuid

from content_machine.storage.db import connect
from content_machine.workflow.legacy_import import initialize_import_schema

SQL_PATH = Path(__file__).resolve().parents[1] / 'supabase/migrations/202611060001_workflow_foundation.sql'


def table_blocks(sql):
    return dict(re.findall(r'CREATE TABLE public\.(workflow_\w+)\s*\((.*?)\n\);', sql, re.S))


class PostgresSchemaContractTest(unittest.TestCase):
    def test_postgres_review_schema_covers_every_runtime_and_explicit_import_column(self):
        sql = SQL_PATH.read_text(encoding='utf-8')
        tables = table_blocks(sql)
        with tempfile.TemporaryDirectory(prefix='pg-schema-contract-') as root:
            with closing(connect(Path(root) / 'runtime.db')) as conn:
                initialize_import_schema(conn)
                names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'workflow_%'")]
                self.assertEqual(set(tables), set(names))
                for name in names:
                    columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{name}")')]
                    for column in columns:
                        with self.subTest(table=name, column=column):
                            self.assertRegex(tables[name], rf'\b{column}\s+(?:text|uuid|integer|bigint|boolean|timestamptz)\b')

    def test_json_payloads_use_text_not_jsonb_and_retain_history_ownership_guards(self):
        sql = SQL_PATH.read_text(encoding='utf-8')
        for table, block in table_blocks(sql).items():
            for column in re.findall(r'\b(\w+_json)\s+\w+', block):
                self.assertRegex(block, rf'\b{column}\s+text\b', (table, column))
        for name in ('workflow_versions', 'workflow_approvals', 'workflow_preference_events',
                     'workflow_operation_inputs', 'workflow_legacy_imports'):
            self.assertRegex(sql, rf'CREATE TRIGGER {name}_immutable BEFORE UPDATE OR DELETE ON public\.{name}')
        self.assertIn('FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id)', sql)

    def test_new_owned_tables_have_owner_read_policies_but_quarantine_archive_does_not(self):
        sql = SQL_PATH.read_text(encoding='utf-8')
        policy_loop = next(block.split('] LOOP', 1)[0] for block in
                           sql.split('FOREACH name IN ARRAY ARRAY[')[1:]
                           if "'workflow_items'" in block.split('] LOOP', 1)[0])
        self.assertIn("'workflow_guest_examples'", policy_loop)
        self.assertIn("'workflow_discovery_cache'", policy_loop)
        self.assertNotIn("'workflow_legacy_imports'", policy_loop)
        self.assertIn('ALTER TABLE public.workflow_legacy_imports ENABLE ROW LEVEL SECURITY', sql)
        self.assertIn('REVOKE ALL ON TABLE public.workflow_legacy_imports FROM PUBLIC, anon, authenticated', sql)


@unittest.skipUnless(os.environ.get('CM_POSTGRES_SCHEMA_TEST_DISPOSABLE') == '1'
                     and os.environ.get('CM_POSTGRES_SCHEMA_TEST_DSN'),
                     'requires explicit disposable PostgreSQL DSN and confirmation; not verified by offline checks')
class DisposablePostgresSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import psycopg
        except ImportError:
            raise unittest.SkipTest('psycopg3 is required for actual PostgreSQL verification')
        try:
            cls.conn = psycopg.connect(os.environ['CM_POSTGRES_SCHEMA_TEST_DSN'], autocommit=True)
        except Exception:
            raise RuntimeError('Disposable PostgreSQL connection failed; credentials withheld') from None
        cls.schema = 'cm_schema_check_' + uuid.uuid4().hex
        cls.conn.execute('CREATE SCHEMA ' + cls.schema)
        cls.addClassCleanup(cls.cleanup)
        cls.sql = SQL_PATH.read_text(encoding='utf-8').replace('public.', cls.schema + '.')
        # auth.uid() and anon/authenticated must exist; this harness does not
        # create shared cluster roles or impersonate a successful Supabase setup.
        cls.conn.execute(cls.sql)
        cls.conn.execute('GRANT USAGE ON SCHEMA ' + cls.schema + ' TO authenticated')

    @classmethod
    def cleanup(cls):
        try:
            cls.conn.execute('DROP SCHEMA IF EXISTS ' + cls.schema + ' CASCADE')
        finally:
            cls.conn.close()

    def test_actual_postgres_exact_escaped_json_and_quarantine_privileges(self):
        owner = uuid.uuid4()
        payload = json.dumps({'segments': ['exact\x00text\ud800\r\n']}, ensure_ascii=True)
        self.conn.execute(f'INSERT INTO {self.schema}.workflow_items '
            '(item_id,owner_id,title,destination,format,stage,working_revision,context_json,artifact_json,created_at,updated_at) '
            "VALUES ('escaped',%s,'fixture','linkedin','linkedin_post','idea',1,'{}',%s,now(),now())", (owner, payload))
        stored = self.conn.execute(f"SELECT artifact_json FROM {self.schema}.workflow_items WHERE item_id='escaped'").fetchone()[0]
        self.assertEqual(stored, payload)
        self.assertEqual(json.loads(stored)['segments'], ['exact\x00text\ud800\r\n'])
        self.assertFalse(self.conn.execute('SELECT has_table_privilege(%s,%s,%s)',
            ('authenticated', f'{self.schema}.workflow_legacy_imports', 'SELECT')).fetchone()[0])

    def test_repeat_one_shot_application_fails_atomically_without_erasing_data(self):
        with self.assertRaises(Exception):
            self.conn.execute(self.sql)
        self.conn.execute('ROLLBACK')
        tables = self.conn.execute('SELECT count(*) FROM information_schema.tables WHERE table_schema=%s', (self.schema,)).fetchone()[0]
        self.assertEqual(tables, len(table_blocks(SQL_PATH.read_text(encoding='utf-8'))))

    def test_actual_owner_rls_and_browser_write_denial(self):
        first, second = uuid.uuid4(), uuid.uuid4()
        for item_id, owner in [('rls-a', first), ('rls-b', second)]:
            self.conn.execute(f'INSERT INTO {self.schema}.workflow_items '
                '(item_id,owner_id,title,destination,format,stage,working_revision,context_json,artifact_json,created_at,updated_at) '
                "VALUES (%s,%s,'fixture','linkedin','linkedin_post','idea',1,'{}','{}',now(),now())", (item_id, owner))
        with self.conn.transaction():
            self.conn.execute('SET LOCAL ROLE authenticated')
            self.conn.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (str(first),))
            self.conn.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps({'sub': str(first)}),))
            visible = self.conn.execute(f'SELECT item_id FROM {self.schema}.workflow_items').fetchall()
            self.assertEqual(visible, [('rls-a',)])
            with self.assertRaises(Exception):
                with self.conn.transaction():
                    self.conn.execute(f"UPDATE {self.schema}.workflow_items SET title='unauthorized'")

    def test_actual_cross_owner_reference_and_immutable_version_rejection(self):
        owner = uuid.uuid4()
        self.conn.execute(f'INSERT INTO {self.schema}.workflow_items '
            '(item_id,owner_id,title,destination,format,stage,working_revision,context_json,artifact_json,created_at,updated_at) '
            "VALUES ('history',%s,'fixture','linkedin','linkedin_post','idea',1,'{}','{}',now(),now())", (owner,))
        digest = 'sha256:' + 'a' * 64
        statement = f'INSERT INTO {self.schema}.workflow_versions '
        statement += '(version_id,item_id,owner_id,revision,context_json,artifact_json,destination,format,artifact_digest,purpose,created_by,created_at) '
        statement += "VALUES (%s,'history',%s,1,'{}','{}','linkedin','linkedin_post',%s,'review',%s,now())"
        with self.assertRaises(Exception):
            self.conn.execute(statement, ('wrong-owner', uuid.uuid4(), digest, owner))
        self.conn.execute(statement, ('history-v1', owner, digest, owner))
        for action in (f"UPDATE {self.schema}.workflow_versions SET context_json='{{}}' WHERE version_id='history-v1'",
                       f"DELETE FROM {self.schema}.workflow_versions WHERE version_id='history-v1'"):
            with self.assertRaises(Exception):
                self.conn.execute(action)
