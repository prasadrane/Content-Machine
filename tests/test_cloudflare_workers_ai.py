"""Cloudflare adapter tests using only in-memory HTTP transports."""
import json
import threading
import time
import unittest

import httpx
from pydantic import BaseModel, ConfigDict

from content_machine.router.base import AllRoutesFailed, ModelError, ModelRouter, ProviderError, ProviderRejected, Route
from content_machine.router.cloudflare_workers_ai import CloudflareWorkersAI
from content_machine.router import cloudflare_workers_ai


class Reply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str
    count: int


ACCOUNT = 'a' * 32
TOKEN = 'fixture-secret-token'
MODEL = '@cf/meta/llama-3.1-8b-instruct'


def success(content='hello', finish='stop'):
    return {'choices': [{'message': {'content': content}, 'finish_reason': finish}]}


class CloudflareWorkersAITest(unittest.TestCase):
    def test_reasoning_effort_is_explicit_validated_and_optional(self):
        seen = []
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json=success())
        adapter = self.adapter(handler)
        adapter.complete(MODEL, 'Write')
        self.assertNotIn('reasoning_effort', seen[-1])
        adapter.complete(MODEL, 'Write', reasoning_effort='low')
        self.assertEqual(seen[-1]['reasoning_effort'], 'low')
        adapter.complete(MODEL, 'Write', reasoning_effort='xhigh')
        self.assertEqual(seen[-1]['reasoning_effort'], 'xhigh')
        for invalid in ('off', 'high', '', 0, {}, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                adapter.complete(MODEL, 'Write', reasoning_effort=invalid)
        self.assertEqual(len(seen), 3)

    def adapter(self, handler, timeout=1):
        return CloudflareWorkersAI(ACCOUNT, TOKEN, timeout_s=timeout, transport=httpx.MockTransport(handler))

    def test_request_uses_explicit_model_bearer_and_messages(self):
        seen = []
        def handle(request):
            seen.append(request)
            return httpx.Response(200, json=success())
        adapter = self.adapter(handle)
        self.assertEqual(adapter.complete(MODEL, 'User text', system='System text'), 'hello')
        request = seen[0]
        self.assertEqual(str(request.url), f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/ai/v1/chat/completions')
        self.assertEqual(request.headers['Authorization'], f'Bearer {TOKEN}')
        payload = json.loads(request.content)
        self.assertEqual(payload['model'], MODEL)
        self.assertEqual(payload['messages'], [{'role': 'system', 'content': 'System text'},
                                               {'role': 'user', 'content': 'User text'}])
        self.assertFalse(payload['stream'])
        self.assertNotIn(TOKEN, repr(adapter))

    def test_schema_output_is_locally_validated(self):
        seen = []
        def handle(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json=success('{"text":"yes","count":3}'))
        result = self.adapter(handle).complete(MODEL, 'Write', schema=Reply)
        self.assertEqual(result, Reply(text='yes', count=3))
        self.assertEqual(seen[0]['response_format'], {'type': 'json_object'})
        self.assertIn('count', seen[0]['messages'][-1]['content'])

    def test_invalid_json_schema_extra_fields_and_empty_refusal_fail(self):
        cases = [success('not json'), success('{"text":"x","count":"bad"}'),
                 success('{"text":"x","count":1,"extra":true}'), success(''),
                 success('{"text":"x","count":1}', 'length'),
                 {'choices': [{'message': {'refusal': 'No', 'content': ''}, 'finish_reason': 'stop'}]},
                 {'choices': []}, {'error': {'message': TOKEN}}]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ModelError) as raised:
                    self.adapter(lambda request: httpx.Response(200, json=payload)).complete(MODEL, 'Write', schema=Reply)
                self.assertNotIn(TOKEN, str(raised.exception))

    def test_http_status_and_network_errors_are_redacted(self):
        for status, error in [(401, ProviderError), (403, ProviderError), (429, ProviderError),
                              (503, ProviderError), (400, ModelError)]:
            with self.subTest(status=status):
                with self.assertRaises(error) as raised:
                    self.adapter(lambda request: httpx.Response(status, text=TOKEN)).complete(MODEL, 'Write')
                self.assertNotIn(TOKEN, str(raised.exception))
        def broken(request):
            raise httpx.ConnectError('credential ' + TOKEN, request=request)
        with self.assertRaises(ProviderError) as raised:
            self.adapter(broken).complete(MODEL, 'Write')
        self.assertNotIn(TOKEN, str(raised.exception))

    def test_rejection_statuses_map_to_provider_rejected(self):
        for status in (401, 403, 429, 500, 503):
            with self.subTest(status=status):
                with self.assertRaises(ProviderRejected) as raised:
                    self.adapter(lambda request: httpx.Response(status, text=TOKEN)).complete(MODEL, 'Write')
                self.assertNotIn(TOKEN, str(raised.exception))
        with self.assertRaises(ModelError):
            self.adapter(lambda request: httpx.Response(400, text=TOKEN)).complete(MODEL, 'Write')

    def test_per_call_timeout_is_clamped_to_constructor_timeout(self):
        gate = threading.Event()
        def blocked(request):
            gate.wait(3)
            return httpx.Response(200, json=success())
        try:
            started = time.monotonic()
            with self.assertRaises(ProviderError):
                self.adapter(blocked, timeout=2).complete(MODEL, 'Write', timeout_s=0.1)
            self.assertLess(time.monotonic() - started, 0.8)
            started = time.monotonic()
            with self.assertRaises(ProviderError):
                self.adapter(blocked, timeout=0.1).complete(MODEL, 'Write', timeout_s=60)
            self.assertLess(time.monotonic() - started, 0.8)
        finally:
            gate.set()
        seen = []
        def ok(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json=success())
        self.adapter(ok).complete(MODEL, 'Write', timeout_s=5)
        self.assertNotIn('timeout_s', seen[0])
        with self.assertRaises(ValueError):
            self.adapter(ok).complete(MODEL, 'Write', timeout_s=0)

    def test_timeout_is_bounded_and_late_calls_hold_a_concurrency_slot(self):
        gate = threading.Event()
        def blocked(request):
            gate.wait(2)
            return httpx.Response(200, json=success())
        try:
            started = time.monotonic()
            with self.assertRaises(ProviderError):
                self.adapter(blocked, timeout=0.1).complete(MODEL, 'Write')
            self.assertLess(time.monotonic() - started, 0.8)
        finally:
            gate.set()

    def test_busy_slot_rejects_without_sending_and_slot_recovers(self):
        slots = threading.BoundedSemaphore(1)
        gate = threading.Event()
        entered = threading.Event()
        calls = []
        def blocked(request):
            calls.append(1)
            entered.set()
            gate.wait(2)
            return httpx.Response(200, json=success())
        try:
            with unittest.mock.patch.object(cloudflare_workers_ai, '_SLOTS', slots):
                with self.assertRaises(ProviderError):
                    self.adapter(blocked, timeout=0.1).complete(MODEL, 'First')
                self.assertTrue(entered.wait(1))
                with self.assertRaises(ProviderError):
                    self.adapter(blocked, timeout=0.1).complete(MODEL, 'Second')
                self.assertEqual(len(calls), 1)
                gate.set()
                self.assertTrue(slots.acquire(timeout=2))
                slots.release()
        finally:
            gate.set()

    def test_bad_model_configuration_and_oversized_response_are_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter(lambda request: httpx.Response(200)).complete('https://bad.example', 'x')
        with self.assertRaises(ValueError):
            CloudflareWorkersAI('invalid', TOKEN)
        with self.assertRaises(ModelError):
            self.adapter(lambda request: httpx.Response(200, content=b'x' * 1_100_000)).complete(MODEL, 'x')

    def test_normal_model_router_propagates_failure_without_secret(self):
        adapter = self.adapter(lambda request: httpx.Response(401, text=TOKEN))
        router = ModelRouter({'cloudflare': Route('cloudflare', 'cloudflare', adapter)}, {'*': ['cloudflare']})
        with self.assertRaises(AllRoutesFailed) as raised:
            router.complete([MODEL], 'Write')
        self.assertNotIn(TOKEN, str(raised.exception))

    def test_normal_model_router_returns_locally_validated_schema(self):
        adapter = self.adapter(lambda request: httpx.Response(200, json=success('{"text":"ok","count":2}')))
        router = ModelRouter({'cloudflare': Route('cloudflare', 'cloudflare', adapter)}, {'*': ['cloudflare']})
        self.assertEqual(router.complete([MODEL], 'Write', schema=Reply), Reply(text='ok', count=2))
