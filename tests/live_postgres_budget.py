"""Opt-in durable shared-provider quota acceptance against PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sys
import threading
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_postgres_workflow import LivePostgresWorkflowTest, _HOME
from content_machine.workflow import provider_budget as budget
from content_machine.workflow.errors import WorkflowError


class LivePostgresBudgetTest(LivePostgresWorkflowTest):
    def setUp(self):
        super().setUp()
        self.pool = 'live-budget-' + uuid.uuid4().hex

    def reserve(self, key='one', conn=None, **changes):
        options = dict(pool=self.pool, day='2026-11-08', request_id=key,
            subject_id=self.a.owner_id, provider='cloudflare_workers_ai',
            model='@cf/qwen/qwen3.8-27b', units=60, daily_limit=100, max_inflight=2)
        options.update(changes)
        return budget.reserve(conn or self.conn, **options)

    def test_budget_reservation_reopens_replays_and_conflicting_claims_rollback(self):
        reserved, created = self.reserve()
        self.assertTrue(created)
        self.assertFalse(self.conn.in_transaction)
        with closing(self.session()) as conn:
            replay, created = self.reserve(conn=conn)
            self.assertEqual(replay, reserved)
            self.assertFalse(created)
            for key, changes, code in (('two', {'subject_id': self.b.owner_id}, 'guest_budget_exhausted'),
                    ('one', {'model': '@cf/other'}, 'guest_budget_conflict'),
                    ('two', {'daily_limit': 200}, 'guest_budget_policy_conflict')):
                with self.assertRaises(WorkflowError) as error:
                    self.reserve(key, conn=conn, **changes)
                self.assertEqual(error.exception.code, code)
                self.assertFalse(conn.in_transaction)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_provider_reservations WHERE pool=?',
            (self.pool,)).fetchone()[0], 1)

    def test_budget_parallel_subjects_cannot_overrun_shared_daily_cap(self):
        barrier = threading.Barrier(5)
        def claim(number):
            with closing(self.session()) as conn:
                barrier.wait(timeout=10)
                try:
                    self.reserve(str(number), conn=conn, subject_id=str(uuid.uuid4()), max_inflight=5)
                    return 'reserved'
                except WorkflowError as error:
                    return error.code
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(claim, range(5)))
        self.assertEqual(results.count('reserved'), 1)
        self.assertEqual(results.count('guest_budget_exhausted'), 4)
        self.assertEqual(self.conn.execute('SELECT SUM(charged_units) FROM workflow_provider_reservations WHERE pool=?',
            (self.pool,)).fetchone()[0], 60)

    def test_budget_dispatch_once_uncertain_retains_slot_across_subjects_and_days(self):
        self.reserve(units=10, max_inflight=1)
        self.assertTrue(budget.dispatch(self.conn, self.pool, 'one'))
        with closing(self.session()) as conn:
            self.assertFalse(budget.dispatch(conn, self.pool, 'one'))
            uncertain = budget.settle(conn, self.pool, 'one')
            self.assertEqual((uncertain['state'], uncertain['charged_units']), ('uncertain', 10))
            with self.assertRaises(WorkflowError):
                budget.release(conn, self.pool, 'one')
            with self.assertRaises(WorkflowError) as full:
                self.reserve('next-day', conn=conn, day='2026-11-09', subject_id=self.b.owner_id,
                    units=10, max_inflight=1)
            self.assertEqual(full.exception.code, 'guest_budget_busy')
            budget.settle(conn, self.pool, 'one', actual_units=5)
            self.assertTrue(self.reserve('next-day', conn=conn, day='2026-11-09',
                subject_id=self.b.owner_id, units=10, max_inflight=1)[1])

    def test_budget_release_and_measured_terminal_usage_are_durable(self):
        self.reserve()
        released = budget.release(self.conn, self.pool, 'one')
        self.assertEqual((released['state'], released['charged_units']), ('released', 0))
        self.assertFalse(budget.dispatch(self.conn, self.pool, 'one'))
        self.reserve('two')
        budget.dispatch(self.conn, self.pool, 'two')
        result = budget.settle(self.conn, self.pool, 'two', actual_units=20)
        with closing(self.session()) as conn:
            self.assertEqual(result, budget.settle(conn, self.pool, 'two', actual_units=20))
            with self.assertRaises(WorkflowError):
                budget.settle(conn, self.pool, 'two', actual_units=0)
            self.assertTrue(self.reserve('three', conn=conn)[1])

    def test_budget_browser_roles_cannot_inspect_shared_quota(self):
        self.reserve()
        for role in ('anon', 'authenticated'):
            with self.connect_raw() as raw:
                raw.execute('BEGIN')
                raw.execute('SET LOCAL ROLE ' + role)
                with self.assertRaises(self.driver.errors.InsufficientPrivilege):
                    raw.execute('SELECT * FROM ' + self.schema + '.workflow_provider_reservations')
                raw.rollback()


if __name__ == '__main__':
    names = [name for name in LivePostgresBudgetTest.__dict__ if name.startswith('test_budget_')]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        LivePostgresBudgetTest(name) for name in sorted(names)))
    _HOME.cleanup()
    sys.exit(not result.wasSuccessful())
