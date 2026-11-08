"""Durable shared quota reservations; no provider or real workspace access."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow import provider_budget as budget


class ProviderBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'budget.db'
        self.conn = self.connect()
        self.addCleanup(self.conn.close)
        budget.migrate_budget(self.conn)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def reserve(self, key='one', conn=None, **kwargs):
        options = dict(pool='cloudflare-guest', day='2026-11-08', request_id=key,
                       subject_id='guest-a', provider='cloudflare_workers_ai', model='@cf/fixture',
                       units=60, daily_limit=100, max_inflight=2)
        options.update(kwargs)
        return budget.reserve(conn or self.conn, **options)

    def test_reservation_is_committed_reopened_and_duplicate_does_not_dispatch(self):
        row, created = self.reserve()
        self.assertTrue(created)
        self.assertFalse(self.conn.in_transaction)
        with closing(self.connect()) as other:
            replay, created = self.reserve(conn=other)
        self.assertFalse(created)
        self.assertEqual(row, replay)
        self.assertEqual(row['provider'], 'cloudflare_workers_ai')
        self.assertEqual(row['model'], '@cf/fixture')

    def test_quota_exhaustion_and_changed_request_fail_without_extra_reservation(self):
        self.reserve()
        for key, options, code in [('two', {}, 'guest_budget_exhausted'),
                                   ('one', {'model': '@cf/other'}, 'guest_budget_conflict'),
                                   ('two', {'daily_limit': 200}, 'guest_budget_policy_conflict')]:
            with self.subTest(code=code), self.assertRaises(WorkflowError) as error:
                self.reserve(key, **options)
            self.assertEqual(error.exception.code, code)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM workflow_provider_reservations').fetchone()[0], 1)

    def test_only_undispatched_work_can_release_and_unknown_usage_charges_full(self):
        self.reserve()
        budget.release(self.conn, 'cloudflare-guest', 'one')
        self.assertFalse(self.reserve()[1])
        self.reserve('two')
        budget.dispatch(self.conn, 'cloudflare-guest', 'two')
        with self.assertRaises(WorkflowError):
            budget.release(self.conn, 'cloudflare-guest', 'two')
        result = budget.settle(self.conn, 'cloudflare-guest', 'two')
        self.assertEqual(result['charged_units'], 60)
        self.assertEqual(result['state'], 'uncertain')
        with self.assertRaises(WorkflowError):
            self.reserve('three')

    def test_measured_settlement_refunds_unused_bound_and_is_immutable(self):
        self.reserve()
        budget.dispatch(self.conn, 'cloudflare-guest', 'one')
        result = budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=20)
        self.assertEqual(result['charged_units'], 20)
        self.assertEqual(result, budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=20))
        with self.assertRaises(WorkflowError):
            budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=0)
        self.assertTrue(self.reserve('two')[1])

    def test_dispatch_permission_is_once_and_uncertain_native_call_retains_slot(self):
        self.reserve(units=10, max_inflight=1)
        self.assertTrue(budget.dispatch(self.conn, 'cloudflare-guest', 'one'))
        self.assertFalse(budget.dispatch(self.conn, 'cloudflare-guest', 'one'))
        budget.settle(self.conn, 'cloudflare-guest', 'one')
        with self.assertRaises(WorkflowError) as error:
            self.reserve('two', units=10, max_inflight=1)
        self.assertEqual(error.exception.code, 'guest_budget_busy')
        budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=5)
        self.assertTrue(self.reserve('two', units=10, max_inflight=1)[1])

    def test_unexpected_actual_overrun_is_recorded_in_full_and_blocks_further_quota(self):
        self.reserve()
        budget.dispatch(self.conn, 'cloudflare-guest', 'one')
        result = budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=120)
        self.assertEqual(result['charged_units'], 120)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('two')
        self.assertEqual(error.exception.code, 'guest_budget_exhausted')

    def test_parallel_connections_cannot_overrun_shared_quota(self):
        def claim(index):
            conn = self.connect()
            try:
                self.reserve(str(index), conn=conn)
                return True
            except WorkflowError:
                return False
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=5) as executor:
            self.assertEqual(sum(executor.map(claim, range(5))), 1)

    def test_global_inflight_limit_does_not_reset_at_midnight_or_between_owners(self):
        self.reserve(units=10, max_inflight=1)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('two', day='2026-11-09', subject_id='guest-b', units=10, max_inflight=1)
        self.assertEqual(error.exception.code, 'guest_budget_busy')
        budget.dispatch(self.conn, 'cloudflare-guest', 'one')
        budget.settle(self.conn, 'cloudflare-guest', 'one', actual_units=10)
        self.assertTrue(self.reserve('two', day='2026-11-09', units=10, max_inflight=1)[1])

    def test_outer_transaction_rejected_and_invalid_bounds_do_not_change_state(self):
        self.conn.execute('BEGIN')
        with self.assertRaises(WorkflowError):
            self.reserve()
        self.conn.rollback()
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                self.reserve(units=value)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM workflow_provider_reservations').fetchone()[0], 0)
