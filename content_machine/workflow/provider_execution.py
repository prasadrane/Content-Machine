"""Request-scoped actual-attempt metadata and durable free-only provider guards.

Every verified hosted principal (anonymous guest or signed-in user) is metered
against per-provider daily pools so the shared free tiers cannot be drained.
Trusted-local mode (no hosted verifier) is unmetered.
"""
from datetime import datetime, timezone
import json
import math
import os
import sys
import threading
import time
import uuid

from content_machine.router.base import ProviderError, ProviderRejected, Route
from content_machine.router.free_providers import provider_for
from content_machine.workflow import provider_budget as budget
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.access import _hosted_deployment

_PREFIX = 'CONTENT_MACHINE_GUEST_AI_'
# Optional policy variables: name -> default. Missing values use the default;
# present-but-invalid values fail closed with guest_budget_unconfigured.
_DEFAULTS = {'MAX_INPUT_BYTES': 12_000, 'PER_CALL_MILLINEURONS': 1_200_000,
             'DAILY_MILLINEURONS': 9_000_000, 'MAX_INFLIGHT': 4,
             'GEMINI_DAILY_REQUESTS': 100, 'GEMINI_MAX_INFLIGHT': 2}
MAX_OUTPUT_TOKENS = 2000
# A request (including fallthrough between providers) must finish within this
# many seconds of ProviderExecution creation, leaving room for the host limit.
OVERALL_DEADLINE_S = 50.0
MIN_ATTEMPT_S = 5.0
_RESERVE_MARGIN_S = 3.0
# Budget error code -> informativeness rank (higher is surfaced first).
_BUDGET_CODES = {'guest_budget_exhausted': 4, 'guest_budget_subject_exhausted': 3,
                 'guest_budget_busy': 2, 'guest_budget_subject_busy': 1}


def _read_policy():
    """Policy ints from env (defaults when unset); raises ValueError if invalid."""
    values = {}
    for name, default in _DEFAULTS.items():
        raw = os.environ.get(_PREFIX + name)
        values[name] = default if raw is None else int(raw)
    return values


