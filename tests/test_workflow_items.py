"""Tests for C05 owned working-item persistence.

Covers create/list/get/save with two owners and duplicate titles, owner-filtered
reads and writes, compare-and-set saves, concurrency, idempotent replay and
conflict detection, exact text/whitespace preservation, metadata-only saves,
approval invalidation and input validation.

All tests use a cleaned TemporaryDirectory-backed SQLite database. No storage
home outside the test directory, provider or network is used.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow import items  # noqa: E402
from content_machine.workflow.errors import WorkflowError  # noqa: E402
from content_machine.workflow.migrations import migrate_workflow  # noqa: E402
from content_machine.workflow.persistence import canonical_json  # noqa: E402
from content_machine.workflow.schemas import (  # noqa: E402
    Artifact,
    Context,
    ItemCreate,
    ItemPatch,
    Principal,
)

TS = "2026-11-05T09:12:00.000Z"
DIGEST = "sha256:" + ("a" * 64)


def principal(owner_id: str) -> Principal:
    return Principal(owner_id=owner_id, mode="trusted_local")


def create_payload(title: str = "Indexing tradeoffs") -> ItemCreate:
    return ItemCreate(
        title=title,
        destination="linkedin",
        format="linkedin_post",
    )


def text(value: str) -> Artifact:
    return Artifact(segments=[value])


class WorkflowItemsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c05-home-")
        self._previous_home = os.environ.get("CONTENT_MACHINE_HOME")
        os.environ["CONTENT_MACHINE_HOME"] = self._home.name

        def restore_environment() -> None:
            if self._previous_home is None:
                os.environ.pop("CONTENT_MACHINE_HOME", None)
            else:
                os.environ["CONTENT_MACHINE_HOME"] = self._previous_home
            self._home.cleanup()

        self.addCleanup(restore_environment)
        self.db_path = Path(self._home.name) / "workflow.db"
        self.conn = self._connect()
        self.addCleanup(self.conn.close)
        self.a = principal("own_A")
        self.b = principal("own_B")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        migrate_workflow(conn)
        conn.commit()
        return conn

    def _create(
        self,
        *,
        owner: Principal | None = None,
        title: str = "Indexing tradeoffs",
        key: str = "req_create",
        conn: sqlite3.Connection | None = None,
    ) -> dict:
        result = items.create_item(
            conn or self.conn,
            owner or self.a,
            create_payload(title),
            request_id=key,
        )
        return result.body["item"]

    def _save(
        self,
        item_id: str,
        patch: ItemPatch,
        *,
        key: str = "req_save",
        owner: Principal | None = None,
        conn: sqlite3.Connection | None = None,
    ):
        return items.save_item(
            conn or self.conn,
            owner or self.a,
            item_id,
            patch,
            request_id=key,
        )

    def _seed_approval(self, item: dict) -> None:
        """Insert the minimal immutable version/approval rows for revision 2."""

        version_id = "ver_02"
        approval_id = "apr_02"
        self.conn.execute(
            "INSERT INTO workflow_versions("
            " version_id, item_id, owner_id, revision, context_json,"
            " artifact_json, destination, format, artifact_digest, purpose,"
            " created_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version_id,
                item["item_id"],
                item["owner_id"],
                item["working_revision"],
                canonical_json(item["context"]),
                canonical_json(item["artifact"]),
                item["destination"],
                item["format"],
                DIGEST,
                "approval",
                item["owner_id"],
                TS,
            ),
        )
        self.conn.execute(
            "INSERT INTO workflow_approvals("
            " approval_id, owner_id, item_id, version_id, artifact_digest,"
            " destination, format, approved_by, approved_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                approval_id,
                item["owner_id"],
                item["item_id"],
                version_id,
                DIGEST,
                item["destination"],
                item["format"],
                item["owner_id"],
                TS,
            ),
        )
        self.conn.execute(
            "UPDATE workflow_items SET active_approval_id = ?, stage = 'approve'"
            " WHERE item_id = ? AND owner_id = ?",
            (approval_id, item["item_id"], item["owner_id"]),
        )
        self.conn.commit()

    def test_create_list_and_get_are_owner_scoped_and_titles_are_labels(self) -> None:
        a = self._create(key="req_shared")
        b = self._create(owner=self.b, key="req_shared")

        self.assertEqual(a["title"], b["title"])
        self.assertNotEqual(a["item_id"], b["item_id"])
        self.assertTrue(a["item_id"].startswith("itm_"))
        self.assertEqual(
            (
                a["working_revision"],
                a["stage"],
                a["active_approval_id"],
                a["artifact"],
                a["context"]["notes"],
            ),
            (1, "idea", None, {"segments": []}, ""),
        )

        self.assertEqual(
            [item.item_id for item in items.list_items(self.conn, self.a)],
            [a["item_id"]],
        )
        self.assertEqual(
            [item.item_id for item in items.list_items(self.conn, self.b)],
            [b["item_id"]],
        )

        loaded = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                loaded.title,
                loaded.destination,
                loaded.format,
                loaded.stage,
                loaded.working_revision,
            ),
            (a["title"], "linkedin", "linkedin_post", "idea", 1),
        )

        with self.assertRaises(WorkflowError) as raised:
            items.get_item(self.conn, self.a, b["item_id"])
        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code, error.current),
            (404, "item_not_found", None),
        )

    def test_cross_owner_save_is_not_found_and_cannot_mutate(self) -> None:
        a = self._create()

        with self.assertRaises(WorkflowError) as raised:
            self._save(
                a["item_id"],
                ItemPatch(expected_revision=1, artifact=text("B text")),
                key="req_b_save",
                owner=self.b,
            )

        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code, error.current),
            (404, "item_not_found", None),
        )
        self.assertEqual(
            items.get_item(self.conn, self.a, a["item_id"]).artifact.segments,
            [],
        )

    def test_stale_revision_conflicts_and_preserves_newer_text(self) -> None:
        a = self._create()
        newer = self._save(
            a["item_id"],
            ItemPatch(expected_revision=1, artifact=text("newer  ")),
            key="req_newer",
        ).body["item"]

        with self.assertRaises(WorkflowError) as raised:
            self._save(
                a["item_id"],
                ItemPatch(expected_revision=1, artifact=text("stale overwrite")),
                key="req_stale",
            )

        error = raised.exception
        self.assertEqual((error.status_code, error.code), (409, "revision_conflict"))
        self.assertEqual(
            error.current,
            {
                "working_revision": 2,
                "stage": "draft_review",
                "updated_at": newer["updated_at"],
                "active_approval_id": None,
            },
        )
        self.assertEqual(
            items.get_item(self.conn, self.a, a["item_id"]).artifact.segments,
            ["newer  "],
        )
        rejected_record = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_idempotency"
            " WHERE owner_id = ? AND request_id = ?",
            (self.a.owner_id, "req_stale"),
        ).fetchone()[0]
        self.assertEqual(rejected_record, 0)

    def test_concurrent_saves_allow_one_writer_and_one_revision_conflict(self) -> None:
        a = self._create()
        other = self._connect()
        self.addCleanup(other.close)
        barrier = threading.Barrier(2)

        def attempt(conn: sqlite3.Connection, value: str, key: str):
            barrier.wait(timeout=10)
            try:
                return self._save(
                    a["item_id"],
                    ItemPatch(expected_revision=1, artifact=text(value)),
                    key=key,
                    conn=conn,
                )
            except WorkflowError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(attempt, self.conn, "alpha", "req_alpha"),
                pool.submit(attempt, other, "beta", "req_beta"),
            ]
            results = [future.result(timeout=15) for future in futures]

        successes = [result for result in results if not isinstance(result, WorkflowError)]
        conflicts = [result for result in results if isinstance(result, WorkflowError)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].status_code, 409)
        self.assertEqual(conflicts[0].code, "revision_conflict")

        current = items.get_item(self.conn, self.a, a["item_id"])
        winner = successes[0].body["item"]["artifact"]["segments"]
        self.assertEqual(current.working_revision, 2)
        self.assertEqual(current.artifact.segments, winner)

    def test_matching_create_and_save_retries_replay_without_new_revisions(self) -> None:
        create_input = create_payload()
        original_create = items.create_item(
            self.conn, self.a, create_input, request_id="req_create"
        )
        item_id = original_create.body["item"]["item_id"]
        first_save = self._save(
            item_id,
            ItemPatch(expected_revision=1, artifact=text("second")),
            key="req_save",
        )
        self._save(
            item_id,
            ItemPatch(expected_revision=2, artifact=text("third")),
            key="req_save_2",
        )

        replay_create = items.create_item(
            self.conn, self.a, create_input, request_id="req_create"
        )
        replay_save = self._save(
            item_id,
            ItemPatch(expected_revision=1, artifact=text("second")),
            key="req_save",
        )

        self.assertEqual(
            (replay_create.status_code, replay_create.body),
            (201, original_create.body),
        )
        self.assertEqual(
            (replay_save.status_code, replay_save.body),
            (200, first_save.body),
        )
        current = items.get_item(self.conn, self.a, item_id)
        self.assertEqual(current.working_revision, 3)
        self.assertEqual(current.artifact.segments, ["third"])
        self.assertEqual(len(items.list_items(self.conn, self.a)), 1)

    def test_reused_key_with_changed_body_or_resource_conflicts_without_writes(
        self,
    ) -> None:
        created = items.create_item(
            self.conn, self.a, create_payload(), request_id="req_create"
        )
        item_id = created.body["item"]["item_id"]

        with self.assertRaises(WorkflowError) as raised:
            items.create_item(
                self.conn,
                self.a,
                create_payload("Different title"),
                request_id="req_create",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(len(items.list_items(self.conn, self.a)), 1)

        self._save(
            item_id,
            ItemPatch(expected_revision=1, artifact=text("first")),
            key="req_save",
        )
        with self.assertRaises(WorkflowError) as raised:
            self._save(
                item_id,
                ItemPatch(expected_revision=2, artifact=text("different")),
                key="req_save",
            )
        self.assertEqual(raised.exception.code, "idempotency_conflict")

        other = self._create(key="req_other")
        with self.assertRaises(WorkflowError) as raised:
            self._save(
                other["item_id"],
                ItemPatch(expected_revision=1, artifact=text("first")),
                key="req_save",
            )
        self.assertEqual(raised.exception.code, "idempotency_conflict")

        self.assertEqual(
            items.get_item(self.conn, self.a, item_id).artifact.segments, ["first"]
        )
        self.assertEqual(
            items.get_item(self.conn, self.a, other["item_id"]).artifact.segments, []
        )

    def test_failed_success_record_rolls_back_item_update(self) -> None:
        a = self._create()

        with patch.object(
            items, "record_idempotent", side_effect=RuntimeError("forced failure")
        ):
            with self.assertRaises(RuntimeError):
                self._save(
                    a["item_id"],
                    ItemPatch(expected_revision=1, artifact=text("not committed")),
                    key="req_fail",
                )

        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual((current.working_revision, current.artifact.segments), (1, []))
        count = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_idempotency"
            " WHERE owner_id = ? AND request_id = ?",
            (self.a.owner_id, "req_fail"),
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_exact_text_survives_and_metadata_or_unchanged_saves_keep_revision(
        self,
    ) -> None:
        a = self._create()
        exact = "Line one\nLine two  "
        notes = "  note text  \n"
        saved = self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=1,
                artifact=text(exact),
                context=Context(notes=notes),
            ),
            key="req_text",
        ).body["item"]
        self.assertEqual((saved["working_revision"], saved["stage"]), (2, "draft_review"))
        loaded = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(loaded.artifact.segments, [exact])
        self.assertEqual(loaded.context.notes, notes)

        titled = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, title="  Renamed  "),
            key="req_title",
        ).body["item"]
        self.assertEqual(
            (titled["title"], titled["working_revision"], titled["stage"]),
            ("  Renamed  ", 2, "draft_review"),
        )

        staged = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, stage="approve"),
            key="req_stage",
        ).body["item"]
        self.assertEqual(
            (staged["stage"], staged["working_revision"], staged["title"]),
            ("approve", 2, "  Renamed  "),
        )

        unchanged = self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=2,
                artifact=text(exact),
                context=Context(notes=notes),
            ),
            key="req_unchanged",
        ).body["item"]
        self.assertEqual(
            (
                unchanged["working_revision"],
                unchanged["stage"],
                unchanged["title"],
                unchanged["active_approval_id"],
                unchanged["artifact"]["segments"],
            ),
            (2, "approve", "  Renamed  ", None, [exact]),
        )

    def test_invalid_merged_pairs_and_explicit_nulls_are_rejected_without_writes(
        self,
    ) -> None:
        a = self._create()
        invalid_pairs = (
            ItemPatch(expected_revision=1, format="x_thread"),
            ItemPatch(expected_revision=1, destination="x"),
        )
        for index, patch in enumerate(invalid_pairs):
            with self.subTest(patch=patch):
                with self.assertRaises(WorkflowError) as raised:
                    self._save(
                        a["item_id"], patch, key=f"req_bad_pair_{index}"
                    )
                self.assertEqual(
                    (raised.exception.status_code, raised.exception.code),
                    (422, "invalid_item"),
                )
                self.assertEqual(
                    items.get_item(
                        self.conn, self.a, a["item_id"]
                    ).working_revision,
                    1,
                )

        explicit_nulls = (
            ItemPatch(expected_revision=1, title=None),
            ItemPatch(expected_revision=1, destination=None),
            ItemPatch(expected_revision=1, format=None),
            ItemPatch(expected_revision=1, stage=None),
            ItemPatch(expected_revision=1, context=None),
            ItemPatch(expected_revision=1, artifact=None),
        )
        for index, patch in enumerate(explicit_nulls):
            with self.subTest(patch=patch):
                with self.assertRaises(WorkflowError) as raised:
                    self._save(
                        a["item_id"], patch, key=f"req_null_{index}"
                    )
                self.assertEqual(
                    (raised.exception.status_code, raised.exception.code),
                    (422, "invalid_item"),
                )
                self.assertEqual(
                    items.get_item(
                        self.conn, self.a, a["item_id"]
                    ).working_revision,
                    1,
                )

        changed = self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=1, destination="x", format="x_thread"
            ),
            key="req_valid_pair",
        ).body["item"]
        self.assertEqual(
            (
                changed["working_revision"],
                changed["destination"],
                changed["format"],
                changed["stage"],
            ),
            (2, "x", "x_thread", "draft_review"),
        )

    def test_content_edits_invalidate_active_approval_while_metadata_saves_preserve_it(
        self,
    ) -> None:
        a = self._create()
        approved = self._save(
            a["item_id"],
            ItemPatch(expected_revision=1, artifact=text("Approved text.")),
            key="req_approved_text",
        ).body["item"]
        self._seed_approval(approved)

        titled = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, title="Renamed"),
            key="req_title",
        ).body["item"]
        self.assertEqual(
            (
                titled["working_revision"],
                titled["stage"],
                titled["active_approval_id"],
            ),
            (2, "approve", "apr_02"),
        )

        staged = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, stage="draft_review"),
            key="req_stage",
        ).body["item"]
        self.assertEqual(
            (
                staged["working_revision"],
                staged["stage"],
                staged["active_approval_id"],
            ),
            (2, "draft_review", "apr_02"),
        )

        unchanged = self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=2,
                artifact=text("Approved text."),
                context=Context(),
            ),
            key="req_unchanged_approval",
        ).body["item"]
        self.assertEqual(
            (
                unchanged["working_revision"],
                unchanged["stage"],
                unchanged["active_approval_id"],
            ),
            (2, "draft_review", "apr_02"),
        )

        edited = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, artifact=text("Approved text. ")),
            key="req_edit",
        ).body["item"]
        self.assertEqual(
            (
                edited["working_revision"],
                edited["stage"],
                edited["active_approval_id"],
            ),
            (3, "draft_review", None),
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_approvals WHERE item_id = ?",
            (a["item_id"],),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_commit_failure_rolls_back_pending_save_and_success_record(self) -> None:
        a = self._create()
        reader = self._connect()
        self.addCleanup(reader.close)
        self.conn.execute("PRAGMA busy_timeout = 0")
        reader.execute("BEGIN")
        reader.execute(
            "SELECT item_id FROM workflow_items WHERE item_id = ?",
            (a["item_id"],),
        ).fetchall()

        patch = ItemPatch(
            expected_revision=1, artifact=text("Unacknowledged change")
        )
        with self.assertRaises(sqlite3.OperationalError) as raised:
            self._save(a["item_id"], patch, key="failed-save")
        self.assertIn("locked", str(raised.exception))
        self.assertFalse(self.conn.in_transaction)

        reader.rollback()
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual((current.working_revision, current.artifact.segments), (1, []))
        count = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_idempotency"
            " WHERE owner_id = ? AND request_id = ?",
            (self.a.owner_id, "failed-save"),
        ).fetchone()[0]
        self.assertEqual(count, 0)

        saved = self._save(a["item_id"], patch, key="failed-save")
        self.assertEqual(
            (saved.status_code, saved.body["item"]["working_revision"]),
            (200, 2),
        )
        self.assertEqual(
            saved.body["item"]["artifact"]["segments"],
            ["Unacknowledged change"],
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_idempotency"
            " WHERE owner_id = ? AND request_id = ?",
            (self.a.owner_id, "failed-save"),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_save_does_not_commit_a_caller_owned_transaction(self) -> None:
        a = self._create()
        self.conn.execute("BEGIN")
        saved = self._save(
            a["item_id"],
            ItemPatch(expected_revision=1, artifact=text("temporary")),
            key="req_nested_transaction",
        )
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(saved.body["item"]["working_revision"], 2)

        self.conn.rollback()
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (current.working_revision, current.artifact.segments),
            (1, []),
        )

    def test_export_stage_requires_a_current_approval(self) -> None:
        a = self._create()
        approved = self._save(
            a["item_id"],
            ItemPatch(expected_revision=1, artifact=text("Export me.")),
            key="req_text",
        ).body["item"]

        with self.assertRaises(WorkflowError) as raised:
            self._save(
                a["item_id"],
                ItemPatch(expected_revision=2, stage="export"),
                key="req_export_too_early",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual((current.working_revision, current.stage), (2, "draft_review"))

        self._seed_approval(approved)
        exported = self._save(
            a["item_id"],
            ItemPatch(expected_revision=2, stage="export"),
            key="req_export",
        ).body["item"]
        self.assertEqual(
            (
                exported["working_revision"],
                exported["stage"],
                exported["active_approval_id"],
            ),
            (2, "export", "apr_02"),
        )

        with self.assertRaises(WorkflowError) as raised:
            self._save(
                a["item_id"],
                ItemPatch(
                    expected_revision=2,
                    artifact=text("Changed."),
                    stage="export",
                ),
                key="req_export_edit",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )
        reloaded = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                reloaded.working_revision,
                reloaded.stage,
                reloaded.active_approval_id,
                reloaded.artifact.segments,
            ),
            (2, "export", "apr_02", ["Export me."]),
        )
