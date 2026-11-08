"""Opt-in exact logical backup/restore rehearsal in disposable schemas only.

This test-only algorithm is not an operator backup tool. It verifies one
coherent snapshot, all workflow tables, atomic restore/retry, and exact exports.
"""
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_postgres_workflow import LivePostgresWorkflowTest, ROOT, _HOME
from content_machine.workflow.approvals import approve_item
from content_machine.workflow.exports import export_version
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guest_transfer import copy_guest_workspace, get_transfer_receipt, preview_guest_copy
from content_machine.workflow.guests import VerifiedGuestSession, bootstrap_guest
from content_machine.workflow.history import restore_version
from content_machine.workflow.items import create_item, get_item, list_items, save_item
from content_machine.workflow.operations import begin_operation, complete_operation
from content_machine.workflow import provider_budget as budget
from content_machine.workflow.preferences import mutate_preference, preference_history
from content_machine.workflow.schemas import ApproveRequest, ItemCreate, ItemPatch, RestoreRequest
from content_machine.workflow.settings import ProfileSave, SourceCreate, create_source, get_profile, save_profile
from content_machine.workflow.versions import artifact_digest

ORDER = ('workflow_items', 'workflow_versions', 'workflow_approvals', 'workflow_profiles',
    'workflow_sources', 'workflow_preferences', 'workflow_preference_events',
    'workflow_operations', 'workflow_operation_inputs', 'workflow_reviews', 'workflow_idempotency',
    'workflow_guest_examples', 'workflow_discovery_cache', 'workflow_legacy_imports',
    'workflow_guest_transfers', 'workflow_guest_transfer_items',
    'workflow_provider_budget_days', 'workflow_provider_reservations')


