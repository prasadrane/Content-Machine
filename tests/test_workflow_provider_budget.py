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
                       units=60, daily_limit=100, max_inflight=2,
                       subject_daily_limit=100, subject_max_inflight=4)  # legacy tests: per-subject caps off
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

    def test_yesterdays_stuck_rows_do_not_block_today(self):
        self.reserve(units=10, max_inflight=1)
        budget.dispatch(self.conn, 'cloudflare-guest', 'one')
        budget.settle(self.conn, 'cloudflare-guest', 'one')  # uncertain, left stuck
        self.assertTrue(self.reserve('two', day='2026-11-09', subject_id='guest-b', units=10, max_inflight=1)[1])

    def test_same_day_crash_left_row_still_blocks_known_limitation(self):
        # No timestamp column, so no lease expiry: a stuck same-day row holds its slot.
        self.reserve(units=10, max_inflight=1)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('two', subject_id='guest-b', units=10, max_inflight=1)
        self.assertEqual(error.exception.code, 'guest_budget_busy')

    def test_subject_inflight_cap_blocks_same_subject_not_other_subject(self):
        dflt = dict(subject_daily_limit=None, subject_max_inflight=1)
        self.reserve(units=10, daily_limit=1000, max_inflight=3, **dflt)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('two', units=10, daily_limit=1000, max_inflight=3, **dflt)
        self.assertEqual(error.exception.code, 'guest_budget_subject_busy')
        self.assertTrue(self.reserve('three', subject_id='guest-b', units=10, daily_limit=1000, max_inflight=3, **dflt)[1])
        budget.release(self.conn, 'cloudflare-guest', 'one')
        self.assertTrue(self.reserve('four', units=10, daily_limit=1000, max_inflight=3, **dflt)[1])

    def test_subject_daily_cap_defaults_to_quarter_of_pool_and_spares_others(self):
        opts = dict(units=10, daily_limit=100, max_inflight=4, subject_daily_limit=None, subject_max_inflight=1)
        for key in ('one', 'two'):
            self.reserve(key, **opts)
            budget.dispatch(self.conn, 'cloudflare-guest', key)
            budget.settle(self.conn, 'cloudflare-guest', key, actual_units=10)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('three', **opts)  # 20 used + 10 > cap 25
        self.assertEqual((error.exception.code, error.exception.status_code), ('guest_budget_subject_exhausted', 429))
        self.assertTrue(self.reserve('four', subject_id='guest-b', **opts)[1])

    def test_daily_spend_still_counts_settled_and_uncertain_rows(self):
        opts = dict(units=40, daily_limit=100, max_inflight=4, subject_daily_limit=100, subject_max_inflight=4)
        self.reserve('one', **opts)
        budget.dispatch(self.conn, 'cloudflare-guest', 'one')
        budget.settle(self.conn, 'cloudflare-guest', 'one')  # uncertain, charged in full
        self.reserve('two', **opts)
        with self.assertRaises(WorkflowError) as error:
            self.reserve('three', **opts)
        self.assertEqual(error.exception.code, 'guest_budget_exhausted')

    def test_outer_transaction_rejected_and_invalid_bounds_do_not_change_state(self):
        self.conn.execute('BEGIN')
        with self.assertRaises(WorkflowError):
            self.reserve()
        self.conn.rollback()
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                self.reserve(units=value)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM workflow_provider_reservations').fetchone()[0], 0)
