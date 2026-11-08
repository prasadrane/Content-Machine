"""Explicit local attachment recovery data, separate from editorial approval.

Callers select a quiescent, trusted local directory and private destination;
there is no storage discovery, ownership assignment, or database transaction.
Hashes detect corruption, not an attacker replacing both manifest and payload.
Concurrent hostile filesystem mutation and power-loss durability are outside
this offline rehearsal's contract. Handled failures remove private staging;
an uncatchable process termination may leave staging, never a partial target.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile


class AttachmentRecoveryError(RuntimeError):
    """An explicit attachment directory could not be safely copied or verified."""


def _checked(path: Path) -> os.stat_result:
    """Reject symlinks and all Windows reparse points, including junctions."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise AttachmentRecoveryError('Links and reparse points are not recovery inputs')
    return info


def _absolute(path: str | Path) -> Path:
    requested = Path(path)
    # Reject dot components before normalizing, including destination '..'.
    if requested.drive.startswith('\\\\'):
        raise AttachmentRecoveryError('UNC and device namespace paths are not local recovery inputs')
    for component in requested.parts:
        if component != requested.anchor:
            _relative(component)
    result = Path(os.path.abspath(requested))
    for ancestor in reversed((result, *result.parents)):
        if ancestor.exists() or ancestor.is_symlink():
            _checked(ancestor)
    return result


def _directory(path: str | Path) -> Path:
    result = _absolute(path)
    if not stat.S_ISDIR(_checked(result).st_mode):
        raise AttachmentRecoveryError('Expected an existing directory')
    return result


def _overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _destination(path: str | Path, *protected: Path) -> Path:
    result = _absolute(path)
    _directory(result.parent)
    if result.exists() or result.is_symlink():
        raise AttachmentRecoveryError('Destination already exists')
    if any(_overlap(result, other) for other in protected):
        raise AttachmentRecoveryError('Destination overlaps source or recovery bundle')
    return result


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or '\\' in value:
        raise AttachmentRecoveryError('Unsafe relative attachment path')
    parts = value.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                *(f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in '123456789\u00b9\u00b2\u00b3')}
    if PurePosixPath(value).is_absolute() or any(
        part in {'', '.', '..'} or part.endswith((' ', '.'))
        or re.search(r'[\x00-\x1f<>:"|?*]', part)
        or part.split('.')[0].upper() in reserved for part in parts
    ):
        raise AttachmentRecoveryError('Unsafe relative attachment path')
    return value


def _read_file(path: Path, target: Path | None = None) -> tuple[int, str]:
    before = _checked(path)
    if not stat.S_ISREG(before.st_mode):
        raise AttachmentRecoveryError('Only regular attachment files are supported')
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as source:
        opened = os.fstat(source.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise AttachmentRecoveryError('Attachment changed while opening')
        output = target.open('xb') if target else None
        try:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
                if output:
                    output.write(chunk)
            if output:
                output.flush()
                os.fsync(output.fileno())
        finally:
            if output:
                output.close()
        after = os.fstat(source.fileno())
    if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise AttachmentRecoveryError('Attachment changed while reading')
    return size, 'sha256:' + digest.hexdigest()


def _inventory(root: Path) -> tuple[list[str], list[dict]]:
    directories, files = [], []
    def visit(directory):
        for child in sorted(directory.iterdir()):
            info = _checked(child)
            name = _relative(child.relative_to(root).as_posix())
            if stat.S_ISDIR(info.st_mode):
                directories.append(name)
                visit(child)
            elif stat.S_ISREG(info.st_mode):
                size, digest = _read_file(child)
                files.append({'path': name, 'size': size, 'sha256': digest})
            else:
                raise AttachmentRecoveryError('Unsupported filesystem entry')
    visit(root)
    return sorted(directories), sorted(files, key=lambda item: item['path'])


def _fingerprint(manifest: dict) -> str:
    body = {key: value for key, value in manifest.items() if key != 'fingerprint'}
    return 'sha256:' + hashlib.sha256(json.dumps(
        body, sort_keys=True, ensure_ascii=True, separators=(',', ':')
    ).encode('ascii')).hexdigest()


def _validate(manifest: dict) -> Path:
    if (not isinstance(manifest, dict) or manifest.get('schema_version') != 1
            or manifest.get('kind') != 'attachment-recovery-data'
            or manifest.get('editorial_approval') is not False
            or manifest.get('fingerprint') != _fingerprint(manifest)):
        raise AttachmentRecoveryError('Invalid recovery manifest or fingerprint')
    source = manifest.get('source_root')
    if (not isinstance(source, str) or not Path(source).is_absolute()
            or Path(source).drive.startswith('\\\\') or '..' in Path(source).parts):
        raise AttachmentRecoveryError('Invalid source directory in manifest')
    for component in Path(source).parts:
        if component != Path(source).anchor:
            _relative(component)
    directories, files = manifest.get('directories'), manifest.get('files')
    if not isinstance(directories, list) or not isinstance(files, list):
        raise AttachmentRecoveryError('Invalid attachment inventory')
    names = [_relative(name) for name in directories]
    for entry in files:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'size', 'sha256'}
                or type(entry['size']) is not int or entry['size'] < 0
                or not isinstance(entry['sha256'], str)
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', entry['sha256'])):
            raise AttachmentRecoveryError('Invalid attachment entry')
        names.append(_relative(entry['path']))
    if len({name.casefold() for name in names}) != len(names):
        raise AttachmentRecoveryError('Duplicate or ambiguous attachment paths')
    return Path(os.path.abspath(source))


