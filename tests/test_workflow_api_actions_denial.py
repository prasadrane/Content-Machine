"""Unapproved adaptation and restore export denial."""

import unittest

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsDenialTest(ActionApiFixture, unittest.TestCase):
    def test_adaptation_and_restore_exports_require_their_own_approval(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        skipped = self.action(
            item_id, "skip-review", {"expected_revision": 2}, "adapt-skip"
        )
        self.assertEqual(skipped.status_code, 200, skipped.text)
        frozen_id = skipped.json()["review"]["input_version_id"]
        refused = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": frozen_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "adapt-unapproved",
        )
        self.assertEqual(
            (refused.status_code, refused.json()["code"]),
            (409, "approval_required"),
        )
        self.assertEqual(refused.json()["working_revision"], 2)
        self.assertEqual(self.fixture._count("workflow_items"), 1)

        approved = self._approve(item_id, 2, [text], "adapt-approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        approval = approved.json()["approval"]
        version_id = approved.json()["version"]["version_id"]
        adapted = self.action(
            item_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "adapt-approved",
        )
        self.assertEqual(adapted.status_code, 201, adapted.text)
        target = adapted.json()["item"]
        self.assertEqual(
            (
                target["parent_version_id"],
                target["working_revision"],
                target["stage"],
                target["active_approval_id"],
                target["artifact"]["segments"],
            ),
            (version_id, 1, "draft_review", None, []),
        )
        self.assertNotEqual(target["item_id"], item_id)
        source_item = self._item(item_id)
        self.assertEqual(source_item["working_revision"], 2)
        self.assertEqual(source_item["active_approval_id"], approval["approval_id"])

        target_history = self._history(target["item_id"])
        self.assertEqual(
            [row["purpose"] for row in target_history["versions"]],
            ["adaptation"],
        )
        self.assertEqual(target_history["approvals"], [])
        target_version = target_history["versions"][0]["version_id"]
        target_export = self.client.get(
            f"/api/workflow/items/{target['item_id']}/exports/{target_version}"
        )
        self.assertEqual(
            (target_export.status_code, target_export.json()["code"]),
            (409, "approval_required"),
        )

        restored = self.action(
            item_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "restore-approved",
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["version"]["purpose"], "restore")
        self.assertEqual(restored.json()["item"]["parent_version_id"], version_id)
        restored_version = restored.json()["version"]["version_id"]
        restored_export = self.client.get(
            f"/api/workflow/items/{item_id}/exports/{restored_version}"
        )
        self.assertEqual(
            (restored_export.status_code, restored_export.json()["code"]),
            (409, "approval_required"),
        )
        self.assertEqual(
            self.client.get(
                f"/api/workflow/items/{item_id}/exports/{version_id}"
            ).content,
            text.encode(),
        )


if __name__ == "__main__":
    unittest.main()
