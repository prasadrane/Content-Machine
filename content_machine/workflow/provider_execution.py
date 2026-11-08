"""Request-scoped actual-attempt metadata and durable free-only guest guards."""
from datetime import datetime, timezone
import json
import math
import os
import threading
import uuid

from content_machine.router.base import Route
from content_machine.workflow import provider_budget as budget
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.access import _hosted_deployment

GUEST_MODEL = '@cf/qwen/qwen3.8-27b'
_PREFIX = 'CONTENT_MACHINE_GUEST_AI_'


class ProviderExecution:
    def __init__(self, *, guest, subject_id, operation_id, connection_factory=None):
        self.guest, self.subject_id, self.operation_id = guest, subject_id, operation_id
        self.factory = connection_factory
        self.calls, self._lock, self.failure = [], threading.Lock(), None
        if guest:
            try:
                self.daily, self.per_call, self.concurrent, self.max_input = (
                    int(os.environ[_PREFIX + name]) for name in
                    ('DAILY_MILLINEURONS', 'PER_CALL_MILLINEURONS', 'MAX_INFLIGHT', 'MAX_INPUT_BYTES'))
                # UTF-8 bytes bound tokenizer input, plus 512 framing tokens per
                # message (at most system+user). Output includes reasoning. Rates
                # $0.45/$3.20 per million, neuron unit $0.011/1000 (reviewed).
                minimum = math.ceil(((self.max_input + 1024) * 450 + 2000 * 3200) / 11)
                valid = (callable(self.factory) and 0 < self.daily <= 10_000_000
                         and minimum <= self.per_call <= self.daily
                         and 0 < self.concurrent <= 4 and 0 < self.max_input <= 1_000_000)
            except (KeyError, ValueError, TypeError):
                valid = False
            if not valid:
                raise WorkflowError(503, 'guest_budget_unconfigured',
                                    'Guest AI quota is not configured. Your draft is preserved; continue manually.')

    @classmethod
    def for_request(cls, request, principal, operation_id):
        guest = False
        verifier = getattr(getattr(request.app.state, 'workflow_authenticator', None), 'verify_session', None)
        # Local server-injected principal-only authenticators are the existing
        # offline seam. Hosted deployment always requires signed session proof.
        if principal.mode.value == 'hosted_verified' and (callable(verifier) or _hosted_deployment()):
            parts = request.headers.get('Authorization', '').split()
            try:
                session = verifier(parts[1]) if callable(verifier) and len(parts) == 2 and parts[0].lower() == 'bearer' else None
            except Exception:
                session = None
            if (not isinstance(session, VerifiedGuestSession) or session.principal != principal
                    or type(session.is_anonymous) is not bool):
                raise WorkflowError(503, 'ai_session_unavailable', 'AI session verification is unavailable. Your draft is preserved.')
            guest = session.is_anonymous
        factory = getattr(request.app.state, 'workflow_connection_factory', None)
        return cls(guest=guest, subject_id=principal.owner_id, operation_id=operation_id,
                   connection_factory=factory)

    def invoke(self, provider, snapshot):
        from content_machine.workflow import runtime
        try:
            if provider in (runtime.generate, runtime.review):
                result = provider(snapshot, execution=self)
            elif self.guest:
                raise WorkflowError(503, 'guest_provider_unavailable',
                                    'Guest AI requires the approved free provider. Continue manually.')
            else:
                result = provider(snapshot)
        except Exception:
            if self.failure is not None:
                raise self.failure from None
            raise
        if self.failure is not None:
            raise self.failure
        return result

    def wrap_router(self, router):
        # Only concrete routes can certify actual invocation metadata. Test-only
        # injected creator providers may not expose routes; guests fail closed.
        routes = getattr(router, 'routes', None)
        if not isinstance(routes, dict):
            if self.guest:
                raise WorkflowError(503, 'guest_provider_unavailable', 'Guest AI provider metadata is unavailable.')
            return router
        execution = self
        for name, route in list(routes.items()):
            class Adapter:
                def __init__(self, route_name, original):
                    self.name, self.original = route_name, original

                def complete(self, model, prompt, **kwargs):
                    return execution._complete(self.name, self.original, model, prompt, kwargs)
            routes[name] = Route(route.name, route.protocol, Adapter(name, route))
        return router

    def _complete(self, name, route, model, prompt, kwargs):
        record = {'route': name, 'provider': route.protocol, 'model': model,
                  'model_identity': 'requested', 'state': 'blocked', 'dispatched': False}
        with self._lock:
            self.calls.append(record)
        conn = None
        try:
            if self.guest:
                if route.protocol != 'cloudflare_workers_ai' or model != GUEST_MODEL:
                    raise WorkflowError(503, 'guest_provider_unavailable', 'Guest AI is limited to the approved free provider.')
                kwargs = dict(kwargs)
                tokens = kwargs.get('max_tokens', 2000)
                if type(tokens) is not int or tokens <= 0:
                    raise WorkflowError(422, 'guest_input_unsupported', 'A valid bounded output size is required.')
                kwargs['max_tokens'] = min(tokens, 2000)
                text = prompt
                if kwargs.get('schema') is not None:
                    text += '\n\nReturn only a JSON object conforming to this schema: ' + json.dumps(kwargs['schema'].model_json_schema())
                messages = ([{'role': 'system', 'content': kwargs['system']}] if kwargs.get('system') else [])
                messages.append({'role': 'user', 'content': text})
                payload = {'model': model, 'messages': messages, 'stream': False, 'max_tokens': kwargs['max_tokens']}
                if kwargs.get('schema') is not None:
                    payload['response_format'] = {'type': 'json_object'}
                if 'reasoning_effort' in kwargs:
                    payload['reasoning_effort'] = kwargs['reasoning_effort']
                if len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > self.max_input:
                    raise WorkflowError(413, 'guest_input_too_large', 'Guest AI input exceeds its free quota bound. Shorten the context or continue manually.')
                key = self.operation_id + ':' + uuid.uuid4().hex
                record['reservation_key'] = key
                conn = self.factory()
                _, created = budget.reserve(conn, pool='cloudflare-guest', day=datetime.now(timezone.utc).date().isoformat(),
                    request_id=key, subject_id=self.subject_id, provider=route.protocol, model=model,
                    units=self.per_call, daily_limit=self.daily, max_inflight=self.concurrent)
                if not created or not budget.dispatch(conn, 'cloudflare-guest', key):
                    raise WorkflowError(409, 'guest_budget_conflict', 'This provider attempt already has a dispatch claim.')
            record.update(state='running', dispatched=True)
            result = route.adapter.complete(model=model, prompt=prompt, **kwargs)
            if conn is not None:
                budget.settle(conn, 'cloudflare-guest', record['reservation_key'], actual_units=self.per_call)
                record.update(charged_millineurons=self.per_call, usage_basis='conservative_reservation')
            record['state'] = 'completed'
            return result
        except Exception as error:
            if record['dispatched']:
                record['state'] = 'failed'
                if conn is not None:
                    budget.settle(conn, 'cloudflare-guest', record['reservation_key'])
                    record.update(charged_millineurons=self.per_call, usage_basis='uncertain_reservation')
            record['code'] = error.code if isinstance(error, WorkflowError) else 'provider_failed'
            if isinstance(error, WorkflowError):
                with self._lock:
                    self.failure = error
            raise
        finally:
            if conn is not None:
                conn.close()
