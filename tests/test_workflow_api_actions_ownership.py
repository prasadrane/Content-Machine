"""Nested item/version ownership, required keys and retry identity."""

import unittest

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsOwnershipTest(ActionApiFixture, unittest.TestCase):
    def test_actions_are_bound_to_the_owned_item_and_version(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        skipped = self.action(
            item_id, "skip-review", {"expected_revision": 2}, "owned-skip"
        )
        self.assertEqual(skipped.status_code, 200, skipped.text)
        version_id = skipped.json()["review"]["input_version_id"]

        other = self.fixture._create_item(title="Second owned item")
        other_id = other["item_id"]
        other_saved = self.fixture._patch(
            other_id,
            {"expected_revision": 1, "artifact": {"segments": ["other text"]}},
        )
        self.assertEqual(other_saved.status_code, 200, other_saved.text)

        self.fixture._as(self.fixture.b)
        foreign = self.fixture._create_item(title="Foreign item")
        foreign_id = foreign["item_id"]
        foreign_saved = self.fixture._patch(
            foreign_id,
            {"expected_revision": 1, "artifact": {"segments": ["foreign text"]}},
        )
        self.assertEqual(foreign_saved.status_code, 200, foreign_saved.text)
        foreign_approval = self.action(
            foreign_id,
            "approve",
            {
                "expected_revision": 2,
                "artifact_digest": self._digest(["foreign text"]),
                "consent": True,
            },
            "foreign-owner-approve",
        )
        self.assertEqual(foreign_approval.status_code, 200, foreign_approval.text)
        foreign_version = foreign_approval.json()["version"]["version_id"]
        self.fixture._as(self.fixture.a)

        digest = self._digest([text])
        for name, body in (
            ("skip-review", {"expected_revision": 2}),
            (
                "approve",
                {
                    "expected_revision": 2,
                    "artifact_digest": digest,
                    "consent": True,
                },
            ),
            ("restore", {"expected_revision": 2, "version_id": version_id}),
            (
                "adapt",
                {
                    "source_version_id": version_id,
                    "destination": "instagram",
                    "format": "instagram_caption",
                },
            ),
        ):
            with self.subTest(action=name):
                denied = self.action(foreign_id, name, body, f"foreign-{name}")
                self.assertEqual(
                    (denied.status_code, denied.json()["code"]),
                    (404, "item_not_found"),
                )

        cross_item = self.client.get(
            f"/api/workflow/items/{other_id}/exports/{version_id}"
        )
        self.assertEqual(
            (cross_item.status_code, cross_item.json()["code"]),
            (404, "version_not_found"),
        )
        wrong_restore = self.action(
            other_id,
            "restore",
            {"expected_revision": 2, "version_id": version_id},
            "wrong-item-restore",
        )
        self.assertEqual(
            (wrong_restore.status_code, wrong_restore.json()["code"]),
            (404, "version_not_found"),
        )
        wrong_adapt = self.action(
            other_id,
            "adapt",
            {
                "source_version_id": version_id,
                "destination": "instagram",
                "format": "instagram_caption",
            },
            "wrong-item-adapt",
        )
        self.assertEqual(
            (wrong_adapt.status_code, wrong_adapt.json()["code"]),
            (404, "version_not_found"),
        )
        wrong_export = self.client.get(
            f"/api/workflow/items/{other_id}/exports/{version_id}"
        )
        self.assertEqual(wrong_export.status_code, 404)

        self.assertEqual(
            self.client.get(f"/api/workflow/items/{foreign_id}/versions").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"/api/workflow/items/{foreign_id}/exports/{foreign_version}"
            ).status_code,
            404,
        )

        self.fixture._as(self.fixture.b)
        foreign_item = self._item(foreign_id)
        self.fixture._as(self.fixture.a)
        self.assertEqual(foreign_item["stage"], "export")
        self.assertEqual(foreign_item["working_revision"], 2)
        self.assertEqual(self._item(item_id)["stage"], "approve")
        self.assertEqual(self._item(other_id)["working_revision"], 2)
        self.assertEqual(self._item(other_id)["stage"], "draft_review")
        self.assertEqual(self.fixture._count("workflow_versions"), 2)
        self.assertEqual(self.fixture._count("workflow_approvals"), 1)

    def test_mutation_routes_require_nonblank_idempotency_keys(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        bodies = {
            "skip-review": {"expected_revision": 2},
            "approve": {
                "expected_revision": 2,
                "artifact_digest": self._digest([text]),
                "consent": True,
            },
            "restore": {"expected_revision": 2, "version_id": "ver_missing"},
            "adapt": {
                "source_version_id": "ver_missing",
                "destination": "instagram",
                "format": "instagram_caption",
            },
        }
        for name, body in bodies.items():
            for key in (None, "   "):
                with self.subTest(action=name, key=key):
                    headers = {} if key is None else {"Idempotency-Key": key}
                    response = self.client.post(
                        f"/api/workflow/items/{item_id}/{name}",
                        json=body,
                        headers=headers,
                    )
                    self.assertEqual(
                        (response.status_code, response.json()["code"]),
                        (422, "invalid_request"),
                    )
                    self.assertIsInstance(response.json()["detail"], str)
        counts = self._counts()
        self.assertEqual(
            (
                counts["workflow_versions"],
                counts["workflow_approvals"],
                counts["workflow_reviews"],
            ),
            (0, 0, 0),
        )
        self.assertEqual(self.fixture._key_count(self.fixture.a, ""), 0)
        self.assertEqual(self.fixture._key_count(self.fixture.a, "   "), 0)
        self.assertEqual(self._item(item_id)["working_revision"], 2)
        self.assertEqual(self._item(item_id)["stage"], "draft_review")


if __name__ == "__main__":
    unittest.main()
