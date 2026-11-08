"""Explicit backup-first hosted foundation migration; never invoked at startup.

Configure SUPABASE_URL, CONTENT_MACHINE_DATABASE_MODE and
CONTENT_MACHINE_DATABASE_URL in the operator environment (verified TLS only).
Run ``check`` first; ``apply --backup ABSOLUTE_NEW_PRIVATE.json`` installs only
into an empty public application schema. No dotenv discovery or credential log.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from content_machine.workflow.hosted_configuration import parse_hosted_configuration

MIGRATION_ID = '202611060001_workflow_foundation'
SQL_PATH = ROOT / 'supabase/migrations' / (MIGRATION_ID + '.sql')
LEDGER = 'content_machine_schema_migrations'
INVENTORY = """WITH target AS (SELECT oid FROM pg_catalog.pg_namespace WHERE nspname=%s)
SELECT 'relation',c.relname,c.relkind::text FROM pg_catalog.pg_class c,target n
 WHERE c.relnamespace=n.oid AND c.relkind IN ('r','p','v','m','S','f')
UNION ALL SELECT 'column',c.relname||'.'||a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod)
 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid,target n
 WHERE c.relnamespace=n.oid AND c.relkind IN ('r','p','v','m','S','f') AND a.attnum>0 AND NOT a.attisdropped
UNION ALL SELECT 'column_rule',c.relname||'.'||a.attname,a.attnotnull::text||':'||COALESCE(pg_catalog.pg_get_expr(d.adbin,d.adrelid),'')
 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum,target n
 WHERE c.relnamespace=n.oid AND c.relkind IN ('r','p','v','m','f') AND a.attnum>0 AND NOT a.attisdropped
UNION ALL SELECT 'security',c.relname,c.relowner::text||':'||c.relrowsecurity::text||':'||c.relforcerowsecurity::text||':'||COALESCE(c.relacl::text,'')
 FROM pg_catalog.pg_class c,target n WHERE c.relnamespace=n.oid AND c.relkind IN ('r','p','v','m','S','f')
UNION ALL SELECT 'constraint',c.relname||'.'||k.conname,pg_catalog.pg_get_constraintdef(k.oid,true)
 FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid,target n WHERE c.relnamespace=n.oid
UNION ALL SELECT 'index',c.relname,pg_catalog.pg_get_indexdef(c.oid)
 FROM pg_catalog.pg_class c,target n WHERE c.relnamespace=n.oid AND c.relkind='i'
UNION ALL SELECT 'trigger',c.relname||'.'||t.tgname,pg_catalog.pg_get_triggerdef(t.oid,true)||':'||t.tgenabled::text
 FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid,target n WHERE c.relnamespace=n.oid AND NOT t.tgisinternal
UNION ALL SELECT 'policy',c.relname||'.'||p.polname,
 p.polcmd::text||':'||p.polpermissive::text||':'||p.polroles::text||':'||COALESCE(pg_catalog.pg_get_expr(p.polqual,p.polrelid),'')||':'||COALESCE(pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid),'')
 FROM pg_catalog.pg_policy p JOIN pg_catalog.pg_class c ON c.oid=p.polrelid,target n WHERE c.relnamespace=n.oid
UNION ALL SELECT 'function',p.oid::regprocedure::text,pg_catalog.md5(pg_catalog.pg_get_functiondef(p.oid))||':'||p.proowner::text||':'||COALESCE(p.proacl::text,'')
 FROM pg_catalog.pg_proc p,target n WHERE p.pronamespace=n.oid AND p.prokind='f'
