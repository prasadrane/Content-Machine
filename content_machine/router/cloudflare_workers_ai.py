"""Opt-in Cloudflare Workers AI Chat Completions adapter.

Only the fixed Cloudflare API hostname is contacted. No environment-derived
proxies, redirects, credential discovery, or paid fallback are enabled.
"""
from __future__ import annotations

import json
import math
import queue
import re
import threading
import time

import httpx
from pydantic import BaseModel, ValidationError

from content_machine.router.base import ModelError, ProviderError, ProviderRejected

MAX_RESPONSE_BYTES = 1_000_000
MAX_INPUT_BYTES = 1_000_000
MAX_TOKENS = 4096
_SLOTS = threading.BoundedSemaphore(4)
_ACCOUNT = re.compile(r'^[a-fA-F0-9]{32}$')
_MODEL = re.compile(r'^@[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)+$')


class CloudflareWorkersAI:
    """ModelRouter route adapter. Credentials must be passed explicitly."""

    protocol = 'cloudflare_workers_ai'

    def __init__(self, account_id: str, api_token: str, *, timeout_s: float = 30.0, transport=None):
        if not isinstance(account_id, str) or not _ACCOUNT.fullmatch(account_id):
            raise ValueError('A valid Cloudflare account ID is required')
        if not isinstance(api_token, str) or not api_token.strip() or any(c.isspace() for c in api_token):
            raise ValueError('A valid Cloudflare API token is required')
        if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 120:
            raise ValueError('Cloudflare timeout must be between 0 and 120 seconds')
        self._url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions'
        self._token = api_token
        self._timeout_s = float(timeout_s)
        self._transport = transport

    def complete(self, model: str, prompt: str, *, system: str | None = None,
                 schema: type[BaseModel] | None = None, **kwargs):
        """Return text or a validated model, or a redacted provider/model error."""
        timeout_s = self._timeout_s
        requested = kwargs.pop('timeout_s', None)
        if requested is not None:
            if (isinstance(requested, bool) or not isinstance(requested, (int, float))
                    or not math.isfinite(requested) or requested <= 0):
                raise ValueError('timeout_s must be a positive number')
            timeout_s = min(timeout_s, float(requested))
        deadline = time.monotonic() + timeout_s
        if not isinstance(model, str) or not _MODEL.fullmatch(model):
            raise ValueError('A provider-native Cloudflare model ID is required')
        if not isinstance(prompt, str) or not prompt.strip() or (system is not None and not isinstance(system, str)):
            raise ValueError('A text prompt is required')
        if schema is not None and (not isinstance(schema, type) or not issubclass(schema, BaseModel)):
            raise ValueError('Schema must be a Pydantic model class')
        max_tokens = kwargs.get('max_tokens', 2000)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError('max_tokens is outside the supported range')
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        if schema:
            prompt += '\n\nReturn only a JSON object conforming to this schema: ' + json.dumps(schema.model_json_schema())
        messages.append({'role': 'user', 'content': prompt})
        payload = {'model': model, 'messages': messages, 'stream': False, 'max_tokens': max_tokens}
        if 'reasoning_effort' in kwargs:
            effort = kwargs['reasoning_effort']
            if not isinstance(effort, str) or effort not in ('low', 'medium', 'xhigh'):
                raise ValueError('Unsupported Cloudflare reasoning effort')
            payload['reasoning_effort'] = effort
        if schema:
            payload['response_format'] = {'type': 'json_object'}
        if len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > MAX_INPUT_BYTES:
            raise ValueError('Prompt exceeds the supported size')
        raw = self._bounded_request(payload, deadline)
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get('error') or data.get('success') is False:
                raise ValueError('provider error')
            choice = data['choices'][0]
            message = choice['message']
            text = message.get('content')
            if choice.get('finish_reason') != 'stop' or message.get('refusal'):
                raise ValueError('incomplete or refused response')
            if not isinstance(text, str) or not text.strip():
                raise ValueError('missing response')
            return schema.model_validate_json(text) if schema else text
        except (KeyError, IndexError, TypeError, ValueError, ValidationError):
            raise ModelError('Cloudflare returned an invalid, incomplete, or refused response') from None

    def _bounded_request(self, payload, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not _SLOTS.acquire(timeout=remaining):
            raise ProviderError('Cloudflare request timed out')
        result = queue.Queue(maxsize=1)

        def run():
            try:
                result.put((True, self._send(payload, deadline)))
            except (ModelError, ProviderError) as error:
                result.put((False, error))
            except Exception:
                result.put((False, ProviderError('Cloudflare request failed')))
            finally:
                _SLOTS.release()

        try:
            threading.Thread(target=run, daemon=True).start()
        except Exception:
            _SLOTS.release()
            raise ProviderError('Cloudflare request could not start') from None
        try:
            success, value = result.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            raise ProviderError('Cloudflare request timed out') from None
        if not success:
            raise value from None
        return value

    def _send(self, payload, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderError('Cloudflare request timed out')
        headers = {'Authorization': f'Bearer {self._token}', 'Accept': 'application/json'}
        try:
            with httpx.Client(transport=self._transport, trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(remaining)) as client:
                with client.stream('POST', self._url, json=payload, headers=headers) as response:
                    if response.status_code in (401, 403, 408, 429) or response.status_code >= 500:
                        raise ProviderRejected(f'Cloudflare request unavailable (HTTP {response.status_code})')
                    if response.status_code != 200:
                        raise ModelError(f'Cloudflare rejected the request (HTTP {response.status_code})')
                    body = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if time.monotonic() >= deadline:
                            raise ProviderError('Cloudflare request timed out')
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ModelError('Cloudflare response exceeds the size limit')
                    return bytes(body)
        except httpx.HTTPError:
            raise ProviderError('Cloudflare network request failed') from None
