"""Approval field/digest/consent validation and replay semantics."""

import unittest
import test_workflow_api_items as fixtures

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsApprovalTest(ActionApiFixture, unittest.TestCase):
    def test_approve_validates_fields_digest_consent_and_final_artifact(self):
        created = self.fixture._post(fixtures.item_payload("Approval boundary"))
        self.assertEqual(created.status_code, 201, created.text)
        item_id = created.json()["item"]["item_id"]
        text = "Final text"
        saved = self.fixture._patch(
            item_id, {"expected_revision": 1, "artifact": {"segments": [text]}}
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        saved_item = saved.json()["item"]
        digest = self._digest([text])

        for label, body in (
            ("empty", {}),
            ("no-digest", {"expected_revision": 2, "consent": True}),
            ("no-consent", {"expected_revision": 2, "artifact_digest": digest}),
            (
                "malformed-digest",
                {
                    "expected_revision": 2,
                    "artifact_digest": "not-a-digest",
                    "consent": True,
                },
            ),
        ):
            with self.subTest(case=label):
                response = self.action(item_id, "approve", body, f"invalid-{label}")
                self.assertEqual(
                    (response.status_code, response.json()["code"]),
                    (422, "invalid_request"),
                )

        refused = self._approve(
            item_id, 2, [text], "no-consent-approve", consent=False
        )
        self.assertEqual(
            (refused.status_code, refused.json()["code"]),
            (409, "approval_conflict"),
        )
        self.assertEqual(refused.json()["working_revision"], 2)
        self.assertEqual(refused.json()["stage"], "draft_review")

        wrong = self.action(
            item_id,
            "approve",
            {
                "expected_revision": 2,
                "artifact_digest": "sha256:" + "0" * 64,
                "consent": True,
            },
            "wrong-digest-approve",
        )
        self.assertEqual(
            (wrong.status_code, wrong.json()["code"]),
            (409, "artifact_digest_mismatch"),
        )
        self.assertEqual(wrong.json()["working_revision"], 2)
        self.assertIsNone(wrong.json()["active_approval_id"])

        stale = self.action(
            item_id,
            "approve",
            {
                "expected_revision": 1,
                "artifact_digest": digest,
                "consent": True,
            },
            "stale-approve",
        )
        self.assertEqual(
            (stale.status_code, stale.json()["code"]),
            (409, "revision_conflict"),
        )
        self.assertEqual(
            (
                stale.json()["working_revision"],
                stale.json()["stage"],
                stale.json()["updated_at"],
                stale.json()["active_approval_id"],
            ),
            (2, "draft_review", saved_item["updated_at"], None),
        )

        blank = self.fixture._post(fixtures.item_payload("Blank artifact"))
        blank_id = blank.json()["item"]["item_id"]
        blank_approval = self.action(
            blank_id,
            "approve",
            {
                "expected_revision": 1,
                "artifact_digest": self._digest([]),
                "consent": True,
            },
            "blank-approve",
        )
        self.assertEqual(
            (blank_approval.status_code, blank_approval.json()["code"]),
            (422, "invalid_artifact"),
        )

        counts = self._counts()
        self.assertEqual(
            (counts["workflow_approvals"], counts["workflow_versions"]),
            (0, 0),
        )
        self.assertEqual(self._item(item_id)["artifact"]["segments"], [text])
        self.assertEqual(self._item(item_id)["stage"], "draft_review")
        self.assertIsNone(self._item(item_id)["active_approval_id"])

    def test_action_retries_replay_and_changed_requests_conflict(self):
        item, text = self.saved_item()
        item_id = item["item_id"]

        approved = self._approve(item_id, 2, [text], "approve-retry")
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()["version"]["version_id"]
        replay = self._approve(item_id, 2, [text], "approve-retry")
        self.assertEqual((replay.status_code, replay.json()), (200, approved.json()))
        changed = self._approve(item_id, 2, [text + " "], "approve-retry")
        self.assertEqual(
            (changed.status_code, changed.json()["code"]),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(self.fixture._count("workflow_approvals"), 1)

        restored = self.action(
            item_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "restore-retry",
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        restored_replay = self.action(
            item_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "restore-retry",
        )
        self.assertEqual(
            (restored_replay.status_code, restored_replay.json()),
            (200, restored.json()),
        )
        restored_changed = self.action(
            item_id,
            "restore",
            {"expected_revision": 3, "version_id": version_id},
            "restore-retry",
        )
        self.assertEqual(
            (restored_changed.status_code, restored_changed.json()["code"]),
            (409, "idempotency_conflict"),
        )

        adapt_body = {
            "source_version_id": version_id,
            "destination": "instagram",
            "format": "instagram_caption",
        }
        adapted = self.action(item_id, "adapt", adapt_body, "adapt-retry")
        self.assertEqual(adapted.status_code, 201, adapted.text)
        adapted_replay = self.action(item_id, "adapt", adapt_body, "adapt-retry")
        self.assertEqual(
            (adapted_replay.status_code, adapted_replay.json()),
            (201, adapted.json()),
        )
        adapted_changed = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_reel_script",
            },
            "adapt-retry",
        )
        self.assertEqual(
            (adapted_changed.status_code, adapted_changed.json()["code"]),
            (409, "idempotency_conflict"),
        )
        self.assertEqual(self.fixture._count("workflow_items"), 2)

        across_routes = self.action(
            item_id, "skip-review", {"expected_revision": 3}, "approve-retry"
        )
        self.assertEqual(
            (across_routes.status_code, across_routes.json()["code"]),
            (409, "idempotency_conflict"),
        )


if __name__ == "__main__":
    unittest.main()
