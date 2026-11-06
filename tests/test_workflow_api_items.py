"""Tests for C09 owned item CRUD through the workflow API router.

Covers real FastAPI/TestClient requests against temporary SQLite storage:
authentication before connection creation, create/list/get/save, duplicate
titles, cross-owner denial, spoofed owner fields, idempotency retries and
conflicts, stale CAS, connection cleanup, database-failure retry, actual
review/approval metadata, readable workflow validation, and unchanged
legacy/SPA entry points.

Every database is a cleaned TemporaryDirectory-backed SQLite file. No provider,
network or production storage path is used.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from content_machine.api.app import app  # noqa: E402
from content_machine.storage.db import connect  # noqa: E402
from content_machine.workflow import approvals, items, versions  # noqa: E402
from content_machine.workflow.schemas import ApproveRequest, Principal  # noqa: E402

TS = "2026-11-05T09:12:00.000Z"
_UNSET = object()
_AUTO = object()
_ENV_KEYS = (
    "CONTENT_MACHINE_HOME",
    "CONTENT_MACHINE_WORKFLOW_MODE",
    "CONTENT_MACHINE_LOCAL_OWNER_ID",
    "CONTENT_MACHINE_DEPLOYMENT_MODE",
    "VERCEL",
)


def principal(owner_id: str) -> Principal:
    return Principal(owner_id=owner_id, mode="hosted_verified")


def item_payload(
    title: str = "Indexing tradeoffs",
    destination: str = "linkedin",
    format: str = "linkedin_post",
) -> dict:
    return {
        "title": title,
        "destination": destination,
        "format": format,
    }


class WorkflowItemsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory(prefix="c09-home-")
        self._previous_env = {
            key: os.environ.get(key) for key in _ENV_KEYS
        }
        os.environ["CONTENT_MACHINE_HOME"] = self._home.name
        for key in _ENV_KEYS[1:]:
            os.environ.pop(key, None)

        self.db_path = Path(self._home.name) / "workflow.db"
        with closing(connect(self.db_path)):
            pass

        self.a = principal("own_A")
        self.b = principal("own_B")
        self._current = self.a
        self.connections: list[sqlite3.Connection] = []
        self._sequence = 0

        self._previous_factory = getattr(
            app.state, "workflow_connection_factory", _UNSET
        )
        self._previous_auth = getattr(
            app.state, "workflow_authenticator", _UNSET
        )

        def connection_factory() -> sqlite3.Connection:
            conn = connect(self.db_path)
            self.connections.append(conn)
            return conn

        app.state.workflow_connection_factory = connection_factory
        app.state.workflow_authenticator = lambda request: self._current
        self.client = TestClient(app)

        def cleanup() -> None:
            self.client.close()
            for conn in self.connections:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._restore_state_attribute(
                "workflow_connection_factory", self._previous_factory
            )
            self._restore_state_attribute(
                "workflow_authenticator", self._previous_auth
            )
            for key, value in self._previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            self._home.cleanup()

        self.addCleanup(cleanup)

    @staticmethod
    def _restore_state_attribute(name: str, value: object) -> None:
        if value is _UNSET:
            if hasattr(app.state, name):
                delattr(app.state, name)
        else:
            setattr(app.state, name, value)

    def _next_key(self, prefix: str = "request") -> str:
        self._sequence += 1
        return f"{prefix}-{self._sequence}"

    def _as(self, owner: Principal) -> None:
        self._current = owner

    def _headers(
        self,
        key: str | None | object = _AUTO,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers = dict(extra or {})
        selected = self._next_key() if key is _AUTO else key
        if selected is not None:
            headers["Idempotency-Key"] = str(selected)
        return headers

    def _post(
        self,
        payload: dict,
        *,
        key: str | None | object = _AUTO,
        extra_headers: dict[str, str] | None = None,
        client: TestClient | None = None,
    ):
        return (client or self.client).post(
            "/api/workflow/items",
            json=payload,
            headers=self._headers(key, extra_headers),
        )

    def _patch(
        self,
        item_id: str,
        payload: dict,
        *,
        key: str | None | object = _AUTO,
        client: TestClient | None = None,
    ):
        return (client or self.client).patch(
            f"/api/workflow/items/{item_id}",
            json=payload,
            headers=self._headers(key),
        )

    def _get(self, item_id: str, *, client: TestClient | None = None):
        return (client or self.client).get(
            f"/api/workflow/items/{item_id}"
        )

    def _create_item(
        self,
        *,
        title: str = "Indexing tradeoffs",
        key: str | None | object = _AUTO,
        extra_headers: dict[str, str] | None = None,
    ) -> dict:
        response = self._post(
            item_payload(title), key=key, extra_headers=extra_headers
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["item"]

    def _summary(self, item: dict) -> dict:
        return {
            "item_id": item["item_id"],
            "title": item["title"],
            "destination": item["destination"],
            "format": item["format"],
            "stage": item["stage"],
            "working_revision": item["working_revision"],
            "updated_at": item["updated_at"],
            "active_approval_id": item["active_approval_id"],
        }

    def _count(self, table: str) -> int:
        with closing(connect(self.db_path)) as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

    def _key_count(self, owner: Principal, request_id: str) -> int:
        with closing(connect(self.db_path)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM workflow_idempotency"
                " WHERE owner_id = ? AND request_id = ?",
                (owner.owner_id, request_id),
            ).fetchone()[0]

    def _assert_closed(self, conn: sqlite3.Connection) -> None:
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def _use_transactional_factory(self) -> None:
        def connection_factory() -> sqlite3.Connection:
            conn = connect(self.db_path)
            conn.execute("BEGIN")
            self.connections.append(conn)
            return conn

        app.state.workflow_connection_factory = connection_factory

    def test_create_list_get_and_save_use_real_storage(self) -> None:
        created = self._create_item(
            extra_headers={"X-Owner-Id": self.b.owner_id}
        )

        self.assertEqual(created["owner_id"], self.a.owner_id)
        self.assertEqual(
            (
                created["working_revision"],
                created["stage"],
                created["active_approval_id"],
                created["artifact"]["segments"],
                created["context"]["notes"],
            ),
            (1, "idea", None, [], ""),
        )

        listed = self.client.get("/api/workflow/items")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(
            listed.json(),
            {"items": [self._summary(created)]},
        )

        fetched = self._get(created["item_id"])
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(
            fetched.json(),
            {"item": created, "review": None, "approval": None},
        )

        exact = "  Exact text\r\nsecond line  \n"
        saved_response = self._patch(
            created["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": [exact]},
                "context": {"notes": "  note text  \n"},
            },
        )
        self.assertEqual(saved_response.status_code, 200, saved_response.text)
        saved = saved_response.json()["item"]
        self.assertEqual(
            (
                saved["working_revision"],
                saved["stage"],
                saved["active_approval_id"],
                saved["artifact"]["segments"],
                saved["context"]["notes"],
            ),
            (2, "draft_review", None, [exact], "  note text  \n"),
        )

        reread = self._get(created["item_id"])
        self.assertEqual(reread.status_code, 200, reread.text)
        self.assertEqual(reread.json()["item"], saved)
        self._assert_closed(self.connections[-1])

    def test_duplicate_titles_and_cross_owner_ids_remain_independent(self) -> None:
        a1 = self._create_item(title="Same title")
        a2 = self._create_item(title="Same title")
        self._as(self.b)
        b1 = self._create_item(title="Same title")
        self._as(self.a)

        a_list = self.client.get("/api/workflow/items").json()["items"]
        self.assertEqual(
            {item["item_id"] for item in a_list},
            {a1["item_id"], a2["item_id"]},
        )
        self._as(self.b)
        b_list = self.client.get("/api/workflow/items").json()["items"]
        self.assertEqual(
            [item["item_id"] for item in b_list],
            [b1["item_id"]],
        )
        self._as(self.a)

        cross_get = self._get(b1["item_id"])
        self.assertEqual(
            (cross_get.status_code, cross_get.json()["code"]),
            (404, "item_not_found"),
        )
        cross_patch = self._patch(
            b1["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": ["must not land"]},
            },
        )
        self.assertEqual(
            (cross_patch.status_code, cross_patch.json()["code"]),
            (404, "item_not_found"),
        )

        self._as(self.b)
        b_after = self._get(b1["item_id"]).json()["item"]
        self.assertEqual(
            (
                b_after["working_revision"],
                b_after["artifact"]["segments"],
            ),
            (1, []),
        )

    def test_authentication_failure_never_opens_the_database(self) -> None:
        del app.state.workflow_authenticator

        missing = self.client.get("/api/workflow/items")

        self.assertEqual(
            (missing.status_code, missing.json()["code"]),
            (503, "workflow_auth_misconfigured"),
        )
        self.assertEqual(self.connections, [])

        app.state.workflow_authenticator = lambda request: None
        unauthenticated = self.client.get("/api/workflow/items")

        self.assertEqual(
            (unauthenticated.status_code, unauthenticated.json()["code"]),
            (401, "unauthenticated"),
        )
        self.assertEqual(self.connections, [])

    def test_owner_and_timestamp_fields_are_rejected_and_headers_ignored(
        self,
    ) -> None:
        spoofed = item_payload("Spoofed item")
        spoofed.update(
            {
                "owner_id": self.b.owner_id,
                "created_at": TS,
                "updated_at": TS,
                "active_approval_id": "apr_forged",
            }
        )

        response = self._post(
            spoofed,
            extra_headers={
                "X-Owner-Id": self.b.owner_id,
                "X-Forwarded-User": self.b.owner_id,
            },
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["code"], "invalid_request")
        self.assertIsInstance(response.json()["detail"], str)
        self.assertEqual(self._count("workflow_items"), 0)

        created = self._create_item(
            title="Header cannot choose owner",
            extra_headers={"X-Owner-Id": self.b.owner_id},
        )
        self.assertEqual(created["owner_id"], self.a.owner_id)

    def test_missing_and_blank_idempotency_headers_are_422_without_writes(
        self,
    ) -> None:
        for key in (None, "   "):
            with self.subTest(method="POST", key=key):
                response = self._post(item_payload(), key=key)
                self.assertEqual(
                    (response.status_code, response.json()["code"]),
                    (422, "invalid_request"),
                )

        self.assertEqual(self._count("workflow_items"), 0)
        item = self._create_item()

        for key in (None, "   "):
            with self.subTest(method="PATCH", key=key):
                response = self._patch(
                    item["item_id"],
                    {
                        "expected_revision": 1,
                        "artifact": {"segments": ["must not save"]},
                    },
                    key=key,
                )
                self.assertEqual(
                    (response.status_code, response.json()["code"]),
                    (422, "invalid_request"),
                )

        current = self._get(item["item_id"]).json()["item"]
        self.assertEqual(
            (
                current["working_revision"],
                current["stage"],
                current["artifact"]["segments"],
            ),
            (1, "idea", []),
        )

    def test_stale_cas_returns_acknowledged_state_and_writes_nothing(
        self,
    ) -> None:
        item = self._create_item()
        first = self._patch(
            item["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": ["first save"]},
            },
            key="first-save",
        )
        self.assertEqual(first.status_code, 200, first.text)
        saved = first.json()["item"]

        stale = self._patch(
            item["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": ["stale overwrite"]},
            },
            key="stale-save",
        )

        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(
            {
                "code": stale.json()["code"],
                "detail": stale.json()["detail"],
                "working_revision": stale.json()["working_revision"],
                "stage": stale.json()["stage"],
                "updated_at": stale.json()["updated_at"],
                "active_approval_id": stale.json()["active_approval_id"],
            },
            {
                "code": "revision_conflict",
                "detail": "The item revision changed before this save",
                "working_revision": 2,
                "stage": "draft_review",
                "updated_at": saved["updated_at"],
                "active_approval_id": None,
            },
        )
        self.assertEqual(self._get(item["item_id"]).json()["item"], saved)
        self.assertEqual(self._key_count(self.a, "stale-save"), 0)

    def test_matching_retries_replay_and_changed_keys_conflict(self) -> None:
        payload = item_payload("Idempotent item")
        original = self._post(payload, key="create-key")
        replay = self._post(payload, key="create-key")

        self.assertEqual(
            (replay.status_code, replay.json()),
            (201, original.json()),
        )
        changed = self._post(
            item_payload("Changed under the same key"),
            key="create-key",
        )
        self.assertEqual(
            (changed.status_code, changed.json()["code"]),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(self._count("workflow_items"), 1)

        item = original.json()["item"]
        save_payload = {
            "expected_revision": 1,
            "artifact": {"segments": ["first body"]},
        }
        saved = self._patch(item["item_id"], save_payload, key="save-key")
        saved_replay = self._patch(
            item["item_id"], save_payload, key="save-key"
        )
        self.assertEqual(
            (saved_replay.status_code, saved_replay.json()),
            (200, saved.json()),
        )
        saved_changed = self._patch(
            item["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": ["second body"]},
            },
            key="save-key",
        )
        self.assertEqual(
            (saved_changed.status_code, saved_changed.json()["code"]),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(
            self._get(item["item_id"]).json()["item"]["artifact"]["segments"],
            ["first body"],
        )

        reused_resource = self._patch(
            item["item_id"],
            {"expected_revision": 2, "title": "Different resource"},
            key="create-key",
        )
        self.assertEqual(
            (
                reused_resource.status_code,
                reused_resource.json()["code"],
            ),
            (409, "idempotency_conflict"),
        )

    def test_database_failure_closes_and_does_not_record_a_saved_response(
        self,
    ) -> None:
        with closing(connect(self.db_path)) as conn:
            conn.execute(
                "CREATE TRIGGER fail_item_insert"
                " BEFORE INSERT ON workflow_items"
                " BEGIN SELECT RAISE(ABORT, 'forced item failure'); END"
            )
            conn.commit()

        failure_client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(failure_client.close)
        failed = self._post(
            item_payload("Failure then retry"),
            key="retry-create",
            client=failure_client,
        )

        self.assertEqual(failed.status_code, 500)
        self.assertEqual(self._count("workflow_items"), 0)
        self.assertEqual(self._key_count(self.a, "retry-create"), 0)
        self._assert_closed(self.connections[-1])

        with closing(connect(self.db_path)) as conn:
            conn.execute("DROP TRIGGER fail_item_insert")
            conn.commit()

        retried = self._post(
            item_payload("Failure then retry"),
            key="retry-create",
            client=failure_client,
        )
        self.assertEqual(retried.status_code, 201, retried.text)
        self.assertEqual(self._count("workflow_items"), 1)
        self.assertEqual(self._key_count(self.a, "retry-create"), 1)

    def test_request_owned_transaction_create_commits_before_success(
        self,
    ) -> None:
        self._use_transactional_factory()

        created_response = self._post(
            item_payload("Transaction-owned create"),
            key="transaction-create",
        )
        self.assertEqual(
            created_response.status_code, 201, created_response.text
        )
        created = created_response.json()["item"]

        fetched = self._get(created["item_id"])
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["item"], created)
        self.assertEqual(
            self._key_count(self.a, "transaction-create"), 1
        )

    def test_request_owned_transaction_save_commits_before_success(
        self,
    ) -> None:
        item = self._create_item(title="Transaction-owned save")
        self._use_transactional_factory()
        exact = "  transactional\r\nexact text  \n"

        saved_response = self._patch(
            item["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": [exact]},
            },
            key="transaction-save",
        )
        self.assertEqual(
            saved_response.status_code, 200, saved_response.text
        )
        saved = saved_response.json()["item"]
        self.assertEqual(saved["working_revision"], 2)

        fetched = self._get(item["item_id"])
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["item"], saved)
        self.assertEqual(
            fetched.json()["item"]["artifact"]["segments"], [exact]
        )

    def test_deferred_commit_failure_rolls_back_and_same_key_retries(
        self,
    ) -> None:
        with closing(connect(self.db_path)) as conn:
            conn.executescript(
                "CREATE TABLE tx_probe_parent (id TEXT PRIMARY KEY);"
                "CREATE TABLE tx_probe_child ("
                " id TEXT PRIMARY KEY,"
                " parent_id TEXT NOT NULL"
                " REFERENCES tx_probe_parent(id)"
                " DEFERRABLE INITIALLY DEFERRED);"
                "CREATE TRIGGER fail_deferred_commit"
                " AFTER INSERT ON workflow_items"
                " BEGIN"
                "   INSERT INTO tx_probe_child(id, parent_id)"
                "   VALUES ('child_missing', 'parent_missing');"
                " END;"
            )
            conn.commit()

        self._use_transactional_factory()
        failure_client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(failure_client.close)

        failed = self._post(
            item_payload("Deferred commit failure"),
            key="deferred-create",
            client=failure_client,
        )

        self.assertEqual(failed.status_code, 500)
        self.assertEqual(self._count("workflow_items"), 0)
        self.assertEqual(
            self._key_count(self.a, "deferred-create"), 0
        )
        self._assert_closed(self.connections[-1])

        with closing(connect(self.db_path)) as conn:
            conn.execute("DROP TRIGGER fail_deferred_commit")
            conn.commit()

        retried = self._post(
            item_payload("Deferred commit failure"),
            key="deferred-create",
            client=failure_client,
        )
        self.assertEqual(retried.status_code, 201, retried.text)
        created = retried.json()["item"]
        self.assertEqual(self._count("workflow_items"), 1)
        self.assertEqual(
            self._key_count(self.a, "deferred-create"), 1
        )

        fetched = self._get(created["item_id"])
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["item"], created)

    def test_get_returns_actual_review_and_active_approval_metadata(
        self,
    ) -> None:
        item = self._create_item()
        exact = "approved API text"
        saved_response = self._patch(
            item["item_id"],
            {
                "expected_revision": 1,
                "artifact": {"segments": [exact]},
            },
        )
        self.assertEqual(saved_response.status_code, 200, saved_response.text)

        with closing(connect(self.db_path)) as conn:
            saved_item = items.get_item(
                conn, self.a, item["item_id"]
            )
            approval_result = approvals.approve_item(
                conn,
                self.a,
                item["item_id"],
                ApproveRequest(
                    expected_revision=saved_item.working_revision,
                    artifact_digest=versions.artifact_digest(
                        saved_item.destination,
                        saved_item.format,
                        saved_item.artifact,
                    ),
                    consent=True,
                ),
                request_id="direct-approval",
            )
            version_id = approval_result.body["version"]["version_id"]
            conn.execute(
                "INSERT INTO workflow_reviews("
                " review_id, owner_id, item_id, input_version_id,"
                " request_id, state, actions_json, score_basis_json,"
                " proposals_json, model_config, started_at, finished_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "rev_api_1",
                    self.a.owner_id,
                    item["item_id"],
                    version_id,
                    "review-api-1",
                    "completed",
                    json.dumps({"status": "reviewed"}),
                    json.dumps({"rubric": "council"}),
                    "[]",
                    "qwen3.8-max",
                    TS,
                    TS,
                ),
            )
            conn.commit()

        response = self._get(item["item_id"])

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(
            body["item"]["active_approval_id"],
            approval_result.body["approval"]["approval_id"],
        )
        self.assertEqual(body["approval"], approval_result.body["approval"])
        self.assertEqual(
            body["review"],
            {
                "review_id": "rev_api_1",
                "owner_id": self.a.owner_id,
                "item_id": item["item_id"],
                "input_version_id": version_id,
                "request_id": "review-api-1",
                "state": "completed",
                "actions": {"status": "reviewed"},
                "score_basis": {"rubric": "council"},
                "proposals": [],
                "model_config": "qwen3.8-max",
                "started_at": TS,
                "finished_at": TS,
            },
        )

        self._as(self.b)
        self.assertEqual(self._get(item["item_id"]).status_code, 404)

    def test_workflow_validation_is_readable_and_legacy_entry_points_remain(
        self,
    ) -> None:
        invalid = self._post({"destination": "linkedin", "format": "linkedin_post"})

        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertEqual(invalid.json()["code"], "invalid_request")
        self.assertIsInstance(invalid.json()["detail"], str)

        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})

        legacy = self.client.post("/api/humanize", json={"text": "short"})
        self.assertEqual(legacy.status_code, 422)
        self.assertIsInstance(legacy.json()["detail"], list)

        unknown = self.client.get("/api/workflow/not-a-route")
        self.assertEqual(unknown.status_code, 404)
        self.assertIn("application/json", unknown.headers["content-type"])
        self.assertEqual(unknown.json()["detail"], "Not Found")

        spa = self.client.get("/")
        self.assertEqual(spa.status_code, 200)
        self.assertIn("text/html", spa.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
