"""Hosted workflow identity cannot select the process-global legacy persona."""
import os
import tempfile
import unittest
from unittest.mock import patch

import test_workflow_api_items as fixtures
from content_machine.api.app import app
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.provider_execution import ProviderExecution


class CreatorSelectorsTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        # This owner-selection test injects trusted authentication. Supply the
        # newer signed-session verifier seam as well; signature validation has
        # separate ES256 tests and must not be disabled in hosted production.
        app.state.workflow_authenticator.verify_session = lambda token: (
            VerifiedGuestSession(self.fixture._current, False) if token == 'creator-fixture' else None)

    def mutate(self, method, path, body, key):
        return self.client.request(method, '/api/workflow/' + path, json=body,
                                   headers={'Idempotency-Key': key, 'Authorization': 'Bearer creator-fixture'})

    def test_creator_b_cannot_select_a_profile_sources_preferences_or_model_context(self):
        a_item = self.fixture._create_item(title='Creator A private')
        profile = self.mutate('PUT', 'settings/profile', {
            'name': 'Creator A private', 'role': 'Engineer', 'bio': 'A-private-bio',
            'expected_revision': 0}, 'profile')
        self.assertEqual(profile.status_code, 200, profile.text)
        source = self.mutate('POST', 'settings/sources', {
            'kind': 'rss', 'name': 'A-private-source', 'url': 'https://example.com/feed',
            'enabled': True}, 'source')
        self.assertEqual(source.status_code, 201, source.text)
        source_id = source.json()['source']['source_id']
        pref = self.mutate('POST', 'preferences', {'text': 'A-private-preference', 'consent': True}, 'preference')
        self.assertEqual(pref.status_code, 201, pref.text)
        pref_id = pref.json()['preference']['preference_id']
        self.fixture._as(self.fixture.b)
        b_item = self.fixture._create_item(title='Creator B own idea')
        snapshots = []

        def generator(snapshot):
            snapshots.append(snapshot)
            return {'segments': ['Creator B proposal']}

        with tempfile.TemporaryDirectory(prefix='c47-decoy-') as decoy, \
             patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted',
                                     'CONTENT_MACHINE_HOME': decoy,
                                     'CONTENT_MACHINE_LOCAL_OWNER_ID': self.fixture.a.owner_id}), \
             patch.object(app.state, 'workflow_generator', generator, create=True), \
             patch.object(ProviderExecution, 'for_request', classmethod(  # signed-in AI is metered; this test injects a fake provider
                 lambda cls, request, principal, op: cls(metered=False, subject_id=principal.owner_id, operation_id=op))), \
             patch('content_machine.api.app.ProfileManager') as legacy_profile, \
             patch('content_machine.storage.paths.home_root', side_effect=AssertionError('legacy path selection')):
            forged = {'X-Owner-ID': self.fixture.a.owner_id, 'Authorization': 'Bearer forged'}
            settings = self.client.get('/api/workflow/settings?owner_id=' + self.fixture.a.owner_id, headers=forged)
            self.assertEqual(settings.status_code, 200)
            self.assertEqual(settings.json()['profile']['name'], '')
            self.assertEqual(settings.json()['sources'], [])
            self.assertEqual(self.client.get('/api/workflow/preferences', headers=forged).json()['preferences'], [])
            self.assertEqual(self.client.get(f'/api/workflow/items/{a_item["item_id"]}', headers=forged).status_code, 404)
            self.assertEqual(self.client.get(f'/api/workflow/preferences/{pref_id}/history', headers=forged).status_code, 404)
            self.assertEqual(self.mutate('PATCH', f'settings/sources/{source_id}', {
                'expected_revision': 1, 'name': 'Stolen'}, 'steal-source').status_code, 404)
            self.assertEqual(self.mutate('POST', f'preferences/{pref_id}/stop', {
                'expected_revision': 1}, 'steal-preference').status_code, 404)
            generated = self.mutate('POST', f'items/{b_item["item_id"]}/generate', {'expected_revision': 1}, 'b-generate')
            self.assertEqual(generated.status_code, 200, generated.text)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0].owner_id, self.fixture.b.owner_id)
            self.assertIsNone(snapshots[0].profile)
            self.assertEqual(snapshots[0].preferences, ())
            self.assertNotIn('A-private', snapshots[0].to_json())
            legacy_profile.assert_not_called()
        self.fixture._as(self.fixture.a)
        self.assertEqual(self.client.get('/api/workflow/settings').json()['profile']['bio'], 'A-private-bio')
        self.assertEqual(self.client.get('/api/workflow/preferences').json()['preferences'][0]['status'], 'active')
