"""Tests for C06 immutable workflow content snapshots.

Covers exact canonical digests, transactional freeze/reuse, concurrent freezes,
empty artifacts, stale-revision conflicts, ownership-bound nested lookups,
later working edits, returned-value independence and transaction rollback.

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
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow import items, versions  # noqa: E402
from content_machine.workflow.errors import WorkflowError  # noqa: E402
from content_machine.workflow.migrations import migrate_workflow  # noqa: E402
from content_machine.workflow.schema_types import (  # noqa: E402
    TIMESTAMP_PATTERN,
    VersionPurpose,
)
from content_machine.workflow.schemas import (  # noqa: E402
    Artifact,
    Context,
    ItemCreate,
    ItemPatch,
    Principal,
)


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


def create_payload(
    title: str = "Snapshot item",
    destination: str = "linkedin",
    format: str = "linkedin_post",
) -> ItemCreate:
    return ItemCreate(title=title, destination=destination, format=format)


def text(value: str) -> Artifact:
    return Artifact(segments=[value])


class WorkflowVersionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c06-home-")
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
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
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
        title: str = "Snapshot item",
        destination: str = "linkedin",
        format: str = "linkedin_post",
        conn: sqlite3.Connection | None = None,
    ) -> dict:
        result = items.create_item(
            conn or self.conn,
            owner or self.a,
            create_payload(title, destination, format),
            request_id=self._next_key("create"),
        )
        return result.body["item"]

    def _save(
        self,
        item_id: str,
        patch: ItemPatch,
        *,
        owner: Principal | None = None,
        conn: sqlite3.Connection | None = None,
    ):
        return items.save_item(
            conn or self.conn,
            owner or self.a,
            item_id,
            patch,
            request_id=self._next_key("save"),
        )

    def _freeze(
        self,
        item_id: str,
        *,
        expected_revision: int,
        purpose: VersionPurpose = VersionPurpose.REVIEW,
        owner: Principal | None = None,
        conn: sqlite3.Connection | None = None,
    ):
        return versions.freeze_version(
            conn or self.conn,
            owner or self.a,
            item_id,
            expected_revision=expected_revision,
            purpose=purpose,
        )

    def _version_count(self, item_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM workflow_versions WHERE item_id = ?",
            (item_id,),
        ).fetchone()[0]

    def test_canonical_digest_preserves_text_and_segment_boundaries(self) -> None:
        artifact = Artifact(
            segments=["  Leading\r\n", "", "é🙂 trailing  "]
        )
        digest = versions.artifact_digest(
            "newsletter", "newsletter_draft", artifact
        )

        self.assertEqual(
            digest,
            expected_digest(
                "newsletter",
                "newsletter_draft",
                ["  Leading\r\n", "", "é🙂 trailing  "],
            ),
        )
        self.assertNotEqual(
            digest,
            expected_digest(
                "newsletter",
                "newsletter_draft",
                ["  Leading\r\n", "", "é🙂 trailing "],
            ),
        )
        self.assertNotEqual(
            versions.artifact_digest("x", "x_thread", artifact),
            digest,
        )
        self.assertNotEqual(
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["ab", "cd"])
            ),
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["abcd"])
            ),
        )
        self.assertNotEqual(
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["a", "b"])
            ),
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["b", "a"])
            ),
        )
        self.assertNotEqual(
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["a b"])
            ),
            versions.artifact_digest(
                "newsletter", "newsletter_draft", Artifact(segments=["a  b"])
            ),
        )

    def test_freeze_snapshots_exact_content_without_mutating_working_item(self) -> None:
        a = self._create()
        exact_segments = ["  Line one\r\nLine two  "]
        context = Context(
            notes="  note text  \n",
            experience="lived experience",
            interpretation="interpretation  ",
        )
        saved = self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=1,
                artifact=Artifact(segments=exact_segments),
                context=context,
            ),
        ).body["item"]

        version = self._freeze(a["item_id"], expected_revision=2)

        self.assertTrue(version.version_id.startswith("ver_"))
        self.assertEqual(
            (
                version.item_id,
                version.owner_id,
                version.revision,
                version.destination,
                version.format,
                version.purpose,
                version.created_by,
            ),
            (
                a["item_id"],
                self.a.owner_id,
                2,
                "linkedin",
                "linkedin_post",
                VersionPurpose.REVIEW,
                self.a.owner_id,
            ),
        )
        self.assertRegex(version.created_at, TIMESTAMP_PATTERN)
        self.assertEqual(version.context, context)
        self.assertEqual(version.artifact.segments, exact_segments)
        self.assertEqual(
            version.artifact_digest,
            expected_digest(
                "linkedin", "linkedin_post", exact_segments
            ),
        )

        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                working.working_revision,
                working.stage,
                working.active_approval_id,
                working.artifact.segments,
                working.context,
            ),
            (2, "draft_review", None, exact_segments, context),
        )
        review_count = self.conn.execute(
            "SELECT COUNT(*) FROM workflow_reviews WHERE item_id = ?",
            (a["item_id"],),
        ).fetchone()[0]
        self.assertEqual(review_count, 0)
        self.assertEqual(saved["working_revision"], 2)

    def test_empty_working_item_can_be_frozen(self) -> None:
        a = self._create()

        version = self._freeze(a["item_id"], expected_revision=1)

        self.assertEqual(version.revision, 1)
        self.assertEqual(version.artifact.segments, [])
        self.assertEqual(version.context.notes, "")
        self.assertEqual(
            version.artifact_digest,
            expected_digest("linkedin", "linkedin_post", []),
        )
        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                working.working_revision,
                working.stage,
                working.active_approval_id,
                working.artifact.segments,
            ),
            (1, "idea", None, []),
        )

    def test_repeated_freeze_reuses_version_and_original_purpose(self) -> None:
        a = self._create()
        first = self._freeze(
            a["item_id"],
            expected_revision=1,
            purpose=VersionPurpose.REVIEW,
        )
        repeated = self._freeze(
            a["item_id"],
            expected_revision=1,
            purpose=VersionPurpose.APPROVAL,
        )

        self.assertEqual(repeated.version_id, first.version_id)
        self.assertEqual(repeated.purpose, VersionPurpose.REVIEW)
        self.assertEqual(repeated.created_at, first.created_at)
        self.assertEqual(self._version_count(a["item_id"]), 1)
        stored_purpose = self.conn.execute(
            "SELECT purpose FROM workflow_versions WHERE version_id = ?",
            (first.version_id,),
        ).fetchone()[0]
        self.assertEqual(stored_purpose, "review")
        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                working.working_revision,
                working.stage,
                working.active_approval_id,
            ),
            (1, "idea", None),
        )

    def test_concurrent_freezes_create_one_snapshot(self) -> None:
        a = self._create()
        other = self._connect()
        self.addCleanup(other.close)
        barrier = threading.Barrier(2)

        def attempt(conn: sqlite3.Connection, purpose: VersionPurpose):
            barrier.wait(timeout=10)
            return self._freeze(
                a["item_id"],
                expected_revision=1,
                purpose=purpose,
                conn=conn,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(attempt, self.conn, VersionPurpose.REVIEW),
                pool.submit(attempt, other, VersionPurpose.APPROVAL),
            ]
            results = [future.result(timeout=15) for future in futures]

        self.assertEqual(results[0].version_id, results[1].version_id)
        self.assertEqual(results[0].purpose, results[1].purpose)
        self.assertEqual(self._version_count(a["item_id"]), 1)

    def test_later_edits_and_returned_values_do_not_mutate_history(self) -> None:
        a = self._create(destination="x", format="x_thread")
        old_segments = ["Original  ", "second\n"]
        self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=1,
                artifact=Artifact(segments=old_segments),
                context=Context(notes="  keep  \n"),
            ),
        )
        version = self._freeze(a["item_id"], expected_revision=2)

        version.artifact.segments.append("mutated in memory")
        version.context.notes = "mutated in memory"

        reloaded = versions.get_version(
            self.conn, self.a, version.version_id, item_id=a["item_id"]
        )
        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(reloaded.artifact.segments, old_segments)
        self.assertEqual(reloaded.context.notes, "  keep  \n")
        self.assertEqual(working.artifact.segments, old_segments)
        self.assertEqual(working.context.notes, "  keep  \n")

        self._save(
            a["item_id"],
            ItemPatch(
                expected_revision=2,
                artifact=Artifact(segments=["New  "]),
                context=Context(notes="new context"),
            ),
        )
        historical = versions.get_version(
            self.conn, self.a, version.version_id, item_id=a["item_id"]
        )
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(historical.artifact.segments, old_segments)
        self.assertEqual(historical.context.notes, "  keep  \n")
        self.assertEqual(current.working_revision, 3)
        self.assertEqual(current.artifact.segments, ["New  "])

    def test_owned_lookups_bind_owner_and_optional_item(self) -> None:
        a1 = self._create()
        a2 = self._create()
        b = self._create(owner=self.b)
        va1 = self._freeze(a1["item_id"], expected_revision=1)
        va2 = self._freeze(a2["item_id"], expected_revision=1)
        vb = self._freeze(b["item_id"], expected_revision=1, owner=self.b)

        self.assertEqual(
            versions.get_version(
                self.conn, self.a, va1.version_id, item_id=a1["item_id"]
            ).version_id,
            va1.version_id,
        )
        self.assertEqual(
            versions.get_version(self.conn, self.a, va1.version_id).version_id,
            va1.version_id,
        )

        for version_id, item_id in (
            (va2.version_id, a1["item_id"]),
            (vb.version_id, a1["item_id"]),
            (vb.version_id, None),
            (va1.version_id, b["item_id"]),
        ):
            with self.subTest(version_id=version_id, item_id=item_id):
                with self.assertRaises(WorkflowError) as raised:
                    versions.get_version(
                        self.conn, self.a, version_id, item_id=item_id
                    )
                self.assertEqual(raised.exception.status_code, 404)

        with self.assertRaises(WorkflowError) as raised:
            versions.get_version(self.conn, self.b, va1.version_id)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "version_not_found"),
        )

        self.assertEqual(
            [
                version.version_id
                for version in versions.list_versions(
                    self.conn, self.a, item_id=a1["item_id"]
                )
            ],
            [va1.version_id],
        )
        self.assertEqual(
            {
                version.version_id
                for version in versions.list_versions(self.conn, self.a)
            },
            {va1.version_id, va2.version_id},
        )
        self.assertEqual(
            [
                version.version_id
                for version in versions.list_versions(
                    self.conn, self.b, item_id=b["item_id"]
                )
            ],
            [vb.version_id],
        )
        with self.assertRaises(WorkflowError) as raised:
            versions.list_versions(self.conn, self.a, item_id=b["item_id"])
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "item_not_found"),
        )

    def test_stale_freeze_writes_nothing_and_reports_current_state(self) -> None:
        a = self._create()
        current = self._save(
            a["item_id"],
            ItemPatch(expected_revision=1, artifact=text("newer text  ")),
        ).body["item"]

        with self.assertRaises(WorkflowError) as raised:
            self._freeze(a["item_id"], expected_revision=1)

        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code),
            (409, "revision_conflict"),
        )
        self.assertEqual(
            error.current,
            {
                "working_revision": 2,
                "stage": "draft_review",
                "updated_at": current["updated_at"],
                "active_approval_id": None,
            },
        )
        self.assertEqual(self._version_count(a["item_id"]), 0)
        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (working.working_revision, working.artifact.segments),
            (2, ["newer text  "]),
        )

        version = self._freeze(a["item_id"], expected_revision=2)
        self.assertEqual(version.revision, 2)
        self.assertEqual(self._version_count(a["item_id"]), 1)

    def test_transaction_failure_rolls_back_freeze(self) -> None:
        a = self._create()
        self.conn.execute(
            "CREATE TRIGGER fail_version_insert"
            " BEFORE INSERT ON workflow_versions"
            " BEGIN SELECT RAISE(ABORT, 'forced version failure'); END"
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError) as raised:
            self._freeze(a["item_id"], expected_revision=1)
        self.assertIn("forced version failure", str(raised.exception))
        self.assertEqual(self._version_count(a["item_id"]), 0)
        working = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (working.working_revision, working.artifact.segments),
            (1, []),
        )

        self.conn.execute("DROP TRIGGER fail_version_insert")
        self.conn.commit()
        version = self._freeze(a["item_id"], expected_revision=1)
        self.assertEqual(version.revision, 1)
        self.assertEqual(self._version_count(a["item_id"]), 1)
