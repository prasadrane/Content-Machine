"""Actual router attempts are guarded even across Council worker threads."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from content_machine.router.base import ModelRouter, Route, ProviderError, AllRoutesFailed
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.provider_budget import migrate_budget
from content_machine.workflow.provider_execution import ProviderExecution

MODEL = '@cf/qwen/qwen3.8-27b'
POLICY = {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '10000000',
          'CONTENT_MACHINE_GUEST_AI_PER_CALL_MILLINEURONS': '1000000',
          'CONTENT_MACHINE_GUEST_AI_MAX_INFLIGHT': '4',
          'CONTENT_MACHINE_GUEST_AI_MAX_INPUT_BYTES': '4096'}


class ProviderExecutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'budget.db'
        conn = self.factory()
        migrate_budget(conn)
        conn.close()
        self.env = patch.dict('os.environ', POLICY)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.seen = []

    def factory(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def execution(self, guest=True):
        return ProviderExecution(guest=guest, subject_id='guest-a', operation_id='op-one',
                                 connection_factory=self.factory)

    def router(self, execution, error=False, model=MODEL, protocol='cloudflare_workers_ai'):
        outer = self
        class Adapter:
            def complete(self, **kwargs):
                outer.seen.append(kwargs)
                if error:
                    raise ProviderError('fixture outage')
                return 'result'
        router = ModelRouter({'candidate': Route('candidate', protocol, Adapter())})
        return execution.wrap_router(router)

    def test_guest_call_commits_before_provider_and_records_actual_route_without_changing_result(self):
        execution = self.execution()
        router = self.router(execution)
        self.assertEqual(router.complete([MODEL], 'Fixture source', max_tokens=4096), 'result')
        self.assertEqual(self.seen[0]['max_tokens'], 2000)
        self.assertEqual(execution.calls[0]['model'], MODEL)
        self.assertEqual(execution.calls[0]['route'], 'candidate')
        self.assertEqual(execution.calls[0]['state'], 'completed')
        conn = self.factory()
        try:
            row = conn.execute('SELECT state,charged_units FROM workflow_provider_reservations').fetchone()
            self.assertEqual(tuple(row), ('settled', 1000000))
        finally:
            conn.close()

    def test_missing_policy_disallowed_provider_and_underfunded_bound_do_not_invoke(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': ''}):
            with self.assertRaises(WorkflowError):
                self.execution()
        for protocol, model in [('anthropic_messages', MODEL), ('cloudflare_workers_ai', '@cf/unreviewed')]:
            with self.subTest(protocol=protocol, model=model), self.assertRaises(AllRoutesFailed):
                self.router(self.execution(), protocol=protocol).complete([model], 'Fixture')
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_PER_CALL_MILLINEURONS': '10'}):
            with self.assertRaises(WorkflowError):
                self.execution()
        self.assertEqual(self.seen, [])

    def test_parallel_worker_calls_share_durable_budget_and_timeout_is_not_refunded(self):
        execution = self.execution()
        router = self.router(execution)
        with ThreadPoolExecutor(max_workers=4) as executor:
            self.assertEqual(list(executor.map(lambda _: router.complete([MODEL], 'Fixture'), range(4))), ['result'] * 4)
        self.assertEqual(len(execution.calls), 4)
        self.assertEqual(len({row['reservation_key'] for row in execution.calls}), 4)
        failure = self.execution()
        with self.assertRaises(AllRoutesFailed):
            self.router(failure, error=True).complete([MODEL], 'Fixture')
        conn = self.factory()
        try:
            self.assertEqual(conn.execute("SELECT charged_units FROM workflow_provider_reservations WHERE state='uncertain'").fetchone()[0], 1000000)
        finally:
            conn.close()

    def test_oversized_source_is_preserved_without_network_and_creator_metadata_has_no_budget(self):
        execution = self.execution()
        with self.assertRaises(AllRoutesFailed):
            self.router(execution).complete([MODEL], 'x' * 5000)
        self.assertEqual(self.seen, [])
        creator = self.execution(guest=False)
        self.assertEqual(self.router(creator, protocol='anthropic_messages').complete(['relay-model'], 'Fixture'), 'result')
        self.assertEqual(creator.calls[0]['model'], 'relay-model')
        self.assertNotIn('reservation_key', creator.calls[0])
