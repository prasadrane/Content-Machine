"""Shared action-test fixture helpers (never collected as tests).

Deliberately outside the ``test*.py`` discovery pattern and free of
``test_*`` methods, so each of the 16 action cases is defined exactly once
in the focused modules that use this mixin. Only fixture setup and
boundary helpers live here; no TestCase class is bound into a test module.
"""

import hashlib
import json

import test_workflow_api_items as fixtures


class ActionApiFixture:
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
    def saved_item(self):
        item = self.fixture._create_item()
        text = "  Exact café text\r\nsecond line  \n"
        saved = self.fixture._patch(
            item["item_id"],
            {"expected_revision": 1, "artifact": {"segments": [text]}},
        )
        self.assertEqual(saved.status_code, 200)
        return saved.json()["item"], text
    def action(self, item_id, name, body, key):
        return self.client.post(
            f"/api/workflow/items/{item_id}/{name}",
            json=body,
            headers={"Idempotency-Key": key},
        )
    def _digest(self, segments, destination="linkedin", format="linkedin_post"):
        material = {
            "destination": destination,
            "format": format,
            "segments": list(segments),
        }
        encoded = json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()
    def _approve(self, item_id, revision, segments, key, *, consent=True):
        return self.action(
            item_id,
            "approve",
            {
                "expected_revision": revision,
                "artifact_digest": self._digest(segments),
                "consent": consent,
            },
            key,
        )
    def _item(self, item_id):
        response = self.client.get(f"/api/workflow/items/{item_id}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["item"]
    def _history(self, item_id):
        response = self.client.get(f"/api/workflow/items/{item_id}/versions")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()
    def _counts(self):
        return {
            table: self.fixture._count(table)
            for table in (
                "workflow_items",
                "workflow_versions",
                "workflow_approvals",
                "workflow_reviews",
                "workflow_idempotency",
            )
        }
