"""Explicit local legacy import with disposable inputs and no discovered paths."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import copy
import io
import json
from pathlib import Path
import runpy
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item, list_items, save_item
from content_machine.workflow.schemas import ItemPatch, Principal
from content_machine.workflow.recovery import inspect_database
from content_machine.workflow import legacy_import as imports


class LegacyImportTest(unittest.TestCase):
    def setUp(self):
        self.home = TemporaryDirectory(prefix='legacy-import-')
        self.addCleanup(self.home.cleanup)
        self.path = Path(self.home.name) / 'workflow.db'
        self.conn = connect(self.path)
        self.addCleanup(self.conn.close)
        imports.initialize_import_schema(self.conn)
        self.a = Principal(owner_id='creator-a', mode='trusted_local')
        self.b = Principal(owner_id='creator-b', mode='trusted_local')

    def record(self, key='legacy-1', provenance='actual', **changes):
        return {'legacy_id': key, 'provenance': provenance,
            'provenance_evidence': None if provenance == 'unknown' else 'Operator-reviewed original export',
            'title': '  Original draft  ', 'destination': 'linkedin', 'format': 'linkedin_post',
            'context': {'notes': '  Original notes\n'}, 'artifact': {'segments': ['  Original caf\u00e9\r\n  ']},
            'legacy_payload': {'comments': [{'author': None, 'text': 'Exact comment\n'}],
                'published_text': ' historical final text  ', 'approval': {'claimed': True, 'verified': None}},
            **changes}

    def run_import(self, records, mapping=None):
        return imports.import_legacy_records(self.conn, 'explicit-backup-v1', records,
                                            owner_mapping={} if mapping is None else mapping)

    def test_actual_synthetic_unknown_are_separated_and_original_payload_recoverable(self):
        actual = self.record()
        synthetic = self.record('demo', 'proven_synthetic', title='Ordinary looking title')
        unknown = self.record('uncertain', 'unknown', title='Example: real or demo?')
        result = self.run_import([actual, synthetic, unknown], {'legacy-1': self.a})
        self.assertEqual([row['state'] for row in result],
                         ['imported', 'synthetic_quarantined', 'unknown_quarantined'])
        owned = list_items(self.conn, self.a)
        self.assertEqual(len(owned), 1)
        self.assertEqual(owned[0].title, actual['title'])
        self.assertEqual(owned[0].artifact.segments, actual['artifact']['segments'])
        self.assertIsNone(owned[0].active_approval_id)
        self.assertIsNone(owned[0].parent_version_id)
        for table in ('workflow_approvals', 'workflow_versions', 'workflow_reviews', 'workflow_operations'):
            self.assertEqual(self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)
        for record in (actual, synthetic, unknown):
            archived = imports.inspect_import(self.conn, 'explicit-backup-v1', record['legacy_id'])
            self.assertEqual(archived['record']['legacy_payload'], record['legacy_payload'])
            self.assertEqual(archived['record']['provenance'], record['provenance'])
            self.assertEqual(archived['historical_approval'], 'unknown')
        self.assertEqual(list_items(self.conn, self.b), [])

    def test_actual_owner_mapping_is_required_and_never_inferred_from_payload(self):
        record = self.record(legacy_payload={'owner_id': self.a.owner_id, 'author': 'Creator A'})
        for mapping in ({}, {'legacy-1': self.a.owner_id}, {'other': self.a}):
            with self.subTest(mapping=mapping), self.assertRaises(WorkflowError):
                self.run_import([record], mapping)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_legacy_imports').fetchone()[0], 0)
        self.assertEqual(list_items(self.conn, self.a), [])

    def test_quarantine_owner_mapping_and_missing_provenance_proof_are_rejected(self):
        for record, mapping in [(self.record(provenance_evidence=''), {'legacy-1': self.a}),
                                (self.record(provenance_evidence=None), {'legacy-1': self.a}),
                                (self.record(provenance='proven_synthetic'), {'legacy-1': self.a}),
                                (self.record(provenance='unknown'), {'legacy-1': self.a})]:
            with self.subTest(record=record['provenance']), self.assertRaises(WorkflowError):
                self.run_import([record], mapping)

    def test_repeat_import_preserves_creator_edits_counts_and_historical_archive(self):
        record = self.record()
        original = copy.deepcopy(record)
        first = self.run_import([record], {'legacy-1': self.a})
        item = get_item(self.conn, self.a, first[0]['item_id'])
        edited = save_item(self.conn, self.a, item.item_id, ItemPatch(expected_revision=item.working_revision,
            artifact={'segments': ['New creator edits\n']}), request_id='post-import-edit').body['item']
        archived = imports.inspect_import(self.conn, 'explicit-backup-v1', 'legacy-1')
        counts = {table: self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                  for table in ('workflow_items', 'workflow_legacy_imports', 'workflow_idempotency')}
        for _ in range(2):
            self.assertEqual(self.run_import([record], {'legacy-1': self.a}), first)
            self.assertEqual(get_item(self.conn, self.a, item.item_id).model_dump(mode='json'), edited)
            self.assertEqual(imports.inspect_import(self.conn, 'explicit-backup-v1', 'legacy-1'), archived)
        self.assertEqual(record, original)
        self.assertEqual(counts, {table: self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                                 for table in counts})

    def test_changed_input_or_owner_fails_without_overwriting_existing_import(self):
        record = self.record()
        imported = self.run_import([record], {'legacy-1': self.a})
        for changed, mapping in [(dict(record, title='Changed'), {'legacy-1': self.a}),
                                 (dict(record, provenance='unknown', provenance_evidence=None), {}),
                                 (record, {'legacy-1': self.b})]:
            with self.subTest(mapping=mapping), self.assertRaises(WorkflowError) as raised:
                self.run_import([changed], mapping)
            self.assertEqual(raised.exception.code, 'legacy_import_conflict')
        self.assertEqual(list_items(self.conn, self.b), [])
        self.assertEqual(get_item(self.conn, self.a, imported[0]['item_id']).title, record['title'])

    def test_invalid_batch_and_duplicate_ids_do_not_leave_partial_work(self):
        batches = [[self.record(), self.record('bad', title='')],
                   [self.record(), self.record()], [self.record(legacy_payload={'invalid': float('nan')})]]
        for records in batches:
            with self.subTest(size=len(records)), self.assertRaises(WorkflowError):
                self.run_import(records, {'legacy-1': self.a, 'bad': self.a})
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_legacy_imports').fetchone()[0], 0)
        self.assertEqual(list_items(self.conn, self.a), [])

    def test_real_commit_failure_rolls_back_items_and_tracking_then_can_retry(self):
        self.conn.executescript('CREATE TABLE import_parent(id INTEGER PRIMARY KEY);'
            'CREATE TABLE import_child(parent_id INTEGER REFERENCES import_parent(id) DEFERRABLE INITIALLY DEFERRED);'
            'CREATE TRIGGER fail_import AFTER INSERT ON workflow_legacy_imports '
            'BEGIN INSERT INTO import_child VALUES (999); END;')
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_import([self.record()], {'legacy-1': self.a})
        self.assertEqual(list_items(self.conn, self.a), [])
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_legacy_imports').fetchone()[0], 0)
        self.conn.execute('DROP TRIGGER fail_import')
        self.conn.commit()
        self.assertEqual(len(self.run_import([self.record()], {'legacy-1': self.a})), 1)

    def test_late_conflict_rolls_back_earlier_new_records_in_the_batch(self):
        original = self.record()
        self.run_import([original], {'legacy-1': self.a})
        with self.assertRaises(WorkflowError) as raised:
            self.run_import([self.record('new-first'), dict(original, title='conflicting source')],
                            {'new-first': self.a, 'legacy-1': self.a})
        self.assertEqual(raised.exception.code, 'legacy_import_conflict')
        self.assertEqual(len(list_items(self.conn, self.a)), 1)
        with self.assertRaises(WorkflowError) as missing:
            imports.inspect_import(self.conn, 'explicit-backup-v1', 'new-first')
        self.assertEqual(missing.exception.code, 'legacy_import_not_found')

    def test_uninitialized_schema_and_unsafe_json_fail_without_creating_work(self):
        with closing(connect(':memory:')) as unprepared:
            with self.assertRaises(WorkflowError) as raised:
                imports.import_legacy_records(unprepared, 'explicit-backup-v1', [self.record()],
                                              owner_mapping={'legacy-1': self.a})
            self.assertEqual(raised.exception.code, 'legacy_import_unavailable')
            self.assertEqual(list_items(unprepared, self.a), [])
        for payload in ({1: 'numeric key'}, {'blob': b'not JSON'}, {'bad': float('inf')}):
            with self.subTest(payload=payload), self.assertRaises(WorkflowError):
                self.run_import([self.record(legacy_payload=payload)], {'legacy-1': self.a})
        invalid = imports.LegacyRecord.model_validate(self.record()).model_copy(update={'legacy_id': ''})
        with self.assertRaises(WorkflowError):
            self.run_import([invalid], {'legacy-1': self.a})

    def test_concurrent_imports_create_one_item_and_schema_reinitialization_is_safe(self):
        record = self.record()
        def run(_):
            with closing(connect(self.path)) as conn:
                return imports.import_legacy_records(conn, 'explicit-backup-v1', [record],
                                                     owner_mapping={'legacy-1': self.a})
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(run, range(2)))
        self.assertEqual(first, second)
        self.assertEqual(len(list_items(self.conn, self.a)), 1)
        before = imports.inspect_import(self.conn, 'explicit-backup-v1', 'legacy-1')
        imports.initialize_import_schema(self.conn)
        self.assertEqual(imports.inspect_import(self.conn, 'explicit-backup-v1', 'legacy-1'), before)

    def test_same_legacy_id_in_distinct_explicit_namespaces_does_not_conflate_sources(self):
        record = self.record()
        first = self.run_import([record], {'legacy-1': self.a})
        second = imports.import_legacy_records(self.conn, 'separate-reviewed-backup', [record],
                                              owner_mapping={'legacy-1': self.b})
        self.assertNotEqual(first[0]['item_id'], second[0]['item_id'])
        self.assertEqual(len(list_items(self.conn, self.a)), 1)
        self.assertEqual(len(list_items(self.conn, self.b)), 1)
        self.assertEqual(imports.inspect_import(self.conn, 'explicit-backup-v1', 'legacy-1')['owner_id'],
                         self.a.owner_id)
        self.assertEqual(imports.inspect_import(self.conn, 'separate-reviewed-backup', 'legacy-1')['owner_id'],
                         self.b.owner_id)

    def test_import_history_is_immutable_and_source_database_tables_are_untouched(self):
        self.conn.execute('CREATE TABLE supplied_legacy (text TEXT)')
        self.conn.execute('INSERT INTO supplied_legacy VALUES (?)', ('Historical text',))
        self.conn.commit()
        self.run_import([self.record()], {'legacy-1': self.a})
        for statement in ('DELETE FROM workflow_legacy_imports',
                          "UPDATE workflow_legacy_imports SET state='unknown_quarantined'"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(statement)
            self.conn.rollback()
        self.assertEqual(self.conn.execute('SELECT text FROM supplied_legacy').fetchone()[0], 'Historical text')

    def cli(self, *, records=None, backup=None, confirm=True):
        from contextlib import redirect_stdout
        record_path, owner_path = Path(self.home.name) / 'records.json', Path(self.home.name) / 'owners.json'
        record_path.write_text(json.dumps([self.record()] if records is None else records), encoding='utf-8')
        owner_path.write_text(json.dumps({'legacy-1': self.a.owner_id}), encoding='utf-8')
        arguments = ['--database', str(self.path), '--records', str(record_path), '--owners', str(owner_path),
                     '--backup', str(backup or Path(self.home.name) / 'before-import.db'),
                     '--namespace', 'explicit-cli-v1', '--quiescent']
        if confirm:
            arguments.append('--confirm-import')
        main = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools/local_legacy_import.py'))['main']
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(arguments)
        return status, json.loads(output.getvalue())

    def test_cli_backs_up_before_import_and_reports_counts_without_original_text(self):
        before = inspect_database(self.path)['fingerprint']
        status, result = self.cli()
        self.assertEqual(status, 0)
        self.assertEqual(result['counts']['imported'], 1)
        self.assertEqual(inspect_database(Path(self.home.name) / 'before-import.db')['fingerprint'], before)
        self.assertEqual(len(list_items(self.conn, self.a)), 1)
        self.assertNotIn('Original', json.dumps(result))
        # A fresh explicit pre-import backup is required even on an idempotent rerun.
        status, again = self.cli(backup=Path(self.home.name) / 'before-repeat.db')
        self.assertEqual(status, 0)
        self.assertEqual(again['counts']['imported'], 1)
        self.assertEqual(len(list_items(self.conn, self.a)), 1)

    def test_cli_backup_destination_conflict_never_imports_or_overwrites(self):
        backup = Path(self.home.name) / 'existing.db'
        backup.write_bytes(b'preserve existing backup')
        before = inspect_database(self.path)['fingerprint']
        status, result = self.cli(backup=backup)
        self.assertEqual(status, 1)
        self.assertFalse(result['success'])
        self.assertEqual(backup.read_bytes(), b'preserve existing backup')
        self.assertEqual(inspect_database(self.path)['fingerprint'], before)
        self.assertEqual(list_items(self.conn, self.a), [])

    def test_cli_invalid_mapping_rolls_back_and_retains_preimport_backup(self):
        before = inspect_database(self.path)['fingerprint']
        status, result = self.cli(records=[self.record('unmapped')])
        self.assertEqual(status, 1)
        self.assertEqual(result['code'], 'legacy_import_invalid')
        self.assertTrue(result['backup_created'])
        self.assertEqual(inspect_database(Path(self.home.name) / 'before-import.db')['fingerprint'], before)
        self.assertEqual(inspect_database(self.path)['fingerprint'], before)

    def test_cli_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit) as missing:
            self.cli(confirm=False)
        self.assertEqual(missing.exception.code, 2)
        self.assertFalse((Path(self.home.name) / 'before-import.db').exists())
