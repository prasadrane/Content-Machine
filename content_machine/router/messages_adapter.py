"""Anthropic Messages-protocol adapter (primary route: Token Plan relay).

Plan v2 §8.2/§9.4: relay `messages.parse` is best-effort — one retry on
parse/validation failure before escalating to router failover. Numeric
bounds are NOT enforced server-side; callers must validate with Pydantic
(parse() does this; raw callers must too).
"""

from __future__ import annotations

import os
import re

import anthropic
from pydantic import BaseModel

from .base import ModelError, ProviderError

CONTEXT_MARKERS = ("context length", "too long", "maximum context", "token limit", "context_length")
REFUSAL_MARKERS = ("refusal", "moderation", "content policy", "safety")


def classify_status(status: int | None, message: str) -> type[Exception]:
    """Map an API status error to ProviderError (try other routes) or
    ModelError (advance model layer). Pure function for testability."""
    msg = message.lower()
    if status is not None:
        if status >= 500 or status in (408, 429):
            return ProviderError
        if status in (401, 403):
            return ProviderError  # auth/quota is a route problem
        if status == 400:
            if any(m in msg for m in CONTEXT_MARKERS):
                return ModelError
            if any(m in msg for m in REFUSAL_MARKERS):
                return ModelError
    if any(m in msg for m in REFUSAL_MARKERS):
        return ModelError
    return ModelError  # unclassified 4xx: don't burn other routes


class MessagesAdapter:
    def __init__(
        self,
        base_url: str | None = None,
        base_url_env: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        auth_token: str | None = None,
        auth_token_env: str | None = None,
        max_tokens: int = 2000,
        parse_retries: int = 1,
    ):
        kwargs: dict = {}
        url = base_url or (os.environ.get(base_url_env) if base_url_env else None)
        if url:
            kwargs["base_url"] = url
        # Bearer token (Authorization header) wins over api_key (x-api-key header):
        # the Token Plan relay authenticates bearer-only.
        token = auth_token or (os.environ.get(auth_token_env) if auth_token_env else None)
        key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
        if token:
            kwargs["auth_token"] = token
        elif key:
            kwargs["api_key"] = key
        # bare Anthropic() resolves env on its own when nothing is passed
        self._client = anthropic.Anthropic(**kwargs)
        self.max_tokens = max_tokens
        self.parse_retries = parse_retries

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        max_tokens: int | None = None,
    ):
        try:
            return self._call(model, prompt, system=system, schema=schema,
                              max_tokens=max_tokens or self.max_tokens)
        except (ProviderError, ModelError):
            raise
        except anthropic.APIConnectionError as e:
            raise ProviderError(f"connection: {e}") from e
        except anthropic.APITimeoutError as e:
            raise ProviderError(f"timeout: {e}") from e
        except anthropic.APIStatusError as e:
            exc = classify_status(getattr(e, "status_code", None), str(e))
            raise exc(f"{type(e).__name__}: {str(e)[:300]}") from e

    def _call(self, model, prompt, *, system, schema, max_tokens):
        messages = [{"role": "user", "content": prompt}]
        extra = {"system": system} if system else {}

        if schema is None:
            create_extra = dict(extra)
            if "thinking" not in create_extra:
                create_extra["thinking"] = {"type": "disabled"}
            try:
                resp = self._client.messages.create(
                    model=model, max_tokens=max_tokens, messages=messages, **create_extra
                )
            except Exception:
                resp = self._client.messages.create(
                    model=model, max_tokens=max_tokens, messages=messages, **extra
                )
            self._check_refusal(resp)
            return next((b.text for b in resp.content if b.type == "text"), "")

        try:
            return self._parse_mode(model, messages, extra, schema, max_tokens)
        except anthropic.APIStatusError as e:
            if getattr(e, "status_code", None) == 400:
                # Relay quirk: older model generations get translated to
                # response_format=json_object, which 400s without the word
                # "json" in messages. Degrade to explicit JSON prompting.
                return self._plain_json_mode(model, prompt, extra, schema, max_tokens)
            raise

    def _parse_mode(self, model, messages, extra, schema, max_tokens):
        last_err: Exception | None = None
        for attempt in range(self.parse_retries + 1):
            try:
                resp = self._client.messages.parse(
                    model=model, max_tokens=max_tokens, messages=messages,
                    output_format=schema, **extra
                )
                parsed = getattr(resp, "parsed_output", None)
                if parsed is not None:
                    return parsed
                text = next((b.text for b in resp.content if b.type == "text"), "")
                return schema.model_validate_json(text)
            except anthropic.APIError:
                raise  # classified by complete()
            except Exception as e:  # malformed JSON / Pydantic validation
                last_err = e
        raise ModelError(
            f"schema-invalid after {self.parse_retries + 1} attempts: {str(last_err)[:200]}"
        )

    def _plain_json_mode(self, model, prompt, extra, schema, max_tokens):
        import json as _json

        instruction = (
            "\n\nReturn ONLY a single valid JSON object matching this JSON schema "
            "(no code fences, no commentary):\n" + _json.dumps(schema.model_json_schema())
        )
        messages = [{"role": "user", "content": prompt + instruction}]
        last_err: Exception | None = None
        for attempt in range(self.parse_retries + 1):
            resp = self._client.messages.create(
                model=model, max_tokens=max_tokens, messages=messages, **extra
            )
            self._check_refusal(resp)
            text = next((b.text for b in resp.content if b.type == "text"), "")
            try:
                return schema.model_validate_json(text.strip())
            except Exception as e:
                m = re.search(r"\{.*\}", text, re.S)
                if m:
                    try:
                        return schema.model_validate_json(m.group(0))
                    except Exception:
                        pass
                last_err = e
        raise ModelError(
            f"plain-json schema-invalid after {self.parse_retries + 1} attempts: {str(last_err)[:200]}"
        )

    @staticmethod
    def _check_refusal(resp) -> None:
        if getattr(resp, "stop_reason", None) == "refusal":
            raise ModelError("model refused (stop_reason=refusal)")
