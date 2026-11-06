"""Tests for C07 human approval and exact approved-version export.

Covers explicit consent, stale/digest conflicts, immutable matching approvals,
idempotent retries, historical export after edits and restoration, configured
limits and script cues, exact Unicode/CRLF/thread serialization, safe filenames,
integrity checks, ownership denial and atomic rollback.

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
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow import approvals, exports, items, versions  # noqa: E402
from content_machine.workflow.errors import WorkflowError  # noqa: E402
from content_machine.workflow.migrations import migrate_workflow  # noqa: E402
from content_machine.workflow.persistence import canonical_json  # noqa: E402
from content_machine.workflow.schema_types import VersionPurpose  # noqa: E402
from content_machine.workflow.schemas import (  # noqa: E402
    ApproveRequest,
    Artifact,
    ItemCreate,
    ItemPatch,
    Principal,
)

TS = "2026-11-05T09:12:00.000Z"
BAD_DIGEST = "sha256:" + ("a" * 64)


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


class WorkflowApprovalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c07-home-")
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
        title: str = "Approval item",
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
        destination: str | None = None,
        format: str | None = None,
        owner: Principal | None = None,
    ) -> dict:
        patch_values: dict = {"expected_revision": expected_revision}
        if artifact is not None:
            patch_values["artifact"] = artifact
        if destination is not None:
            patch_values["destination"] = destination
        if format is not None:
            patch_values["format"] = format
        result = items.save_item(
            self.conn,
            owner or self.a,
            item_id,
            ItemPatch(**patch_values),
            request_id=self._next_key("save"),
        )
        return result.body["item"]

    def _approve(
        self,
        item: dict,
        *,
        expected_revision: int | None = None,
        digest: str | None = None,
        consent: bool = True,
        owner: Principal | None = None,
        key: str | None = None,
    ):
        return approvals.approve_item(
            self.conn,
            owner or self.a,
            item["item_id"],
            ApproveRequest(
                expected_revision=(
                    item["working_revision"]
                    if expected_revision is None
                    else expected_revision
                ),
                artifact_digest=(
                    expected_digest(
                        item["destination"],
                        item["format"],
                        item["artifact"]["segments"],
                    )
                    if digest is None
                    else digest
                ),
                consent=consent,
            ),
            request_id=key or self._next_key("approve"),
        )

    def _freeze(self, item_id: str, revision: int):
        return versions.freeze_version(
            self.conn,
            self.a,
            item_id,
            expected_revision=revision,
            purpose=VersionPurpose.REVIEW,
        )

    def _export(self, item_id: str, version_id: str, owner: Principal | None = None):
        return exports.export_version(
            self.conn, owner or self.a, item_id, version_id
        )

    def _count(self, table: str, item_id: str) -> int:
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE item_id = ?", (item_id,)
        ).fetchone()[0]

    def test_explicit_consent_creates_matching_approval_and_export_stage(self) -> None:
        a = self._create()
        exact = "  Approved text\r\nsecond line  \n"
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text(exact)
        )
        digest = expected_digest("linkedin", "linkedin_post", [exact])

        result = self._approve(saved, digest=digest, key="approve-once")

        self.assertEqual(result.status_code, 200)
        body = result.body
        approval = body["approval"]
        self.assertTrue(approval["approval_id"].startswith("apr_"))
        self.assertEqual(
            (
                approval["owner_id"],
                approval["item_id"],
                approval["version_id"],
                approval["artifact_digest"],
                approval["destination"],
                approval["format"],
                approval["approved_by"],
            ),
            (
                self.a.owner_id,
                a["item_id"],
                body["version"]["version_id"],
                digest,
                "linkedin",
                "linkedin_post",
                self.a.owner_id,
            ),
        )
        self.assertEqual(
            (
                body["item"]["working_revision"],
                body["item"]["stage"],
                body["item"]["active_approval_id"],
                body["item"]["artifact"]["segments"],
            ),
            (2, "export", approval["approval_id"], [exact]),
        )
        self.assertEqual(body["version"]["revision"], 2)
        self.assertEqual(body["version"]["artifact"]["segments"], [exact])
        self.assertEqual(body["version"]["purpose"], "approval")
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 1)
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                current.working_revision,
                current.stage,
                current.active_approval_id,
                current.artifact.segments,
            ),
            (2, "export", approval["approval_id"], [exact]),
        )

    def test_consent_false_is_approval_conflict_and_writes_nothing(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("Do not approve")
        )

        with self.assertRaises(WorkflowError) as raised:
            self._approve(saved, consent=False)

        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code), (409, "approval_conflict")
        )
        self.assertEqual(error.current["working_revision"], 2)
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 0)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 0)
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (current.stage, current.active_approval_id), ("draft_review", None)
        )

    def test_stale_revision_and_changed_digest_are_conflicts_without_writes(self) -> None:
        a = self._create()
        self._save(a["item_id"], expected_revision=1, artifact=text("first"))
        newer = self._save(
            a["item_id"], expected_revision=2, artifact=text("second")
        )

        with self.assertRaises(WorkflowError) as raised:
            self._approve(
                newer,
                expected_revision=2,
                digest=expected_digest("linkedin", "linkedin_post", ["second"]),
            )
        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code), (409, "revision_conflict")
        )
        self.assertEqual(
            error.current,
            {
                "working_revision": 3,
                "stage": "draft_review",
                "updated_at": newer["updated_at"],
                "active_approval_id": None,
            },
        )

        with self.assertRaises(WorkflowError) as raised:
            self._approve(newer, digest=BAD_DIGEST)
        error = raised.exception
        self.assertEqual(
            (error.status_code, error.code), (409, "artifact_digest_mismatch")
        )
        self.assertEqual(error.current["working_revision"], 3)
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 0)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 0)
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (current.working_revision, current.stage, current.active_approval_id),
            (3, "draft_review", None),
        )

    def test_empty_and_malformed_final_artifacts_are_rejected_without_versions(self) -> None:
        empty = self._create()
        with self.assertRaises(WorkflowError) as raised:
            self._approve(empty)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (422, "invalid_artifact"),
        )

        thread = self._create(destination="x", format="x_thread")
        malformed_thread = self._save(
            thread["item_id"],
            expected_revision=1,
            artifact=Artifact(segments=["valid first", "  \n"]),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._approve(malformed_thread)
        self.assertEqual(raised.exception.status_code, 422)

        single = self._create()
        multiple = self._save(
            single["item_id"],
            expected_revision=1,
            artifact=Artifact(segments=["first", "second"]),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._approve(multiple)
        self.assertEqual(raised.exception.status_code, 422)

        for item in (empty, thread, single):
            self.assertEqual(self._count("workflow_versions", item["item_id"]), 0)
            self.assertEqual(self._count("workflow_approvals", item["item_id"]), 0)

    def test_configured_length_limits_and_script_cues_are_enforced(self) -> None:
        x = self._create(destination="x", format="x_thread")
        x_exact = self._save(
            x["item_id"], expected_revision=1, artifact=Artifact(segments=["😀" * 280])
        )
        self._approve(x_exact)
        x_too_long = self._save(
            x["item_id"], expected_revision=2, artifact=Artifact(segments=["😀" * 281])
        )
        with self.assertRaises(WorkflowError) as raised:
            self._approve(x_too_long)
        self.assertEqual(raised.exception.status_code, 422)

        instagram = self._create(
            destination="instagram", format="instagram_caption"
        )
        ig_exact = self._save(
            instagram["item_id"],
            expected_revision=1,
            artifact=text("é" * 2200),
        )
        self._approve(ig_exact)
        ig_too_long = self._save(
            instagram["item_id"],
            expected_revision=2,
            artifact=text("é" * 2201),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._approve(ig_too_long)
        self.assertEqual(raised.exception.status_code, 422)

        valid_script = (
            "[Visual Cue: terminal] Open the editor.\n"
            "[Camera Zoom] Show the failing request.\n"
            "[Pause]\nThen name the tradeoff."
        )
        script = self._create(
            destination="youtube", format="youtube_short_script"
        )
        valid = self._save(
            script["item_id"], expected_revision=1, artifact=text(valid_script)
        )
        approved = self._approve(valid)
        self.assertEqual(approved.body["item"]["stage"], "export")

        for missing in ("[Visual Cue", "[Camera Zoom", "[Pause"):
            with self.subTest(missing=missing):
                candidate = self._create(
                    destination="youtube", format="youtube_short_script"
                )
                lines = [
                    line
                    for line in valid_script.splitlines()
                    if not line.startswith(missing)
                ]
                saved = self._save(
                    candidate["item_id"],
                    expected_revision=1,
                    artifact=text("\n".join(lines)),
                )
                with self.assertRaises(WorkflowError) as raised:
                    self._approve(saved)
                self.assertEqual(raised.exception.status_code, 422)

    def test_script_cues_require_closed_exact_bracketed_markers(self) -> None:
        malformed_scripts = (
            "[Visual Cue unfinished\n[Camera Zoom unfinished\n[Pause",
            "[Visual Cuesheet] text\n[Camera Zoomed] text\n[Paused] text",
        )
        for index, script_text in enumerate(malformed_scripts):
            with self.subTest(script=script_text):
                item = self._create(
                    destination="instagram", format="instagram_reel_script"
                )
                saved = self._save(
                    item["item_id"],
                    expected_revision=1,
                    artifact=text(script_text),
                )
                key = f"approve-malformed-{index}"

                with self.assertRaises(WorkflowError) as raised:
                    self._approve(saved, key=key)

                self.assertEqual(
                    (raised.exception.status_code, raised.exception.code),
                    (422, "invalid_artifact"),
                )
                self.assertEqual(
                    self._count("workflow_versions", item["item_id"]), 0
                )
                self.assertEqual(
                    self._count("workflow_approvals", item["item_id"]), 0
                )
                current = items.get_item(self.conn, self.a, item["item_id"])
                self.assertEqual(
                    (
                        current.working_revision,
                        current.stage,
                        current.active_approval_id,
                        current.artifact.segments,
                    ),
                    (2, "draft_review", None, [script_text]),
                )
                self.assertEqual(
                    self.conn.execute(
                        "SELECT COUNT(*) FROM workflow_idempotency"
                        " WHERE owner_id = ? AND request_id = ?",
                        (self.a.owner_id, key),
                    ).fetchone()[0],
                    0,
                )

        valid_script = (
            "[Visual Cue: show code]\n"
            "[Camera Zoom: highlight the line]\n"
            "[Pause]"
        )
        valid_item = self._create(
            destination="instagram", format="instagram_reel_script"
        )
        valid_saved = self._save(
            valid_item["item_id"],
            expected_revision=1,
            artifact=text(valid_script),
        )

        approved = self._approve(valid_saved)

        self.assertEqual(approved.body["item"]["stage"], "export")
        self.assertEqual(
            approved.body["item"]["artifact"]["segments"], [valid_script]
        )

    def test_matching_retry_replays_before_cas_and_changed_body_conflicts(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("approved once")
        )
        original = self._approve(saved, key="stable-key")
        approval_id = original.body["approval"]["approval_id"]
        version_id = original.body["version"]["version_id"]
        self._save(
            a["item_id"], expected_revision=2, artifact=text("later edit")
        )

        replay = self._approve(saved, key="stable-key")
        self.assertEqual((replay.status_code, replay.body), (200, original.body))
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 1)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (current.working_revision, current.active_approval_id, current.artifact.segments),
            (3, None, ["later edit"]),
        )

        with self.assertRaises(WorkflowError) as raised:
            self._approve(saved, consent=False, key="stable-key")
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 1)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        stored = self.conn.execute(
            "SELECT version_id FROM workflow_versions WHERE item_id = ?",
            (a["item_id"],),
        ).fetchone()[0]
        self.assertEqual(stored, version_id)
        self.assertEqual(
            self.conn.execute(
                "SELECT approval_id FROM workflow_approvals WHERE item_id = ?",
                (a["item_id"],),
            ).fetchone()[0],
            approval_id,
        )

    def test_one_space_edit_and_edit_back_never_revive_the_old_approval(self) -> None:
        a = self._create(title="Edit history")
        original = self._save(
            a["item_id"], expected_revision=1, artifact=text("Hello  world")
        )
        approval = self._approve(original)
        version_id = approval.body["version"]["version_id"]

        edited = self._save(
            a["item_id"], expected_revision=2, artifact=text("Hello world")
        )
        self.assertEqual(
            (edited["working_revision"], edited["stage"], edited["active_approval_id"]),
            (3, "draft_review", None),
        )
        historical = self._export(a["item_id"], version_id)
        self.assertEqual(historical.content, b"Hello  world")
        self.assertTrue(historical.filename.endswith("-r2.txt"))

        reverted = self._save(
            a["item_id"], expected_revision=3, artifact=text("Hello  world")
        )
        self.assertEqual(
            (reverted["working_revision"], reverted["active_approval_id"]),
            (4, None),
        )
        reverted_version = self._freeze(a["item_id"], 4)
        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], reverted_version.version_id)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 1)
        self.assertEqual(self._export(a["item_id"], version_id).content, b"Hello  world")

    def test_format_change_invalidates_active_approval_but_keeps_old_export(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("format-bound text")
        )
        old_version = self._approve(saved).body["version"]["version_id"]
        changed = self._save(
            a["item_id"],
            expected_revision=2,
            destination="x",
            format="x_thread",
        )
        self.assertEqual(
            (changed["working_revision"], changed["stage"], changed["active_approval_id"]),
            (3, "draft_review", None),
        )
        new_version = self._freeze(a["item_id"], 3)
        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], new_version.version_id)
        self.assertEqual(raised.exception.code, "approval_required")
        old = self._export(a["item_id"], old_version)
        self.assertEqual(old.destination, "linkedin")
        self.assertEqual(old.content, b"format-bound text")

    def test_single_export_preserves_exact_unicode_crlf_and_trailing_whitespace(self) -> None:
        a = self._create(title="  Hello // WORLD: \"Q\";  ")
        exact = "  Café 🙂\r\nline two\n\n"
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text(exact)
        )
        approval = self._approve(saved)
        version_id = approval.body["version"]["version_id"]
        digest = approval.body["approval"]["artifact_digest"]
        self._save(
            a["item_id"], expected_revision=2, artifact=text("changed later")
        )

        result = self._export(a["item_id"], version_id)

        self.assertEqual(result.content, exact.encode("utf-8"))
        self.assertFalse(result.content.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(result.text, exact)
        self.assertEqual(result.artifact_digest, digest)
        self.assertEqual(result.filename, "hello-world-q-r2.txt")
        self.assertEqual(
            result.as_json(),
            {
                "version_id": version_id,
                "destination": "linkedin",
                "format": "linkedin_post",
                "artifact_digest": digest,
                "segments": [exact],
            },
        )
        self.assertEqual(result.headers["X-Artifact-Digest"], digest)
        self.assertIn("text/plain; charset=utf-8", result.headers["Content-Type"])
        self.assertIn(result.filename, result.headers["Content-Disposition"])

    def test_thread_export_joins_two_lf_without_appending_or_rewriting_segments(self) -> None:
        a = self._create(destination="x", format="x_thread")
        segments = ["  one\r\n", "two\n", "é🙂  "]
        saved = self._save(
            a["item_id"],
            expected_revision=1,
            artifact=Artifact(segments=segments),
        )
        approval = self._approve(saved)
        result = self._export(
            a["item_id"], approval.body["version"]["version_id"]
        )

        self.assertEqual(
            result.content,
            b"  one\r\n" + b"\n\n" + b"two\n" + b"\n\n" + "é🙂  ".encode("utf-8"),
        )
        self.assertEqual(result.as_json()["segments"], segments)
        self.assertFalse(result.content.endswith(b"\n\n"))

    def test_owned_reads_and_export_deny_borrowed_approvals(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("owned text")
        )
        approval = self._approve(saved)
        approval_id = approval.body["approval"]["approval_id"]
        version_id = approval.body["version"]["version_id"]
        other = self._create(owner=self.a)

        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], version_id, owner=self.b)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "item_not_found"),
        )
        with self.assertRaises(WorkflowError) as raised:
            self._export(other["item_id"], version_id)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (404, "version_not_found"),
        )
        with self.assertRaises(WorkflowError) as raised:
            approvals.get_approval(self.conn, self.b, approval_id)
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(WorkflowError) as raised:
            approvals.list_approvals(self.conn, self.b, item_id=a["item_id"])
        self.assertEqual(raised.exception.status_code, 404)

        self._save(
            a["item_id"], expected_revision=2, artifact=text("edited")
        )
        historical = approvals.list_approvals(
            self.conn, self.a, item_id=a["item_id"]
        )
        self.assertEqual([row.approval_id for row in historical], [approval_id])
        self.assertEqual(
            approvals.get_approval(
                self.conn, self.a, approval_id, item_id=a["item_id"]
            ).version_id,
            version_id,
        )

    def test_export_recomputes_digest_instead_of_trusting_a_rewritten_snapshot(self) -> None:
        a = self._create()
        version_id = "ver_tampered"
        approval_id = "apr_tampered"
        self.conn.execute(
            "INSERT INTO workflow_versions("
            " version_id, item_id, owner_id, revision, context_json,"
            " artifact_json, destination, format, artifact_digest, purpose,"
            " created_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version_id,
                a["item_id"],
                self.a.owner_id,
                1,
                canonical_json(a["context"]),
                canonical_json({"segments": ["rewritten after approval"]}),
                "linkedin",
                "linkedin_post",
                BAD_DIGEST,
                "approval",
                self.a.owner_id,
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
                self.a.owner_id,
                a["item_id"],
                version_id,
                BAD_DIGEST,
                "linkedin",
                "linkedin_post",
                self.a.owner_id,
                TS,
            ),
        )
        self.conn.commit()

        with self.assertRaises(WorkflowError) as raised:
            self._export(a["item_id"], version_id)
        self.assertEqual(
            (raised.exception.status_code, raised.exception.code),
            (409, "approval_required"),
        )

    def test_safe_filenames_never_leak_paths_controls_or_reserved_names(self) -> None:
        self.assertEqual(
            exports.safe_filename("  Hello // WORLD: \"Q\";  ", "itm_abc", 4),
            "hello-world-q-r4.txt",
        )
        reserved = exports.safe_filename("CON", "itm_abc", 2)
        self.assertTrue(reserved.startswith("content-itm-abc-"))
        self.assertTrue(reserved.endswith("-r2.txt"))
        self.assertEqual(
            exports.safe_filename("", "../../evil\r\nX", 1),
            "content-evil-x-r1.txt",
        )
        long_name = exports.safe_filename("A" * 100, "itm_long", 7)
        self.assertLessEqual(len(long_name.removesuffix("-r7.txt")), 80)
        self.assertTrue(long_name.startswith("a" * 80))

        unsafe = exports.safe_filename(
            "NUL", "../../CON\r\nX:;\\\"", 3
        )
        for forbidden in ("..", "/", "\\", "\r", "\n", ":", ";", '"'):
            self.assertNotIn(forbidden, unsafe)
        self.assertTrue(unsafe.isascii())

    def test_approval_insert_failure_rolls_back_every_effect(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("atomic text")
        )
        self.conn.execute(
            "CREATE TRIGGER fail_approval_insert"
            " BEFORE INSERT ON workflow_approvals"
            " BEGIN SELECT RAISE(ABORT, 'forced approval failure'); END"
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError) as raised:
            self._approve(saved, key="failed-approval")
        self.assertIn("forced approval failure", str(raised.exception))

        current = items.get_item(self.conn, self.a, a["item_id"])
        self.assertEqual(
            (
                current.working_revision,
                current.stage,
                current.active_approval_id,
                current.artifact.segments,
            ),
            (2, "draft_review", None, ["atomic text"]),
        )
        self.assertEqual(self._count("workflow_versions", a["item_id"]), 0)
        self.assertEqual(self._count("workflow_approvals", a["item_id"]), 0)
        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM workflow_idempotency"
                " WHERE owner_id = ? AND request_id = ?",
                (self.a.owner_id, "failed-approval"),
            ).fetchone()[0],
            0,
        )

        self.conn.execute("DROP TRIGGER fail_approval_insert")
        self.conn.commit()
        retried = self._approve(saved, key="failed-approval")
        self.assertEqual(retried.body["item"]["stage"], "export")

    def test_approval_and_export_make_no_generation_calls(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("manual text")
        )

        with patch(
            "content_machine.router.base.ModelRouter.complete",
            side_effect=AssertionError("generation must not be called"),
        ):
            approved = self._approve(saved)
            exported = self._export(
                a["item_id"], approved.body["version"]["version_id"]
            )

        self.assertEqual(exported.content, b"manual text")

    def test_approval_rows_stay_immutable_after_edit(self) -> None:
        a = self._create()
        saved = self._save(
            a["item_id"], expected_revision=1, artifact=text("immutable approval")
        )
        approval_id = self._approve(saved).body["approval"]["approval_id"]
        self._save(
            a["item_id"], expected_revision=2, artifact=text("later text")
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE workflow_approvals SET approved_at = ? WHERE approval_id = ?",
                (TS, approval_id),
            )
        self.conn.rollback()
        current = approvals.get_approval(self.conn, self.a, approval_id)
        self.assertNotEqual(current.approved_at, TS)


if __name__ == "__main__":
    unittest.main()
