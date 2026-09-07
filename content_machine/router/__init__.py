"""Router package: build a ModelRouter from AppConfig."""

from __future__ import annotations

from ..config import AppConfig
from .base import AllRoutesFailed, ModelError, ModelRouter, ProviderError, Route
from .messages_adapter import MessagesAdapter

__all__ = [
    "ModelRouter", "Route", "ModelError", "ProviderError", "AllRoutesFailed",
    "router_from_config",
]


def router_from_config(cfg: AppConfig, max_tokens: int = 2000) -> ModelRouter:
    routes: dict[str, Route] = {}
    for name, rc in cfg.routes.items():
        if rc.protocol == "messages":
            adapter = MessagesAdapter(
                base_url=rc.base_url,
                base_url_env=rc.base_url_env,
                api_key=rc.api_key,
                api_key_env=rc.api_key_env,
                auth_token=rc.auth_token,
                auth_token_env=rc.auth_token_env,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"unsupported route protocol: {rc.protocol} (route {name})")
        routes[name] = Route(name=name, protocol=rc.protocol, adapter=adapter)
    return ModelRouter(
        routes=routes,
        route_models=cfg.route_models or None,
        preferred_max_latency_s=cfg.thresholds.preferred_max_latency_s,
    )
