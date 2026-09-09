"""Gemini native provider adapter (generateContent REST, no new deps)."""

from __future__ import annotations

from typing import Any

import httpx

from .base import ModelError, ProviderError

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_RETRYABLE = {429, 500, 502, 503, 504}


class GeminiAdapter:
    """Route adapter speaking Gemini's native protocol.

    Mirrors MessagesAdapter's call shape so ModelRouter failover is unchanged:
    complete(model, prompt, *, system=None, schema=None, **kw) -> str
    """

    protocol = "gemini"

    def __init__(self, api_key: str, timeout_s: float = 60.0):
        if not api_key:
            raise ValueError("GeminiAdapter requires an api_key (GEMINI_API_KEY)")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        schema: Any = None,
        **kw: Any,
    ) -> str:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        gen: dict[str, Any] = {}
        if kw.get("temperature") is not None:
            gen["temperature"] = kw["temperature"]
        if gen:
            body["generationConfig"] = gen
        try:
            resp = httpx.post(
                API_URL.format(model=model),
                json=body,
                headers={"x-goog-api-key": self.api_key},
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini network error: {exc}") from exc
        if resp.status_code in _RETRYABLE:
            raise ProviderError(f"gemini retryable {resp.status_code}")
        if resp.status_code != 200:
            raise ModelError(f"gemini {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise ModelError("gemini returned no text")
        return text
