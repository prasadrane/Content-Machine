"""Owner-scoped factual profile and discovery source configuration."""

from __future__ import annotations

import sqlite3
import re
import uuid
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

from pydantic import Field, field_validator, model_validator

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import (
    WorkflowResult, atomic_write, find_idempotent, record_idempotent, request_digest,
)
from content_machine.workflow.schemas import Principal, WorkflowModel, utc_timestamp

SETTINGS_MIGRATION_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS workflow_profiles (
        owner_id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
        bio TEXT NOT NULL, revision INTEGER NOT NULL CHECK (revision >= 1),
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workflow_sources (
        source_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
        kind TEXT NOT NULL CHECK (kind = 'rss'), name TEXT NOT NULL, url TEXT NOT NULL,
        enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
        revision INTEGER NOT NULL CHECK (revision >= 1),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE (source_id, owner_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_workflow_sources_owner ON workflow_sources (owner_id, created_at, source_id)",
)


class ProfileSave(WorkflowModel):
    name: str = Field(max_length=200)
    role: str = Field(max_length=200)
    bio: str = Field(max_length=20_000)
    expected_revision: int = Field(ge=0, strict=True)


def validate_url(value: str) -> str:
    """Accept ordinary HTTP(S) feed URLs without embedded credentials."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid HTTP or HTTPS feed URL") from exc
    if (value != value.strip() or any(char.isspace() for char in value)
            or parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.fragment or (port is not None and not 1 <= port <= 65535)):
        raise ValueError("Enter an HTTP or HTTPS feed URL without credentials or a fragment")
    for name, _ in parse_qsl(parsed.query, keep_blank_values=True):
        normalized = re.sub(r"[^a-z0-9]", "", name.lower())
        if (normalized in {"key", "auth", "sig"} or any(part in normalized for part in
                ("token", "secret", "password", "passwd", "apikey", "authorization",
                 "signature", "credential", "session", "oauth", "bearer"))):
            raise ValueError("Feed URLs cannot contain credentials")
    return value


class SourceCreate(WorkflowModel):
    kind: Literal["rss"]
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2_000)
    enabled: bool = Field(strict=True)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source name is required")
        return value

    _valid_url = field_validator("url")(validate_url)


class SourceUpdate(WorkflowModel):
    expected_revision: int = Field(ge=1, strict=True)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, min_length=1, max_length=2_000)
    enabled: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def validate_changes(self):
        fields = self.model_fields_set - {"expected_revision"}
        if not fields or any(getattr(self, field) is None for field in fields):
            raise ValueError("Supply at least one source field to update")
        if self.name is not None and not self.name.strip():
            raise ValueError("Source name is required")
        if self.url is not None:
            validate_url(self.url)
        return self


def get_profile(conn: sqlite3.Connection, principal: Principal) -> dict:
    row = conn.execute(
        "SELECT name, role, bio, revision, updated_at FROM workflow_profiles WHERE owner_id = ?",
        (principal.owner_id,),
    ).fetchone()
    return dict(row) if row else {"name": "", "role": "", "bio": "", "revision": 0, "updated_at": None}


def _source(row: sqlite3.Row) -> dict:
    source = dict(row)
    source["enabled"] = bool(source["enabled"])
    return source


_SOURCE_COLUMNS = "source_id, kind, name, url, enabled, revision, created_at, updated_at"


def list_sources(conn: sqlite3.Connection, principal: Principal, enabled_only: bool = False) -> list[dict]:
    sql = f"SELECT {_SOURCE_COLUMNS} FROM workflow_sources WHERE owner_id = ?"
    if enabled_only:
        sql += " AND enabled = 1"
    sql += " ORDER BY created_at, source_id"
    return [_source(row) for row in conn.execute(sql, (principal.owner_id,)).fetchall()]


def _owned_source(conn: sqlite3.Connection, principal: Principal, source_id: str) -> dict:
    row = conn.execute(
        f"SELECT {_SOURCE_COLUMNS} FROM workflow_sources WHERE owner_id = ? AND source_id = ?",
        (principal.owner_id, source_id),
    ).fetchone()
    if row is None:
        raise WorkflowError(404, "source_not_found", "Source not found")
    return _source(row)


def _mutation(conn, principal, request_id, method, path, payload, operation):
    if not isinstance(request_id, str) or not request_id.strip():
        raise WorkflowError(422, "invalid_request", "Idempotency-Key is required")
    digest = request_digest(method, path, payload)
    with atomic_write(conn):
        replay = find_idempotent(conn, principal.owner_id, request_id, method=method,
                                 resource_path=path, digest=digest)
        if replay is not None:
            return replay
        status, body = operation()
        record_idempotent(conn, principal.owner_id, request_id, method=method,
                          resource_path=path, digest=digest, response_status=status,
                          body=body, created_at=utc_timestamp())
        return WorkflowResult(status, body)


def save_profile(conn, principal, payload: ProfileSave, *, request_id: str) -> WorkflowResult:
    def save():
        current = get_profile(conn, principal)
        if current["revision"] != payload.expected_revision:
            raise WorkflowError(409, "revision_conflict", "Profile changed since it was loaded", current=current)
        updated_at = utc_timestamp()
        conn.execute(
            "INSERT INTO workflow_profiles (owner_id, name, role, bio, revision, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(owner_id) DO UPDATE SET"
            " name=excluded.name, role=excluded.role, bio=excluded.bio,"
            " revision=excluded.revision, updated_at=excluded.updated_at",
            (principal.owner_id, payload.name, payload.role, payload.bio, current["revision"] + 1, updated_at),
        )
        return 200, {"profile": get_profile(conn, principal)}

    return _mutation(conn, principal, request_id, "PUT", "/api/workflow/settings/profile",
                     payload.model_dump(mode="json"), save)


def create_source(conn, principal, payload: SourceCreate, *, request_id: str) -> WorkflowResult:
    def create():
        source_id = f"src_{uuid.uuid4().hex}"
        now = utc_timestamp()
        conn.execute(
            "INSERT INTO workflow_sources (source_id, owner_id, kind, name, url, enabled, revision, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (source_id, principal.owner_id, payload.kind, payload.name, payload.url, int(payload.enabled), now, now),
        )
        return 201, {"source": _owned_source(conn, principal, source_id)}

    return _mutation(conn, principal, request_id, "POST", "/api/workflow/settings/sources",
                     payload.model_dump(mode="json"), create)


def update_source(conn, principal, source_id: str, payload: SourceUpdate, *, request_id: str) -> WorkflowResult:
    def update():
        current = _owned_source(conn, principal, source_id)
        if current["revision"] != payload.expected_revision:
            raise WorkflowError(409, "revision_conflict", "Source changed since it was loaded", current=current)
        fields = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        current.update(fields)
        conn.execute(
            "UPDATE workflow_sources SET name=?, url=?, enabled=?, revision=?, updated_at=?"
            " WHERE owner_id=? AND source_id=? AND revision=?",
            (current["name"], current["url"], int(current["enabled"]), current["revision"] + 1,
             utc_timestamp(), principal.owner_id, source_id, current["revision"]),
        )
        return 200, {"source": _owned_source(conn, principal, source_id)}

    return _mutation(conn, principal, request_id, "PATCH", f"/api/workflow/settings/sources/{source_id}",
                     payload.model_dump(mode="json", exclude_unset=True), update)
