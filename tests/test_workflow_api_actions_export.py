"""Exact export bytes/headers/filename, read-only history, skip currency."""

import unittest
import re

import test_workflow_api_items as fixtures

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsExportTest(ActionApiFixture, unittest.TestCase):
    def test_skip_after_approval_preserves_the_active_approval(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        approved = self._approve(item_id, 2, [text], "approve-before-skip")
        self.assertEqual(approved.status_code, 200, approved.text)
        approval = approved.json()["approval"]
        version_id = approved.json()["version"]["version_id"]

        skipped = self.action(
            item_id, "skip-review", {"expected_revision": 2}, "skip-after-approval"
        )
        self.assertEqual(skipped.status_code, 200, skipped.text)
        self.assertEqual(skipped.json()["review"]["state"], "skipped")
        self.assertEqual(skipped.json()["review"]["input_version_id"], version_id)
        self.assertEqual(skipped.json()["item"]["stage"], "approve")
        self.assertEqual(
            skipped.json()["item"]["active_approval_id"], approval["approval_id"]
        )
        self.assertEqual(skipped.json()["item"]["working_revision"], 2)

        fetched = self.client.get(f"/api/workflow/items/{item_id}").json()
        self.assertEqual(fetched["item"]["active_approval_id"], approval["approval_id"])
        self.assertEqual(fetched["approval"], approval)
        self.assertEqual(self._history(item_id)["approvals"][0]["status"], "active")
        exported = self.client.get(
            f"/api/workflow/items/{item_id}/exports/{version_id}"
        )
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(exported.content, text.encode())

        edited = self.fixture._patch(
            item_id,
            {"expected_revision": 2, "artifact": {"segments": [text + "x"]}},
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["item"]["working_revision"], 3)
        self.assertIsNone(edited.json()["item"]["active_approval_id"])
        self.assertEqual(
            self._history(item_id)["approvals"][0]["status"], "historical"
        )
        self.assertEqual(
            self.client.get(
                f"/api/workflow/items/{item_id}/exports/{version_id}"
            ).content,
            text.encode(),
        )

    def test_export_returns_exact_bytes_headers_filename_and_json_payload(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        approved = self._approve(item_id, 2, [text], "export-approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()["version"]["version_id"]
        digest = approved.json()["approval"]["artifact_digest"]
        url = f"/api/workflow/items/{item_id}/exports/{version_id}"

        counts = self._counts()
        download = self.client.get(url)
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, text.encode())
        self.assertEqual(
            download.headers["content-type"], "text/plain; charset=utf-8"
        )
        self.assertEqual(
            download.headers["content-disposition"],
            'attachment; filename="indexing-tradeoffs-r2.txt"',
        )
        self.assertEqual(download.headers["x-artifact-digest"], digest)
        invalid_alias = self.client.get(url, params={"as": "bogus"})
        self.assertEqual(
            (invalid_alias.status_code, invalid_alias.json()["code"]),
            (422, "invalid_request"),
        )
        payload = self.client.get(url, params={"as": "json"}).json()
        self.assertEqual(
            set(payload),
            {"version_id", "destination", "format", "artifact_digest", "segments"},
        )
        self.assertEqual(
            payload,
            {
                "version_id": version_id,
                "destination": "linkedin",
                "format": "linkedin_post",
                "artifact_digest": digest,
                "segments": [text],
            },
        )
        self.assertEqual(self._counts(), counts)

        reserved = self.fixture._post(fixtures.item_payload("CON"))
        reserved_id = reserved.json()["item"]["item_id"]
        self.fixture._patch(
            reserved_id,
            {"expected_revision": 1, "artifact": {"segments": ["reserved"]}},
        )
        reserved_approval = self._approve(
            reserved_id, 2, ["reserved"], "reserved-approve"
        )
        self.assertEqual(reserved_approval.status_code, 200, reserved_approval.text)
        reserved_header = self.client.get(
            f"/api/workflow/items/{reserved_id}/exports/"
            f"{reserved_approval.json()['version']['version_id']}"
        ).headers["content-disposition"]
        safe_id = re.sub(r"[^A-Za-z0-9-]+", "-", reserved_id).strip("-").lower()
        self.assertEqual(
            reserved_header,
            f'attachment; filename="content-{safe_id}-r2.txt"',
        )

        odd = self.fixture._post(
            fixtures.item_payload('A "quoted"; CRT: title\\ path')
        )
        odd_id = odd.json()["item"]["item_id"]
        self.fixture._patch(
            odd_id, {"expected_revision": 1, "artifact": {"segments": ["odd"]}}
        )
        odd_approval = self._approve(odd_id, 2, ["odd"], "odd-approve")
        self.assertEqual(odd_approval.status_code, 200, odd_approval.text)
        odd_header = self.client.get(
            f"/api/workflow/items/{odd_id}/exports/"
            f"{odd_approval.json()['version']['version_id']}"
        ).headers["content-disposition"]
        filename = odd_header.split('filename="', 1)[1].rstrip('"')
        self.assertRegex(filename, r"^[a-z0-9-]+-r2\.txt$")
        for forbidden in ('"', "\\", ":", ";", "\r", "\n", " "):
            self.assertNotIn(forbidden, filename)

    def test_history_is_read_only_and_owner_bound(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        approved = self._approve(item_id, 2, [text], "history-approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        approval = approved.json()["approval"]
        version_id = approved.json()["version"]["version_id"]

        counts = self._counts()
        first = self._history(item_id)
        second = self._history(item_id)
        self.assertEqual(first, second)
        self.assertEqual(self._counts(), counts)
        self.assertEqual(
            [
                (
                    row["version_id"],
                    row["revision"],
                    row["purpose"],
                    row["artifact_digest"],
                    row["destination"],
                    row["format"],
                )
                for row in first["versions"]
            ],
            [
                (
                    version_id,
                    2,
                    "approval",
                    approval["artifact_digest"],
                    "linkedin",
                    "linkedin_post",
                )
            ],
        )
        self.assertEqual(
            first["approvals"],
            [
                {
                    "approval_id": approval["approval_id"],
                    "version_id": version_id,
                    "status": "active",
                    "approved_at": approval["approved_at"],
                }
            ],
        )

        self.fixture._as(self.fixture.b)
        self.assertEqual(
            self.client.get(f"/api/workflow/items/{item_id}/versions").status_code,
            404,
        )
        self.fixture._as(self.fixture.a)
        self.assertEqual(self._counts(), counts)

        empty = self.fixture._create_item(title="No history yet")
        self.assertEqual(
            self._history(empty["item_id"]),
            {"versions": [], "approvals": []},
        )


if __name__ == "__main__":
    unittest.main()
