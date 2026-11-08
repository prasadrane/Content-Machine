"""Attachment recovery uses explicit disposable directories, never user storage."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from content_machine.workflow import attachment_recovery as recovery


class AttachmentRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cm-attachment-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'attachments'
        self.source.mkdir()
        (self.source / 'nested').mkdir()
        (self.source / 'empty').mkdir()
        (self.source / 'nested' / 'binary.bin').write_bytes(bytes(range(256)) + b'\x00\xff')
        (self.source / 'notes.txt').write_bytes(b'Exact text\r\nNo rewriting.\n')
        self.bundle = self.root / 'backup'
        self.restored = self.root / 'restored'

    def backup(self):
        return recovery.backup_attachments(self.source, self.bundle)

    def test_exact_nested_bytes_names_and_empty_directories_roundtrip(self):
        report = self.backup()
        self.assertEqual(report['kind'], 'attachment-recovery-data')
        self.assertIs(report['editorial_approval'], False)
        self.assertEqual(report, recovery.inspect_attachment_bundle(self.bundle))
        self.assertEqual(report, recovery.rehearse_attachment_restore(self.bundle, self.restored))
        for relative in ['notes.txt', 'nested/binary.bin']:
            self.assertEqual((self.source / relative).read_bytes(), (self.restored / relative).read_bytes())
        self.assertTrue((self.restored / 'empty').is_dir())

    def test_existing_destinations_and_source_overlap_are_rejected(self):
        self.backup()
        original = (self.bundle / 'manifest.json').read_bytes()
        with self.assertRaises(recovery.AttachmentRecoveryError):
            self.backup()
        self.assertEqual((self.bundle / 'manifest.json').read_bytes(), original)
        self.restored.mkdir()
        for destination in [self.restored, self.source, self.source / 'nested' / 'new',
                            self.bundle / 'new']:
            with self.subTest(destination=destination), self.assertRaises(recovery.AttachmentRecoveryError):
                recovery.rehearse_attachment_restore(self.bundle, destination)
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.backup_attachments(self.source, self.source / 'new')

    def test_corrupt_payload_and_unlisted_files_fail_without_restore(self):
        self.backup()
        (self.bundle / 'files' / 'notes.txt').write_bytes(b'Changed')
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.rehearse_attachment_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())

    def test_extra_payload_is_rejected(self):
        self.backup()
        (self.bundle / 'files' / 'extra').write_bytes(b'unlisted')
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.inspect_attachment_bundle(self.bundle)

    def test_manifest_tampering_and_traversal_are_rejected(self):
        self.backup()
        path = self.bundle / 'manifest.json'
        original = json.loads(path.read_text())
        for name in ['../outside', '/absolute', 'C:/escape', 'nested\\escape',
                     'nested/../escape', 'notes.txt:stream', 'CON', 'trailing.',
                     '//server/share', 'nested/trailing ', 'COM\u00b9.txt']:
            tampered = json.loads(json.dumps(original))
            tampered['files'][0]['path'] = name
            # Even a self-consistent manifest must not authorize unsafe paths.
            tampered['fingerprint'] = recovery._fingerprint(tampered)
            path.write_text(json.dumps(tampered))
            with self.subTest(path=name), self.assertRaises(recovery.AttachmentRecoveryError):
                recovery.rehearse_attachment_restore(self.bundle, self.restored)
            self.assertFalse(self.restored.exists())
        path.write_text(json.dumps(original).replace('sha256:', 'broken:', 1))
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.inspect_attachment_bundle(self.bundle)

    def test_backup_and_restore_interruption_cleanup_and_preservation(self):
        original = (self.source / 'notes.txt').read_bytes()
        with patch.object(recovery, '_copy_file', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.backup()
        self.assertFalse(self.bundle.exists())
        self.assertFalse(list(self.root.glob('.cm-attachments-*')))
        self.backup()
        backup_bytes = (self.bundle / 'manifest.json').read_bytes()
        with patch.object(recovery, '_copy_file', side_effect=OSError('interrupted')):
            with self.assertRaises(recovery.AttachmentRecoveryError):
                recovery.rehearse_attachment_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())
        self.assertFalse(list(self.root.glob('.cm-attachments-*')))
        self.assertEqual((self.bundle / 'manifest.json').read_bytes(), backup_bytes)
        self.assertEqual((self.source / 'notes.txt').read_bytes(), original)

    def test_publish_failure_leaves_new_destination_absent(self):
        with patch.object(recovery, '_publish', side_effect=OSError('rename failed')):
            with self.assertRaises(recovery.AttachmentRecoveryError):
                self.backup()
        self.assertFalse(self.bundle.exists())
        self.assertFalse(list(self.root.glob('.cm-attachments-*')))

    def test_destination_created_at_publish_is_not_overwritten(self):
        publish = recovery._publish
        def race(staged, destination):
            destination.mkdir()
            (destination / 'previous').write_bytes(b'preserve')
            publish(staged, destination)
        with patch.object(recovery, '_publish', side_effect=race):
            with self.assertRaises(recovery.AttachmentRecoveryError):
                self.backup()
        self.assertEqual((self.bundle / 'previous').read_bytes(), b'preserve')
        self.assertFalse((self.bundle / 'manifest.json').exists())
        self.assertFalse(list(self.root.glob('.cm-attachments-*')))

    def test_self_consistent_duplicate_and_casefold_paths_are_rejected(self):
        self.backup()
        path = self.bundle / 'manifest.json'
        original = json.loads(path.read_text())
        for name in ['notes.txt', 'NOTES.TXT']:
            manifest = json.loads(json.dumps(original))
            manifest['files'].append({**manifest['files'][-1], 'path': name})
            manifest['fingerprint'] = recovery._fingerprint(manifest)
            path.write_text(json.dumps(manifest))
            with self.subTest(path=name), self.assertRaises(recovery.AttachmentRecoveryError):
                recovery.rehearse_attachment_restore(self.bundle, self.restored)
            self.assertFalse(self.restored.exists())

    def test_changed_source_during_copy_is_not_published(self):
        copy = recovery._copy_file
        def mutate(source, target):
            copy(source, target)
            source.write_bytes(b'changed during copy')
        with patch.object(recovery, '_copy_file', side_effect=mutate):
            with self.assertRaises(recovery.AttachmentRecoveryError):
                self.backup()
        self.assertFalse(self.bundle.exists())
        self.assertFalse(list(self.root.glob('.cm-attachments-*')))

    def test_empty_directory_bundle_restores_without_source_present(self):
        for entry in (self.source / 'nested').iterdir():
            entry.unlink()
        (self.source / 'nested').rmdir()
        (self.source / 'empty').rmdir()
        (self.source / 'notes.txt').unlink()
        self.backup()
        self.source.rmdir()
        recovery.rehearse_attachment_restore(self.bundle, self.restored)
        self.assertEqual(list(self.restored.iterdir()), [])

    def test_device_and_unc_source_paths_are_rejected_before_read(self):
        for path in ['\\\\?\\C:\\attachments', '\\\\server\\share\\attachments']:
            with self.subTest(path=path), self.assertRaises(recovery.AttachmentRecoveryError):
                recovery.backup_attachments(path, self.bundle)

    def test_source_and_bundle_symlinks_are_rejected_when_supported(self):
        link = self.source / 'linked'
        try:
            link.symlink_to(self.source / 'notes.txt')
        except OSError:
            self.skipTest('Symlink creation unavailable on this Windows account')
        with self.assertRaises(recovery.AttachmentRecoveryError):
            self.backup()
        link.unlink()
        self.backup()
        payload = self.bundle / 'files' / 'notes.txt'
        payload.unlink()
        payload.symlink_to(self.source / 'notes.txt')
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.rehearse_attachment_restore(self.bundle, self.restored)
        self.assertFalse(self.restored.exists())

    def test_destination_parent_symlink_is_rejected_when_supported(self):
        link = self.root / 'alias'
        try:
            link.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest('Directory symlink creation unavailable')
        with self.assertRaises(recovery.AttachmentRecoveryError):
            recovery.backup_attachments(self.source, link / 'backup')


if __name__ == '__main__':
    unittest.main()
