"""Reading a historical snapshot is owned and cannot approve or rewrite work."""
import unittest

from workflow_action_fixtures import ActionApiFixture


class SnapshotApiTest(ActionApiFixture, unittest.TestCase):
    def test_viewing_an_unapproved_snapshot_cannot_grant_approval(self):
        item, text = self.saved_item()
        skipped = self.action(item['item_id'], 'skip-review', {'expected_revision': 2}, 'snapshot-skip')
        self.assertEqual(skipped.status_code, 200, skipped.text)
        version_id = skipped.json()['review']['input_version_id']
        before = self._counts()
        response = self.client.get(f"/api/workflow/items/{item['item_id']}/versions/{version_id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['version']['artifact']['segments'], [text])
        self.assertEqual(self._counts(), before)
        self.assertIsNone(self._item(item['item_id'])['active_approval_id'])

    def test_snapshot_read_is_exact_owner_bound_and_read_only(self):
        item, text = self.saved_item()
        approved = self._approve(item['item_id'], 2, [text], 'snapshot-approval')
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()['approval']['version_id']
        before = self._counts()
        path = f"/api/workflow/items/{item['item_id']}/versions/{version_id}"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['version']['artifact']['segments'], [text])
        self.assertEqual(response.json()['version']['revision'], 2)
        self.assertEqual(self._counts(), before)
        other_item = self.fixture._create_item()
        mismatch = self.client.get(f"/api/workflow/items/{other_item['item_id']}/versions/{version_id}")
        self.assertEqual(mismatch.status_code, 404, mismatch.text)
        self.fixture._current = self.fixture.b
        denied = self.client.get(path)
        self.assertEqual(denied.status_code, 404, denied.text)
        self.assertNotIn(text, denied.text)
