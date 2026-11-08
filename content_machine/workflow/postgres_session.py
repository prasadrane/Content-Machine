"""Narrow sqlite3-style session over a psycopg connection for workflow services.

Translates qmark SQL to ``%s``, restricts statements to ``workflow_*`` tables,
maps ``BEGIN IMMEDIATE`` to a writer-serialising advisory lock, and redacts
driver errors. It is a protocol adapter only; it does not open connections.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import sqlite3
from typing import Any
import uuid

from .errors import WorkflowError

_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_DOLLAR = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)?\$')
_TABLE_REF = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE(?!\s+SET\b))\s+((?:public\.)?[A-Za-z_][A-Za-z0-9_]*)', re.I)
_FORBIDDEN = re.compile(r'^\s*(?:PRAGMA|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COPY|ATTACH|VACUUM)\b', re.I)
_SAVEPOINT = re.compile(r'^(SAVEPOINT|RELEASE(?:\s+SAVEPOINT)?|ROLLBACK\s+TO(?:\s+SAVEPOINT)?)\s+([A-Za-z_][A-Za-z0-9_]*)$', re.I)
_WRITER_LOCK = "SELECT pg_advisory_xact_lock(hashtext('content_machine_workflow_writers'))"


def _scan(sql: str) -> tuple[str, int, str]:
    """Return (psycopg SQL, qmark count, SQL with literals/comments blanked)."""
    out: list[str] = []
    code: list[str] = []
    count = 0
    i, n = 0, len(sql)
    statement_done = False

    def emit(text: str, is_code: bool) -> None:
        out.append(text.replace('%', '%%'))
        code.append(text if is_code else ' ' * len(text))

    while i < n:
        c = sql[i]
        if c == "'":
            escaped = i > 0 and sql[i - 1] in 'eE' and (i < 2 or not (sql[i - 2].isalnum() or sql[i - 2] == '_'))
            j = i + 1
            while True:
                if j >= n:
                    raise sqlite3.ProgrammingError('Unterminated SQL literal.')
                if escaped and sql[j] == '\\':
                    j += 2
                    continue
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            emit(sql[i:j + 1], False)
            i = j + 1
        elif c == '"':
            j = sql.find('"', i + 1)
            while j != -1 and j + 1 < n and sql[j + 1] == '"':
                j = sql.find('"', j + 2)
            if j == -1:
                raise sqlite3.ProgrammingError('Unterminated SQL identifier.')
            emit(sql[i:j + 1], False)
            i = j + 1
        elif sql.startswith('--', i):
            j = sql.find('\n', i)
            j = n if j == -1 else j
            emit(sql[i:j], False)
            i = j
        elif sql.startswith('/*', i):
            depth, j = 1, i + 2
            while depth:
                if j >= n:
                    raise sqlite3.ProgrammingError('Unterminated SQL comment.')
                if sql.startswith('/*', j):
                    depth, j = depth + 1, j + 2
                elif sql.startswith('*/', j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            emit(sql[i:j], False)
            i = j
        elif c == '$' and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == '_')) and _DOLLAR.match(sql, i):
            tag = _DOLLAR.match(sql, i).group(0)
            j = sql.find(tag, i + len(tag))
            if j == -1:
                raise sqlite3.ProgrammingError('Unterminated SQL literal.')
            emit(sql[i:j + len(tag)], False)
            i = j + len(tag)
        elif c == ';':
            statement_done = True
            emit(c, True)
            i += 1
        else:
            if statement_done and not c.isspace():
                raise sqlite3.ProgrammingError('Multiple SQL statements are not supported.')
            if c == '?':
                count += 1
                out.append('%s')
                code.append('?')
            else:
                emit(c, True)
            i += 1
    return ''.join(out), count, ''.join(code)


def compile_qmark(sql: str) -> tuple[str, int]:
    compiled, count, _ = _scan(sql)
    return compiled, count


def _iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.strftime('%Y-%m-%dT%H:%M:%S.') + f'{value.microsecond // 1000:03d}Z'


def _normalize(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return _iso(value)
    return value


class PostgresRow:
    __slots__ = ('_names', '_values')

    def __init__(self, names: list[str], values: tuple) -> None:
        self._names = names
        self._values = tuple(_normalize(v) for v in values)

    def __getitem__(self, key: int | str | slice):
        if isinstance(key, str):
            try:
                return self._values[self._names.index(key)]
            except ValueError:
                raise IndexError(key) from None
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self) -> list[str]:
        return list(self._names)


class PostgresCursor:
    def __init__(self, result: Any) -> None:
        self._result = result
        self.rowcount = getattr(result, 'rowcount', -1)
        description = getattr(result, 'description', None) or []
        self._names = [column.name for column in description]

    @property
    def description(self):
        return [(name,) for name in self._names]

    def _row(self, values):
        return None if values is None else PostgresRow(self._names, tuple(values))

    def fetchone(self):
        return self._row(self._result.fetchone())

    def fetchall(self):
        return [self._row(v) for v in self._result.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


def _bad_scalar(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if '\x00' in value:
        return True
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)


class PostgresSession:
    dialect = 'postgresql'

    def __init__(self, raw: Any) -> None:
        if not getattr(raw, 'autocommit', False) or raw.info.transaction_status != 0:
            raise sqlite3.ProgrammingError('Postgres session requires an idle autocommit connection.')
        self._raw = raw
        self._owner_savepoint: str | None = None

    @property
    def in_transaction(self) -> bool:
        return self._raw.info.transaction_status != 0

    def _driver(self, call, *args):
        try:
            return call(*args)
        except Exception as exc:  # redact: driver messages may carry SQL/DSN/values
            state = str(getattr(exc, 'sqlstate', '') or '')
            if state.startswith('23'):
                raise sqlite3.IntegrityError('Database constraint failed.') from None
            raise sqlite3.OperationalError('Database operation failed.') from None

    def execute(self, sql: str, params: tuple | list = ()) -> PostgresCursor:
        compiled, count, code = _scan(sql)
        statement = ' '.join(code.replace(';', ' ').split())
        upper = statement.upper()
        if count != len(params):
            raise sqlite3.ProgrammingError('Parameter count does not match placeholders.')
        for value in params:
            if _bad_scalar(value):
                raise WorkflowError(422, 'hosted_input_unsupported', 'Input contains unsupported characters.')
        if upper in ('BEGIN IMMEDIATE', 'BEGIN', 'BEGIN TRANSACTION'):
            result = self._driver(self._raw.execute, 'BEGIN ISOLATION LEVEL READ COMMITTED')
            if upper == 'BEGIN IMMEDIATE':
                self._driver(self._raw.execute, _WRITER_LOCK)
            return PostgresCursor(result)
        if upper in ('COMMIT', 'END'):
            self.commit()
            return PostgresCursor(_Empty())
        if upper == 'ROLLBACK':
            self.rollback()
            return PostgresCursor(_Empty())
        match = _SAVEPOINT.match(statement)
        if match:
            return self._savepoint(match.group(1).upper().split()[0], match.group(2), statement)
        if _FORBIDDEN.match(statement):
            raise sqlite3.ProgrammingError('Statement is not supported.')
        tables = _TABLE_REF.findall(code)
        for table in tables:
            if not table.lower().removeprefix('public.').startswith('workflow_'):
                raise sqlite3.ProgrammingError('Table is not supported.')
        if re.search(r'\bsqlite_\w+', code, re.I):
            raise sqlite3.ProgrammingError('Table is not supported.')
        result = self._driver(self._raw.execute, compiled, tuple(params))
        return PostgresCursor(result)

    def _savepoint(self, verb: str, name: str, statement: str) -> PostgresCursor:
        if verb == 'SAVEPOINT' and not self.in_transaction:
            self._driver(self._raw.execute, 'BEGIN ISOLATION LEVEL REPEATABLE READ')
            self._owner_savepoint = name
        result = self._driver(self._raw.execute, statement)
        if verb == 'RELEASE' and self._owner_savepoint == name:
            self._owner_savepoint = None
            self.commit()
        return PostgresCursor(result)

    def commit(self) -> None:
        self._owner_savepoint = None
        self._driver(self._raw.commit)

    def rollback(self) -> None:
        self._owner_savepoint = None
        self._driver(self._raw.rollback)

    def close(self) -> None:
        try:
            if self.in_transaction:
                self.rollback()
        finally:
            self._driver(self._raw.close)


class _Empty:
    rowcount = -1
    description = None

    def fetchone(self):
        return None

    def fetchall(self):
        return []


__all__ = ['PostgresCursor', 'PostgresRow', 'PostgresSession', 'compile_qmark']
