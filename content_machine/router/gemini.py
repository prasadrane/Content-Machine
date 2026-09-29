"""Gemini native provider adapter (generateContent REST, no new deps)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ModelError, ProviderError

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_RETRYABLE = {429, 500, 502, 503, 504}

_GEMINI_TYPES = {float: "NUMBER", int: "INTEGER", bool: "BOOLEAN", str: "STRING"}


def _gemini_schema(model_cls) -> dict:
    """Pydantic model -> Gemini responseSchema (OpenAPI subset, upper-case types)."""
    from typing import Literal, get_args, get_origin
    from pydantic import BaseModel

    def field_schema(annotation) -> dict:
        origin = get_origin(annotation)
        if origin is list:
            return {"type": "ARRAY", "items": field_schema(get_args(annotation)[0])}
        if origin is Literal:
            return {"type": "STRING", "enum": [str(a) for a in get_args(annotation)]}
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return _gemini_schema(annotation)
        if annotation in _GEMINI_TYPES:
            return {"type": _GEMINI_TYPES[annotation]}
        return {"type": "STRING"}

    props: dict = {}
    required: list[str] = []
    for name, field in model_cls.model_fields.items():
        props[name] = field_schema(field.annotation)
        required.append(name)
    return {"type": "OBJECT", "properties": props, "required": required}


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
    ) -> Any:
        """Return str, or a `schema` instance when structured output requested."""
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        gen: dict[str, Any] = {}
        if os.environ.get("DEMO_MODE") == "1" and model.startswith("gemini-2.5-flash"):
            gen["thinkingConfig"] = {"thinkingBudget": 0}
        if kw.get("temperature") is not None:
            gen["temperature"] = kw["temperature"]
        if schema is not None:
            gen["responseMimeType"] = "application/json"
            gen["responseSchema"] = _gemini_schema(schema)
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
        if schema is not None:
            try:
                return schema.model_validate_json(text)
            except ValueError as exc:
                raise ModelError(f"gemini schema-invalid json: {exc}") from exc
        return text
