"""Normal saved-work lists disclose only stored, owned guest provenance."""
from contextlib import closing
import unittest

import test_workflow_api_items as fixtures
from content_machine.storage.db import connect
from content_machine.workflow.guests import (
    GUEST_MIGRATION_STATEMENTS, VerifiedGuestSession, bootstrap_guest,
)


class GuestLabelsHttpTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client

    def listed(self):
        response = self.client.get('/api/workflow/items')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['items']

    def boot(self, owner):
        with closing(connect(self.fixture.db_path)) as conn:
            # Provision explicitly in this case so it isolates list integration
            # from the separate ordinary-migration regression below.
            for statement in GUEST_MIGRATION_STATEMENTS:
                conn.execute(statement)
            conn.commit()
            return bootstrap_guest(conn, 'verified-proof', lambda _: VerifiedGuestSession(owner, True))

    def test_normal_connection_registers_empty_metadata_without_seeding(self):
        self.assertEqual(self.listed(), [])
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_examples').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)

    def test_owned_origin_survives_edits_and_return_without_title_inference(self):
        seeded = self.boot(self.fixture.a)['examples']
        example = seeded[0]['item']
        private = self.fixture._create_item(title=example['title'])
        records = {item['item_id']: item for item in self.listed()}
        self.assertEqual(records[example['item_id']]['guest_example_label'], 'Demo example')
        self.assertIsNone(records[private['item_id']].get('guest_example_label'))
        changed = self.fixture._patch(example['item_id'], {
            'expected_revision': example['working_revision'], 'title': 'My edited title',
            'context': {'notes': 'My replacement notes'},
        })
        self.assertEqual(changed.status_code, 200, changed.text)
        self.boot(self.fixture.a)
        records = {item['item_id']: item for item in self.listed()}
        self.assertEqual(len(records), 3)
        self.assertEqual(records[example['item_id']]['title'], 'My edited title')
        self.assertEqual(records[example['item_id']]['guest_example_label'], 'Demo example')
        self.assertIsNone(records[example['item_id']]['active_approval_id'])
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.listed(), [])
        other_private = self.fixture._create_item(title=private['title'])
        other_seed = self.boot(self.fixture.b)['examples']
        records = {item['item_id']: item for item in self.listed()}
        self.assertEqual(set(records), {other_private['item_id'], *(entry['item']['item_id'] for entry in other_seed)})
        self.assertIsNone(records[other_private['item_id']].get('guest_example_label'))
        self.assertTrue(all(records[entry['item']['item_id']]['guest_example_label'] == 'Demo example' for entry in other_seed))

