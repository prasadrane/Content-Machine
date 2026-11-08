"""Receipt schema and inert source-archive validation for guest copies."""
import hashlib
import json

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import canonical_json

TABLES = ('workflow_items', 'workflow_versions', 'workflow_approvals', 'workflow_operations',
          'workflow_reviews', 'workflow_operation_inputs', 'workflow_idempotency',
          'workflow_profiles', 'workflow_sources', 'workflow_preferences',
          'workflow_preference_events', 'workflow_discovery_cache', 'workflow_guest_examples')
MAX_ARCHIVE_BYTES = 8_000_000
MAX_ITEMS = 1000
OPTIONAL_TABLES = ('workflow_legacy_imports',)
TRANSFER_MIGRATION_STATEMENTS = (
    '''CREATE TABLE IF NOT EXISTS workflow_guest_transfers (
       transfer_id TEXT PRIMARY KEY, source_owner_id TEXT NOT NULL, destination_owner_id TEXT NOT NULL,
       request_id TEXT NOT NULL, source_fingerprint TEXT NOT NULL, policy TEXT NOT NULL,
       archive_json TEXT NOT NULL, response_json TEXT NOT NULL, created_at TEXT NOT NULL,
       UNIQUE(transfer_id,destination_owner_id),
       UNIQUE(source_owner_id,destination_owner_id,request_id),
       UNIQUE(source_owner_id,destination_owner_id),
       CHECK(source_owner_id <> destination_owner_id))''',
    '''CREATE TABLE IF NOT EXISTS workflow_guest_transfer_items (
       transfer_id TEXT NOT NULL, source_item_id TEXT NOT NULL, target_item_id TEXT NOT NULL,
       destination_owner_id TEXT NOT NULL, context_mapping_json TEXT NOT NULL, example_label TEXT,
       PRIMARY KEY(transfer_id,source_item_id), UNIQUE(target_item_id,destination_owner_id),
       FOREIGN KEY(transfer_id,destination_owner_id) REFERENCES workflow_guest_transfers(transfer_id,destination_owner_id),
       FOREIGN KEY(target_item_id,destination_owner_id) REFERENCES workflow_items(item_id,owner_id))''',
    *tuple(f'''CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}
          BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Transfer receipts are immutable'); END'''
           for table in ('workflow_guest_transfers', 'workflow_guest_transfer_items') for action in ('UPDATE', 'DELETE')),
)


def fingerprint(archive):
    return 'sha256:' + hashlib.sha256(canonical_json(archive).encode('utf-8')).hexdigest()


def _table_columns(conn):
    if getattr(conn, 'dialect', None) == 'postgresql':
        # Trusted server connection and schema only. Catalog names are never
        # interpolated into archive queries; those use the fixed allowlist.
        rows = conn._driver(conn._raw.execute, '''SELECT c.relname,a.attname
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid
            WHERE n.nspname=current_schema() AND c.relkind IN ('r','p')
              AND c.relname LIKE 'workflow_%' AND a.attnum>0 AND NOT a.attisdropped''').fetchall()
        columns = {}
        for table, column in rows:
            columns.setdefault(table, set()).add(column)
        return columns
    present = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'workflow_%'")}
    return {table: {entry[1] for entry in conn.execute('PRAGMA table_info("' + table.replace('"', '""') + '")')}
            for table in present}


def capture(conn, owner):
    # Refuse silently dropping a future owner-scoped workflow table. Transfer
    # receipt tables are provenance for earlier copies, not native source work.
    excluded = {'workflow_guest_transfers', 'workflow_guest_transfer_items'}
    present = _table_columns(conn)
    for table, columns in present.items():
        if table not in TABLES and table not in OPTIONAL_TABLES and table not in excluded:
            if 'owner_id' in columns:
                raise WorkflowError(409, 'transfer_unsupported_history', 'Workspace history needs an updated transfer adapter.')
    tables = {}
    for table in (*TABLES, *(table for table in OPTIONAL_TABLES if table in present)):
        rows = [dict(row) for row in conn.execute(f'SELECT * FROM {table} WHERE owner_id=?', (owner,))]
        tables[table] = sorted(rows, key=canonical_json)
    if len(tables['workflow_items']) > MAX_ITEMS:
        raise WorkflowError(413, 'transfer_too_large', 'Guest workspace exceeds the transfer item limit.')
    if any(row['state'] == 'pending' for row in tables['workflow_operations']):
        raise WorkflowError(409, 'guest_operations_pending', 'Finish or explicitly abandon pending AI work before copying.')
    archive = {'schema_version': 1, 'source_owner_id': owner, 'tables': tables}
    if len(canonical_json(archive).encode('utf-8')) > MAX_ARCHIVE_BYTES:
        raise WorkflowError(413, 'transfer_too_large', 'Guest workspace exceeds the recovery archive size limit.')
    # Foreign keys verify typed relational edges. Archived JSON remains exact;
    # only known operation identity fields are validated, never substituted.
    if getattr(conn, 'dialect', None) == 'postgresql':
        # Enforce any deferred relations before issuing a successful receipt.
        conn._driver(conn._raw.execute, 'SET CONSTRAINTS ALL IMMEDIATE')
    elif conn.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise WorkflowError(409, 'transfer_invalid_history', 'Workspace references need repair before copying.')
    operations = {row['operation_id']: row for row in tables['workflow_operations']}
    for row in tables['workflow_operation_inputs']:
        try:
            snapshot = json.loads(row['editorial_snapshot_json'])
            operation = operations.get(row['operation_id'])
            valid = (operation is not None and snapshot['owner_id'] == owner
                     and snapshot['item_id'] == operation['item_id']
                     and snapshot['version_id'] == operation['input_version_id'])
        except (ValueError, TypeError, KeyError):
            valid = False
        if not valid:
            raise WorkflowError(409, 'transfer_invalid_history', 'Operation history does not match its recorded owner.')
    return archive
