"""Opt-in actual PostgreSQL workflow acceptance in one disposable schema.

Run from the worker: CONTENT_MACHINE_LIVE_POSTGRES=1 python
tests/live_postgres_workflow.py. Credentials come from the backend .env or an
explicit CONTENT_MACHINE_DATABASE_URL override and are never printed.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
import uuid
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Must precede all storage imports; never open the operator's local workspace.
_HOME = tempfile.TemporaryDirectory(prefix='cm-live-pg-local-')
os.environ['CONTENT_MACHINE_HOME'] = _HOME.name

from content_machine.workflow.approvals import approve_item
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.exports import export_version
from content_machine.workflow.guests import VerifiedGuestSession, bootstrap_guest
from content_machine.workflow.guest_transfer import copy_guest_workspace, get_transfer_receipt, preview_guest_copy
from content_machine.workflow.items import create_item, get_item, list_items, save_item
from content_machine.workflow.operations import begin_operation, complete_operation
from content_machine.workflow.postgres_session import PostgresSession
from content_machine.workflow.preferences import list_preferences, mutate_preference, preference_history
from content_machine.workflow.schemas import ApproveRequest, ItemCreate, ItemPatch, Principal
from content_machine.workflow.settings import (ProfileSave, SourceCreate, create_source,
    get_profile, list_sources, save_profile)
from content_machine.workflow.versions import artifact_digest


@unittest.skipUnless(os.getenv('CONTENT_MACHINE_LIVE_POSTGRES') == '1', 'explicit live opt-in required')
class LivePostgresWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from dotenv import dotenv_values
        from content_machine.workflow.hosted_configuration import parse_hosted_configuration
        values = dict(dotenv_values(ROOT / '.env'))
        if os.getenv('CONTENT_MACHINE_DATABASE_URL'):
            values['CONTENT_MACHINE_DATABASE_URL'] = os.environ['CONTENT_MACHINE_DATABASE_URL']
        cls.dsn = parse_hosted_configuration(values).database_url
        cls.schema = 'cm_verify_' + uuid.uuid4().hex
        assert re.fullmatch(r'cm_verify_[0-9a-f]{32}', cls.schema)
        cls.driver = psycopg
        cls.admin = cls.connect_raw()
        cls.admin.execute('CREATE SCHEMA ' + cls.schema)
        cls.addClassCleanup(cls.cleanup_schema)
        # Only rewrite the literal owning schema, including dynamic policy SQL;
        # auth.uid() remains Supabase's real function. No public DDL is executed.
        migration = (ROOT / 'supabase/migrations/202611060001_workflow_foundation.sql').read_text(encoding='utf-8')
        cls.admin.execute(migration.replace('public.', cls.schema + '.'))
        cls.admin.execute('GRANT USAGE ON SCHEMA ' + cls.schema + ' TO authenticated, anon')

    @classmethod
    def connect_raw(cls):
        try:
            return cls.driver.connect(cls.dsn, autocommit=True, connect_timeout=10)
        except Exception:
            raise RuntimeError('Live PostgreSQL connection unavailable; details redacted.') from None

    @classmethod
    def cleanup_schema(cls):
        try:
            cls.admin.rollback()
            if not re.fullmatch(r'cm_verify_[0-9a-f]{32}', cls.schema):
                raise RuntimeError('Unsafe cleanup schema')
            cls.admin.execute('DROP SCHEMA ' + cls.schema + ' CASCADE')
        finally:
            cls.admin.close()

    def session(self):
        raw = self.connect_raw()
        raw.execute('SET search_path TO ' + self.schema + ', pg_catalog')
        raw.execute("SET statement_timeout TO '15s'")
        return PostgresSession(raw)

    def setUp(self):
        self.a = Principal(owner_id=str(uuid.uuid4()), mode='hosted_verified')
        self.b = Principal(owner_id=str(uuid.uuid4()), mode='hosted_verified')
        self.conn = self.session()
        self.addCleanup(self.conn.close)

    def create(self, conn=None, key='create'):
        return create_item(conn or self.conn, self.a, ItemCreate(title='Live isolated fixture',
            destination='linkedin', format='linkedin_post'), request_id=key).body['item']

    def test_crud_replay_cas_isolation_and_reopen(self):
        original = self.create()
        self.assertEqual(original, self.create())
        item_id = original['item_id']
        payload = ItemPatch(expected_revision=1, context={'notes': 'Exact source\n'},
                            artifact={'segments': ['Exact grounded draft.']})
        saved = save_item(self.conn, self.a, item_id, payload, request_id='save').body['item']
        self.assertEqual(saved, save_item(self.conn, self.a, item_id, payload, request_id='save').body['item'])
        with self.assertRaises(WorkflowError) as stale:
            save_item(self.conn, self.a, item_id, payload, request_id='stale')
        self.assertEqual(stale.exception.code, 'revision_conflict')
        with self.assertRaises(WorkflowError) as foreign:
            get_item(self.conn, self.b, item_id)
        self.assertEqual(foreign.exception.status_code, 404)
        self.assertEqual(list_items(self.conn, self.b), [])
        with closing(self.session()) as reopened:
            self.assertEqual(get_item(reopened, self.a, item_id).model_dump(mode='json'), saved)

    def test_settings_preferences_and_frozen_operation(self):
        item = self.create()
        profile = ProfileSave(name='Fixture creator', role='Engineer', bio='Known facts.', expected_revision=0)
        save_profile(self.conn, self.a, profile, request_id='profile')
        create_source(self.conn, self.a, SourceCreate(kind='rss', name='Fixture',
            url='https://example.com/feed', enabled=True), request_id='source')
        self.assertEqual(len(list_sources(self.conn, self.a, enabled_only=True)), 1)
        pref = mutate_preference(self.conn, self.a, 'create', None,
            {'text': 'Use evidence from the source.', 'consent': True}, 'preference').body['preference']
        op, created = begin_operation(self.conn, self.a, item['item_id'], 1, 'generate', 'operation')
        self.assertTrue(created)
        self.assertEqual(op['editorial_snapshot']['profile']['name'], 'Fixture creator')
        self.assertEqual(len(op['editorial_snapshot']['preferences']), 1)
        mutate_preference(self.conn, self.a, 'stop', pref['preference_id'], {'expected_revision': 1}, 'stop')
        self.assertEqual(len(preference_history(self.conn, self.a, pref['preference_id'])), 2)
        terminal = complete_operation(self.conn, self.a, item['item_id'], op['operation_id'], {'segments': ['Suggestion']})
        self.assertEqual(terminal['state'], 'completed')
        self.assertEqual(begin_operation(self.conn, self.a, item['item_id'], 1, 'generate', 'operation')[0], terminal)
        self.assertEqual(get_profile(self.conn, self.b)['revision'], 0)
        self.assertEqual(list_preferences(self.conn, self.b), [])
        self.assertEqual(get_item(self.conn, self.a, item['item_id']).artifact.segments, [])

    def test_approval_exact_export_and_immutable_history(self):
        item_id = self.create()['item_id']
        text = 'A bounded queue makes overload visible.\nExact fixture content.  '
        saved = save_item(self.conn, self.a, item_id, ItemPatch(expected_revision=1,
            artifact={'segments': [text]}), request_id='draft').body['item']
        item = get_item(self.conn, self.a, item_id)
        result = approve_item(self.conn, self.a, item_id, ApproveRequest(expected_revision=saved['working_revision'],
            artifact_digest=artifact_digest(item.destination, item.format, item.artifact), consent=True), request_id='approval')
        version_id = result.body['approval']['version_id']
        self.assertEqual(export_version(self.conn, self.a, item_id, version_id).content, text.encode('utf-8'))
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute('UPDATE workflow_versions SET artifact_json=? WHERE version_id=?', ('{}', version_id))
        self.assertEqual(export_version(self.conn, self.a, item_id, version_id).content, text.encode('utf-8'))

    def test_outer_rollback_and_failed_input_leave_no_partial_write(self):
        self.conn.execute('BEGIN IMMEDIATE')
        self.create()
        self.conn.rollback()
        self.assertEqual(list_items(self.conn, self.a), [])
        with self.assertRaises(WorkflowError) as invalid:
            create_item(self.conn, self.a, ItemCreate(title='Invalid\x00',
                destination='linkedin', format='linkedin_post'), request_id='unsupported')
        self.assertEqual(invalid.exception.code, 'hosted_input_unsupported')
        with self.assertRaises(ValidationError):
            ItemCreate(title='Invalid\ud800', destination='linkedin', format='linkedin_post')
        self.assertFalse(self.conn.in_transaction)
        self.assertEqual(list_items(self.conn, self.a), [])

    def test_real_deferred_commit_failure_rolls_back_item_and_retry_record(self):
        # PostgreSQL's deferred FK fails at COMMIT, after service SQL has run.
        # This detects acknowledgements escaping before durability is known.
        schema = self.schema
        self.admin.execute('CREATE TABLE ' + schema + '.verification_parent(id integer PRIMARY KEY)')
        self.admin.execute('CREATE TABLE ' + schema + '.verification_child(id integer REFERENCES ' +
            schema + '.verification_parent(id) DEFERRABLE INITIALLY DEFERRED)')
        self.admin.execute('CREATE FUNCTION ' + schema + '.verification_fail_commit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO ' +
            schema + '.verification_child VALUES(99); RETURN NEW; END $$')
        self.admin.execute('CREATE TRIGGER verification_commit_failure AFTER INSERT ON ' + schema +
            '.workflow_items FOR EACH ROW EXECUTE FUNCTION ' + schema + '.verification_fail_commit()')
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                self.create()
            self.assertFalse(self.conn.in_transaction)
            self.assertEqual(list_items(self.conn, self.a), [])
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_idempotency WHERE owner_id=?',
                (self.a.owner_id,)).fetchone()[0], 0)
        finally:
            self.admin.execute('DROP TRIGGER verification_commit_failure ON ' + schema + '.workflow_items')
            self.admin.execute('DROP FUNCTION ' + schema + '.verification_fail_commit()')
            self.admin.execute('DROP TABLE ' + schema + '.verification_child')
            self.admin.execute('DROP TABLE ' + schema + '.verification_parent')
        self.assertEqual(self.create()['working_revision'], 1)

    def test_concurrent_same_operation_claim_is_created_once(self):
        item_id = self.create()['item_id']
        barrier = threading.Barrier(2)
        def claim(_):
            with closing(self.session()) as conn:
                barrier.wait(timeout=10)
                return begin_operation(conn, self.a, item_id, 1, 'generate', 'same-claim')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, (1, 2)))
        self.assertEqual(results[0][0], results[1][0])
        self.assertEqual(sorted(result[1] for result in results), [False, True])

    def test_concurrent_cas_has_exactly_one_winner(self):
        item_id = self.create()['item_id']
        barrier = threading.Barrier(2)
        def update(number):
            with closing(self.session()) as conn:
                barrier.wait(timeout=10)
                try:
                    save_item(conn, self.a, item_id, ItemPatch(expected_revision=1,
                        context={'notes': 'Writer ' + str(number)}), request_id='cas-' + str(number))
                    return 'saved'
                except WorkflowError as error:
                    return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, (1, 2)))
        self.assertEqual(sorted(results), ['revision_conflict', 'saved'])
        self.assertEqual(get_item(self.conn, self.a, item_id).working_revision, 2)

    def test_guest_bootstrap_return_preserves_edits(self):
        verifier = lambda proof: VerifiedGuestSession(self.a, is_anonymous=True)
        first = bootstrap_guest(self.conn, 'fixture-proof', verifier)
        item = first['examples'][0]['item']
        save_item(self.conn, self.a, item['item_id'], ItemPatch(expected_revision=item['working_revision'],
            context={'notes': 'Guest personal fixture edit'}), request_id='guest-edit')
        with closing(self.session()) as conn:
            again = bootstrap_guest(conn, 'fixture-proof', verifier)
        self.assertEqual(len(again['examples']), 2)
        self.assertEqual({entry['item']['item_id'] for entry in first['examples']},
                         {entry['item']['item_id'] for entry in again['examples']})
        self.assertEqual(get_item(self.conn, self.a, item['item_id']).context.notes, 'Guest personal fixture edit')

    def test_guest_transfer_preserves_archive_and_copies_without_approval(self):
        def verifier(proof):
            return VerifiedGuestSession(self.a if proof == 'guest' else self.b, is_anonymous=proof == 'guest')
        boot = bootstrap_guest(self.conn, 'guest', verifier)
        original = next(entry['item'] for entry in boot['examples'] if any(entry['item']['artifact']['segments']))
        source = get_item(self.conn, self.a, original['item_id'])
        approved = approve_item(self.conn, self.a, source.item_id, ApproveRequest(
            expected_revision=source.working_revision, consent=True,
            artifact_digest=artifact_digest(source.destination, source.format, source.artifact)), request_id='guest-approval')
        before = [entry.model_dump(mode='json') for entry in list_items(self.conn, self.a)]
        preview = preview_guest_copy(self.conn, 'guest', 'creator', verifier)
        result = copy_guest_workspace(self.conn, 'guest', 'creator', verifier, consent=True,
            request_id='copy', source_fingerprint=preview['source_fingerprint'])
        self.assertEqual(result, copy_guest_workspace(self.conn, 'guest', 'creator', verifier, consent=True,
            request_id='copy', source_fingerprint=preview['source_fingerprint']))
        self.assertEqual(before, [entry.model_dump(mode='json') for entry in list_items(self.conn, self.a)])
        copied = list_items(self.conn, self.b)
        self.assertEqual(len(copied), 2)
        self.assertTrue(all(entry.active_approval_id is None and entry.working_revision == 1 for entry in copied))
        receipt = get_transfer_receipt(self.conn, self.b, result['transfer_id'])
        self.assertIs(receipt['editorial_approval'], False)
        self.assertEqual(receipt['archive']['tables']['workflow_approvals'][0]['approval_id'],
                         approved.body['approval']['approval_id'])
        with self.assertRaises(WorkflowError) as foreign:
            get_transfer_receipt(self.conn, self.a, result['transfer_id'])
        self.assertEqual(foreign.exception.status_code, 404)
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute('UPDATE workflow_guest_transfers SET archive_json=? WHERE transfer_id=?',
                ('{}', result['transfer_id']))

    def test_real_authenticated_role_rls_and_mutation_denial(self):
        item = self.create()
        # Execute as the actual Supabase browser role. RLS cannot be certified
        # through the postgres/admin role, which bypasses its owner policies.
        with self.connect_raw() as raw:
            raw.execute('BEGIN')
            raw.execute('SET LOCAL ROLE authenticated')
            raw.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (self.a.owner_id,))
            raw.execute("SELECT set_config('request.jwt.claims', %s, true)",
                        ('{"sub":"' + self.a.owner_id + '","role":"authenticated"}',))
            rows = raw.execute('SELECT item_id FROM ' + self.schema + '.workflow_items').fetchall()
            self.assertEqual(rows, [(item['item_id'],)])
            raw.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (self.b.owner_id,))
            raw.execute("SELECT set_config('request.jwt.claims', %s, true)",
                        ('{"sub":"' + self.b.owner_id + '","role":"authenticated"}',))
            self.assertEqual(raw.execute('SELECT item_id FROM ' + self.schema + '.workflow_items').fetchall(), [])
            with self.assertRaises(self.driver.errors.InsufficientPrivilege):
                raw.execute('UPDATE ' + self.schema + '.workflow_items SET title=%s', ('Forbidden',))
            raw.rollback()


if __name__ == '__main__':
    # Avoid traceback locals/driver messages exposing connection information.
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LivePostgresWorkflowTest))
    _HOME.cleanup()
    sys.exit(not result.wasSuccessful())
