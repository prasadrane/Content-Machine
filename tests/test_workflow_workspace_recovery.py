"""Combined recovery exercises disposable inputs; no storage discovery or live data."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_workflow_recovery as fixtures
from content_machine.storage.db import connect
from content_machine.storage.paths import sync_seed
from content_machine.workflow.exports import export_version
from content_machine.workflow.guests import VerifiedGuestSession, bootstrap_guest, guest_example_labels
from content_machine.workflow.items import get_item, save_item
from content_machine.workflow.migrations import migrate_workflow
from content_machine.workflow.recovery import inspect_database
from content_machine.workflow.schemas import ItemPatch
from content_machine.workflow.settings import (
    ProfileSave, SourceCreate, create_source, get_profile, list_sources, save_profile,
)
from content_machine.workflow import workspace_recovery as recovery


class WorkspaceRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RecoveryTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.attachments = self.root / 'attachments'
        self.attachments.mkdir()
        (self.attachments / 'empty').mkdir()
        (self.attachments / 'raw.bin').write_bytes(b'\x00exact\r\n\xff')
        self.bundle = self.root / 'bundle'
        self.restored = self.root / 'restored'

    def backup(self, **kwargs):
        return recovery.backup_workspace(self.fixture.source, self.attachments, self.bundle,
                                         quiescent=kwargs.get('quiescent', True))

    def assert_no_staging(self):
        self.assertFalse(list(self.root.glob('.cm-workspace-*')))

    def test_roundtrip_preserves_exact_approval_legacy_and_attachment_bytes(self):
        report = self.backup()
        self.assertIs(report['editorial_approval'], False)
        self.assertEqual(report, recovery.inspect_workspace_bundle(self.bundle))
        self.assertEqual(report, recovery.rehearse_workspace_restore(self.bundle, self.restored))
        self.assertEqual(inspect_database(self.fixture.source)['fingerprint'],
                         inspect_database(self.restored / 'workflow.sqlite')['fingerprint'])
        with closing(connect(self.restored / 'workflow.sqlite', init=False)) as conn:
            self.assertEqual(export_version(conn, self.fixture.a, self.fixture.a_id, self.fixture.version).content,
                             b'  An exact approved draft\n')
            self.assertEqual(conn.execute('SELECT text FROM legacy_comments').fetchone()[0], 'Historical comment')
        self.assertEqual((self.restored / 'attachments/raw.bin').read_bytes(), b'\x00exact\r\n\xff')
        self.assertTrue((self.restored / 'attachments/empty').is_dir())
        self.assert_no_staging()

    def test_requires_explicit_quiescent_confirmation(self):
        for value in (False, None, 1, 'true'):
            with self.subTest(value=value), self.assertRaises(recovery.WorkspaceRecoveryError):
                self.backup(quiescent=value)
        self.assertFalse(self.bundle.exists())

    def test_restored_workspace_retains_edits_provenance_and_approval_through_repeat_migration_and_seed_refresh(self):
        conn, owner = self.fixture.conn, self.fixture.a
        profile = save_profile(conn, owner, ProfileSave(name='  Creator  ', role='Engineer',
            bio='Owner-provided context\n', expected_revision=0), request_id='recovery-profile').body['profile']
        source = create_source(conn, owner, SourceCreate(kind='rss', name='Owned feed',
            url='https://example.org/feed', enabled=False), request_id='recovery-source').body['source']
        evidence = {'source_id': source['source_id'], 'url': 'https://example.org/article',
                    'title': 'Captured evidence', 'excerpt': 'Exact original excerpt.\n',
                    'fetched_at': '2026-11-07T12:00:00.000Z'}
        current = get_item(conn, owner, self.fixture.a_id)
        edited = save_item(conn, owner, current.item_id, ItemPatch(
            expected_revision=current.working_revision, stage='draft_review',
            context={'notes': '  New creator edits\n', 'sources': [evidence]},
            artifact={'segments': ['  A newer unapproved draft\n']}),
            request_id='recovery-creator-edit').body['item']
        self.assertIsNone(edited['active_approval_id'])
        session = VerifiedGuestSession(self.fixture.b, is_anonymous=True)
        examples = bootstrap_guest(conn, session, lambda proof: proof)['examples']
        example = examples[0]['item']
        guest_edit = save_item(conn, self.fixture.b, example['item_id'], ItemPatch(
            expected_revision=example['working_revision'], context={'notes': 'Guest replacement notes\n'}),
            request_id='recovery-guest-edit').body['item']
        labels = guest_example_labels(conn, self.fixture.b)
        self.backup()
        recovery.rehearse_workspace_restore(self.bundle, self.restored)
        database = self.restored / 'workflow.sqlite'
        fingerprint = inspect_database(database)['fingerprint']
        seed, runtime = self.root / 'seed.md', self.root / 'runtime.md'
        runtime.write_text('Previous seed', encoding='utf-8')
        for iteration in range(3):
            seed.write_text(f'Refreshed seed {iteration}', encoding='utf-8')
            with patch.dict('os.environ', {'DEMO_MODE': '0'}):
                sync_seed(seed, runtime)
            self.assertEqual(runtime.read_text(encoding='utf-8'), f'Refreshed seed {iteration}')
            with closing(connect(database, init=False)) as restored:
                # Exercise the actual additive migration again, not a mock or
                # a copied schema. Every pass uses a fresh connection.
                migrate_workflow(restored)
                migrate_workflow(restored)
                restored.commit()
                self.assertEqual(get_item(restored, owner, current.item_id).model_dump(mode='json'), edited)
                self.assertEqual(get_profile(restored, owner), profile)
                self.assertEqual(list_sources(restored, owner), [source])
                self.assertEqual(guest_example_labels(restored, self.fixture.b), labels)
                returned = bootstrap_guest(restored, session, lambda proof: proof)['examples']
                self.assertEqual(len(returned), 2)
                self.assertEqual(next(row['item'] for row in returned
                    if row['item']['item_id'] == example['item_id']), guest_edit)
                self.assertEqual(export_version(restored, owner, current.item_id, self.fixture.version).content,
                                 b'  An exact approved draft\n')
                self.assertEqual(restored.execute('SELECT author, text FROM legacy_comments').fetchone()[:],
                                 ('Unassigned', 'Historical comment'))
                self.assertEqual(restored.execute('SELECT hook_thesis FROM spikes WHERE id=?',
                    ('legacy',)).fetchone()[0], 'Original legacy idea')
            self.assertEqual(inspect_database(database)['fingerprint'], fingerprint)
            self.assertEqual((self.restored / 'attachments/raw.bin').read_bytes(), b'\x00exact\r\n\xff')

    def test_existing_backup_and_restore_destinations_are_never_overwritten(self):
        self.backup()
        before = (self.bundle / 'manifest.json').read_bytes()
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            self.backup()
        self.assertEqual((self.bundle / 'manifest.json').read_bytes(), before)
        self.restored.mkdir()
        (self.restored / 'keep').write_bytes(b'preserved')
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            recovery.rehearse_workspace_restore(self.bundle, self.restored)
        self.assertEqual((self.restored / 'keep').read_bytes(), b'preserved')

    def test_overlapping_inputs_and_outputs_are_rejected(self):
        for attachments, destination in [(self.root, self.bundle), (self.attachments, self.attachments / 'backup')]:
            with self.subTest(destination=destination), self.assertRaises(recovery.WorkspaceRecoveryError):
                recovery.backup_workspace(self.fixture.source, attachments, destination, quiescent=True)
        self.assertFalse(self.bundle.exists())

    def test_database_writers_are_excluded_until_both_parts_are_captured(self):
        original = recovery.backup_attachments
        def copy_while_locked(*args):
            with closing(sqlite3.connect(self.fixture.source, timeout=0.01)) as other:
                with self.assertRaises(sqlite3.OperationalError):
                    other.execute("INSERT INTO legacy_comments VALUES (9, 'race', 'must not commit')")
            return original(*args)
        with patch.object(recovery, 'backup_attachments', side_effect=copy_while_locked):
            self.backup()
        self.fixture.conn.execute("INSERT INTO legacy_comments VALUES (9, 'after', 'lock released')")
        self.fixture.conn.rollback()

    def test_failed_attachment_capture_leaves_no_published_database_only_bundle(self):
        with patch.object(recovery, 'backup_attachments', side_effect=OSError('interrupted copy')):
            with self.assertRaises(recovery.WorkspaceRecoveryError):
                self.backup()
        self.assertFalse(self.bundle.exists())
        self.assert_no_staging()
        self.backup()

    def test_corrupt_database_or_attachment_prevents_any_restore(self):
        self.backup()
        database = self.bundle / 'workflow.sqlite'
        original = database.read_bytes()
        database.write_bytes(b'not a database')
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            recovery.rehearse_workspace_restore(self.bundle, self.restored)
        database.write_bytes(original)
        (self.bundle / 'attachments/files/raw.bin').write_bytes(b'corrupt')
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            recovery.rehearse_workspace_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())
        self.assert_no_staging()

    def test_manifest_tampering_and_extra_entries_are_rejected(self):
        self.backup()
        manifest = self.bundle / 'manifest.json'
        original = manifest.read_text()
        changed = json.loads(original)
        changed['editorial_approval'] = True
        manifest.write_text(json.dumps(changed))
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            recovery.inspect_workspace_bundle(self.bundle)
        manifest.write_text(original)
        (self.bundle / 'unexpected').write_text('extra')
        with self.assertRaises(recovery.WorkspaceRecoveryError):
            recovery.inspect_workspace_bundle(self.bundle)

    def test_restore_second_leg_failure_leaves_no_partial_target(self):
        self.backup()
        with patch.object(recovery, 'rehearse_attachment_restore', side_effect=OSError('restore interrupted')):
            with self.assertRaises(recovery.WorkspaceRecoveryError):
                recovery.rehearse_workspace_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())
        self.assert_no_staging()

    def test_attachment_changes_between_capture_and_publication_abort_backup(self):
        original = recovery.backup_attachments
        def copy_then_change(*args):
            result = original(*args)
            (self.attachments / 'raw.bin').write_bytes(b'changed after copy')
            return result
        with patch.object(recovery, 'backup_attachments', side_effect=copy_then_change):
            with self.assertRaises(recovery.WorkspaceRecoveryError):
                self.backup()
        self.assertFalse(self.bundle.exists())
        self.assert_no_staging()

    def test_bundle_change_during_restore_prevents_publication(self):
        self.backup()
        original = recovery.rehearse_attachment_restore
        def restore_then_change(*args):
            result = original(*args)
            (self.bundle / 'attachments/files/raw.bin').write_bytes(b'changed during restore')
            return result
        with patch.object(recovery, 'rehearse_attachment_restore', side_effect=restore_then_change):
            with self.assertRaises(recovery.WorkspaceRecoveryError):
                recovery.rehearse_workspace_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())
        self.assert_no_staging()

    def test_publication_race_keeps_concurrent_destination(self):
        original = recovery.attachments._publish
        def publish(staged, destination):
            if Path(destination) == self.bundle:
                self.bundle.mkdir()
                (self.bundle / 'keep').write_bytes(b'concurrent')
            return original(staged, destination)
        with patch.object(recovery.attachments, '_publish', side_effect=publish):
            with self.assertRaises(recovery.WorkspaceRecoveryError):
                self.backup()
        self.assertEqual((self.bundle / 'keep').read_bytes(), b'concurrent')
        self.assert_no_staging()