class LivePostgresRecoveryTest(LivePostgresWorkflowTest):
    def qualified(self, schema, table):
        from psycopg import sql
        if not re.fullmatch(r'cm_verify_[0-9a-f]{32}', schema):
            raise ValueError('Unsafe verification schema')
        if not re.fullmatch(r'workflow_[a-z0-9_]+', table):
            raise ValueError('Unsafe verification table')
        return sql.SQL('{}.{}').format(sql.Identifier(schema), sql.Identifier(table))

    def snapshot(self, schema, mutate=None):
        from psycopg import sql
        def serial(value):
            return value.isoformat() if isinstance(value, datetime) else str(value) if isinstance(value, uuid.UUID) else value
        with self.connect_raw() as raw:
            raw.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            names = raw.execute('SELECT c.relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n '
                "ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind='r' ORDER BY c.relname", (schema,)).fetchall()
            self.assertEqual({row[0] for row in names}, set(ORDER))
            # Acquire the same snapshot before a separately committed mutation.
            if mutate is not None:
                mutate()
            tables = {}
            for name, in names:
                cursor = raw.execute(sql.SQL('SELECT * FROM {}').format(self.qualified(schema, name)))
                rows = [[serial(value) for value in row] for row in cursor.fetchall()]
                tables[name] = {'columns': [column.name for column in cursor.description],
                    'rows': sorted(rows, key=lambda row: json.dumps(row, ensure_ascii=True))}
            raw.commit()
        return {'format_version': 1, 'tables': tables}

    def restore(self, target, archive, fail_after=None):
        from psycopg import sql
        self.assertEqual(set(archive['tables']), set(ORDER))
        with self.connect_raw() as raw:
            raw.execute('BEGIN')
            try:
                for index, table in enumerate(ORDER):
                    columns = archive['tables'][table]['columns']
                    for original in archive['tables'][table]['rows']:
                        row = list(original)
                        pointers = ('parent_version_id', 'active_approval_id') if table == 'workflow_items' else (
                            ('conflict_preference_id',) if table == 'workflow_preferences' else ())
                        for column in pointers:
                            row[columns.index(column)] = None
                        query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(self.qualified(target, table),
                            sql.SQL(',').join(map(sql.Identifier, columns)),
                            sql.SQL(',').join(sql.Placeholder() for _ in columns))
                        raw.execute(query, row)
                    if fail_after == index:
                        raise RuntimeError('Injected restore interruption')
                # Restore real typed references only after their original rows
                # exist; do not alter any canonical JSON or identity values.
                for table, key, pointers in (('workflow_items', 'item_id', ('parent_version_id', 'active_approval_id')),
                        ('workflow_preferences', 'preference_id', ('conflict_preference_id',))):
                    columns = archive['tables'][table]['columns']
                    for original in archive['tables'][table]['rows']:
                        values = [original[columns.index(column)] for column in pointers]
                        query = sql.SQL('UPDATE {} SET {} WHERE {}=%s').format(self.qualified(target, table),
                            sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(column)) for column in pointers),
                            sql.Identifier(key))
                        raw.execute(query, [*values, original[columns.index(key)]])
                raw.commit()
            except BaseException:
                raw.rollback()
                raise

    def target_session(self, target):
        from content_machine.workflow.postgres_session import PostgresSession
        raw = self.connect_raw()
        raw.execute('SET search_path TO ' + target + ', pg_catalog')
        return PostgresSession(raw)

    def drop_target(self, target):
        if not re.fullmatch(r'cm_verify_[0-9a-f]{32}', target):
            raise ValueError('Unsafe cleanup schema')
        self.admin.execute('DROP SCHEMA ' + target + ' CASCADE')

    def approve(self, item_id, key):
        item = get_item(self.conn, self.a, item_id)
        return approve_item(self.conn, self.a, item_id, ApproveRequest(expected_revision=item.working_revision,
            consent=True, artifact_digest=artifact_digest(item.destination, item.format, item.artifact)),
            request_id=key).body['approval']

    def test_recovery_coherent_exact_backup_atomic_restore_and_owned_reopen(self):
        original = self.create()
        item_id = original['item_id']
        text = 'Known fixture observation.\r\nExact content survives recovery.  '
        save_item(self.conn, self.a, item_id, ItemPatch(expected_revision=1,
            artifact={'segments': [text]}, context={'notes': 'Exact evidence\n'}), request_id='draft')
        historical = self.approve(item_id, 'approval-original')
        save_item(self.conn, self.a, item_id, ItemPatch(expected_revision=2,
            artifact={'segments': ['Later draft']}), request_id='later')
        restore_version(self.conn, self.a, item_id, RestoreRequest(expected_revision=3,
            version_id=historical['version_id']), request_id='history-restore')
        current = self.approve(item_id, 'approval-current')
        self.assertIsNotNone(get_item(self.conn, self.a, item_id).parent_version_id)
        save_profile(self.conn, self.a, ProfileSave(name='Recovery fixture', role='Engineer', bio='Known facts.',
            expected_revision=0), request_id='profile')
        create_source(self.conn, self.a, SourceCreate(kind='rss', name='Fixture', url='https://example.com/feed',
            enabled=True), request_id='source')
        pref = mutate_preference(self.conn, self.a, 'create', None,
            {'text': 'Use observations from evidence.', 'consent': True}, 'preference').body['preference']
        mutate_preference(self.conn, self.a, 'stop', pref['preference_id'], {'expected_revision': 1}, 'stop')
        operation, _ = begin_operation(self.conn, self.a, item_id, 4, 'generate', 'operation')
        complete_operation(self.conn, self.a, item_id, operation['operation_id'], {'segments': ['Preserved suggestion']})
        verifier = lambda proof: VerifiedGuestSession(self.b if proof == 'guest' else self.a, is_anonymous=proof == 'guest')
        bootstrap_guest(self.conn, 'guest', verifier)
        preview = preview_guest_copy(self.conn, 'guest', 'creator', verifier)
        transfer = copy_guest_workspace(self.conn, 'guest', 'creator', verifier, consent=True,
            request_id='transfer', source_fingerprint=preview['source_fingerprint'])
        budget.reserve(self.conn, pool='recovery-fixture', day='2026-11-08', request_id='provider-attempt',
            subject_id=self.b.owner_id, provider='cloudflare_workers_ai', model='@cf/qwen/qwen3.8-27b',
            units=60, daily_limit=100, max_inflight=2)
        budget.dispatch(self.conn, 'recovery-fixture', 'provider-attempt')
        budget.settle(self.conn, 'recovery-fixture', 'provider-attempt')

        def concurrent_change():
            with closing(self.session()) as conn:
                save_item(conn, self.a, item_id, ItemPatch(expected_revision=4,
                    title='Committed after snapshot began'), request_id='after-snapshot')
        archive = self.snapshot(self.schema, mutate=concurrent_change)
        captured = archive['tables']['workflow_items']
        row = next(row for row in captured['rows'] if row[captured['columns'].index('item_id')] == item_id)
        self.assertEqual(row[captured['columns'].index('title')], original['title'])
        idem = archive['tables']['workflow_idempotency']
        self.assertFalse(any(row[idem['columns'].index('request_id')] == 'after-snapshot' for row in idem['rows']))
        with tempfile.TemporaryDirectory(prefix='cm-pg-backup-fixture-') as home:
            path = Path(home) / 'snapshot.json'
            payload = json.dumps(archive, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('utf-8')
            path.write_bytes(payload)
            checksum = hashlib.sha256(payload).hexdigest()
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), checksum)
            restored_archive = json.loads(path.read_text(encoding='utf-8'))
        target = 'cm_verify_' + uuid.uuid4().hex
        self.admin.execute('CREATE SCHEMA ' + target)
        self.addCleanup(self.drop_target, target)
        migration = (ROOT / 'supabase/migrations/202611060001_workflow_foundation.sql').read_text(encoding='utf-8')
        self.admin.execute(migration.replace('public.', target + '.'))
        with self.assertRaisesRegex(RuntimeError, 'Injected restore interruption'):
            self.restore(target, restored_archive, fail_after=3)
        empty = self.snapshot(target)
        self.assertTrue(all(not table['rows'] for table in empty['tables'].values()))
        corrupt = json.loads(json.dumps(restored_archive))
        table = corrupt['tables']['workflow_items']
        selected = next(row for row in table['rows'] if row[table['columns'].index('item_id')] == item_id)
        selected[table['columns'].index('parent_version_id')] = 'missing-version-fixture'
        with self.assertRaises(self.driver.errors.ForeignKeyViolation):
            self.restore(target, corrupt)
        self.assertTrue(all(not table['rows'] for table in self.snapshot(target)['tables'].values()))
        self.restore(target, restored_archive)
        self.assertEqual(self.snapshot(target), archive)
        with closing(self.target_session(target)) as conn:
            for approval in (historical, current):
                self.assertEqual(export_version(conn, self.a, item_id, approval['version_id']).content, text.encode('utf-8'))
            self.assertEqual(get_profile(conn, self.a)['name'], 'Recovery fixture')
            self.assertEqual(get_profile(conn, self.b)['revision'], 0)
            self.assertEqual(len(preference_history(conn, self.a, pref['preference_id'])), 2)
            self.assertEqual(get_transfer_receipt(conn, self.a, transfer['transfer_id'])['copy'], transfer)
            self.assertEqual(create_item(conn, self.a, ItemCreate(title=original['title'], destination='linkedin',
                format='linkedin_post'), request_id='create').body['item'], original)
            with self.assertRaises(WorkflowError) as denied:
                get_item(conn, self.b, item_id)
            self.assertEqual(getattr(denied.exception, 'status_code', None), 404)
            self.assertEqual(len(list_items(conn, self.b)), 2)
            self.assertFalse(budget.dispatch(conn, 'recovery-fixture', 'provider-attempt'))
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute('UPDATE workflow_versions SET artifact_json=? WHERE version_id=?',
                    ('{}', historical['version_id']))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        LivePostgresRecoveryTest('test_recovery_coherent_exact_backup_atomic_restore_and_owned_reopen')]))
    _HOME.cleanup()
    sys.exit(not result.wasSuccessful())
