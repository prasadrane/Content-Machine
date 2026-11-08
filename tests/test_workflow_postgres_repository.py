"""Scripted psycopg interface checks; these do not simulate PostgreSQL."""
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.postgres_repository import PostgresWorkflowRepository
from content_machine.workflow.persistence import request_digest
from content_machine.workflow.schemas import ItemCreate, ItemPatch, Principal
from content_machine.workflow.versions import artifact_digest

OWNER = '8250c7e1-90a9-4a41-9b86-410177cc9fd1'


def row(**overrides):
    return {'item_id': 'item-1', 'owner_id': OWNER, 'title': 'Idea', 'destination': 'linkedin',
            'format': 'linkedin_post', 'stage': 'draft_review', 'working_revision': 2,
            'context_json': {'notes': '  exact\r\n', 'experience': None, 'interpretation': None,
                             'sources': [], 'preference_snapshot_id': None},
            'artifact_json': {'segments': ['  café\r\nsecond  \n']}, 'parent_version_id': None,
            'active_approval_id': 'approval-1',
            'created_at': datetime(2026, 11, 5, 1, 0, tzinfo=timezone.utc),
            'updated_at': datetime(2026, 11, 5, 1, 0, tzinfo=timezone.utc), **overrides}


class ScriptedConnection:
    def __init__(self, script=(), fail_commit=False):
        self.script = list(script)
        self.events = []
        self.info = SimpleNamespace(transaction_status=0)
        self.fail_commit = fail_commit

    @contextmanager
    def transaction(self):
        self.events.append(('begin',))
        try:
            yield
            if self.fail_commit:
                raise RuntimeError('commit failed')
            self.events.append(('commit',))
        except BaseException:
            self.events.append(('rollback',))
            raise

    def execute(self, sql, params=()):
        self.events.append(('sql', sql, params))
        expected, result = self.script.pop(0)
        if expected not in sql:
            raise AssertionError(f'Expected {expected!r} in {sql!r}')
        return result


def cursor(one=None, many=None, rowcount=1):
    return SimpleNamespace(fetchone=Mock(return_value=one), fetchall=Mock(return_value=many), rowcount=rowcount)


class PostgresRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.principal = Principal(owner_id=OWNER, mode='hosted_verified')
        self.payload = ItemCreate(title='Idea', destination='linkedin', format='linkedin_post')

    def test_create_commits_before_ack_and_locks_idempotency_scope(self):
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor()),
                                   ('INSERT INTO public.workflow_items', cursor()), ('INSERT INTO public.workflow_idempotency', cursor())])
        result = PostgresWorkflowRepository(conn).create_item(self.principal, self.payload, request_id='same-key')
        self.assertEqual(conn.events[-1], ('commit',))
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.body['item']['owner_id'], OWNER)
        self.assertEqual(result.body['item']['artifact']['segments'], [])
        self.assertEqual(conn.events[1][2], (OWNER, 'same-key'))
        self.assertEqual(conn.script, [])

    def test_failed_commit_cannot_return_success(self):
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor()),
                                   ('INSERT INTO public.workflow_items', cursor()), ('INSERT INTO public.workflow_idempotency', cursor())], fail_commit=True)
        with self.assertRaisesRegex(RuntimeError, 'commit failed'):
            PostgresWorkflowRepository(conn).create_item(self.principal, self.payload, request_id='key')
        self.assertEqual(conn.events[-1], ('rollback',))

    def test_changed_key_conflicts_and_blank_key_never_starts_transaction(self):
        stored = {'method': 'POST', 'resource_path': '/api/workflow/items', 'request_digest': 'other',
                  'response_status': 201, 'response_body_json': {'item': {'item_id': 'original'}}}
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor(one=stored))])
        with self.assertRaises(WorkflowError) as conflict:
            PostgresWorkflowRepository(conn).create_item(self.principal, self.payload, request_id='key')
        self.assertEqual(conflict.exception.code, 'idempotency_conflict')
        self.assertEqual(conn.events[-1], ('rollback',))
        empty = ScriptedConnection()
        with self.assertRaises(WorkflowError):
            PostgresWorkflowRepository(empty).create_item(self.principal, self.payload, request_id=' ')
        self.assertEqual(empty.events, [])

    def test_identical_retry_replays_without_inserting_and_commits_before_returning(self):
        body = {'item': {'item_id': 'first', 'artifact': {'segments': ['exact']}}}
        stored = {'method': 'POST', 'resource_path': '/api/workflow/items',
                  'request_digest': request_digest('POST', '/api/workflow/items', self.payload.model_dump(mode='json')),
                  'response_status': 201, 'response_body_json': body}
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()),
                                   ('FROM public.workflow_idempotency', cursor(one=stored))])
        result = PostgresWorkflowRepository(conn).create_item(self.principal, self.payload, request_id='same')
        self.assertEqual(result.body, body)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(conn.events[-1], ('commit',))
        self.assertEqual(conn.script, [])

    def test_wrong_owner_and_wrong_item_versions_do_not_resolve(self):
        conn = ScriptedConnection([('FROM public.workflow_items', cursor())])
        with self.assertRaises(WorkflowError) as missing:
            PostgresWorkflowRepository(conn).get_item(self.principal, 'foreign')
        self.assertEqual((missing.exception.status_code, missing.exception.code), (404, 'item_not_found'))
        conn = ScriptedConnection([('FROM public.workflow_items', cursor(one=row())),
                                   ('FROM public.workflow_versions', cursor())])
        with self.assertRaises(WorkflowError) as wrong:
            PostgresWorkflowRepository(conn).get_version(self.principal, 'item-1', 'other-item-version')
        self.assertEqual((wrong.exception.status_code, wrong.exception.code), (404, 'version_not_found'))
        query = conn.events[2]
        self.assertEqual(query[2], ('other-item-version', 'item-1', OWNER))

    def test_reads_bind_owner_and_preserve_content_and_timestamps(self):
        conn = ScriptedConnection([('FROM public.workflow_items', cursor(one=row()))])
        result = PostgresWorkflowRepository(conn).get_item(self.principal, 'item-1')
        sql = conn.events[1]
        self.assertIn('owner_id = %s', sql[1])
        self.assertEqual(sql[2], ('item-1', OWNER))
        self.assertEqual(result.artifact.segments, ['  café\r\nsecond  \n'])
        self.assertEqual(result.updated_at, '2026-11-05T01:00:00.000Z')
        self.assertEqual(conn.events[-1], ('commit',))

    def test_save_uses_row_lock_cas_and_invalidates_approval(self):
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor()),
                                   ('FOR UPDATE', cursor(one=row())), ('UPDATE public.workflow_items', cursor()),
                                   ('INSERT INTO public.workflow_idempotency', cursor())])
        result = PostgresWorkflowRepository(conn).save_item(self.principal, 'item-1',
            ItemPatch(expected_revision=2, artifact={'segments': ['new exact  \n']}), request_id='save')
        self.assertEqual(result.body['item']['working_revision'], 3)
        self.assertIsNone(result.body['item']['active_approval_id'])
        self.assertEqual(result.body['item']['artifact']['segments'], ['new exact  \n'])
        self.assertEqual(conn.events[-1], ('commit',))
        update = next(event for event in conn.events if event[0] == 'sql' and 'UPDATE public.workflow_items' in event[1])
        self.assertIn('owner_id = %s', update[1])
        self.assertIn('working_revision = %s', update[1])

    def test_stale_save_and_unapproved_export_do_not_write(self):
        stale = ScriptedConnection([('pg_advisory_xact_lock', cursor()),
                                    ('FROM public.workflow_idempotency', cursor()), ('FOR UPDATE', cursor(one=row()))])
        with self.assertRaises(WorkflowError) as failure:
            PostgresWorkflowRepository(stale).save_item(self.principal, 'item-1', ItemPatch(expected_revision=1), request_id='save')
        self.assertEqual(failure.exception.code, 'revision_conflict')
        self.assertEqual(failure.exception.current['working_revision'], 2)
        unapproved = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor()),
                                         ('FOR UPDATE', cursor(one=row(active_approval_id=None)))])
        with self.assertRaises(WorkflowError) as failure:
            PostgresWorkflowRepository(unapproved).save_item(self.principal, 'item-1',
                ItemPatch(expected_revision=2, stage='export'), request_id='export')
        self.assertEqual(failure.exception.code, 'approval_required')
        self.assertEqual(unapproved.events[-1], ('rollback',))

    def test_no_content_change_preserves_revision_and_existing_approval(self):
        conn = ScriptedConnection([('pg_advisory_xact_lock', cursor()), ('FROM public.workflow_idempotency', cursor()),
                                   ('FOR UPDATE', cursor(one=row())), ('UPDATE public.workflow_items', cursor()),
                                   ('INSERT INTO public.workflow_idempotency', cursor())])
        result = PostgresWorkflowRepository(conn).save_item(self.principal, 'item-1',
            ItemPatch(expected_revision=2, title='Renamed'), request_id='rename')
        self.assertEqual(result.body['item']['working_revision'], 2)
        self.assertEqual(result.body['item']['active_approval_id'], 'approval-1')

    def test_snapshot_reuses_prior_version_and_stale_snapshot_is_denied(self):
        stale = ScriptedConnection([('FOR UPDATE', cursor(one=row()))])
        with self.assertRaises(WorkflowError) as failure:
            PostgresWorkflowRepository(stale).freeze_version(self.principal, 'item-1', 1, 'review')
        self.assertEqual(failure.exception.code, 'revision_conflict')
        self.assertEqual(stale.events[-1], ('rollback',))
        previous = {'version_id': 'v1', 'item_id': 'item-1', 'owner_id': OWNER, 'revision': 2,
                    'context_json': row()['context_json'], 'artifact_json': row()['artifact_json'],
                    'destination': 'linkedin', 'format': 'linkedin_post', 'artifact_digest': 'sha256:' + 'a' * 64,
                    'purpose': 'approval', 'created_by': OWNER, 'created_at': row()['created_at']}
        conn = ScriptedConnection([('FOR UPDATE', cursor(one=row())), ('FROM public.workflow_versions', cursor(one=previous))])
        result = PostgresWorkflowRepository(conn).freeze_version(self.principal, 'item-1', 2, 'review')
        self.assertEqual(result.version_id, 'v1')
        self.assertEqual(result.purpose.value, 'approval')
        self.assertEqual(conn.script, [])

    def test_freeze_locks_current_item_and_preserves_digest(self):
        conn = ScriptedConnection([('FOR UPDATE', cursor(one=row())), ('FROM public.workflow_versions', cursor()),
                                   ('INSERT INTO public.workflow_versions', cursor())])
        version = PostgresWorkflowRepository(conn).freeze_version(self.principal, 'item-1', 2, 'review')
        self.assertEqual(version.artifact.segments, ['  café\r\nsecond  \n'])
        self.assertEqual(version.artifact_digest, artifact_digest(version.destination, version.format, version.artifact))
        self.assertEqual(conn.events[-1], ('commit',))

    def test_requires_verified_hosted_principal_and_an_idle_connection(self):
        conn = ScriptedConnection()
        with self.assertRaises(WorkflowError):
            PostgresWorkflowRepository(conn).get_item(Principal(owner_id=OWNER, mode='trusted_local'), 'item')
        conn.info.transaction_status = 2
        with self.assertRaises(WorkflowError):
            PostgresWorkflowRepository(conn).get_item(self.principal, 'item')
        self.assertEqual(conn.events, [])
