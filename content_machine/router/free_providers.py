"""Ordered registry of free-tier AI providers and a router built from it.

A provider is 'available' only when its credentials are present in the env.
``build_free_router`` tries available providers in registry order and falls
through on any provider or model failure. Adding a provider later = one adapter
file + one ``FreeProvider`` entry in ``REGISTRY`` (plus a builder in
``_BUILDERS`` keyed by protocol, or a ``builder`` on the entry itself).

Only the explicit credential variables listed in ``env_vars`` are ever read.
No paid, relay or ``messages`` route is ever created here.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from content_machine.config import AppConfig, load_config
from content_machine.router.base import ModelRouter, Route

STRONG = "free-strong"
FAST = "free-fast"
ENV_ORDER = "CONTENT_MACHINE_AI_PROVIDERS"


def _build_cloudflare(env: Mapping[str, str], timeout_s: float):
    account = (env.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    token = (env.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if not account or not token:
        return None
    from content_machine.router.cloudflare_workers_ai import CloudflareWorkersAI

    try:
        return CloudflareWorkersAI(account, token, timeout_s=timeout_s)
    except ValueError:
        return None


def _build_gemini(env: Mapping[str, str], timeout_s: float):
    key = (env.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    from content_machine.router.gemini import GeminiAdapter

    return GeminiAdapter(api_key=key, timeout_s=timeout_s)


# protocol -> (env, timeout_s) -> adapter | None
_BUILDERS: dict[str, Callable[[Mapping[str, str], float], Any]] = {
    "cloudflare_workers_ai": _build_cloudflare,
    "gemini": _build_gemini,
}


@dataclass(frozen=True)
class FreeProvider:
    name: str
    protocol: str  # 'cloudflare_workers_ai' | 'gemini'
    pool: str  # 'cloudflare-guest' | 'gemini-guest'
    unit_label: str
    env_vars: tuple[str, ...]
    native_models: frozenset[str]
    aliases: dict[str, str]  # alias -> native model id
    default_timeout_s: float
    # Optional override of the protocol builder: (env, timeout_s) -> adapter | None.
    builder: Callable[[Mapping[str, str], float], Any] | None = None

    def cost(self, max_input_bytes: int, max_tokens: int) -> int:
        """Conservative per-call cost in this provider's pool units."""
        if self.protocol == "cloudflare_workers_ai":
            # Same formula as workflow/provider_execution.py (millineurons).
            return math.ceil(((max_input_bytes + 1024) * 450 + max_tokens * 3200) / 11)
        return 1  # Gemini: one request

    def build(self, env: Mapping[str, str] | None = None):
        """Adapter, or None when credentials are missing/invalid."""
        env = os.environ if env is None else env
        builder = self.builder or _BUILDERS.get(self.protocol)
        if builder is None:
            return None
        # Hand the builder only this provider's variables.
        scoped = {k: env[k] for k in self.env_vars if k in env and isinstance(env[k], str)}
        return builder(scoped, self.default_timeout_s)


# Order matters: first available provider is tried first.
# UNVERIFIED: both Gemini model ids ('gemini-2.5-flash', 'gemini-2.5-flash-lite')
# must be confirmed against the current Gemini API free tier before relying on them.
REGISTRY: list[FreeProvider] = [
    FreeProvider(
        name="cloudflare_workers_ai",
        protocol="cloudflare_workers_ai",
        pool="cloudflare-guest",
        unit_label="millineurons",
        env_vars=("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"),
        native_models=frozenset({"@cf/qwen/qwen3.8-27b"}),
        aliases={STRONG: "@cf/qwen/qwen3.8-27b", FAST: "@cf/qwen/qwen3.8-27b"},
        default_timeout_s=30.0,
    ),
    FreeProvider(
        name="gemini",
        protocol="gemini",
        pool="gemini-guest",
        unit_label="requests",
        env_vars=("GEMINI_API_KEY",),
        native_models=frozenset({"gemini-2.5-flash", "gemini-2.5-flash-lite"}),
        aliases={STRONG: "gemini-2.5-flash", FAST: "gemini-2.5-flash-lite"},
        default_timeout_s=25.0,
    ),
]


def available_providers(env: Mapping[str, str] | None = None) -> list[FreeProvider]:
    env = os.environ if env is None else env
    providers = list(REGISTRY)
    raw = env.get(ENV_ORDER)
    if raw and raw.strip():
        by_name = {p.name: p for p in providers}
        ordered: list[FreeProvider] = []
        for name in (n.strip() for n in raw.split(",")):
            provider = by_name.get(name)
            if provider is not None and provider not in ordered:
                ordered.append(provider)
        providers = ordered
    return [p for p in providers if p.build(env) is not None]


def free_ai_available(env: Mapping[str, str] | None = None) -> bool:
    return bool(available_providers(env))


def provider_for(protocol: str, model: str) -> FreeProvider | None:
    for provider in REGISTRY:
        if provider.protocol == protocol and (model in provider.native_models or model in provider.aliases):
            return provider
    return None


class AliasAdapter:
    """Translate free-strong/free-fast to a provider's native model id."""

    def __init__(self, provider: FreeProvider, adapter: Any):
        self.provider = provider
        self.adapter = adapter
        self.protocol = provider.protocol

    def complete(self, model, prompt, *, system=None, schema=None, **kwargs):
        native = self.provider.aliases.get(model, model)
        kwargs.setdefault("timeout_s", self.provider.default_timeout_s)
        return self.adapter.complete(model=native, prompt=prompt, system=system, schema=schema, **kwargs)


def build_free_router(
    env: Mapping[str, str] | None = None, base_cfg: AppConfig | None = None
) -> tuple[ModelRouter, AppConfig]:
    env = os.environ if env is None else env
    routes: dict[str, Route] = {}
    for provider in available_providers(env):
        adapter = provider.build(env)
        if adapter is not None:
            routes[provider.name] = Route(
                name=provider.name, protocol=provider.protocol, adapter=AliasAdapter(provider, adapter)
            )
    if not routes:
        wanted = sorted({v for p in REGISTRY for v in p.env_vars})
        raise RuntimeError(
            "No free AI provider is configured. Set credentials for at least one provider "
            "(environment variables: " + ", ".join(wanted) + ")."
        )
    router = ModelRouter(
        routes=routes,
        route_models={"*": list(routes)},
        fallthrough_model_errors=True,
    )
    cfg = (base_cfg if base_cfg is not None else load_config()).model_copy(deep=True)
    cfg.routes = {}  # never carry relay/messages or any paid route
    cfg.route_models = {}
    cfg.models.writer = STRONG
    cfg.models.scanner = FAST
    cfg.models.video_long = STRONG
    cfg.models.council = {
        slot: FAST if "flash" in str(model).lower() else STRONG
        for slot, model in cfg.models.council.items()
    }
    return router, cfg
