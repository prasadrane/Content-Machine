"""Owner-isolated, immutable editorial context for a frozen content version."""
import json
import os
import tempfile
import unittest
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from content_machine.knowledge.provider import get_editorial_context
from content_machine.storage.db import connect
from content_machine.workflow.context import build_editorial_snapshot
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import create_item, save_item
from content_machine.workflow.preferences import mutate_preference, propose_preference
from content_machine.workflow.schemas import ItemCreate, ItemPatch, Principal, VersionPurpose
from content_machine.workflow.settings import ProfileSave, get_profile, save_profile
from content_machine.workflow.versions import freeze_version


class EditorialSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workflow-context-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'context.db'
        self.conn = connect(self.path)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.addCleanup(self.conn.close)
        self.a = Principal(owner_id='owner-A', mode='hosted_verified')
        self.b = Principal(owner_id='owner-B', mode='hosted_verified')

    def profile(self, owner, name, revision=0):
        return save_profile(self.conn, owner,
            ProfileSave(name=name, role='Engineer', bio='Factual profile', expected_revision=revision),
            request_id=f'profile-{owner.owner_id}-{revision}')

    def preference(self, owner, text, key):
        return mutate_preference(self.conn, owner, 'create', None,
            {'text': text, 'consent': True}, key).body['preference']

    def version(self, owner, *, excerpt='Actual source excerpt', url='https://example.org/article#part'):
        result = create_item(self.conn, owner,
            ItemCreate(title='A working title', destination='linkedin', format='linkedin_post'),
            request_id=f'item-{owner.owner_id}-{url}')
        item_id = result.body['item']['item_id']
        source = {'source_id': 'source-1', 'url': url, 'title': 'Article title',
                  'excerpt': excerpt, 'fetched_at': '2026-11-06T12:00:00.000Z'}
        saved = save_item(self.conn, owner, item_id,
            ItemPatch(expected_revision=1, context={'notes': '  Exact notes\r\n', 'sources': [source]},
                      artifact={'segments': ['  Exact draft\n']}), request_id=f'save-{owner.owner_id}-{url}')
        self.assertEqual(saved.body['item']['working_revision'], 2)
        version = freeze_version(self.conn, owner, item_id, 2, VersionPurpose.REVIEW)
        return item_id, version.version_id

    def test_real_sources_and_only_the_creator_profile_and_active_preferences(self):
        self.profile(self.a, 'Creator A')
        self.profile(self.b, 'Creator B')
        active = self.preference(self.a, 'Prefer concrete engineering examples.', 'preference-A')
        self.preference(self.b, 'Include only Creator B preference.', 'preference-B')
        item_id, version_id = self.version(self.a)
        pending = propose_preference(self.conn, self.a, 'A pending suggestion.',
                                     origin='item', origin_ref=version_id, request_id='proposal-A')
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        data = snapshot.as_dict()
        self.assertEqual(data['owner_id'], 'owner-A')
        self.assertEqual((data['item_id'], data['version_id'], data['revision']), (item_id, version_id, 2))
        self.assertEqual(data['title'], 'A working title')
        self.assertEqual(data['context']['notes'], '  Exact notes\r\n')
        self.assertIsNone(data['context']['experience'])
        self.assertIsNone(data['context']['interpretation'])
        self.assertEqual(data['context']['sources'][0]['excerpt'], 'Actual source excerpt')
        self.assertFalse(data['context']['sources'][0]['title_only'])
        self.assertEqual(data['artifact']['segments'], ['  Exact draft\n'])
        self.assertEqual(data['profile']['name'], 'Creator A')
        self.assertEqual([p['preference_id'] for p in data['preferences']], [active['preference_id']])
        self.assertNotEqual(pending['preference_id'], active['preference_id'])
        rendered = snapshot.to_json()
        self.assertNotIn('Creator B', rendered)
        self.assertNotIn('pending suggestion', rendered)
        self.assertEqual(json.loads(rendered), data)

    def test_title_only_source_does_not_invent_personal_experience(self):
        item_id, version_id = self.version(self.a, excerpt='')
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        data = snapshot.as_dict()
        self.assertIsNone(data['profile'])
        self.assertTrue(data['context']['sources'][0]['title_only'])
        self.assertEqual(data['context']['sources'][0]['excerpt'], '')
        self.assertIsNone(data['context']['experience'])
        self.assertIsNone(data['context']['interpretation'])
        self.assertEqual(data['preferences'], [])

    def test_requires_the_owned_item_and_its_owned_version(self):
        item_a, version_a = self.version(self.a)
        item_b, version_b = self.version(self.b)
        for principal, item, version in ((self.b, item_a, version_a), (self.a, item_a, version_b),
                                         (self.a, item_b, version_a)):
            with self.subTest(principal=principal.owner_id, item=item, version=version):
                with self.assertRaises(WorkflowError) as error:
                    build_editorial_snapshot(self.conn, principal, item, version)
                self.assertEqual(error.exception.status_code, 404)

    def test_mutations_and_later_settings_changes_cannot_change_existing_snapshot(self):
        self.profile(self.a, 'Original creator')
        original_rule = self.preference(self.a, 'Write short paragraphs.', 'first-rule')
        item_id, version_id = self.version(self.a)
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        original = snapshot.to_json()
        exported = snapshot.as_dict()
        exported['context']['sources'][0]['excerpt'] = 'Changed outside snapshot'
        exported['preferences'][0]['text'] = 'Changed outside snapshot'
        with self.assertRaises(FrozenInstanceError):
            snapshot.context.notes = 'Changed'
        with self.assertRaises(FrozenInstanceError):
            snapshot.profile.name = 'Changed'
        self.profile(self.a, 'Updated creator', revision=1)
        mutate_preference(self.conn, self.a, 'edit', original_rule['preference_id'],
                          {'text': 'Use concrete examples instead.', 'expected_revision': 1, 'consent': True},
                          'edit-rule')
        self.assertEqual(snapshot.to_json(), original)
        later = build_editorial_snapshot(self.conn, self.a, item_id, version_id).as_dict()
        self.assertEqual(later['profile']['name'], 'Updated creator')
        self.assertEqual(later['preferences'][0]['text'], 'Use concrete examples instead.')
        self.assertEqual(later['context']['notes'], snapshot.context.notes)

    def test_scoped_provider_never_loads_global_files_or_rules(self):
        self.profile(self.a, 'Creator A')
        self.preference(self.a, 'Use plain explanations.', 'plain')
        item_id, version_id = self.version(self.a, excerpt='')
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        before = dict(os.environ)
        with (patch('content_machine.knowledge.provider.get_style_guide', side_effect=AssertionError('global style')),
              patch('content_machine.knowledge.provider.get_voice_guide', side_effect=AssertionError('global voice')),
              patch('content_machine.knowledge.provider.get_governed_rules', side_effect=AssertionError('global rules'))):
            context = get_editorial_context(scoped_context=snapshot)
        self.assertTrue(dict(os.environ) == before)
        self.assertEqual(context['active_rules'], ['Use plain explanations.'])
        self.assertIn('Creator A', context['full_context_prompt'])
        self.assertIn('Article title', context['full_context_prompt'])
        self.assertIn('A working title', context['full_context_prompt'])
        self.assertIn('title_only', context['full_context_prompt'])
        self.assertNotIn('Prasad Rane', context['full_context_prompt'])

    def test_source_urls_with_credentials_are_rejected_without_echoing_them(self):
        for index, url in enumerate(('https://user:pass@example.org/article',
                                     'https://example.org/article?access_token=secret-test-value',
                                     'https://example.org/article#access_token=secret-test-value')):
            item_id, version_id = self.version(self.a, url=url)
            with self.subTest(index=index), self.assertRaises(WorkflowError) as error:
                build_editorial_snapshot(self.conn, self.a, item_id, version_id)
            self.assertEqual(error.exception.code, 'unsafe_source_url')
            self.assertNotIn('secret-test-value', str(error.exception))
            self.assertNotIn('user:pass', str(error.exception))

    def test_preserves_caller_transaction(self):
        self.profile(self.a, 'Committed creator')
        item_id, version_id = self.version(self.a)
        self.conn.execute('BEGIN')
        save_profile(self.conn, self.a,
            ProfileSave(name='Uncommitted creator', role='', bio='', expected_revision=1), request_id='uncommitted')
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        self.assertEqual(snapshot.profile.name, 'Uncommitted creator')
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        self.assertEqual(get_profile(self.conn, self.a)['name'], 'Committed creator')

    def test_stale_content_revision_cannot_be_paired_with_the_current_title(self):
        item_id, version_id = self.version(self.a)
        save_item(self.conn, self.a, item_id,
                  ItemPatch(expected_revision=2, title='New title', context={'notes': 'New idea'}),
                  request_id='new-idea')
        with self.assertRaises(WorkflowError) as error:
            build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        self.assertEqual(error.exception.code, 'revision_conflict')
        self.assertEqual(error.exception.current['working_revision'], 3)

    def test_a_title_change_does_not_change_an_already_captured_snapshot(self):
        item_id, version_id = self.version(self.a)
        snapshot = build_editorial_snapshot(self.conn, self.a, item_id, version_id)
        save_item(self.conn, self.a, item_id, ItemPatch(expected_revision=2, title='Retitled'),
                  request_id='retitle')
        self.assertEqual(snapshot.as_dict()['title'], 'A working title')
        self.assertEqual(build_editorial_snapshot(self.conn, self.a, item_id, version_id).as_dict()['title'], 'Retitled')


if __name__ == '__main__':
    unittest.main()