ORDER BY 1,2,3"""


class MigrationError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def digest(sql):
    return hashlib.sha256(sql.encode('utf-8')).hexdigest()


def body(sql):
    start = re.search(r'(?m)^BEGIN;\s*$', sql)
    end = re.search(r'(?m)^COMMIT;\s*\Z', sql)
    if not start or not end or start.end() >= end.start():
        raise MigrationError('migration_envelope_invalid')
    if re.sub(r'--[^\n]*', '', sql[:start.start()]).strip():
        raise MigrationError('migration_envelope_invalid')
    return sql[start.end():end.start()]


def expected_columns(sql):
    aliases = {'timestamptz': 'timestamp with time zone'}
    result = {}
    for name, block in re.findall(r'CREATE TABLE public\.(workflow_\w+)\s*\((.*?)\n\);', sql, re.S):
        result[name] = {column: aliases.get(kind, kind) for column, kind in re.findall(
            r'(?:^|,)\s*(\w+)\s+(text|uuid|integer|bigint|boolean|timestamptz)\b', block)}
    if len(result) != 18:
        raise MigrationError('migration_contract_changed')
    return result


def _inventory(conn, schema):
    return sorted([list(row) for row in conn.execute(INVENTORY, (schema,)).fetchall()])


def _validate(inventory, expected):
    relations = {name for kind, name, _ in inventory if kind == 'relation'}
    if relations != set(expected) | {LEDGER}:
        raise MigrationError('schema_drift')
    for table, columns in expected.items():
        actual = {name[len(table) + 1:]: value for kind, name, value in inventory
                  if kind == 'column' and name.startswith(table + '.')}
        if actual != columns:
            raise MigrationError('schema_drift')


def _private_file(path, payload):
    if path is None:
        raise MigrationError('backup_required')
    path = Path(path)
    if not path.is_absolute() or path.suffix.lower() != '.json' or not path.parent.is_dir():
        raise MigrationError('backup_path_invalid')
    # Exclusive creation refuses existing files and symlinks; never delete or
    # overwrite even an incomplete backup. Only inventory is backed up here.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as target:
        if os.name == 'nt':
            account = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True,
                                     text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            sid = next(csv.reader(account.stdout.splitlines()))[1]
            if not re.fullmatch(r'S-1-\d+(?:-\d+)+', sid):
                raise MigrationError('backup_permissions_failed')
            subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', '*' + sid + ':(F)', '/q'],
                           capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        target.write(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode('utf-8'))
        target.flush()
        os.fsync(target.fileno())


def run(conn, *, apply=False, backup=None, schema='public'):
    """Run against an idle raw psycopg connection; generated schemas are test-only.

    CLI always selects public. The Python seam permits only generated verification
    schemas so actual live acceptance never requires production installation.
    """
    if schema != 'public' and not re.fullmatch(r'cm_verify_[0-9a-f]{32}', schema):
        raise MigrationError('schema_invalid')
    if not getattr(conn, 'autocommit', False) or conn.info.transaction_status != 0:
        raise MigrationError('connection_not_idle')
    sql = SQL_PATH.read_text(encoding='utf-8')
    fingerprint, expected, ddl = digest(sql), expected_columns(sql), body(sql)
    prefix = schema + '.'
    result = {'migration_id': MIGRATION_ID, 'sha256': fingerprint}
    try:
        conn.execute('BEGIN' if apply else 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if apply:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ('content_machine_migrate:' + schema,))
        inventory = _inventory(conn, schema)
        present = {name for kind, name, _ in inventory if kind == 'relation'}
        if LEDGER in present:
            rows = conn.execute('SELECT migration_id,sha256,inventory_json FROM ' + prefix + LEDGER).fetchall()
            if len(rows) != 1 or tuple(rows[0][:2]) != (MIGRATION_ID, fingerprint):
                raise MigrationError('migration_ledger_conflict')
            _validate(inventory, expected)
            if inventory != json.loads(rows[0][2]):
                raise MigrationError('schema_drift')
            conn.commit()
            return {**result, 'status': 'already_applied'}
        if present:
            raise MigrationError('schema_not_empty')
        if not apply:
            conn.commit()
            return {**result, 'status': 'empty'}
        _private_file(backup, {'format_version': 1, **result, 'schema': schema, 'inventory': inventory})
        conn.execute('CREATE TABLE ' + prefix + LEDGER + ' (migration_id text PRIMARY KEY,sha256 text NOT NULL,'
            'inventory_json text NOT NULL,applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('ALTER TABLE ' + prefix + LEDGER + ' ENABLE ROW LEVEL SECURITY')
        conn.execute('ALTER TABLE ' + prefix + LEDGER + ' FORCE ROW LEVEL SECURITY')
        conn.execute('REVOKE ALL ON TABLE ' + prefix + LEDGER + ' FROM PUBLIC,anon,authenticated')
        conn.execute(ddl.replace('public.', prefix))
        installed = _inventory(conn, schema)
        _validate(installed, expected)
        conn.execute('INSERT INTO ' + prefix + LEDGER + '(migration_id,sha256,inventory_json) VALUES(%s,%s,%s)',
                     (MIGRATION_ID, fingerprint, json.dumps(installed, separators=(',', ':'))))
        conn.commit()
        return {**result, 'status': 'applied', 'backup_created': True}
    except BaseException as exc:
        conn.rollback()
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError('migration_failed') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('check', 'apply'))
    parser.add_argument('--backup', type=Path, help='NEW absolute private JSON path; required for first apply')
    args = parser.parse_args(argv)
    record = {'success': False}
    try:
        if args.mode == 'apply' and args.backup is None:
            raise MigrationError('backup_required')
        config = parse_hosted_configuration(os.environ)
        import psycopg
        with psycopg.connect(config.database_url, autocommit=True, connect_timeout=10) as conn:
            record.update(run(conn, apply=args.mode == 'apply', backup=args.backup))
        record['success'] = True
    except Exception as exc:
        record['code'] = exc.code if isinstance(exc, MigrationError) else 'migration_failed'
    print(json.dumps(record))
    return 0 if record['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
