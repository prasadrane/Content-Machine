"""A hosted cold start never creates a shared synthetic workspace."""
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class HostedEntryTest(unittest.TestCase):
    def test_entry_sets_hosted_boundary_without_seeding_or_ephemeral_storage(self):
        path = Path(__file__).resolve().parents[1] / 'api' / 'index.py'
        fake_app = Mock()
        with patch.dict('os.environ', {}, clear=True) as environment, \
             patch.dict(sys.modules, {'content_machine.api.app': SimpleNamespace(app=fake_app)}), \
             patch('content_machine.storage.db.connect') as connect, \
             patch('content_machine.storage.paths.ensure_tree') as ensure, \
             patch('content_machine.demo_seed.seed_demo') as seed:
            runpy.run_path(str(path))
            self.assertEqual(environment.get('CONTENT_MACHINE_DEPLOYMENT_MODE'), 'hosted')
            self.assertNotIn('DEMO_MODE', environment)
            self.assertNotIn('CONTENT_MACHINE_HOME', environment)
        connect.assert_not_called()
        ensure.assert_not_called()
        seed.assert_not_called()
