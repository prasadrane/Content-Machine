"""Request-owned transactions and real deferred-commit rollback."""

import unittest
from contextlib import closing

from fastapi.testclient import TestClient

from content_machine.api.app import app
from content_machine.storage.db import connect

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsTransactionTest(ActionApiFixture, unittest.TestCase):
    def test_skip_commit_failure_does_not_acknowledge_or_persist(self):
        item, _ = self.saved_item()
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript(
                "CREATE TABLE action_parent (id INTEGER PRIMARY KEY);"
                "CREATE TABLE action_child (parent_id INTEGER, FOREIGN KEY(parent_id)"
                " REFERENCES action_parent(id) DEFERRABLE INITIALLY DEFERRED);"
                "CREATE TRIGGER action_commit_failure AFTER INSERT ON workflow_reviews"
                " BEGIN INSERT INTO action_child VALUES (999); END;"
            )
            conn.commit()
        self.fixture._use_transactional_factory()
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post(
                f"/api/workflow/items/{item['item_id']}/skip-review",
                json={"expected_revision": 2},
                headers={"Idempotency-Key": "failed-skip"},
            )
        self.assertEqual(result.status_code, 500)
        self.assertEqual(self.fixture._count("workflow_reviews"), 0)
        self.assertEqual(self.fixture._key_count(self.fixture.a, "failed-skip"), 0)
        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute("DROP TRIGGER action_commit_failure")
            conn.commit()
        retry = self.action(
            item["item_id"], "skip-review", {"expected_revision": 2}, "failed-skip"
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(self.fixture._count("workflow_reviews"), 1)

    def test_request_owned_outer_transactions_commit_before_acknowledgement(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        self.fixture._use_transactional_factory()

        approved = self._approve(item_id, 2, [text], "tx-approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM workflow_approvals").fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT stage FROM workflow_items WHERE item_id = ?",
                    (item_id,),
                ).fetchone()[0],
                "export",
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM workflow_idempotency"
                    " WHERE owner_id = ? AND request_id = ?",
                    (self.fixture.a.owner_id, "tx-approve"),
                ).fetchone()[0],
                1,
            )
        replay = self._approve(item_id, 2, [text], "tx-approve")
        self.assertEqual((replay.status_code, replay.json()), (200, approved.json()))

        version_id = approved.json()["version"]["version_id"]
        restored = self.action(
            item_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "tx-restore",
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        with closing(connect(self.fixture.db_path)) as conn:
            row = conn.execute(
                "SELECT working_revision, stage, active_approval_id"
                " FROM workflow_items"
                " WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            self.assertEqual((row[0], row[1], row[2]), (3, "draft_review", None))
            self.assertEqual(
                conn.execute(
                    "SELECT purpose FROM workflow_versions"
                    " WHERE item_id = ? AND revision = 3",
                    (item_id,),
                ).fetchone()[0],
                "restore",
            )

        adapted = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "tx-adapt",
        )
        self.assertEqual(adapted.status_code, 201, adapted.text)
        target_id = adapted.json()["item"]["item_id"]
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM workflow_items WHERE item_id = ?",
                    (target_id,),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM workflow_versions"
                    " WHERE item_id = ? AND purpose = 'adaptation'",
                    (target_id,),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM workflow_idempotency"
                    " WHERE request_id = 'tx-adapt'"
                ).fetchone()[0],
                1,
            )
        self.fixture._assert_closed(self.fixture.connections[-1])

    def test_deferred_commit_failure_rolls_back_actions_and_same_key_retries(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript(
                "CREATE TABLE action_fk_parent (id INTEGER PRIMARY KEY);"
                "CREATE TABLE action_fk_child (parent_id INTEGER, FOREIGN KEY(parent_id)"
                " REFERENCES action_fk_parent(id) DEFERRABLE INITIALLY DEFERRED);"
                "CREATE TRIGGER action_approval_commit_failure"
                " AFTER INSERT ON workflow_approvals"
                " BEGIN INSERT INTO action_fk_child VALUES (999); END;"
            )
            conn.commit()
        self.fixture._use_transactional_factory()
        with TestClient(app, raise_server_exceptions=False) as client:
            failed = client.post(
                f"/api/workflow/items/{item_id}/approve",
                json={
                    "expected_revision": 2,
                    "artifact_digest": self._digest([text]),
                    "consent": True,
                },
                headers={"Idempotency-Key": "failed-approve"},
            )
        self.assertEqual(failed.status_code, 500)
        self.assertEqual(self.fixture._count("workflow_approvals"), 0)
        self.assertEqual(self.fixture._count("workflow_versions"), 0)
        self.assertEqual(self.fixture._key_count(self.fixture.a, "failed-approve"), 0)
        self.assertEqual(self._item(item_id)["stage"], "draft_review")
        self.assertIsNone(self._item(item_id)["active_approval_id"])
        self.assertEqual(self._item(item_id)["working_revision"], 2)

        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute("DROP TRIGGER action_approval_commit_failure")
            conn.commit()
        retried = self._approve(item_id, 2, [text], "failed-approve")
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(self.fixture._count("workflow_approvals"), 1)
        version_id = retried.json()["version"]["version_id"]

        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute(
                "CREATE TRIGGER action_item_commit_failure"
                " AFTER INSERT ON workflow_items"
                " BEGIN INSERT INTO action_fk_child VALUES (999); END;"
            )
            conn.commit()
        with TestClient(app, raise_server_exceptions=False) as client:
            failed_adapt = client.post(
                f"/api/workflow/items/{item_id}/adapt",
                json={
                    "source_version_id": version_id,
                    "destination": "instagram",
                    "format": "instagram_caption",
                },
                headers={"Idempotency-Key": "failed-adapt"},
            )
        self.assertEqual(failed_adapt.status_code, 500)
        self.assertEqual(self.fixture._count("workflow_items"), 1)
        self.assertEqual(self.fixture._key_count(self.fixture.a, "failed-adapt"), 0)
        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute("DROP TRIGGER action_item_commit_failure")
            conn.commit()
        retried_adapt = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "failed-adapt",
        )
        self.assertEqual(retried_adapt.status_code, 201, retried_adapt.text)
        self.assertEqual(self.fixture._count("workflow_items"), 2)


if __name__ == "__main__":
    unittest.main()
