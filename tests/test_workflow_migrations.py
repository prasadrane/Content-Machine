"""Tests for the additive workflow storage migration (contract C03).

Covers the acceptance scenarios only:
- a fresh database initializes the workflow tables through the existing seam;
- a realistic legacy database with content and Comments rows is preserved;
- repeated initialization preserves counts, IDs and legacy rows;
- owned parent/child references, revisions, states and duplicates are enforced;
- version/approval rows resist UPDATE and DELETE;
- an injected mid-migration failure leaves no workflow schema and recovers;
- the caller's transaction and row factory survive the migration.

Each test uses its own TemporaryDirectory home with the prior environment
restored; no live provider or network call is made.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def _import_storage_isolated():
    """Import storage under a temporary home and restore the caller env at once.

    The temporary environment exists only for the import, never for test
    bodies or other modules selected later during collection.
    """

    previous_home = os.environ.get("CONTENT_MACHINE_HOME")
    import_home = tempfile.TemporaryDirectory(prefix="c03-import-home-")
    os.environ["CONTENT_MACHINE_HOME"] = import_home.name
    try:
        from content_machine.storage import db as storage_db
    finally:
        if previous_home is None:
            os.environ.pop("CONTENT_MACHINE_HOME", None)
        else:
            os.environ["CONTENT_MACHINE_HOME"] = previous_home
    return storage_db, import_home


db, _IMPORT_HOME = _import_storage_isolated()


def tearDownModule() -> None:
    """Remove the empty import-time home without touching any module's env."""

    _IMPORT_HOME.cleanup()

TS = "2026-11-05T09:12:00.000Z"
DIGEST = "sha256:" + ("a" * 64)

WORKFLOW_TABLES = {
    "workflow_items",
    "workflow_versions",
    "workflow_operations",
    "workflow_reviews",
    "workflow_approvals",
    "workflow_idempotency",
}

WORKFLOW_TRIGGERS = {
    "workflow_versions_no_update",
    "workflow_versions_no_delete",
    "workflow_approvals_no_update",
    "workflow_approvals_no_delete",
}


def object_names(conn: sqlite3.Connection, kind: str) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = ?", (kind,)
    ).fetchall()
    return {row[0] for row in rows}


class WorkflowMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c03-home-")
        self._previous_home = os.environ.get("CONTENT_MACHINE_HOME")
        os.environ["CONTENT_MACHINE_HOME"] = self._home.name

        def restore_environment() -> None:
            if self._previous_home is None:
                os.environ.pop("CONTENT_MACHINE_HOME", None)
            else:
                os.environ["CONTENT_MACHINE_HOME"] = self._previous_home
            self._home.cleanup()

        self.addCleanup(restore_environment)
        self.root = Path(self._home.name)

    def db_path(self, name: str = "content_machine.db") -> Path:
        return self.root / name

    def legacy_db(self, name: str = "legacy.db") -> Path:
        """Build a pre-workflow database with real content and Comments rows."""

        path = self.db_path(name)
        conn = sqlite3.connect(path)
        try:
            conn.executescript(db.SCHEMA)
            conn.execute(
                "CREATE TABLE Comments ("
                "id INTEGER PRIMARY KEY, spike_id TEXT, body TEXT)"
            )
            conn.execute(
                "INSERT INTO spikes(id, category, hook_thesis)"
                " VALUES ('spike-legacy', 'internal', 'Legacy hook thesis')"
            )
            conn.execute(
                "INSERT INTO iterations("
                "spike_id, iteration, draft_path, draft_content)"
                " VALUES ('spike-legacy', 1, 'projects/x/draft.md',"
                " 'Exact draft text.  ')"
            )
            conn.execute(
                "INSERT INTO Comments(spike_id, body)"
                " VALUES ('spike-legacy', 'Legacy comment body')"
            )
            conn.commit()
        finally:
            conn.close()
        return path

    def insert_item(
        self,
        conn: sqlite3.Connection,
        item_id: str = "itm_a",
        owner_id: str = "own_01",
        revision: int = 1,
        stage: str = "idea",
        parent_version_id: str | None = None,
        active_approval_id: str | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_items("
            "item_id, owner_id, title, destination, format, stage,"
            " working_revision, context_json, artifact_json,"
            " parent_version_id, active_approval_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                owner_id,
                "Indexing tradeoffs",
                "linkedin",
                "linkedin_post",
                stage,
                revision,
                '{"notes": ""}',
                '{"segments": ["Exact text.  "]}',
                parent_version_id,
                active_approval_id,
                TS,
                TS,
            ),
        )

    def insert_version(
        self,
        conn: sqlite3.Connection,
        version_id: str = "ver_a",
        item_id: str = "itm_a",
        owner_id: str = "own_01",
        revision: int = 1,
        purpose: str = "review",
        artifact_digest: str = DIGEST,
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_versions("
            "version_id, item_id, owner_id, revision, context_json,"
            " artifact_json, destination, format, artifact_digest, purpose,"
            " created_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version_id,
                item_id,
                owner_id,
                revision,
                '{"notes": ""}',
                '{"segments": ["Exact text.  "]}',
                "linkedin",
                "linkedin_post",
                artifact_digest,
                purpose,
                owner_id,
                TS,
            ),
        )

    def insert_approval(
        self,
        conn: sqlite3.Connection,
        approval_id: str = "apr_a",
        item_id: str = "itm_a",
        owner_id: str = "own_01",
        version_id: str = "ver_a",
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_approvals("
            "approval_id, owner_id, item_id, version_id, artifact_digest,"
            " destination, format, approved_by, approved_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                approval_id,
                owner_id,
                item_id,
                version_id,
                DIGEST,
                "linkedin",
                "linkedin_post",
                owner_id,
                TS,
            ),
        )

    def insert_review(
        self,
        conn: sqlite3.Connection,
        review_id: str = "rev_a",
        item_id: str = "itm_a",
        owner_id: str = "own_01",
        version_id: str = "ver_a",
        state: str = "completed",
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_reviews("
            "review_id, owner_id, item_id, input_version_id, request_id,"
            " state, actions_json, score_basis_json, proposals_json,"
            " model_config, started_at, finished_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                review_id,
                owner_id,
                item_id,
                version_id,
                "req_rev",
                state,
                "{}",
                None,
                "[]",
                None,
                TS,
                TS,
            ),
        )

    def insert_operation(
        self,
        conn: sqlite3.Connection,
        operation_id: str = "op_a",
        item_id: str = "itm_a",
        owner_id: str = "own_01",
        version_id: str = "ver_a",
        kind: str = "generate",
        state: str = "completed",
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_operations("
            "operation_id, owner_id, item_id, kind, input_version_id,"
            " context_snapshot_json, state, request_id, result_json,"
            " error_json, started_at, finished_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                operation_id,
                owner_id,
                item_id,
                kind,
                version_id,
                '{"notes": "Indexing cost"}',
                state,
                "req_op",
                '{"segments": ["Draft text."]}',
                None,
                TS,
                TS,
            ),
        )

    def insert_idempotency(
        self,
        conn: sqlite3.Connection,
        request_id: str = "req_a",
        owner_id: str = "own_01",
    ) -> None:
        conn.execute(
            "INSERT INTO workflow_idempotency("
            "owner_id, request_id, method, resource_path, request_digest,"
            " response_status, response_body_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                owner_id,
                request_id,
                "POST",
                "/api/workflow/items",
                "digest-1",
                201,
                '{"item": {"item_id": "itm_a"}}',
                TS,
            ),
        )

    def snapshot(self, conn: sqlite3.Connection) -> dict:
        return {
            "items": conn.execute(
                "SELECT COUNT(*) FROM workflow_items"
            ).fetchone()[0],
            "item_ids": [
                row[0]
                for row in conn.execute(
                    "SELECT item_id FROM workflow_items ORDER BY item_id"
                )
            ],
            "versions": conn.execute(
                "SELECT COUNT(*) FROM workflow_versions"
            ).fetchone()[0],
            "version_ids": [
                row[0]
                for row in conn.execute(
                    "SELECT version_id FROM workflow_versions ORDER BY version_id"
                )
            ],
            "approvals": conn.execute(
                "SELECT COUNT(*) FROM workflow_approvals"
            ).fetchone()[0],
            "approval_ids": [
                row[0]
                for row in conn.execute(
                    "SELECT approval_id FROM workflow_approvals ORDER BY approval_id"
                )
            ],
            "spikes": conn.execute("SELECT COUNT(*) FROM spikes").fetchone()[0],
            "comments": conn.execute(
                "SELECT COUNT(*) FROM Comments"
            ).fetchone()[0],
        }

    def test_fresh_database_initializes_the_workflow_schema(self):
        conn = db.connect(str(self.db_path()))
        try:
            self.assertTrue(WORKFLOW_TABLES <= object_names(conn, "table"))
            self.assertTrue(WORKFLOW_TRIGGERS <= object_names(conn, "trigger"))
            self.assertEqual(
                conn.execute("PRAGMA foreign_keys").fetchone()[0],
                1,
                "normal connect must keep foreign key enforcement on",
            )
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()

    def test_legacy_database_with_content_and_comments_is_preserved(self):
        path = self.legacy_db()
        conn = db.connect(str(path))
        try:
            self.assertTrue(WORKFLOW_TABLES <= object_names(conn, "table"))
            self.assertEqual(
                [row[0] for row in conn.execute("SELECT id FROM spikes")],
                ["spike-legacy"],
            )
            self.assertEqual(
                conn.execute(
                    "SELECT draft_content FROM iterations"
                ).fetchone()[0],
                "Exact draft text.  ",
            )
            self.assertEqual(
                conn.execute("SELECT body FROM Comments").fetchone()[0],
                "Legacy comment body",
            )
        finally:
            conn.close()

    def test_repeated_initialization_preserves_counts_ids_and_legacy_rows(self):
        path = self.legacy_db("repeated.db")
        conn = db.connect(str(path))
        self.insert_item(conn)
        self.insert_version(conn)
        self.insert_approval(conn)
        conn.commit()
        expected = self.snapshot(conn)
        conn.close()

        for _ in range(2):
            conn = db.connect(str(path))
            try:
                self.assertEqual(self.snapshot(conn), expected)
                self.assertEqual(
                    conn.execute("SELECT body FROM Comments").fetchone()[0],
                    "Legacy comment body",
                )
            finally:
                conn.close()

    def test_constraints_reject_invalid_revisions_states_and_duplicates(self):
        conn = db.connect(str(self.db_path()))
        try:
            self.insert_item(conn)
            self.insert_version(conn)
            conn.commit()

            for label, call in (
                ("stage", lambda: self.insert_item(conn, "itm_bad", stage="published")),
                ("revision", lambda: self.insert_item(conn, "itm_zero", revision=0)),
                (
                    "duplicate revision",
                    lambda: self.insert_version(conn, "ver_dup", revision=1),
                ),
                (
                    "digest",
                    lambda: self.insert_version(
                        conn, "ver_digest", revision=2,
                        artifact_digest="sha256:short",
                    ),
                ),
                (
                    "operation kind",
                    lambda: self.insert_operation(conn, "op_bad", kind="publish"),
                ),
                (
                    "review state",
                    lambda: self.insert_review(conn, "rev_bad", state="superseded"),
                ),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        call()

            self.insert_idempotency(conn, "req_dup")
            with self.assertRaises(sqlite3.IntegrityError):
                self.insert_idempotency(conn, "req_dup")
        finally:
            conn.close()

    def test_owned_parent_child_references_are_enforced(self):
        conn = db.connect(str(self.db_path()))
        try:
            self.insert_item(conn, "itm_a", "own_01")
            self.insert_item(conn, "itm_b", "own_02")
            self.insert_version(conn, "ver_b", "itm_b", "own_02")
            conn.commit()

            for label, call in (
                (
                    "version",
                    lambda: self.insert_version(
                        conn, "ver_mix", "itm_a", "own_02"
                    ),
                ),
                (
                    "review",
                    lambda: self.insert_review(
                        conn, "rev_mix", "itm_a", "own_02", "ver_b"
                    ),
                ),
                (
                    "operation",
                    lambda: self.insert_operation(
                        conn, "op_mix", "itm_a", "own_02", "ver_b"
                    ),
                ),
                (
                    "approval",
                    lambda: self.insert_approval(
                        conn, "apr_mix", "itm_a", "own_02", "ver_b"
                    ),
                ),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        call()
        finally:
            conn.close()

    def test_same_owner_cross_item_links_are_rejected_and_ancestry_is_allowed(self):
        conn = db.connect(str(self.db_path()))
        try:
            self.insert_item(conn, "itm_a", "own_01")
            self.insert_item(conn, "itm_b", "own_01")
            self.insert_item(conn, "itm_c", "own_02")
            self.insert_version(conn, "ver_a", "itm_a", "own_01")
            self.insert_version(conn, "ver_b", "itm_b", "own_01")
            conn.commit()

            for label, call in (
                (
                    "approval",
                    lambda: self.insert_approval(
                        conn, "apr_cross", "itm_a", "own_01", "ver_b"
                    ),
                ),
                (
                    "review",
                    lambda: self.insert_review(
                        conn, "rev_cross", "itm_a", "own_01", "ver_b"
                    ),
                ),
                (
                    "operation",
                    lambda: self.insert_operation(
                        conn, "op_cross", "itm_a", "own_01", "ver_b"
                    ),
                ),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        call()

            self.insert_approval(conn, "apr_a", "itm_a", "own_01", "ver_a")
            self.insert_approval(conn, "apr_b", "itm_b", "own_01", "ver_b")
            self.insert_review(conn, "rev_b", "itm_b", "own_01", "ver_b")
            self.insert_operation(conn, "op_b", "itm_b", "own_01", "ver_b")

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE workflow_items SET active_approval_id = 'apr_b'"
                    " WHERE item_id = 'itm_a'"
                )
            conn.execute(
                "UPDATE workflow_items SET active_approval_id = 'apr_a'"
                " WHERE item_id = 'itm_a'"
            )

            # Cross-item ancestry is intentional for linked adaptations.
            conn.execute(
                "UPDATE workflow_items SET parent_version_id = 'ver_b'"
                " WHERE item_id = 'itm_a'"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE workflow_items SET parent_version_id = 'ver_a'"
                    " WHERE item_id = 'itm_c'"
                )
            conn.commit()

            row = conn.execute(
                "SELECT active_approval_id, parent_version_id"
                " FROM workflow_items WHERE item_id = 'itm_a'"
            ).fetchone()
            self.assertEqual((row[0], row[1]), ("apr_a", "ver_b"))
        finally:
            conn.close()

    def test_version_and_approval_rows_cannot_be_updated_or_deleted(self):
        conn = db.connect(str(self.db_path()))
        try:
            self.insert_item(conn)
            self.insert_version(conn)
            self.insert_approval(conn)
            conn.commit()

            for label, sql in (
                (
                    "version update",
                    "UPDATE workflow_versions SET artifact_json = '{\"segments\":"
                    " [\"changed\"]}' WHERE version_id = 'ver_a'",
                ),
                ("version delete", "DELETE FROM workflow_versions WHERE version_id = 'ver_a'"),
                (
                    "approval update",
                    "UPDATE workflow_approvals SET approved_at ="
                    " '1999-01-01T00:00:00.000Z' WHERE approval_id = 'apr_a'",
                ),
                ("approval delete", "DELETE FROM workflow_approvals WHERE approval_id = 'apr_a'"),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(sql)

            self.assertEqual(
                conn.execute(
                    "SELECT artifact_json FROM workflow_versions"
                    " WHERE version_id = 'ver_a'"
                ).fetchone()[0],
                '{"segments": ["Exact text.  "]}',
            )
            self.assertEqual(
                conn.execute(
                    "SELECT approved_at FROM workflow_approvals"
                    " WHERE approval_id = 'apr_a'"
                ).fetchone()[0],
                TS,
            )
        finally:
            conn.close()

    def test_forced_mid_migration_failure_rolls_back_and_recovers(self):
        from content_machine.workflow import migrations

        path = self.legacy_db("failed.db")
        conn = db.connect(str(path), init=False)
        try:
            broken = migrations.MIGRATION_STATEMENTS[:3] + (
                "CREATE TABLE workflow_broken (",
            )
            with patch.object(migrations, "MIGRATION_STATEMENTS", broken):
                with self.assertRaises(sqlite3.OperationalError):
                    migrations.migrate_workflow(conn)

            self.assertFalse(WORKFLOW_TABLES & object_names(conn, "table"))
            self.assertFalse(conn.in_transaction)

            conn.execute(
                "INSERT INTO spikes(id, category, hook_thesis)"
                " VALUES ('spike-after', 'internal', 'after')"
            )
            conn.commit()
            db.init_db(conn)
            self.assertTrue(WORKFLOW_TABLES <= object_names(conn, "table"))
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM spikes").fetchone()[0], 2
            )
            self.assertEqual(
                conn.execute("SELECT body FROM Comments").fetchone()[0],
                "Legacy comment body",
            )
        finally:
            conn.close()

    def test_migration_preserves_caller_transaction_and_row_factory(self):
        from content_machine.workflow import migrations

        path = self.legacy_db("caller-tx.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN")
            conn.execute(
                "INSERT INTO spikes(id, category, hook_thesis)"
                " VALUES ('spike-tx', 'internal', 'tx')"
            )
            migrations.migrate_workflow(conn)

            self.assertTrue(conn.in_transaction)
            self.assertIs(conn.row_factory, sqlite3.Row)

            conn.rollback()
            self.assertFalse(WORKFLOW_TABLES & object_names(conn, "table"))
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM spikes WHERE id = 'spike-tx'"
                ).fetchone()[0],
                0,
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
