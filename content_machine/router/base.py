"""ModelRouter: protocol adapters + two-layer failover (plan v2 §8.2).

Layer 1 (provider/route): same model, alternate route. Handles outages,
rate limits, auth faults.
Layer 2 (model): next model in the layer list. Handles model-level errors
provider failover cannot recover: context overflow, refusals/moderation,
schema-invalid output after retries.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    """Route-level failure: try another route for the same model."""


class ModelError(Exception):
    """Model-level failure: advance to the next model in the layer."""


class AllRoutesFailed(Exception):
    def __init__(self, errors: list[tuple[str, str, str]]):
        self.errors = errors
        detail = "; ".join(f"{m}@{r}: {e}" for m, r, e in errors[-3:])
        super().__init__(f"all routes/models failed: {len(errors)} attempts | last: {detail}")


@dataclass
class Route:
    name: str
    protocol: str
    adapter: Any  # .complete(model, prompt, *, system=None, schema=None) -> BaseModel | str


@dataclass
class EndpointHealth:
    """Rolling window of (timestamp, latency_s, ok) per (route, model)."""

    window_s: float = 300.0
    _samples: deque = field(default_factory=deque)

    def record(self, latency_s: float, ok: bool) -> None:
        now = time.time()
        self._samples.append((now, latency_s, ok))
        self._prune(now)

    def _prune(self, now: float) -> None:
        while self._samples and now - self._samples[0][0] > self.window_s:
            self._samples.popleft()

    def recent_stats(self) -> tuple[int, int, float | None]:
        """(ok_count, fail_count, p50 latency of successes) within window."""
        now = time.time()
        self._prune(now)
        oks = [lat for _, lat, ok in self._samples if ok]
        fails = sum(1 for _, _, ok in self._samples if not ok)
        if not oks:
            return 0, fails, None
        oks.sort()
        return len(oks), fails, oks[len(oks) // 2]


class ModelRouter:
    def __init__(
        self,
        routes: dict[str, Route],
        route_models: dict[str, list[str]] | None = None,
        health_window_s: float = 300.0,
        preferred_max_latency_s: float | None = None,
    ):
        self.routes = routes
        self.route_models = route_models or {"*": list(routes)}
        self.preferred_max_latency_s = preferred_max_latency_s
        self._health: dict[tuple[str, str], EndpointHealth] = {}
        self._window_s = health_window_s

    def _health_for(self, route_name: str, model: str) -> EndpointHealth:
        key = (route_name, model)
        if key not in self._health:
            self._health[key] = EndpointHealth(window_s=self._window_s)
        return self._health[key]

    def _routes_for(self, model: str) -> list[str]:
        if model in self.route_models:
            return self.route_models[model]
        for pattern, names in self.route_models.items():
            if pattern == "*" or model.startswith(pattern.rstrip("*")):
                return names
        return list(self.routes)

    def complete(
        self,
        model_layer: list[str],
        prompt: str,
        *,
        system: str | None = None,
        schema: type | None = None,
    ):
        """Try each model in order; per model, try its routes in order.

        Returns adapter result (Pydantic instance when schema given, else str).
        Raises AllRoutesFailed with the full attempt log.
        """
        if not model_layer:
            raise ValueError("model_layer is empty")
        attempts: list[tuple[str, str, str]] = []
        for model in model_layer:
            routes_for_model = self._routes_for(model)
            for route_name in routes_for_model:
                route = self.routes.get(route_name)
                if route is None:
                    attempts.append((model, route_name, "route not configured"))
                    continue
                health = self._health_for(route_name, model)
                ok_n, fail_n, p50 = health.recent_stats()
                if (
                    self.preferred_max_latency_s is not None
                    and p50 is not None
                    and p50 > self.preferred_max_latency_s
                    and len(routes_for_model) > 1
                ):
                    attempts.append((model, route_name, f"skipped: p50 latency {p50:.1f}s over cap"))
                    continue
                t0 = time.time()
                try:
                    result = route.adapter.complete(
                        model=model, prompt=prompt, system=system, schema=schema
                    )
                except ModelError as e:
                    attempts.append((model, route_name, f"model-level: {e}"))
                    break  # next model
                except ProviderError as e:
                    health.record(time.time() - t0, ok=False)
                    attempts.append((model, route_name, f"provider-level: {e}"))
                    continue  # next route
                except Exception as e:  # unexpected = treat as model-level, log loud
                    attempts.append((model, route_name, f"unexpected {type(e).__name__}: {e}"))
                    break
                health.record(time.time() - t0, ok=True)
                return result
        raise AllRoutesFailed(attempts)
