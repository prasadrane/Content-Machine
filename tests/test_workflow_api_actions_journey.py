"""Manual action journey, skip key checks and exact thread export."""

import unittest
import hashlib
import json

import test_workflow_api_items as fixtures

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsJourneyTest(ActionApiFixture, unittest.TestCase):
    def test_skip_approval_export_restore_and_adapt(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        skipped = self.action(item_id, "skip-review", {"expected_revision": 2}, "skip")
        self.assertEqual(skipped.status_code, 200, skipped.text)
        self.assertEqual(skipped.json()["review"]["state"], "skipped")
        self.assertIsNone(skipped.json()["review"]["score_basis"])
        self.assertIsNone(skipped.json()["item"]["active_approval_id"])
        self.assertEqual(skipped.json()["item"]["working_revision"], 2)
        self.assertEqual(self.fixture._count("workflow_operations"), 0)
        replay = self.action(item_id, "skip-review", {"expected_revision": 2}, "skip")
        self.assertEqual(replay.json(), skipped.json())
        self.assertEqual(self.fixture._count("workflow_reviews"), 1)
        changed_retry = self.action(
            item_id, "skip-review", {"expected_revision": 1}, "skip"
        )
        self.assertEqual(changed_retry.json()["code"], "idempotency_conflict")

        material = {
            "destination": "linkedin",
            "format": "linkedin_post",
            "segments": [text],
        }
        encoded = json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
        refused = self.action(
            item_id,
            "approve",
            {"expected_revision": 2, "artifact_digest": digest, "consent": False},
            "refused",
        )
        self.assertEqual(refused.status_code, 409)
        approved = self.action(
            item_id,
            "approve",
            {"expected_revision": 2, "artifact_digest": digest, "consent": True},
            "approve",
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()["approval"]["version_id"]
        url = f"/api/workflow/items/{item_id}/exports/{version_id}"
        download = self.client.get(url)
        self.assertEqual(download.content, text.encode())
        self.assertEqual(download.headers["x-artifact-digest"], digest)
        self.assertEqual(
            self.client.get(url, params={"as": "json"}).json()["segments"], [text]
        )
        history = self.client.get(f"/api/workflow/items/{item_id}/versions")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["approvals"][0]["status"], "active")

        adapted = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "adapt",
        )
        self.assertEqual(adapted.status_code, 201, adapted.text)
        self.assertIsNone(adapted.json()["item"]["active_approval_id"])
        restored = self.action(
            item_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "restore",
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertIsNone(restored.json()["item"]["active_approval_id"])
        self.assertEqual(self.client.get(url).content, text.encode())
        new_version = restored.json()["version"]["version_id"]
        self.assertEqual(
            self.client.get(
                f"/api/workflow/items/{item_id}/exports/{new_version}"
            ).status_code,
            409,
        )
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.action(
                item_id,
                "restore",
                {"expected_revision": 3, "version_id": version_id},
                "other",
            ).status_code,
            404,
        )

    def test_skip_requires_key_and_checks_revision(self):
        item, _ = self.saved_item()
        path = f"/api/workflow/items/{item['item_id']}/skip-review"
        self.assertEqual(
            self.client.post(path, json={"expected_revision": 2}).status_code, 422
        )
        stale = self.action(
            item["item_id"], "skip-review", {"expected_revision": 1}, "stale"
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.fixture._count("workflow_reviews"), 0)

    def test_thread_export_preserves_segments_and_separator(self):
        created = self.fixture._post(fixtures.item_payload("Thread", "x", "x_thread"))
        item_id = created.json()["item"]["item_id"]
        segments = [" first \r\n", "second  "]
        saved = self.fixture._patch(
            item_id, {"expected_revision": 1, "artifact": {"segments": segments}}
        )
        self.assertEqual(saved.status_code, 200)
        material = {"destination": "x", "format": "x_thread", "segments": segments}
        encoded = json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
        approved = self.action(
            item_id,
            "approve",
            {"expected_revision": 2, "artifact_digest": digest, "consent": True},
            "approve-thread",
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()["version"]["version_id"]
        path = f"/api/workflow/items/{item_id}/exports/{version_id}"
        self.assertEqual(self.client.get(path).content, "\n\n".join(segments).encode())
        self.assertEqual(
            self.client.get(path, params={"as": "json"}).json()["segments"], segments
        )


if __name__ == "__main__":
    unittest.main()
