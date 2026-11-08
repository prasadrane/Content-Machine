"""Additive, atomic SQLite migration for creator workflow persistence.

Every persistent workflow record lives in a ``workflow_*`` table; context and
artifact stay nested JSON on items and versions with no independent identity.
Owner IDs are explicit on every row and parent/child references are composite
``(id, owner_id)`` foreign keys.

The migration is additive only. It never alters or removes legacy tables and
runs all statements inside one savepoint, so a forced mid-migration failure
leaves no partial workflow schema while preserving legacy rows, the caller's
transaction and the connection's row factory. Immutable version and approval
rows reject UPDATE and DELETE through triggers.
"""

from __future__ import annotations

import sqlite3

from content_machine.workflow.settings import SETTINGS_MIGRATION_STATEMENTS
from content_machine.workflow.preferences import MIGRATION_STATEMENTS as PREFERENCE_MIGRATION_STATEMENTS
from content_machine.workflow.operation_storage import OPERATION_MIGRATION_STATEMENTS
from content_machine.workflow.guests import GUEST_MIGRATION_STATEMENTS
from content_machine.workflow.guest_transfer_storage import TRANSFER_MIGRATION_STATEMENTS
from content_machine.workflow.provider_budget import BUDGET_MIGRATION_STATEMENTS

SAVEPOINT_NAME = "workflow_schema_migration"

_CREATE_ITEMS = """
CREATE TABLE IF NOT EXISTS workflow_items (
  item_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  destination TEXT NOT NULL,
  format TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT 'idea'
    CHECK (stage IN ('idea', 'draft_review', 'approve', 'export')),
  working_revision INTEGER NOT NULL CHECK (working_revision >= 1),
  context_json TEXT NOT NULL,
  artifact_json TEXT NOT NULL,
  parent_version_id TEXT,
  active_approval_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (item_id, owner_id),
  FOREIGN KEY (parent_version_id, owner_id)
    REFERENCES workflow_versions (version_id, owner_id),
  FOREIGN KEY (active_approval_id, owner_id, item_id)
    REFERENCES workflow_approvals (approval_id, owner_id, item_id)
)
"""

_CREATE_VERSIONS = """
CREATE TABLE IF NOT EXISTS workflow_versions (
  version_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  context_json TEXT NOT NULL,
  artifact_json TEXT NOT NULL,
  destination TEXT NOT NULL,
  format TEXT NOT NULL,
  artifact_digest TEXT NOT NULL
    CHECK (length(artifact_digest) = 71
      AND substr(artifact_digest, 1, 7) = 'sha256:'
      AND substr(artifact_digest, 8) NOT GLOB '*[^0-9a-f]*'),
  purpose TEXT NOT NULL
    CHECK (purpose IN
      ('review', 'skip_review', 'approval', 'restore', 'adaptation')),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (item_id, revision),
  UNIQUE (version_id, owner_id),
  UNIQUE (version_id, owner_id, item_id),
  FOREIGN KEY (item_id, owner_id)
    REFERENCES workflow_items (item_id, owner_id)
)
"""

_CREATE_APPROVALS = """
CREATE TABLE IF NOT EXISTS workflow_approvals (
  approval_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  artifact_digest TEXT NOT NULL
    CHECK (length(artifact_digest) = 71
      AND substr(artifact_digest, 1, 7) = 'sha256:'
      AND substr(artifact_digest, 8) NOT GLOB '*[^0-9a-f]*'),
  destination TEXT NOT NULL,
  format TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  approved_at TEXT NOT NULL,
  UNIQUE (approval_id, owner_id, item_id),
  FOREIGN KEY (item_id, owner_id)
    REFERENCES workflow_items (item_id, owner_id),
  FOREIGN KEY (version_id, owner_id, item_id)
    REFERENCES workflow_versions (version_id, owner_id, item_id)
)
"""

_CREATE_OPERATIONS = """
CREATE TABLE IF NOT EXISTS workflow_operations (
  operation_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('generate', 'review')),
  input_version_id TEXT NOT NULL,
  context_snapshot_json TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending', 'completed', 'failed')),
  request_id TEXT NOT NULL,
  result_json TEXT,
  error_json TEXT,
  started_at TEXT,
  finished_at TEXT,
  FOREIGN KEY (item_id, owner_id)
    REFERENCES workflow_items (item_id, owner_id),
  FOREIGN KEY (input_version_id, owner_id, item_id)
    REFERENCES workflow_versions (version_id, owner_id, item_id)
)
"""

