"""Offline migration/recovery rehearsal using only disposable SQLite databases."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from content_machine.storage.db import connect
from content_machine.workflow.approvals import approve_item
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.exports import export_version
from content_machine.workflow.items import create_item, get_item, save_item
from content_machine.workflow.operations import begin_operation, get_operation
from content_machine.workflow.recovery import RecoveryError, backup_database, inspect_database, rehearse_restore
from content_machine.workflow.schemas import ApproveRequest, ItemCreate, ItemPatch, Principal
from content_machine.workflow.versions import artifact_digest
from content_machine.workflow import recovery


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cm-recovery-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.db'
        self.conn = connect(self.source)
        self.addCleanup(self.conn.close)
        self.a = Principal(owner_id='creator-a', mode='hosted_verified')
        self.b = Principal(owner_id='creator-b', mode='hosted_verified')
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('CREATE TABLE legacy_comments (id INTEGER PRIMARY KEY, author TEXT, text TEXT)')
        self.conn.execute('INSERT INTO legacy_comments VALUES (1, ?, ?)', ('Unassigned', 'Historical comment'))
        self.conn.execute("INSERT INTO spikes(id, category, hook_thesis) VALUES ('legacy', 'rss', 'Original legacy idea')")
        self.conn.commit()

        def create(principal, key, title):
            return create_item(self.conn, principal, ItemCreate(title=title, destination='linkedin',
                format='linkedin_post'), request_id=key).body['item']

        first = create(self.a, 'a-create', 'Owned A')
        self.a_id = first['item_id']
        self.b_id = create(self.b, 'b-create', 'Owned B')['item_id']
        artifact = {'segments': ['  An exact approved draft\n']}
        saved = save_item(self.conn, self.a, self.a_id,
                          ItemPatch(expected_revision=1, artifact=artifact), request_id='a-save').body['item']
        digest = artifact_digest('linkedin', 'linkedin_post', ItemPatch(expected_revision=1, artifact=artifact).artifact)
        approved = approve_item(self.conn, self.a, self.a_id,
            ApproveRequest(expected_revision=saved['working_revision'], artifact_digest=digest, consent=True),
            request_id='a-approve').body
        self.version = approved['approval']['version_id']
        self.operation = begin_operation(self.conn, self.a, self.a_id, saved['working_revision'], 'generate', 'a-op')[0]

    def test_backup_restore_preserves_all_owned_and_legacy_data_across_restart(self):
        backup = self.root / 'backup.db'
        restored = self.root / 'restored.db'
        backup_report = backup_database(self.source, backup)
        self.assertEqual(backup_report['integrity'], 'ok')
        self.assertEqual(backup_report['foreign_key_violations'], 0)
        self.assertEqual(backup_report['tables']['legacy_comments'], 1)
        restored_report = rehearse_restore(backup, restored)
        self.assertEqual(backup_report['fingerprint'], restored_report['fingerprint'])
        # Open without init/migration to prove this is a restart from backed-up bytes.
        with closing(connect(restored, init=False)) as conn:
            self.assertEqual(conn.execute('SELECT text FROM legacy_comments').fetchone()[0], 'Historical comment')
            self.assertEqual(conn.execute('SELECT hook_thesis FROM spikes').fetchone()[0], 'Original legacy idea')
            self.assertEqual(get_item(conn, self.a, self.a_id).title, 'Owned A')
            self.assertEqual(get_item(conn, self.b, self.b_id).title, 'Owned B')
            with self.assertRaises(WorkflowError):
                get_item(conn, self.b, self.a_id)
            with self.assertRaises(WorkflowError):
                get_operation(conn, self.b, self.a_id, self.operation['operation_id'])
            operation = get_operation(conn, self.a, self.a_id, self.operation['operation_id'])
            self.assertEqual(operation['editorial_snapshot']['artifact']['segments'], ['  An exact approved draft\n'])
            self.assertEqual(export_version(conn, self.a, self.a_id, self.version).content, b'  An exact approved draft\n')
        self.assertEqual(inspect_database(backup)['fingerprint'], inspect_database(restored)['fingerprint'])

    def test_live_wal_backup_includes_committed_changes_only(self):
        self.conn.execute("INSERT INTO legacy_comments VALUES (2, 'Writer', 'committed WAL')")
        self.conn.commit()
        self.conn.execute("INSERT INTO legacy_comments VALUES (3, 'Writer', 'uncommitted')")
        backup = self.root / 'wal-backup.db'
        backup_database(self.source, backup)
        with closing(sqlite3.connect(backup)) as conn:
            self.assertEqual(conn.execute('SELECT text FROM legacy_comments ORDER BY id').fetchall(),
                             [('Historical comment',), ('committed WAL',)])
        self.conn.rollback()

    def test_wal_snapshot_is_self_contained_without_changing_source_journal_mode(self):
        backup = self.root / 'standalone.db'
        backup_database(self.source, backup)
        self.assertEqual(self.conn.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        with closing(sqlite3.connect(backup)) as copied:
            self.assertEqual(copied.execute('PRAGMA journal_mode').fetchone()[0], 'delete')
        self.assertFalse(list(self.root.glob('.cm-backup-*')))
        self.assertFalse((self.root / 'standalone.db-wal').exists())
        self.assertFalse((self.root / 'standalone.db-shm').exists())

    def test_destination_is_never_overwritten_and_source_is_never_created(self):
        target = self.root / 'existing.db'
        target.write_bytes(b'existing data')
        with self.assertRaises(RecoveryError):
            backup_database(self.source, target)
        self.assertEqual(target.read_bytes(), b'existing data')
        missing = self.root / 'missing.db'
        with self.assertRaises(RecoveryError):
            backup_database(missing, self.root / 'new.db')
        self.assertFalse(missing.exists())
        self.assertFalse((self.root / 'new.db').exists())

    def test_corrupt_or_foreign_key_invalid_database_fails_without_retaining_output(self):
        corrupt = self.root / 'corrupt.db'
        corrupt.write_bytes(b'not a sqlite database')
        with self.assertRaises(RecoveryError):
            backup_database(corrupt, self.root / 'bad-copy.db')
        self.assertFalse((self.root / 'bad-copy.db').exists())
        invalid = self.root / 'invalid-fk.db'
        with closing(sqlite3.connect(invalid)) as conn, conn:
            conn.executescript('CREATE TABLE parent (id INTEGER PRIMARY KEY);'
                               'CREATE TABLE child (parent_id INTEGER REFERENCES parent(id));'
                               'INSERT INTO child VALUES (7);')
        with self.assertRaises(RecoveryError):
            backup_database(invalid, self.root / 'invalid-copy.db')
        self.assertFalse((self.root / 'invalid-copy.db').exists())

    def test_restore_mismatch_does_not_delete_a_replacement_file(self):
        backup = self.root / 'backup.db'
        destination = self.root / 'restore.db'
        backup_database(self.source, backup)
        real_backup = recovery._backup
        def replace_after_backup(source, target):
            result, identity = real_backup(source, target)
            destination.unlink()
            destination.write_bytes(b'concurrent replacement')
            result['fingerprint'] = 'different'
            return result, identity
        with patch.object(recovery, '_backup', side_effect=replace_after_backup):
            with self.assertRaises(RecoveryError):
                rehearse_restore(backup, destination)
        self.assertEqual(destination.read_bytes(), b'concurrent replacement')

    def test_destination_created_during_backup_is_never_overwritten(self):
        destination = self.root / 'race.db'
        real_open = recovery._open_readonly
        def open_source(path):
            if Path(path) == self.source:
                destination.write_bytes(b'concurrent file')
            return real_open(path)
        with patch.object(recovery, '_open_readonly', side_effect=open_source):
            with self.assertRaises(RecoveryError):
                backup_database(self.source, destination)
        self.assertEqual(destination.read_bytes(), b'concurrent file')