class ProviderExecution:
    def __init__(self, *, metered=None, subject_id, operation_id, connection_factory=None, guest=None):
        # `guest` is the legacy spelling of `metered`.
        self.metered = bool(guest if metered is None else metered)
        self.subject_id, self.operation_id = subject_id, operation_id
        self.factory = connection_factory
        self.calls, self._lock, self.failure = [], threading.Lock(), None
        self.budget_error = None
        self.deadline = time.monotonic() + OVERALL_DEADLINE_S
        if self.metered:
            try:
                policy = _read_policy()
                self.daily, self.per_call = policy['DAILY_MILLINEURONS'], policy['PER_CALL_MILLINEURONS']
                self.concurrent, self.max_input = policy['MAX_INFLIGHT'], policy['MAX_INPUT_BYTES']
                self.gemini_daily, self.gemini_inflight = policy['GEMINI_DAILY_REQUESTS'], policy['GEMINI_MAX_INFLIGHT']
                # UTF-8 bytes bound tokenizer input, plus 512 framing tokens per
                # message (at most system+user). Output includes reasoning. Rates
                # $0.45/$3.20 per million, neuron unit $0.011/1000 (reviewed).
                minimum = math.ceil(((self.max_input + 1024) * 450 + MAX_OUTPUT_TOKENS * 3200) / 11)
                valid = (callable(self.factory) and 0 < self.daily <= 10_000_000
                         and minimum <= self.per_call <= self.daily
                         and 0 < self.concurrent <= 4 and 0 < self.max_input <= 1_000_000
                         and 0 < self.gemini_daily <= 1_000_000 and 0 < self.gemini_inflight <= 8)
            except (ValueError, TypeError):
                valid = False
            if not valid:
                raise WorkflowError(503, 'guest_budget_unconfigured',
                                    'Guest AI quota is not configured. Your draft is preserved; continue manually.')

    @property
    def guest(self):  # legacy alias
        return self.metered

    @classmethod
    def for_request(cls, request, principal, operation_id):
        metered = False
        verifier = getattr(getattr(request.app.state, 'workflow_authenticator', None), 'verify_session', None)
        # Local server-injected principal-only authenticators are the existing
        # offline seam. Hosted deployment always requires signed session proof.
        # Every verified hosted principal is metered, signed-in or anonymous.
        if principal.mode.value == 'hosted_verified' and (callable(verifier) or _hosted_deployment()):
            parts = request.headers.get('Authorization', '').split()
            try:
                session = verifier(parts[1]) if callable(verifier) and len(parts) == 2 and parts[0].lower() == 'bearer' else None
            except Exception:
                session = None
            if (not isinstance(session, VerifiedGuestSession) or session.principal != principal
                    or type(session.is_anonymous) is not bool):
                raise WorkflowError(503, 'ai_session_unavailable', 'AI session verification is unavailable. Your draft is preserved.')
            metered = True
        factory = getattr(request.app.state, 'workflow_connection_factory', None)
        return cls(metered=metered, subject_id=principal.owner_id, operation_id=operation_id,
                   connection_factory=factory)

    def invoke(self, provider, snapshot):
        from content_machine.workflow import runtime
        try:
            if provider in (runtime.generate, runtime.review):
                result = provider(snapshot, execution=self)
            elif self.metered:
                raise WorkflowError(503, 'guest_provider_unavailable',
                                    'Guest AI requires the approved free provider. Continue manually.')
            else:
                result = provider(snapshot)
        except Exception:
            if self.failure is not None:
                raise self.failure from None
            # Every provider was out of quota and nothing was dispatched: surface the 429.
            if self.budget_error is not None and not any(c['dispatched'] for c in self.calls):
                raise self.budget_error from None
            raise
        if self.failure is not None:
            raise self.failure
        return result

    def wrap_router(self, router):
        # Only concrete routes can certify actual invocation metadata. Test-only
        # injected creator providers may not expose routes; metered fails closed.
        routes = getattr(router, 'routes', None)
        if not isinstance(routes, dict):
            if self.metered:
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

    def _policy(self, provider):
        """(units, daily_limit, max_inflight) for one provider's pool."""
        if provider.protocol == 'cloudflare_workers_ai':
            return self.per_call, self.daily, self.concurrent
        if provider.protocol == 'gemini':
            return provider.cost(self.max_input, MAX_OUTPUT_TOKENS), self.gemini_daily, self.gemini_inflight
        raise WorkflowError(503, 'guest_provider_unavailable', 'Guest AI is limited to the approved free providers.')

    def _remember_budget_error(self, error):
        with self._lock:
            current = self.budget_error
            if current is None or _BUDGET_CODES.get(error.code, 0) > _BUDGET_CODES.get(current.code, 0):
                self.budget_error = error

    @staticmethod
    def _charged(record, pool, units, basis):
        record.update(charged_units=units, usage_basis=basis)
        if pool == 'cloudflare-guest':
            record['charged_millineurons'] = units

    @staticmethod
    def _log_attempt(record, started, error=None):
        """One operator line per attempt: fixed fields only, never prompt, response or key text."""
        if error is None:
            outcome = 'ok'
        elif isinstance(error, ProviderRejected):
            outcome = 'rejected'
        elif isinstance(error, WorkflowError):
            outcome = 'workflow:' + str(error.code)
        elif isinstance(error, ProviderError):
            outcome = 'provider:' + (record.get('code') or type(error).__name__)
        else:
            outcome = 'error:' + type(error).__name__
        print(f"ai_attempt provider={record.get('provider')} model={record.get('model')} outcome={outcome} "
              f"dispatched={record.get('dispatched')} ms={int((time.monotonic() - started) * 1000)}",
              file=sys.stderr, flush=True)

    def _complete(self, name, route, model, prompt, kwargs):
        record = {'route': name, 'provider': route.protocol, 'model': model,
                  'model_identity': 'requested', 'state': 'blocked', 'dispatched': False}
        started = time.monotonic()
        with self._lock:
            self.calls.append(record)
        conn = None
        pool = None
        units = 0
        try:
            if self.metered:
                provider = provider_for(route.protocol, model)
                if provider is None:
                    raise WorkflowError(503, 'guest_provider_unavailable', 'Guest AI is limited to the approved free providers.')
                record['provider'] = provider.name
                pool = provider.pool
                units, daily_limit, max_inflight = self._policy(provider)
                remaining = self.deadline - time.monotonic()
                if remaining < MIN_ATTEMPT_S:
                    raise ProviderError('AI time budget exhausted before dispatch')
                kwargs = dict(kwargs)
                kwargs['timeout_s'] = min(provider.default_timeout_s, remaining - _RESERVE_MARGIN_S)
                tokens = kwargs.get('max_tokens', MAX_OUTPUT_TOKENS)
                if type(tokens) is not int or tokens <= 0:
                    raise WorkflowError(422, 'guest_input_unsupported', 'A valid bounded output size is required.')
                kwargs['max_tokens'] = min(tokens, MAX_OUTPUT_TOKENS)
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
                try:
                    _, created = budget.reserve(conn, pool=pool, day=datetime.now(timezone.utc).date().isoformat(),
                        request_id=key, subject_id=self.subject_id, provider=route.protocol, model=model,
                        units=units, daily_limit=daily_limit, max_inflight=max_inflight,
                        # One subject may fan out up to `max_inflight` calls (Council) and retry once.
                        subject_daily_limit=max(units * max_inflight * 2, daily_limit // 4),
                        subject_max_inflight=max_inflight)
                except WorkflowError as error:
                    if error.code not in _BUDGET_CODES:
                        raise
                    # This pool is spent or busy; let the router try the next provider.
                    self._remember_budget_error(error)
                    record['code'] = error.code
                    raise ProviderError('provider quota unavailable: ' + error.code) from None
                if not created or not budget.dispatch(conn, pool, key):
                    raise WorkflowError(409, 'guest_budget_conflict', 'This provider attempt already has a dispatch claim.')
            record.update(state='running', dispatched=True)
            result = route.adapter.complete(model=model, prompt=prompt, **kwargs)
            if conn is not None:
                budget.settle(conn, pool, record['reservation_key'], actual_units=units)
                self._charged(record, pool, units, 'conservative_reservation')
            record['state'] = 'completed'
            self._log_attempt(record, started)
            return result
        except Exception as error:
            self._log_attempt(record, started, error)
            if record['dispatched']:
                record['state'] = 'failed'
                if conn is not None:
                    if isinstance(error, ProviderRejected):
                        # A response arrived and nothing was produced: free the slot, charge nothing.
                        budget.settle(conn, pool, record['reservation_key'], actual_units=0)
                        self._charged(record, pool, 0, 'provider_rejected')
                    else:
                        budget.settle(conn, pool, record['reservation_key'])
                        self._charged(record, pool, units, 'uncertain_reservation')
            record.setdefault('code', error.code if isinstance(error, WorkflowError) else 'provider_failed')
            if isinstance(error, WorkflowError):
                with self._lock:
                    self.failure = error
            raise
        finally:
            if conn is not None:
                conn.close()
