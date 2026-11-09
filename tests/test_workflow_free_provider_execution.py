"""Per-provider pools, fallthrough, settlement and deadline behaviour (offline)."""
from pathlib import Path
import os
import sqlite3
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

from content_machine.router.base import AllRoutesFailed, ModelRouter, ProviderRejected, Route
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.provider_budget import migrate_budget
from content_machine.workflow.provider_execution import ProviderExecution
from content_machine.workflow.schemas import Principal
from test_workflow_provider_execution import POLICY

ALIAS = 'free-strong'
OWNER = '11111111-1111-1111-1111-111111111111'


class FreeProviderExecutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'budget.db'
        conn = self.factory()
        migrate_budget(conn)
        conn.close()
        env = patch.dict('os.environ', POLICY)
        env.start()
        self.addCleanup(env.stop)
        self.seen = []

    def factory(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def execution(self, subject='guest-a'):
        return ProviderExecution(metered=True, subject_id=subject, operation_id='op-one',
                                 connection_factory=self.factory)

    def router(self, execution, cloudflare=None, gemini=None):
        """cloudflare/gemini: None = succeeds, an exception = raised, False = route absent."""
        outer = self

        def adapter(label, behaviour):
            class Adapter:
                def complete(self, **kwargs):
                    outer.seen.append((label, kwargs))
                    if isinstance(behaviour, BaseException):
                        raise behaviour
                    return label
            return Adapter()
        routes = {}
        if cloudflare is not False:
            routes['cf'] = Route('cf', 'cloudflare_workers_ai', adapter('cf', cloudflare))
        if gemini is not False:
            routes['gem'] = Route('gem', 'gemini', adapter('gem', gemini))
        router = ModelRouter(routes, {'*': list(routes)}, fallthrough_model_errors=True)
        return execution.wrap_router(router)

    def rows(self):
        conn = self.factory()
        try:
            return sorted(tuple(r) for r in conn.execute(
                'SELECT pool,state,charged_units FROM workflow_provider_reservations'))
        finally:
            conn.close()

    def request(self, is_anonymous, session_ok=True):
        principal = Principal(owner_id=OWNER, mode='hosted_verified')
        session = VerifiedGuestSession(principal, is_anonymous=is_anonymous) if session_ok else None
        auth = SimpleNamespace(verify_session=lambda token: session)
        state = SimpleNamespace(workflow_authenticator=auth, workflow_connection_factory=self.factory)
        return SimpleNamespace(app=SimpleNamespace(state=state),
                               headers={'Authorization': 'Bearer proof'}), principal

    def test_signed_in_and_anonymous_hosted_principals_are_both_metered(self):
        for anonymous in (False, True):
            with self.subTest(anonymous=anonymous):
                request, principal = self.request(anonymous)
                self.assertTrue(ProviderExecution.for_request(request, principal, 'op').metered)

    def test_signed_in_principal_is_capped_by_the_pool(self):
        request, principal = self.request(False)
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_GEMINI_DAILY_REQUESTS': '2'}):
            execution = ProviderExecution.for_request(request, principal, 'op-signed')
            router = self.router(execution, cloudflare=False)
            self.assertEqual(router.complete([ALIAS], 'Fixture'), 'gem')
            self.assertEqual(router.complete([ALIAS], 'Fixture'), 'gem')
            with self.assertRaises(AllRoutesFailed):
                router.complete([ALIAS], 'Fixture')
        self.assertEqual(self.rows(), [('gemini-guest', 'settled', 1)] * 2)

    def test_unverifiable_hosted_session_fails_closed(self):
        request, principal = self.request(False, session_ok=False)
        with self.assertRaises(WorkflowError) as caught:
            ProviderExecution.for_request(request, principal, 'op-bad')
        self.assertEqual(caught.exception.code, 'ai_session_unavailable')

    def test_gemini_uses_its_own_pool_units_and_bounded_timeout(self):
        execution = self.execution()
        self.assertEqual(self.router(execution, cloudflare=False).complete([ALIAS], 'Fixture'), 'gem')
        self.assertEqual(self.rows(), [('gemini-guest', 'settled', 1)])
        call = execution.calls[0]
        self.assertEqual((call['provider'], call['charged_units']), ('gemini', 1))
        self.assertNotIn('charged_millineurons', call)
        self.assertTrue(0 < self.seen[0][1]['timeout_s'] <= 25.0)
        self.assertRegex(call['reservation_key'], r'^.+:\d{9,11}:[0-9a-f]{32}$')

    def test_cloudflare_exhaustion_falls_through_to_gemini_without_poisoning_failure(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '1000000'}):
            self.assertEqual(self.router(self.execution()).complete([ALIAS], 'Fixture'), 'cf')
            second = self.execution()
            self.assertEqual(self.router(second).complete([ALIAS], 'Fixture'), 'gem')
        self.assertIsNone(second.failure)
        self.assertFalse(second.calls[0]['dispatched'])
        self.assertEqual(second.calls[0]['code'], 'guest_budget_exhausted')
        self.assertTrue(second.calls[1]['dispatched'])
        # Independent pools on the same day: no policy conflict, separate rows.
        self.assertEqual(self.rows(), [('cloudflare-guest', 'settled', 1000000), ('gemini-guest', 'settled', 1)])

    def test_all_providers_exhausted_surfaces_the_429_budget_error(self):
        from content_machine.workflow import runtime
        env = {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '1000000',
               'CONTENT_MACHINE_GUEST_AI_GEMINI_DAILY_REQUESTS': '1'}
        with patch.dict('os.environ', env):
            for _ in range(2):  # Cloudflare then Gemini each spend their daily pool once
                self.router(self.execution()).complete([ALIAS], 'Fixture')
            execution = self.execution()
            router = self.router(execution)

            def fake(snapshot, execution=None):
                return router.complete([ALIAS], 'Fixture')
            with patch.object(runtime, 'generate', fake), self.assertRaises(WorkflowError) as caught:
                execution.invoke(fake, object())
        self.assertEqual((caught.exception.status_code, caught.exception.code), (429, 'guest_budget_exhausted'))
        self.assertIsNone(execution.failure)
        self.assertEqual(len(self.seen), 2)

    def test_provider_rejection_frees_slot_and_charges_zero_while_timeout_stays_uncertain(self):
        rejected = self.execution()
        with self.assertRaises(AllRoutesFailed):
            self.router(rejected, cloudflare=ProviderRejected('http 429'), gemini=False).complete([ALIAS], 'Fixture')
        self.assertEqual(self.rows(), [('cloudflare-guest', 'settled', 0)])
        self.assertEqual((rejected.calls[0]['charged_units'], rejected.calls[0]['usage_basis']), (0, 'provider_rejected'))
        timed_out = self.execution()
        with self.assertRaises(AllRoutesFailed):
            self.router(timed_out, cloudflare=TimeoutError('slow'), gemini=False).complete([ALIAS], 'Fixture')
        self.assertEqual(self.rows(), [('cloudflare-guest', 'settled', 0), ('cloudflare-guest', 'uncertain', 1000000)])
        self.assertEqual(timed_out.calls[0]['usage_basis'], 'uncertain_reservation')

    def test_each_attempt_logs_one_fixed_field_line_without_secret_or_provider_text(self):
        import io
        from contextlib import redirect_stderr
        secret = 'sk-LEAKED-key-and-response-body'
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            self.router(self.execution(), cloudflare=ProviderRejected(secret)).complete([ALIAS], 'Fixture')
            with self.assertRaises(AllRoutesFailed):
                self.router(self.execution('guest-b'), cloudflare=TimeoutError(secret), gemini=TimeoutError(secret)).complete([ALIAS], 'Fixture')
        lines = [line for line in buffer.getvalue().splitlines() if line.startswith('ai_attempt ')]
        # rejected + ok, then an unexpected error that ends the model layer.
        self.assertEqual(len(lines), 3)
        self.assertIn('provider=cloudflare_workers_ai', lines[0])
        self.assertIn('outcome=rejected', lines[0])
        self.assertIn('provider=gemini', lines[1])
        self.assertIn('outcome=ok', lines[1])
        self.assertIn('outcome=error:TimeoutError', lines[2])
        self.assertTrue(all(' ms=' in line for line in lines))
        self.assertNotIn(secret, buffer.getvalue())

    def test_missing_policy_variables_use_defaults_and_invalid_values_fail_closed(self):
        with patch.dict('os.environ', {}):
            for name in list(os.environ):
                if name.startswith('CONTENT_MACHINE_GUEST_AI_'):
                    del os.environ[name]
            execution = self.execution()
            self.assertEqual((execution.max_input, execution.per_call, execution.daily, execution.concurrent),
                             (12000, 1200000, 9000000, 4))
            self.assertEqual((execution.gemini_daily, execution.gemini_inflight), (100, 4))
        for name, value in [('GEMINI_DAILY_REQUESTS', '0'), ('GEMINI_DAILY_REQUESTS', 'many'),
                            ('GEMINI_MAX_INFLIGHT', '99'), ('GEMINI_MAX_INFLIGHT', ''),
                            ('MAX_INFLIGHT', 'x'), ('MAX_INPUT_BYTES', '0'), ('DAILY_MILLINEURONS', '')]:
            with self.subTest(name=name, value=value), \
                 patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_' + name: value}):
                with self.assertRaises(WorkflowError) as caught:
                    self.execution()
                self.assertEqual(caught.exception.code, 'guest_budget_unconfigured')

    def test_exhausted_deadline_stops_dispatch_before_reserving(self):
        execution = self.execution()
        execution.deadline = time.monotonic() + 4.0
        with self.assertRaises(AllRoutesFailed):
            self.router(execution).complete([ALIAS], 'Fixture')
        self.assertEqual(self.seen, [])
        self.assertEqual(self.rows(), [])
        self.assertIsNone(execution.failure)

    def test_remaining_time_caps_adapter_timeout(self):
        execution = self.execution()
        execution.deadline = time.monotonic() + 12.0
        self.router(execution).complete([ALIAS], 'Fixture')
        self.assertLessEqual(self.seen[0][1]['timeout_s'], 9.0)

    def test_review_falls_back_to_local_cleanup_when_deadline_is_spent(self):
        from content_machine.workflow import runtime
        execution = self.execution()
        execution.deadline = time.monotonic() + 1.0
        router = self.router(execution)
        cfg = SimpleNamespace(models=SimpleNamespace(writer=ALIAS))
        with patch.object(runtime, 'build_free_router', return_value=(router, cfg)), \
             patch.object(execution, 'wrap_router', lambda r: r), \
             patch.object(runtime, 'ai_mode', return_value='auto'), \
             patch.object(runtime, 'review_snapshot', return_value={'actions': {'notes': []}}), \
             patch.object(runtime, 'suggest_wording', lambda snap, r, models: r.complete(models, 'p')), \
             patch.object(runtime, 'cleanup_wording', return_value=[{'segment': 0}]), \
             patch.object(runtime, 'validate_review_advice', lambda advice, snap: advice):
            advice = runtime.review(object(), execution=execution)
        self.assertEqual(advice['proposals'], [{'segment': 0}])
        self.assertTrue(advice['actions']['notes'])
        self.assertEqual(self.seen, [])

    def test_changed_daily_limit_mid_day_is_a_policy_conflict_not_a_fallthrough(self):
        self.router(self.execution(), gemini=False).complete([ALIAS], 'Fixture')
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '9000000'}):
            execution = self.execution()
            with self.assertRaises(AllRoutesFailed):
                self.router(execution, gemini=False).complete([ALIAS], 'Fixture')
        self.assertEqual(execution.failure.code, 'guest_budget_policy_conflict')
