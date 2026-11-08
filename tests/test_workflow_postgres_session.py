"""Narrow service connection protocol; scripted driver is not a real DB claim."""
from datetime import datetime, timezone
import sqlite3
from types import SimpleNamespace
import unittest
import uuid

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.postgres_session import PostgresSession, compile_qmark


class Driver:
    def __init__(self):
        self.autocommit = True
        self.info = SimpleNamespace(transaction_status=0)
        self.events = []
        self.failure = None
        self.rows = []
        self.columns = ['item_id', 'owner_id', 'created_at']

    def execute(self, sql, params=None):
        self.events.append((sql, params))
        if self.failure:
            raise self.failure
        if sql.startswith('BEGIN'):
            self.info.transaction_status = 2
        return SimpleNamespace(rowcount=1, description=[SimpleNamespace(name=k) for k in self.columns],
                               fetchone=lambda: self.rows[0] if self.rows else None,
                               fetchall=lambda: list(self.rows))

    def commit(self):
        self.events.append(('COMMIT', None))
        if self.failure:
            raise self.failure
        self.info.transaction_status = 0

    def rollback(self):
        self.events.append(('ROLLBACK', None))
        self.info.transaction_status = 0

    def close(self):
        self.events.append(('CLOSE', None))


class PostgresSessionTest(unittest.TestCase):
    def test_upsert_update_set_is_not_a_table_reference(self):
        raw = Driver()
        PostgresSession(raw).execute('INSERT INTO workflow_profiles(owner_id) VALUES (?) '
            'ON CONFLICT (owner_id) DO UPDATE SET owner_id=excluded.owner_id', ('owner',))
        self.assertEqual(len(raw.events), 1)

    def test_quote_comment_dollar_quote_and_percent_aware_placeholders(self):
        sql = "SELECT '?', \"?\", $$?%$$, $tag$?$tag$, 'it''s ? 10%', E'escaped\\\'? ', ? -- ?%\n/* ? /* ? */ */ FROM workflow_items WHERE owner_id=?"
        compiled, count = compile_qmark(sql)
        self.assertEqual(count, 2)
        self.assertIn("'it''s ? 10%%'", compiled)
        self.assertIn('$$?%%$$', compiled)
        self.assertEqual(compiled.count('%s'), 2)
        self.assertIn('-- ?%%', compiled)

    def test_unclosed_sql_and_multiple_statements_are_rejected(self):
        for sql in ("SELECT 'unterminated", 'SELECT "unfinished', 'SELECT /* unfinished',
                    'SELECT $$unfinished', 'SELECT * FROM workflow_items; DELETE FROM workflow_items'):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.ProgrammingError):
                compile_qmark(sql)

    def test_begin_immediate_locks_all_writers_until_commit(self):
        raw = Driver()
        session = PostgresSession(raw)
        session.execute('BEGIN IMMEDIATE')
        self.assertTrue(session.in_transaction)
        self.assertEqual(raw.events[0], ('BEGIN ISOLATION LEVEL READ COMMITTED', None))
        self.assertIn('pg_advisory_xact_lock', raw.events[1][0])
        session.execute('INSERT INTO workflow_profiles(owner_id,name) VALUES (?,?)', ('owner', 'exact'))
        session.commit()
        self.assertFalse(session.in_transaction)
        self.assertEqual(raw.events[-1], ('COMMIT', None))

    def test_idle_savepoint_owns_snapshot_transaction_and_release_commits(self):
        raw = Driver()
        session = PostgresSession(raw)
        session.execute('SAVEPOINT workflow_editorial_context')
        self.assertEqual(raw.events[0][0], 'BEGIN ISOLATION LEVEL REPEATABLE READ')
        session.execute('SAVEPOINT nested')
        session.execute('ROLLBACK TO SAVEPOINT nested')
        session.execute('RELEASE SAVEPOINT nested')
        self.assertTrue(session.in_transaction)
        session.execute('RELEASE SAVEPOINT workflow_editorial_context')
        self.assertFalse(session.in_transaction)

    def test_nested_write_savepoint_never_commits_callers_transaction(self):
        raw = Driver()
        session = PostgresSession(raw)
        session.execute('BEGIN IMMEDIATE')
        session.execute('SAVEPOINT workflow_atomic_write')
        session.execute('RELEASE SAVEPOINT workflow_atomic_write')
        self.assertTrue(session.in_transaction)
        self.assertNotIn(('COMMIT', None), raw.events)
        session.rollback()
        self.assertFalse(session.in_transaction)

    def test_rows_have_name_integer_iteration_and_dict_contract(self):
        raw = Driver()
        owner = uuid.uuid4()
        raw.rows = [('one', owner, datetime(2026, 11, 7, 1, 2, 3, 456000, tzinfo=timezone.utc))]
        session = PostgresSession(raw)
        cursor = session.execute('SELECT item_id,owner_id,created_at FROM workflow_items WHERE item_id=?', ('one',))
        row = cursor.fetchone()
        self.assertEqual(row[0], 'one')
        self.assertEqual(row['owner_id'], str(owner))
        self.assertEqual(list(row), ['one', str(owner), '2026-11-07T01:02:03.456Z'])
        self.assertEqual(dict(row)['created_at'], '2026-11-07T01:02:03.456Z')
        self.assertEqual(cursor.rowcount, 1)

    def test_scalar_unsupported_values_and_parameter_count_fail_before_driver(self):
        raw = Driver()
        session = PostgresSession(raw)
        for value in ('nul\x00secret', 'surrogate\ud800secret'):
            with self.assertRaises(WorkflowError) as error:
                session.execute('SELECT * FROM workflow_items WHERE title=?', (value,))
            self.assertEqual(error.exception.code, 'hosted_input_unsupported')
            self.assertNotIn('secret', str(error.exception))
        with self.assertRaises(sqlite3.ProgrammingError):
            session.execute('SELECT * FROM workflow_items WHERE item_id=?', ())
        self.assertEqual(raw.events, [])
        session.execute('SELECT * FROM workflow_items WHERE context_json=?', ('{"notes":"escaped\\u0000\\ud800"}',))
        self.assertEqual(len(raw.events), 1)

    def test_ddl_pragma_and_non_workflow_tables_are_rejected(self):
        raw = Driver()
        session = PostgresSession(raw)
        for sql in ('PRAGMA table_info(workflow_items)', 'CREATE TABLE workflow_fake(id text)',
                    'SELECT * FROM sqlite_master', 'SELECT * FROM arbitrary',
                    'SELECT * FROM workflow_items JOIN arbitrary ON true'):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.ProgrammingError):
                session.execute(sql)
        self.assertFalse(raw.events)

    def test_driver_errors_are_redacted_and_integrity_remains_catchable(self):
        raw = Driver()
        failure = RuntimeError('password-secret SQL payload-secret')
        failure.sqlstate = '23505'
        raw.failure = failure
        with self.assertRaises(sqlite3.IntegrityError) as error:
            PostgresSession(raw).execute('INSERT INTO workflow_items(item_id) VALUES (?)', ('one',))
        self.assertNotIn('secret', str(error.exception))
        self.assertIsNone(error.exception.__cause__)

    def test_rejects_non_idle_driver_and_close_rolls_back(self):
        raw = Driver()
        raw.autocommit = False
        with self.assertRaises(sqlite3.ProgrammingError):
            PostgresSession(raw)
        raw.autocommit = True
        session = PostgresSession(raw)
        session.execute('BEGIN IMMEDIATE')
        session.close()
        self.assertEqual(raw.events[-2:], [('ROLLBACK', None), ('CLOSE', None)])