def inspect_attachment_bundle(bundle_path: str | Path) -> dict:
    """Validate manifest paths, complete inventory and exact payload byte hashes."""
    try:
        bundle = _directory(bundle_path)
        if {path.name for path in bundle.iterdir()} != {'manifest.json', 'files'}:
            raise AttachmentRecoveryError('Unexpected recovery bundle entries')
        _read_file(bundle / 'manifest.json')
        manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
        _validate(manifest)
        directories, files = _inventory(_directory(bundle / 'files'))
        if directories != manifest['directories'] or files != manifest['files']:
            raise AttachmentRecoveryError('Attachment inventory or byte hash mismatch')
        return manifest
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise AttachmentRecoveryError('Attachment bundle could not be verified') from exc


def _copy_file(source: Path, destination: Path) -> None:
    _read_file(source, destination)


def _copy_inventory(source: Path, destination: Path, manifest: dict) -> None:
    for relative in manifest['directories']:
        (destination / relative).mkdir(parents=True, exist_ok=True)
    for entry in manifest['files']:
        target = destination / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        _copy_file(source / entry['path'], target)
    if _inventory(destination) != (manifest['directories'], manifest['files']):
        raise AttachmentRecoveryError('Copied attachments failed verification')


def _publish(staged: Path, destination: Path) -> None:
    # Windows rename is atomic and never replaces any existing entry. On other
    # platforms fail closed unless the native no-replace operation is available.
    _directory(destination.parent)
    if os.name == 'nt':
        os.rename(staged, destination)
    else:
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        if rename is None:
            raise AttachmentRecoveryError('Exclusive directory publication is unsupported')
        if rename(-100, os.fsencode(staged), -100, os.fsencode(destination), 1):
            raise OSError(ctypes.get_errno(), 'Exclusive directory publication failed')


def backup_attachments(source_path: str | Path, destination_path: str | Path) -> dict:
    """Copy one explicit directory to a NEW verified local recovery bundle."""
    staged = None
    try:
        source = _directory(source_path)
        destination = _destination(destination_path, source)
        directories, files = _inventory(source)
        manifest = {'schema_version': 1, 'kind': 'attachment-recovery-data',
                    'editorial_approval': False, 'source_root': str(source),
                    'directories': directories, 'files': files}
        manifest['fingerprint'] = _fingerprint(manifest)
        staged = Path(tempfile.mkdtemp(prefix='.cm-attachments-', dir=destination.parent))
        payload = staged / 'files'
        payload.mkdir()
        _copy_inventory(source, payload, manifest)
        if _inventory(source) != (directories, files):
            raise AttachmentRecoveryError('Source attachments changed during backup')
        with (staged / 'manifest.json').open('x', encoding='utf-8') as output:
            json.dump(manifest, output, ensure_ascii=True, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        inspect_attachment_bundle(staged)
        _publish(staged, destination)
        return manifest
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise AttachmentRecoveryError('Attachment backup could not be completed') from exc
    finally:
        if staged is not None and staged.exists():
            shutil.rmtree(staged)


def rehearse_attachment_restore(bundle_path: str | Path, destination_path: str | Path) -> dict:
    """Verify a recovery bundle, then restore exact bytes to a NEW directory."""
    staged = None
    try:
        bundle = _directory(bundle_path)
        manifest = inspect_attachment_bundle(bundle)
        source = _validate(manifest)
        destination = _destination(destination_path, bundle, source)
        staged = Path(tempfile.mkdtemp(prefix='.cm-attachments-', dir=destination.parent))
        _copy_inventory(bundle / 'files', staged, manifest)
        if inspect_attachment_bundle(bundle) != manifest:
            raise AttachmentRecoveryError('Recovery bundle changed during restore')
        _publish(staged, destination)
        return manifest
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise AttachmentRecoveryError('Attachment restore could not be completed') from exc
    finally:
        if staged is not None and staged.exists():
            shutil.rmtree(staged)