_CREATE_REVIEWS = """
CREATE TABLE IF NOT EXISTS workflow_reviews (
  review_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  input_version_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  state TEXT NOT NULL
    CHECK (state IN ('pending', 'completed', 'failed', 'skipped')),
  actions_json TEXT NOT NULL DEFAULT '{}',
  score_basis_json TEXT,
  proposals_json TEXT NOT NULL DEFAULT '[]',
  model_config TEXT,
  started_at TEXT,
  finished_at TEXT,
  FOREIGN KEY (item_id, owner_id)
    REFERENCES workflow_items (item_id, owner_id),
  FOREIGN KEY (input_version_id, owner_id, item_id)
    REFERENCES workflow_versions (version_id, owner_id, item_id)
)
"""

_CREATE_IDEMPOTENCY = """
CREATE TABLE IF NOT EXISTS workflow_idempotency (
  owner_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  method TEXT NOT NULL
    CHECK (method IN ('POST', 'PATCH', 'PUT', 'DELETE')),
  resource_path TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  response_status INTEGER NOT NULL
    CHECK (response_status BETWEEN 100 AND 599),
  response_body_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, request_id)
)
"""

_CREATE_DISCOVERY_CACHE = """
CREATE TABLE IF NOT EXISTS workflow_discovery_cache (
  owner_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  url TEXT NOT NULL,
  source_revision INTEGER NOT NULL CHECK (source_revision >= 1),
  etag TEXT CHECK (etag IS NULL OR length(etag) <= 512),
  last_modified TEXT CHECK (last_modified IS NULL OR length(last_modified) <= 128),
  PRIMARY KEY (owner_id, source_id),
  FOREIGN KEY (source_id, owner_id)
    REFERENCES workflow_sources (source_id, owner_id)
)
"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_workflow_items_owner_updated"
    " ON workflow_items (owner_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_versions_item"
    " ON workflow_versions (item_id, revision)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_operations_item"
    " ON workflow_operations (item_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_reviews_item"
    " ON workflow_reviews (item_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_approvals_item"
    " ON workflow_approvals (item_id, approved_at)",
)

_IMMUTABLE_TRIGGERS = (
    """
CREATE TRIGGER IF NOT EXISTS workflow_versions_no_update
BEFORE UPDATE ON workflow_versions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'workflow_versions rows are immutable');
END
""",
    """
CREATE TRIGGER IF NOT EXISTS workflow_versions_no_delete
BEFORE DELETE ON workflow_versions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'workflow_versions rows are immutable');
END
""",
    """
CREATE TRIGGER IF NOT EXISTS workflow_approvals_no_update
BEFORE UPDATE ON workflow_approvals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'workflow_approvals rows are immutable');
END
""",
    """
CREATE TRIGGER IF NOT EXISTS workflow_approvals_no_delete
BEFORE DELETE ON workflow_approvals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'workflow_approvals rows are immutable');
END
""",
)

MIGRATION_STATEMENTS: tuple[str, ...] = (
    _CREATE_ITEMS,
    _CREATE_VERSIONS,
    _CREATE_APPROVALS,
    _CREATE_OPERATIONS,
    _CREATE_REVIEWS,
    _CREATE_IDEMPOTENCY,
    *_INDEXES,
    *_IMMUTABLE_TRIGGERS,
    *SETTINGS_MIGRATION_STATEMENTS,
    _CREATE_DISCOVERY_CACHE,
    *PREFERENCE_MIGRATION_STATEMENTS,
    *OPERATION_MIGRATION_STATEMENTS,
    *GUEST_MIGRATION_STATEMENTS,
    *TRANSFER_MIGRATION_STATEMENTS,
    *BUDGET_MIGRATION_STATEMENTS,
)


def migrate_workflow(conn: sqlite3.Connection) -> None:
    """Apply the additive workflow schema atomically and idempotently.

    The savepoint nests inside a caller transaction without committing or
    rolling it back on success. On failure the savepoint is rolled back and
    the connection is left usable with no partial workflow schema.
    """

    conn.execute(f"SAVEPOINT {SAVEPOINT_NAME}")
    try:
        for statement in MIGRATION_STATEMENTS:
            conn.execute(statement)
    except BaseException:
        conn.execute(f"ROLLBACK TO SAVEPOINT {SAVEPOINT_NAME}")
        conn.execute(f"RELEASE SAVEPOINT {SAVEPOINT_NAME}")
        raise
    conn.execute(f"RELEASE SAVEPOINT {SAVEPOINT_NAME}")


__all__ = ["MIGRATION_STATEMENTS", "migrate_workflow"]
