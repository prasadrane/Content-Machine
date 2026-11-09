"""Durable integer-unit provider reservations, committed before external work.

Caller supplies a reviewed conservative bound per actual provider attempt and
the UTC billing day. Unknown usage charges the full bound and retains an
inflight slot: timeout does not prove the provider stopped. No paid fallback,
background expiry, estimated refund, or automatic retry is authorized here.
"""
from datetime import date
import time

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import atomic_write

BUDGET_MIGRATION_STATEMENTS = (
    '''CREATE TABLE IF NOT EXISTS workflow_provider_budget_days (
       pool TEXT NOT NULL, day TEXT NOT NULL, daily_limit BIGINT NOT NULL CHECK(daily_limit>0),
       max_inflight INTEGER NOT NULL CHECK(max_inflight>0), PRIMARY KEY(pool,day))''',
    '''CREATE TABLE IF NOT EXISTS workflow_provider_reservations (
       pool TEXT NOT NULL, request_id TEXT NOT NULL, day TEXT NOT NULL,
       subject_id TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
       reserved_units BIGINT NOT NULL CHECK(reserved_units>0),
       charged_units BIGINT NOT NULL CHECK(charged_units>=0),
       state TEXT NOT NULL CHECK(state IN ('reserved','dispatched','uncertain','settled','released')),
       PRIMARY KEY(pool,request_id),
       FOREIGN KEY(pool,day) REFERENCES workflow_provider_budget_days(pool,day))''',
)
# Same DDL works for PostgreSQL; parent migration adds private RLS/revokes.
POSTGRES_BUDGET_MIGRATION_STATEMENTS = BUDGET_MIGRATION_STATEMENTS


def _error(code, detail, status=409):
    raise WorkflowError(status, code, detail)


def _idle(conn):
    if conn.in_transaction:
        _error('guest_budget_transaction_open', 'Provider quota must commit outside another transaction.')


def _positive(value):
    return type(value) is int and 0 < value <= 9_000_000_000_000_000


def _text(value):
    return isinstance(value, str) and 0 < len(value) <= 200 and value == value.strip()


def migrate_budget(conn):
    with atomic_write(conn):
        for statement in BUDGET_MIGRATION_STATEMENTS:
            conn.execute(statement)


def _read(conn, pool, request_id):
    row = conn.execute('SELECT * FROM workflow_provider_reservations WHERE pool=? AND request_id=?',
                       (pool, request_id)).fetchone()
    if row is None:
        _error('guest_budget_not_found', 'Provider quota reservation not found.', 404)
    return dict(row)


def _lease_epoch(request_id):
    """Epoch seconds from a '<anything>:<epoch>:<hex>' key, or None if it does not parse."""
    parts = request_id.rsplit(':', 2)
    if len(parts) != 3 or not parts[0] or not parts[1].isascii() or not parts[1].isdigit() or not parts[2]:
        return None
    return int(parts[1])


def _holds_slot(request_id, now, lease_s):
    if lease_s is None:
        return True
    epoch = _lease_epoch(request_id)
    return epoch is not None and now - epoch <= lease_s


