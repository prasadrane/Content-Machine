"""Backup-first local operator import. No database, owner or source discovery.

Stop the application and filesystem writers before using --quiescent. Select an
existing workflow SQLite database, JSON record list, explicit JSON owner mapping,
source namespace and NEW backup path. The backup is retained even when import
fails. Historical approval assertions are never turned into current approval.
This command is not a hosted migration, credential reader or public API.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.legacy_import import initialize_import_schema, import_legacy_records
from content_machine.workflow.recovery import backup_database
from content_machine.workflow.schemas import Principal

MAX_INPUT_BYTES = 20_000_000


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object keys are ambiguous')
        result[key] = value
    return result


def _read_json(path):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('Explicit input file exceeds supported size')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Existing local workflow SQLite database')
    parser.add_argument('--records', required=True, help='Explicit JSON list matching LegacyRecord')
    parser.add_argument('--owners', required=True, help='JSON object: actual legacy ID to confirmed owner ID')
    parser.add_argument('--namespace', required=True, help='Stable identifier for this reviewed source export')
    parser.add_argument('--backup', required=True, help='New SQLite backup file; never overwritten')
    parser.add_argument('--quiescent', action='store_true', required=True,
                        help='Confirm application and attachment writers are stopped')
    parser.add_argument('--confirm-import', action='store_true', required=True,
                        help='Confirm creating mapped, unapproved items and quarantined archive records')
    args = parser.parse_args(argv)
    record = {'success': False, 'backup_created': False}
    try:
        database = Path(args.database).resolve(strict=True)
        if not database.is_file():
            raise ValueError('Expected an existing local SQLite file')
        records, supplied_owners = _read_json(args.records), _read_json(args.owners)
        if not isinstance(supplied_owners, dict):
            raise ValueError('Owner mapping must be a JSON object')
        owners = {}
        for legacy_id, owner_id in supplied_owners.items():
            if not isinstance(legacy_id, str) or not isinstance(owner_id, str):
                raise ValueError('Owner mapping keys and values must be strings')
            owners[legacy_id] = Principal(owner_id=owner_id, mode='trusted_local')
        with closing(connect(database, init=False)) as conn:
            # Block database writers before taking the rollback baseline. The
            # readonly SQLite backup connection can read while this reservation
            # is held, before any source mutation has begun.
            conn.execute('BEGIN IMMEDIATE')
            try:
                backup = backup_database(database, args.backup)
                record.update(backup_created=True, backup_fingerprint=backup['fingerprint'])
                initialize_import_schema(conn)
                results = import_legacy_records(conn, args.namespace, records, owner_mapping=owners)
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
        counts = {'imported': 0, 'synthetic_quarantined': 0, 'unknown_quarantined': 0}
        for result in results:
            counts[result['state']] += 1
        record.update(success=True, counts=counts, historical_approval='unknown')
    except WorkflowError as exc:
        record['code'] = exc.code
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        record['code'] = 'legacy_import_failed'
    print(json.dumps(record))
    return 0 if record['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
