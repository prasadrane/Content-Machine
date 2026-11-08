"""Explicit local SQLite backup and restore rehearsal, without migration."""
from __future__ import annotations

import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


class RecoveryError(RuntimeError):
    """The selected database cannot be safely copied or verified."""


def _source(path: str | Path) -> Path:
    try:
        source = Path(path).resolve(strict=True)
        if not source.is_file():
            raise OSError('not a regular file')
        return source
    except (OSError, TypeError, ValueError):
        raise RecoveryError('Source database is unavailable') from None


def _open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)


def _value(value):
    if isinstance(value, bytes):
        return ['blob', base64.b64encode(value).decode('ascii')]
    if isinstance(value, float):
        return ['float', value.hex()]
    if isinstance(value, int):
        return ['integer', str(value)]
    if value is None:
        return ['null']
    if isinstance(value, str):
        return ['text', value]
    raise RecoveryError('Database contains an unsupported value')


def _inspect(conn: sqlite3.Connection) -> dict:
    conn.execute('BEGIN')
    try:
        integrity = conn.execute('PRAGMA integrity_check').fetchall()
        if integrity != [('ok',)]:
            raise RecoveryError('Database integrity verification failed')
        violations = conn.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise RecoveryError('Database foreign-key verification failed')
        objects = conn.execute(
            'SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name'
        ).fetchall()
        digest = hashlib.sha256()
        def include(value):
            encoded = json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode('ascii')
            digest.update(len(encoded).to_bytes(8, 'big'))
            digest.update(encoded)
        include(objects)
        include([conn.execute('PRAGMA user_version').fetchone()[0],
                 conn.execute('PRAGMA application_id').fetchone()[0],
                 conn.execute('PRAGMA encoding').fetchone()[0]])
        tables = {}
        for object_type, name, _, _ in objects:
            if object_type != 'table':
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            rows = []
            for row in conn.execute(f'SELECT * FROM {quoted}'):
                raw = json.dumps([_value(value) for value in row], ensure_ascii=True,
                                 separators=(',', ':')).encode('ascii')
                rows.append(hashlib.sha256(raw).hexdigest())
            rows.sort()
            tables[name] = len(rows)
            include([name, rows])
        return {'integrity': 'ok', 'foreign_key_violations': 0,
                'tables': tables, 'fingerprint': 'sha256:' + digest.hexdigest()}
    finally:
        conn.rollback()


def inspect_database(path: str | Path) -> dict:
    """Inspect an existing database through a read-only connection."""
    try:
        with closing(_open_readonly(_source(path))) as conn:
            return _inspect(conn)
    except RecoveryError:
        raise
    except (sqlite3.Error, OSError, ValueError):
        raise RecoveryError('Database could not be verified') from None


def _destination(path: str | Path) -> Path:
    try:
        requested = Path(path)
        if requested.name in {'', '.', '..'}:
            raise ValueError('destination has no filename')
        return requested.parent.resolve(strict=True) / requested.name
    except (OSError, TypeError, ValueError):
        raise RecoveryError('Destination directory is unavailable') from None


def _remove_owned(path: Path, identity: tuple[int, int]) -> None:
    try:
        stat = path.stat(follow_symlinks=False)
        if (stat.st_dev, stat.st_ino) == identity:
            path.unlink()
    except FileNotFoundError:
        pass


def _backup(source_path: str | Path, destination_path: str | Path) -> tuple[dict, tuple[int, int]]:
    source = _source(source_path)
    destination = _destination(destination_path)
    try:
        fd, temporary = tempfile.mkstemp(prefix='.cm-backup-', suffix='.sqlite', dir=destination.parent)
    except OSError:
        raise RecoveryError('Temporary backup could not be created') from None
    staged = Path(temporary)
    try:
        stat = os.fstat(fd)
    finally:
        os.close(fd)
    identity = (stat.st_dev, stat.st_ino)
    try:
        with closing(_open_readonly(source)) as original, closing(sqlite3.connect(staged)) as target:
            original.backup(target)
            # Only the new snapshot changes journal mode. This makes it a
            # self-contained file and prevents inspection from leaving WAL/SHM
            # sidecars named after the private temporary file.
            if target.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                raise RecoveryError('Backup snapshot could not be made self-contained')
        report = inspect_database(staged)
        # A hard link publishes atomically and fails if any destination entry
        # exists. Never open the caller's destination as an SQLite target.
        os.link(staged, destination)
        return report, identity
    except Exception as exc:
        if isinstance(exc, RecoveryError):
            raise
        raise RecoveryError('Database backup could not be completed') from None
    finally:
        _remove_owned(staged, identity)


def backup_database(source_path: str | Path, destination_path: str | Path) -> dict:
    """Create a new, verified SQLite snapshot at an explicit destination."""
    result, _ = _backup(source_path, destination_path)
    return result


def rehearse_restore(backup_path: str | Path, destination_path: str | Path) -> dict:
    """Restore to a separate new file and compare its content to the backup."""
    before = inspect_database(backup_path)
    destination = _destination(destination_path)
    restored, identity = _backup(backup_path, destination)
    if before['fingerprint'] != restored['fingerprint']:
        # The output was created by this call; remove it only if still the same file.
        _remove_owned(destination, identity)
        raise RecoveryError('Restored database differs from the verified backup')
    return restored
