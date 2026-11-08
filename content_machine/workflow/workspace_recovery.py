"""Verified DB-plus-attachments recovery for an explicitly quiescent local app.

Inputs and destinations are explicit; no discovery, migration or owner mapping
occurs. A SQLite write reservation excludes database writers during capture.
The caller must stop attachment writers. Inventories detect incidental changes,
not malicious replacement or change-and-revert races. Private staging is
published as one new directory only after both parts verify. This is not hosted
PITR, an online filesystem snapshot, or a claim of editorial approval.
"""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from content_machine.workflow import attachment_recovery as attachments
from content_machine.workflow.attachment_recovery import backup_attachments, rehearse_attachment_restore
from content_machine.workflow.recovery import backup_database, inspect_database, rehearse_restore


class WorkspaceRecoveryError(RuntimeError):
    """A combined local bundle could not be safely captured or restored."""


def _database(path):
    result = attachments._absolute(path)
    attachments._read_file(result)
    return result


def _manifest(path):
    attachments._read_file(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {
            'schema_version', 'kind', 'editorial_approval', 'source_database',
            'database_fingerprint', 'attachments_fingerprint', 'fingerprint'}
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or data['kind'] != 'workspace-recovery-data'
            or data['editorial_approval'] is not False
            or data['fingerprint'] != attachments._fingerprint(data)
            or not isinstance(data['source_database'], str)
            or not Path(data['source_database']).is_absolute()):
        raise WorkspaceRecoveryError('Invalid combined recovery manifest')
    return data


def inspect_workspace_bundle(bundle_path):
    """Verify the exact bundle inventory, database state and attachment hashes."""
    try:
        bundle = attachments._directory(bundle_path)
        if {entry.name for entry in bundle.iterdir()} != {'manifest.json', 'workflow.sqlite', 'attachments'}:
            raise WorkspaceRecoveryError('Unexpected combined bundle entries')
        report = _manifest(bundle / 'manifest.json')
        database = inspect_database(_database(bundle / 'workflow.sqlite'))
        files = attachments.inspect_attachment_bundle(bundle / 'attachments')
        if (database['fingerprint'] != report['database_fingerprint']
                or files['fingerprint'] != report['attachments_fingerprint']):
            raise WorkspaceRecoveryError('Combined recovery fingerprint mismatch')
        return report
    except WorkspaceRecoveryError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error) as exc:
        raise WorkspaceRecoveryError('Combined recovery bundle could not be verified') from exc


def _cleanup(staged):
    # Only remove the private directory allocated by this invocation. Publication
    # moves it away; a concurrently created caller destination is never removed.
    if staged is not None and staged.exists():
        if not staged.name.startswith('.cm-workspace-'):
            raise WorkspaceRecoveryError('Unexpected staging directory')
        attachments._directory(staged)
        shutil.rmtree(staged)


def backup_workspace(database_path, attachment_path, destination_path, *, quiescent=False):
    """Capture a NEW unapproved recovery bundle after the app has stopped writing."""
    staged = None
    try:
        if quiescent is not True:
            raise WorkspaceRecoveryError('Explicit quiescent application confirmation is required')
        database = _database(database_path)
        source = attachments._directory(attachment_path)
        if attachments._overlap(database, source):
            raise WorkspaceRecoveryError('Database and attachment inputs must be separate')
        destination = attachments._destination(destination_path, database, source)
        # mode=rw never creates a missing source; BEGIN IMMEDIATE blocks other
        # database writers while the separate readonly backup connection works.
        with closing(sqlite3.connect(database.as_uri() + '?mode=rw', uri=True, timeout=1)) as lock:
            lock.execute('BEGIN IMMEDIATE')
            try:
                before = inspect_database(database)
                inventory = attachments._inventory(source)
                staged = Path(tempfile.mkdtemp(prefix='.cm-workspace-', dir=destination.parent))
                captured = backup_database(database, staged / 'workflow.sqlite')
                files = backup_attachments(source, staged / 'attachments')
                if (captured['fingerprint'] != before['fingerprint']
                        or inspect_database(database)['fingerprint'] != before['fingerprint']
                        or attachments._inventory(source) != inventory):
                    raise WorkspaceRecoveryError('Workspace changed during capture')
                report = {'schema_version': 1, 'kind': 'workspace-recovery-data',
                          'editorial_approval': False, 'source_database': str(database),
                          'database_fingerprint': captured['fingerprint'],
                          'attachments_fingerprint': files['fingerprint']}
                report['fingerprint'] = attachments._fingerprint(report)
                with (staged / 'manifest.json').open('x', encoding='utf-8') as output:
                    json.dump(report, output, ensure_ascii=True, sort_keys=True)
                    output.flush()
                    os.fsync(output.fileno())
                inspect_workspace_bundle(staged)
                attachments._publish(staged, destination)
                return report
            finally:
                lock.rollback()
    except WorkspaceRecoveryError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error) as exc:
        raise WorkspaceRecoveryError('Combined workspace backup could not be completed') from exc
    finally:
        _cleanup(staged)


def rehearse_workspace_restore(bundle_path, destination_path):
    """Restore both verified parts to one NEW directory, never the live inputs."""
    staged = None
    try:
        bundle = attachments._directory(bundle_path)
        report = inspect_workspace_bundle(bundle)
        files = attachments.inspect_attachment_bundle(bundle / 'attachments')
        source = Path(files['source_root'])
        destination = attachments._destination(destination_path, bundle, Path(report['source_database']), source)
        staged = Path(tempfile.mkdtemp(prefix='.cm-workspace-', dir=destination.parent))
        database = rehearse_restore(bundle / 'workflow.sqlite', staged / 'workflow.sqlite')
        rehearse_attachment_restore(bundle / 'attachments', staged / 'attachments')
        if (database['fingerprint'] != report['database_fingerprint']
                or attachments._inventory(staged / 'attachments') != (files['directories'], files['files'])
                or inspect_workspace_bundle(bundle) != report):
            raise WorkspaceRecoveryError('Workspace changed during restore')
        attachments._publish(staged, destination)
        return report
    except WorkspaceRecoveryError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error) as exc:
        raise WorkspaceRecoveryError('Combined workspace restore could not be completed') from exc
    finally:
        _cleanup(staged)
