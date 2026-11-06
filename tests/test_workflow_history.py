"""Tests for C08 historical inspection, restore and linked adaptations.

Covers read-only status reporting, owner-bound source snapshots, restoration
with current-work preservation, fresh approval after equal-text restoration,
stale/cross-owner/cross-item denial, approved-source adaptation, independent
target state, idempotent retries and atomic rollback.

Every database is a cleaned TemporaryDirectory-backed SQLite file. No provider,
network or production storage path is used.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow import (  # noqa: E402
    adaptations,
    approvals,
    exports,
    history,
    items,
    versions,
)
from content_machine.workflow.errors import WorkflowError  # noqa: E402
from content_machine.workflow.migrations import migrate_workflow  # noqa: E402
from content_machine.workflow.schema_types import VersionPurpose  # noqa: E402
from content_machine.workflow.schemas import (  # noqa: E402
    AdaptRequest,
    ApproveRequest,
    Artifact,
    Context,
    ItemCreate,
    ItemPatch,
    Principal,
    RestoreRequest,
    SourceRef,
)

TS = "2026-11-05T09:12:00.000Z"


def principal(owner_id: str) -> Principal:
    return Principal(owner_id=owner_id, mode="trusted_local")


def expected_digest(destination: str, format: str, segments: list[str]) -> str:
    payload = {"destination": destination, "format": format, "segments": segments}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def text(value: str) -> Artifact:
    return Artifact(segments=[value])


def approved_context() -> Context:
    return Context(
        notes="  approved notes\r\n",
        experience="lived experience",
        interpretation="  interpretation  ",
        sources=[
            SourceRef(
                source_id="src_01",
                url="https://example.test/source",
                title="Source title",
                excerpt="  exact excerpt  ",
                fetched_at=TS,
            )
        ],
        preference_snapshot_id="pref_01",
    )


class WorkflowHistoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c08-home-")
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
        self._sequence = 0

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        migrate_workflow(conn)
        conn.commit()
        return conn

    def _next_key(self, prefix: str) -> str:
        self._sequence += 1
        return f"{prefix}-{self._sequence}"

    def _create(
        self,
        *,
        owner: Principal | None = None,
        title: str = "History item",
        destination: str = "linkedin",
        format: str = "linkedin_post",
    ) -> dict:
        result = items.create_item(
            self.conn,
            owner or self.a,
            ItemCreate(title=title, destination=destination, format=format),
            request_id=self._next_key("create"),
        )
        return result.body["item"]

    def _save(
        self,
        item_id: str,
        *,
        expected_revision: int,
        artifact: Artifact | None = None,
        context: Context | None = None,
        title: str | None = None,
        destination: str | None = None,
        format: str | None = None,
        owner: Principal | None = None,
    ) -> dict:
        patch: dict = {"expected_revision": expected_revision}
        if artifact is not None:
            patch["artifact"] = artifact
        if context is not None:
            patch["context"] = context
        if title is not None:
            patch["title"] = title
        if destination is not None:
            patch["destination"] = destination
        if format is not None:
            patch["format"] = format
        result = items.save_item(
            self.conn,
            owner or self.a,
            item_id,
            ItemPatch(**patch),
            request_id=self._next_key("save"),
        )
        return result.body["item"]

    def _freeze(
        self,
        item_id: str,
        revision: int,
        *,
        purpose: VersionPurpose = VersionPurpose.REVIEW,
        owner: Principal | None = None,
    ):
        return versions.freeze_version(
            self.conn,
            owner or self.a,
            item_id,
            expected_revision=revision,
            purpose=purpose,
        )

    def _approve(
        self,
        item: dict,
        *,
        owner: Principal | None = None,
        key: str | None = None,
    ):
        return approvals.approve_item(
            self.conn,
            owner or self.a,
            item["item_id"],
            ApproveRequest(
                expected_revision=item["working_revision"],
                artifact_digest=expected_digest(
                    item["destination"],
                    item["format"],
                    item["artifact"]["segments"],
                ),
                consent=True,
            ),
            request_id=key if key is not None else self._next_key("approve"),
        )

    def _history(self, item_id: str, *, owner: Principal | None = None) -> dict:
        return history.get_history(self.conn, owner or self.a, item_id)

    def _restore(
        self,
        item_id: str,
        version_id: str,
        expected_revision: int,
        *,
        owner: Principal | None = None,
        key: str | None = None,
    ):
        return history.restore_version(
            self.conn,
            owner or self.a,
            item_id,
            RestoreRequest(
                expected_revision=expected_revision,
                version_id=version_id,
            ),
            request_id=key if key is not None else self._next_key("restore"),
        )

    def _adapt(
        self,
        source_item_id: str,
        source_version_id: str,
        destination: str,
        format: str,
        *,
        owner: Principal | None = None,
        key: str | None = None,
    ):
        return adaptations.adapt_version(
            self.conn,
            owner or self.a,
            source_item_id,
            AdaptRequest(
                source_version_id=source_version_id,
                destination=destination,
                format=format,
            ),
            request_id=key if key is not None else self._next_key("adapt"),
        )

    def _export(
        self,
        item_id: str,
        version_id: str,
        *,
        owner: Principal | None = None,
    ):
        return exports.export_version(
            self.conn, owner or self.a, item_id, version_id
        )

    def _count(self, table: str, item_id: str) -> int:
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE item_id = ?", (item_id,)
        ).fetchone()[0]

    def _key_count(self, owner: Principal, request_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM workflow_idempotency"
            " WHERE owner_id = ? AND request_id = ?",
            (owner.owner_id, request_id),
        ).fetchone()[0]

    def test_history_is_read_only_and_marks_active_then_historical_approval(
        self,
    ) -> None:
        a = self._create()
        exact = "  approved history  \n"
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text(exact)
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        approval_id = approved.body["approval"]["approval_id"]
        version = versions.get_version(
            self.conn, self.a, version_id, item_id=a["item_id"]
        )

        active = self._history(a["item_id"])

        self.assertEqual(set(active), {"versions", "approvals"})
        self.assertEqual(
            active["versions"],
            [
                {
                    "version_id": version.version_id,
                    "revision": 2,
                    "purpose": "approval",
                    "artifact_digest": version.artifact_digest,
                    "destination": "linkedin",
                    "format": "linkedin_post",
                    "created_at": version.created_at,
                }
            ],
        )
        self.assertEqual(
            active["approvals"],
            [
                {
                    "approval_id": approval_id,
                    "version_id": version_id,
                    "status": "active",
                    "approved_at": approved.body["approval"]["approved_at"],
                }
            ],
        )

        before = items.get_item(self.conn, self.a, a["item_id"])
        version_count = self._count("workflow_versions", a["item_id"])
        approval_count = self._count("workflow_approvals", a["item_id"])
        edited = self._save(
            a["item_id"], expected_revision=2, artifact=text("later work")
        )

        historical = self._history(a["item_id"])

        self.assertEqual(
            historical["approvals"][0]["status"], "historical"
        )
        self.assertEqual(
            historical["versions"][0]["version_id"], version_id
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), version_count
        )
        self.assertEqual(
            self._count("workflow_approvals", a["item_id"]), approval_count
        )
        after = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(after.working_revision, 3)
        self.assertEqual(after.artifact.segments, ["later work"])
        self.assertNotEqual(before.updated_at, edited["updated_at"])

        with self.assertRaises(WorkflowError) as raised:
            self._history(a["item_id"], owner=self.b)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "item_not_found"),
        )

    def test_restore_preserves_current_work_and_approved_history(self) -> None:
        a = self._create(title="Original title")
        source_text = "  restored text\r\nsecond line  \n"
        source_context = approved_context()
        saved = self._save(
            a["item_id"],
            expected_revision=1,
            artifact=text(source_text),
            context=source_context,
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        approval_id = approved.body["approval"]["approval_id"]
        current_context = Context(notes="current working context")
        current = self._save(
            a["item_id"],
            expected_revision=2,
            artifact=text("current working  \n"),
            context=current_context,
            title="Current title",
        )

        result = self._restore(
            a["item_id"], version_id, current["working_revision"]
        )

        self.assertEqual(result.status_code, 200)
        restored = result.body["item"]
        new_version = result.body["version"]
        self.assertEqual(
            (
                restored["title"],
                restored["working_revision"],
                restored["stage"],
                restored["active_approval_id"],
                restored["parent_version_id"],
                restored["destination"],
                restored["format"],
                restored["artifact"]["segments"],
            ),
            (
                "Current title",
                4,
                "draft_review",
                None,
                version_id,
                "linkedin",
                "linkedin_post",
                [source_text],
            ),
        )
        self.assertEqual(restored["context"], source_context.model_dump(mode="json"))
        self.assertEqual(
            (
                new_version["item_id"],
                new_version["revision"],
                new_version["purpose"],
                new_version["artifact"]["segments"],
                new_version["context"],
            ),
            (
                a["item_id"],
                4,
                "restore",
                [source_text],
                source_context.model_dump(mode="json"),
            ),
        )

        stored = {
            version.revision: version
            for version in versions.list_versions(
                self.conn, self.a, item_id=a["item_id"]
            )
        }
        self.assertEqual(set(stored), {2, 3, 4})
        self.assertEqual(stored[2].version_id, version_id)
        self.assertEqual(stored[2].artifact.segments, [source_text])
        self.assertEqual(stored[3].artifact.segments, ["current working  \n"])
        self.assertEqual(stored[3].context, current_context)
        self.assertEqual(stored[3].purpose, VersionPurpose.RESTORE)
        self.assertEqual(stored[4].purpose, VersionPurpose.RESTORE)

        current_item = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(current_item.active_approval_id, None)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        self.assertEqual(
            self._count("workflow_reviews", a["item_id"]), 0
        )
        self.assertEqual(
            self._count("workflow_operations", a["item_id"]), 0
        )
        self.assertEqual(
            approvals.get_approval(
                self.conn, self.a, approval_id, item_id=a["item_id"]
            ).version_id,
            version_id,
        )
        self.assertEqual(
            self._export(a["item_id"], version_id).content,
            source_text.encode("utf-8"),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], new_version["version_id"])
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )

    def test_equal_text_restore_creates_a_revision_needing_fresh_approval(
        self,
    ) -> None:
        a = self._create()
        exact = "same exact text  \n"
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text(exact)
        )
        approved = self._approve(saved)
        source_version_id = approved.body["version"]["version_id"]

        restored = self._restore(a["item_id"], source_version_id, 2)

        item = restored.body["item"]
        new_version_id = restored.body["version"]["version_id"]
        self.assertEqual(
            (
                item["working_revision"],
                item["stage"],
                item["active_approval_id"],
                item["parent_version_id"],
                item["artifact"]["segments"],
            ),
            (3, "draft_review", None, source_version_id, [exact]),
        )
        self.assertNotEqual(new_version_id, source_version_id)
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 2
        )
        self.assertEqual(
            self._count("workflow_approvals", a["item_id"]), 1
        )
        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], new_version_id)
        self.assertEqual(raised.exception.code, "approval_required")

        reapproved = self._approve(item)
        self.assertTrue(
            reapproved.body["approval"]["approval_id"].startswith("apr_")
        )
        self.assertEqual(
            self._count("workflow_approvals", a["item_id"]), 2
        )
        self.assertEqual(
            self._export(a["item_id"], new_version_id).content,
            exact.encode("utf-8"),
        )

    def test_stale_cross_item_and_cross_owner_restore_write_nothing(
        self,
    ) -> None:
        a = self._create(title="Source")
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("source text")
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        current = self._save(
            a["item_id"], expected_revision=2, artifact=text("current text")
        )
        baseline_versions = self._count("workflow_versions", a["item_id"])
        baseline_approvals = self._count("workflow_approvals", a["item_id"])

        with self.assertRaises(WorkflowError) as raised:
            self._restore(a["item_id"], version_id, 2, key="stale-restore")
        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code), (409, "revision_conflict")
        )
        self.assertEqual(
            error.current,
            {
                "working_revision": 3,
                "stage": "draft_review",
                "updated_at": current["updated_at"],
                "active_approval_id": None,
            },
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]),
            baseline_versions,
        )
        self.assertEqual(self._key_count(self.a, "stale-restore"), 0)

        other = self._create(title="Same owner other item")
        other_before = items.get_item(
            self.conn, self.a, other["item_id"]
        )
        with self.assertRaises(WorkflowError) as raised:
            self._restore(
                other["item_id"], version_id, 1, key="wrong-item-restore"
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "version_not_found"),
        )
        self.assertEqual(
            items.get_item(self.conn, self.a, other["item_id"]),
            other_before,
        )
        self.assertEqual(
            self._count("workflow_versions", other["item_id"]), 0
        )
        self.assertEqual(self._key_count(self.a, "wrong-item-restore"), 0)

        with self.assertRaises(WorkflowError) as raised:
            self._restore(
                a["item_id"],
                version_id,
                3,
                owner=self.b,
                key="cross-owner-restore",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "item_not_found"),
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]),
            baseline_versions,
        )
        self.assertEqual(
            self._count("workflow_approvals", a["item_id"]),
            baseline_approvals,
        )
        self.assertEqual(self._key_count(self.b, "cross-owner-restore"), 0)

    def test_restore_retry_replays_and_changed_body_or_path_conflicts(
        self,
    ) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("approved source")
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        self._save(
            a["item_id"], expected_revision=2, artifact=text("current work")
        )

        original = self._restore(
            a["item_id"], version_id, 3, key="stable-restore"
        )
        replay = self._restore(
            a["item_id"], version_id, 3, key="stable-restore"
        )

        self.assertEqual(
            (replay.status_code, replay.body), (200, original.body)
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 3
        )
        self.assertEqual(
            self._key_count(self.a, "stable-restore"), 1
        )

        with self.assertRaises(WorkflowError) as raised:
            self._restore(
                a["item_id"], version_id, 4, key="stable-restore"
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 3
        )

        target_count = len(items.list_items(self.conn, self.a))
        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                a["item_id"],
                version_id,
                "instagram",
                "instagram_caption",
                key="stable-restore",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(
            len(items.list_items(self.conn, self.a)), target_count
        )

    def test_adapt_creates_independent_unapproved_item_from_approved_version(
        self,
    ) -> None:
        a = self._create(title="Adapt source")
        source_text = "  approved adaptation source  \n"
        source_context = approved_context()
        saved = self._save(
            a["item_id"],
            expected_revision=1,
            artifact=text(source_text),
            context=source_context,
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        approval_id = approved.body["approval"]["approval_id"]
        changed_context = Context(notes="unapproved current context")
        source_current = self._save(
            a["item_id"],
            expected_revision=2,
            artifact=text("unapproved current text"),
            context=changed_context,
            title="Renamed source",
        )

        result = self._adapt(
            a["item_id"],
            version_id,
            "instagram",
            "instagram_caption",
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(set(result.body), {"item"})
        target = result.body["item"]
        self.assertNotEqual(target["item_id"], a["item_id"])
        self.assertTrue(target["item_id"].startswith("itm_"))
        self.assertEqual(
            (
                target["owner_id"],
                target["title"],
                target["destination"],
                target["format"],
                target["stage"],
                target["working_revision"],
                target["parent_version_id"],
                target["active_approval_id"],
                target["artifact"]["segments"],
            ),
            (
                self.a.owner_id,
                "Renamed source",
                "instagram",
                "instagram_caption",
                "draft_review",
                1,
                version_id,
                None,
                [],
            ),
        )
        self.assertEqual(
            target["context"], source_context.model_dump(mode="json")
        )

        target_versions = versions.list_versions(
            self.conn, self.a, item_id=target["item_id"]
        )
        self.assertEqual(len(target_versions), 1)
        boundary = target_versions[0]
        self.assertEqual(
            (
                boundary.revision,
                boundary.purpose,
                boundary.destination,
                boundary.format,
                boundary.artifact.segments,
                boundary.context,
            ),
            (
                1,
                VersionPurpose.ADAPTATION,
                "instagram",
                "instagram_caption",
                [],
                source_context,
            ),
        )
        for table in (
            "workflow_approvals",
            "workflow_reviews",
            "workflow_operations",
        ):
            self.assertEqual(self._count(table, target["item_id"]), 0)

        source_after = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            source_after.model_dump(mode="json"), source_current
        )
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        self.assertEqual(
            approvals.get_approval(
                self.conn, self.a, approval_id, item_id=a["item_id"]
            ).version_id,
            version_id,
        )
        self.assertEqual(
            self._export(a["item_id"], version_id).content,
            source_text.encode("utf-8"),
        )
        self.assertEqual(
            self._count("workflow_approvals", target["item_id"]), 0
        )

    def test_adapt_rejects_unapproved_unknown_and_borrowed_sources(
        self,
    ) -> None:
        unapproved = self._create(title="Unapproved")
        unapproved_saved = self._save(
            unapproved["item_id"],
            expected_revision=1,
            artifact=text("unapproved source text"),
        )
        unapproved_version = self._freeze(
            unapproved["item_id"], unapproved_saved["working_revision"]
        )
        approved_item = self._create(title="Approved")
        approved_saved = self._save(
            approved_item["item_id"],
            expected_revision=1,
            artifact=text("approved source text"),
        )
        approved = self._approve(approved_saved)
        approved_version_id = approved.body["version"]["version_id"]
        other = self._create(title="Same owner other")
        baseline_items = len(items.list_items(self.conn, self.a))
        baseline_versions = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_versions"
        ).fetchone()[0]

        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                unapproved["item_id"],
                unapproved_version.version_id,
                "instagram",
                "instagram_caption",
                key="adapt-unapproved",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )
        self.assertEqual(self._key_count(self.a, "adapt-unapproved"), 0)

        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                approved_item["item_id"],
                "ver_missing",
                "instagram",
                "instagram_caption",
                key="adapt-unknown",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "version_not_found"),
        )

        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                other["item_id"],
                approved_version_id,
                "instagram",
                "instagram_caption",
                key="adapt-wrong-item",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "version_not_found"),
        )

        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                approved_item["item_id"],
                approved_version_id,
                "instagram",
                "instagram_caption",
                owner=self.b,
                key="adapt-cross-owner",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "item_not_found"),
        )

        self.assertEqual(
            len(items.list_items(self.conn, self.a)), baseline_items
        )
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM workflow_versions"
            ).fetchone()[0],
            baseline_versions,
        )
        for key in (
            "adapt-unknown",
            "adapt-wrong-item",
            "adapt-cross-owner",
        ):
            self.assertEqual(self._key_count(self.a, key), 0)

    def test_restore_failure_rolls_back_snapshots_item_and_success_record(
        self,
    ) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("approved source")
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        current = self._save(
            a["item_id"], expected_revision=2, artifact=text("current work")
        )
        self.conn.execute(
            "CREATE TRIGGER fail_restore_version"
            " BEFORE INSERT ON workflow_versions"
            " WHEN NEW.purpose = 'restore'"
            " BEGIN SELECT RAISE(ABORT, 'forced restore failure'); END"
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError) as raised:
            self._restore(
                a["item_id"], version_id, 3, key="failed-restore"
            )
        self.assertIn("forced restore failure", str(raised.exception))

        current_after = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                current_after.working_revision,
                current_after.stage,
                current_after.active_approval_id,
                current_after.artifact.segments,
            ),
            (3, "draft_review", None, ["current work"]),
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 1
        )
        self.assertEqual(
            self._count("workflow_approvals", a["item_id"]), 1
        )
        self.assertEqual(self._key_count(self.a, "failed-restore"), 0)
        self.assertEqual(
            self._export(a["item_id"], version_id).content,
            b"approved source",
        )
        self.assertEqual(current["working_revision"], 3)

        self.conn.execute("DROP TRIGGER fail_restore_version")
        self.conn.commit()
        retried = self._restore(
            a["item_id"], version_id, 3, key="failed-restore"
        )
        self.assertEqual(retried.body["item"]["working_revision"], 4)
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 3
        )
        self.assertEqual(self._key_count(self.a, "failed-restore"), 1)

    def test_adapt_failure_rolls_back_target_item_and_preserves_source(
        self,
    ) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("approved source")
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        self.conn.execute(
            "CREATE TRIGGER fail_adaptation_version"
            " BEFORE INSERT ON workflow_versions"
            " WHEN NEW.purpose = 'adaptation'"
            " BEGIN SELECT RAISE(ABORT, 'forced adaptation failure'); END"
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError) as raised:
            self._adapt(
                a["item_id"],
                version_id,
                "instagram",
                "instagram_caption",
                key="failed-adapt",
            )
        self.assertIn("forced adaptation failure", str(raised.exception))

        self.assertEqual(len(items.list_items(self.conn, self.a)), 1)
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM workflow_versions"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        self.assertEqual(self._key_count(self.a, "failed-adapt"), 0)
        self.assertEqual(
            self._export(a["item_id"], version_id).content,
            b"approved source",
        )

        self.conn.execute("DROP TRIGGER fail_adaptation_version")
        self.conn.commit()
        retried = self._adapt(
            a["item_id"],
            version_id,
            "instagram",
            "instagram_caption",
            key="failed-adapt",
        )
        target = retried.body["item"]
        self.assertEqual(len(items.list_items(self.conn, self.a)), 2)
        self.assertEqual(
            versions.list_versions(
                self.conn, self.a, item_id=target["item_id"]
            )[0].purpose,
            VersionPurpose.ADAPTATION,
        )
        self.assertEqual(self._key_count(self.a, "failed-adapt"), 1)

    def test_services_preserve_a_caller_owned_outer_transaction(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("approved source")
        )
        approved = self._approve(saved)
        version_id = approved.body["version"]["version_id"]
        self._save(
            a["item_id"], expected_revision=2, artifact=text("current work")
        )

        self.conn.execute("BEGIN IMMEDIATE")
        restored = self._restore(
            a["item_id"], version_id, 3, key="outer-restore"
        )
        self.assertEqual(restored.body["item"]["working_revision"], 4)
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()

        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (current.working_revision, current.artifact.segments),
            (3, ["current work"]),
        )
        self.assertEqual(
            self._count("workflow_versions", a["item_id"]), 1
        )
        self.assertEqual(self._key_count(self.a, "outer-restore"), 0)

        self.conn.execute("BEGIN IMMEDIATE")
        adapted = self._adapt(
            a["item_id"],
            version_id,
            "instagram",
            "instagram_caption",
            key="outer-adapt",
        )
        self.assertEqual(adapted.status_code, 201)
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()

        self.assertEqual(len(items.list_items(self.conn, self.a)), 1)
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM workflow_versions"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(self._key_count(self.a, "outer-adapt"), 0)

    def test_blank_request_ids_are_rejected_before_any_write(self) -> None:
        a = self._create()
        before = items.get_item(self.conn, self.a, a["item_id"])

        with self.assertRaises(WorkflowError) as raised:
            self._restore(
                a["item_id"], "ver_missing", 1, key="   "
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (422, "invalid_request"),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._adapt(
                a["item_id"],
                "ver_missing",
                "instagram",
                "instagram_caption",
                key="",
            )
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (422, "invalid_request"),
        )
        self.assertEqual(
            items.get_item(self.conn, self.a, a["item_id"]), before
        )
        self.assertEqual(self._key_count(self.a, "   "), 0)
        self.assertEqual(self._key_count(self.a, ""), 0)


if __name__ == "__main__":
    unittest.main()