def reserve(conn, *, pool, day, request_id, subject_id, provider, model,
            units, daily_limit, max_inflight,
            subject_daily_limit=None, subject_max_inflight=1, lease_s=None):
    """Return (durably stored reservation, newly_created); replay cannot dispatch.

    Use a stable key unique to each actual external attempt, not an operation
    containing several Council calls. Bound must include retries and reasoning
    only if those are part of that single attempt; otherwise reserve each call.

    The inflight count is scoped to `day`. With `lease_s=None` every row in state
    reserved/dispatched/uncertain holds a slot for the whole day. With `lease_s`
    set, a slot is held only by such a row whose request_id ends in
    ':<epoch>:<hex>' with now-epoch <= lease_s; legacy (unparseable) or older rows
    free their slot but still count toward charged daily spend.
    A changed max_inflight (a concurrency limit) updates the day's stored policy;
    a changed daily_limit raises guest_budget_policy_conflict.
    Each subject is also capped: daily units default to max(units, daily_limit//4)
    and inflight attempts default to 1, so one identity cannot drain the pool.
    """
    _idle(conn)
    try:
        valid_day = isinstance(day, str) and date.fromisoformat(day).isoformat() == day
    except ValueError:
        valid_day = False
    if (not valid_day or not all(map(_text, (pool, request_id, subject_id, provider, model)))
            or not all(map(_positive, (units, daily_limit, max_inflight, subject_max_inflight)))
            or not (subject_daily_limit is None or _positive(subject_daily_limit))):
        _error('guest_budget_invalid', 'A valid bounded provider quota policy is required.', 422)
    with atomic_write(conn):
        existing = conn.execute('SELECT * FROM workflow_provider_reservations WHERE pool=? AND request_id=?',
                                (pool, request_id)).fetchone()
        if existing:
            row = dict(existing)
            expected = dict(day=day, subject_id=subject_id, provider=provider, model=model, reserved_units=units)
            if any(row[key] != value for key, value in expected.items()):
                _error('guest_budget_conflict', 'Provider quota request key already identifies another attempt.')
            return row, False
        policy = conn.execute('SELECT daily_limit,max_inflight FROM workflow_provider_budget_days WHERE pool=? AND day=?',
                              (pool, day)).fetchone()
        if policy and policy['daily_limit'] != daily_limit:
            _error('guest_budget_policy_conflict', 'Shared provider quota policy differs from the committed policy.')
        if policy and policy['max_inflight'] != max_inflight:
            conn.execute('UPDATE workflow_provider_budget_days SET max_inflight=? WHERE pool=? AND day=?',
                         (max_inflight, pool, day))
        if not policy:
            conn.execute('INSERT INTO workflow_provider_budget_days(pool,day,daily_limit,max_inflight) VALUES(?,?,?,?)',
                         (pool, day, daily_limit, max_inflight))
        used = conn.execute('SELECT COALESCE(SUM(charged_units),0) FROM workflow_provider_reservations WHERE pool=? AND day=?',
                            (pool, day)).fetchone()[0]
        if used + units > daily_limit:
            _error('guest_budget_exhausted', 'Guest AI quota is used for this UTC day. Your draft is preserved.', 429)
        now = time.time()
        rows = conn.execute("SELECT request_id,subject_id FROM workflow_provider_reservations WHERE pool=? AND day=? AND state IN ('reserved','dispatched','uncertain')",
                            (pool, day)).fetchall()
        held = [r['subject_id'] for r in rows if _holds_slot(r['request_id'], now, lease_s)]
        active = len(held)
        if active >= max_inflight:
            _error('guest_budget_busy', 'Guest AI capacity is busy. Your draft is preserved; try again later.', 429)
        subject_cap = subject_daily_limit or max(units, daily_limit // 4)
        subject_used = conn.execute('SELECT COALESCE(SUM(charged_units),0) FROM workflow_provider_reservations WHERE pool=? AND day=? AND subject_id=?',
                                    (pool, day, subject_id)).fetchone()[0]
        if subject_used + units > subject_cap:
            _error('guest_budget_subject_exhausted', 'Your guest AI allowance is used for this UTC day. Your draft is preserved.', 429)
        subject_active = sum(1 for held_subject in held if held_subject == subject_id)
        if subject_active >= subject_max_inflight:
            _error('guest_budget_subject_busy', 'You already have a guest AI call in progress. Your draft is preserved; try again shortly.', 429)
        conn.execute('''INSERT INTO workflow_provider_reservations(pool,request_id,day,subject_id,provider,model,
            reserved_units,charged_units,state) VALUES(?,?,?,?,?,?,?,?,'reserved')''',
                     (pool, request_id, day, subject_id, provider, model, units, units))
        result = _read(conn, pool, request_id)
    return result, True


def dispatch(conn, pool, request_id):
    """One committed dispatch permission. Only a True result may call provider."""
    _idle(conn)
    with atomic_write(conn):
        row = _read(conn, pool, request_id)
        if row['state'] != 'reserved':
            return False
        conn.execute("UPDATE workflow_provider_reservations SET state='dispatched' WHERE pool=? AND request_id=?",
                     (pool, request_id))
    return True


def release(conn, pool, request_id):
    """Refund only a definitely undispatched reservation; never a timed-out call."""
    _idle(conn)
    with atomic_write(conn):
        row = _read(conn, pool, request_id)
        if row['state'] == 'released':
            return row
        if row['state'] != 'reserved':
            _error('guest_budget_state_conflict', 'Dispatched or uncertain provider quota cannot be released.')
        conn.execute("UPDATE workflow_provider_reservations SET state='released',charged_units=0 WHERE pool=? AND request_id=?",
                     (pool, request_id))
        result = _read(conn, pool, request_id)
    return result


def settle(conn, pool, request_id, *, actual_units=None):
    """Settle measured terminal usage, or retain full quota/slot when uncertain.

    Actual usage is trusted provider metadata, never browser input. If it exceeds
    the reviewed bound, record the full actual charge (do not hide the overrun).
    A timed-out native call may settle later only after its terminal usage is known.
    """
    _idle(conn)
    if actual_units is not None and (type(actual_units) is not int or not 0 <= actual_units <= 9_000_000_000_000_000):
        _error('guest_budget_invalid', 'Provider usage must be a nonnegative integer.', 422)
    with atomic_write(conn):
        row = _read(conn, pool, request_id)
        units = row['reserved_units'] if actual_units is None else actual_units
        state = 'uncertain' if actual_units is None else 'settled'
        if row['state'] not in ('dispatched', 'uncertain'):
            if row['state'] == state and row['charged_units'] == units:
                return row
            _error('guest_budget_state_conflict', 'Provider quota has another terminal outcome.')
        conn.execute('UPDATE workflow_provider_reservations SET state=?,charged_units=? WHERE pool=? AND request_id=?',
                     (state, units, pool, request_id))
        result = _read(conn, pool, request_id)
    return result
