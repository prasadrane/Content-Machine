"""Guest examples require verified sessions and remain owned and editable."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from content_machine.storage.db import connect
from content_machine.workflow import items
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import (
    GUEST_MIGRATION_STATEMENTS, VerifiedGuestSession, bootstrap_guest, preview_transfer,
)
from content_machine.workflow.schemas import ItemPatch, Principal


class GuestLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.home = TemporaryDirectory(prefix='guest-check-')
        self.addCleanup(self.home.cleanup)
        self.path = Path(self.home.name) / 'workflow.db'
        with closing(connect(self.path)) as conn:
            for statement in GUEST_MIGRATION_STATEMENTS:
                conn.execute(statement)
            conn.commit()
        self.guest = Principal(owner_id='guest-1', mode='hosted_verified')
        self.other = Principal(owner_id='guest-2', mode='hosted_verified')
        self.creator = Principal(owner_id='creator-1', mode='hosted_verified')
        self.sessions = {
            'guest-proof': VerifiedGuestSession(self.guest, is_anonymous=True),
            'other-proof': VerifiedGuestSession(self.other, is_anonymous=True),
            'creator-proof': VerifiedGuestSession(self.creator, is_anonymous=False),
        }

    def verify(self, proof):
        return self.sessions.get(proof)

    def boot(self, proof='guest-proof'):
        with closing(connect(self.path)) as conn:
            return bootstrap_guest(conn, proof, self.verify)

    def test_seed_is_labelled_owned_editable_and_never_overwrites_on_return(self):
        seeded = self.boot()
        self.assertEqual(len(seeded['examples']), 2)
        self.assertTrue(all(example['label'] == 'Demo example' for example in seeded['examples']))
        example = seeded['examples'][0]['item']
        self.assertEqual(example['owner_id'], self.guest.owner_id)
        with closing(connect(self.path)) as conn:
            changed = items.save_item(conn, self.guest, example['item_id'],
                ItemPatch(expected_revision=example['working_revision'], context={'notes': 'My real replacement notes'}),
                request_id='creator-edits-example')
        self.assertEqual(changed.body['item']['context']['notes'], 'My real replacement notes')
        again = self.boot()
        retained = next(entry['item'] for entry in again['examples'] if entry['item']['item_id'] == example['item_id'])
        self.assertEqual(retained['context']['notes'], 'My real replacement notes')
        self.assertEqual(len(self.boot('other-proof')['examples']), 2)
        with closing(connect(self.path)) as conn:
            self.assertEqual(len(items.list_items(conn, self.guest)), 2)
            self.assertEqual(len(items.list_items(conn, self.other)), 2)

    def test_bootstrap_rejects_missing_unverified_and_non_guest_identity(self):
        for proof in ('unknown', 'creator-proof'):
            with self.subTest(proof=proof), self.assertRaises(WorkflowError):
                self.boot(proof)
        self.sessions['local'] = VerifiedGuestSession(Principal(owner_id='local', mode='trusted_local'), is_anonymous=True)
        with self.assertRaises(WorkflowError):
            self.boot('local')
        self.sessions['untrusted'] = {'owner_id': 'guest-1', 'is_anonymous': True}
        self.sessions['nonboolean'] = VerifiedGuestSession(self.guest, is_anonymous=1)
        for proof in ('untrusted', 'nonboolean'):
            with self.subTest(proof=proof), self.assertRaises(WorkflowError):
                self.boot(proof)
        with closing(connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)

    def test_concurrent_bootstrap_creates_one_set(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.boot(), range(2)))
        first = {item['item']['item_id'] for item in responses[0]['examples']}
        second = {item['item']['item_id'] for item in responses[1]['examples']}
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)

    def test_real_commit_failure_rolls_back_entire_seed_and_can_retry(self):
        with closing(connect(self.path)) as conn:
            conn.executescript('CREATE TABLE guest_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE guest_child(parent_id INTEGER REFERENCES guest_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_guest AFTER INSERT ON workflow_guest_examples BEGIN INSERT INTO guest_child VALUES (999); END;')
            conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.boot()
        with closing(connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_examples').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_guest')
            conn.commit()
        self.assertEqual(len(self.boot()['examples']), 2)

    def test_transfer_requires_explicit_consent_and_two_verified_identities(self):
        self.boot()
        with closing(connect(self.path)) as conn:
            for guest, creator, consent in [('guest-proof', 'creator-proof', False),
                                            ('unknown', 'creator-proof', True),
                                            ('guest-proof', 'unknown', True),
                                            ('creator-proof', 'guest-proof', True),
                                            ('guest-proof', 'guest-proof', True)]:
                with self.subTest(guest=guest, creator=creator, consent=consent), self.assertRaises(WorkflowError):
                    preview_transfer(conn, guest, creator, self.verify, consent=consent)
            preview = preview_transfer(conn, 'guest-proof', 'creator-proof', self.verify, consent=True)
            self.assertEqual(preview['status'], 'unavailable')
            self.assertEqual(preview['guest_item_count'], 2)
            self.assertEqual(len(items.list_items(conn, self.creator)), 0)


if __name__ == '__main__':
    unittest.main()
