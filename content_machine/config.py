"""Application config loader.

config.json holds routing, model, and threshold settings. It never holds
secrets: routes reference environment variables by name; adapters resolve
them at construction time.
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from pydantic import BaseModel, Field


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


class RouteConfig(BaseModel):
    protocol: str = "messages"  # "messages" (Anthropic protocol) | "openai" (future)
    base_url_env: str | None = None
    api_key_env: str | None = None        # sent as x-api-key
    auth_token_env: str | None = None     # sent as Authorization: Bearer (relay bearer tokens)
    base_url: str | None = None  # non-secret override; env wins when set
    api_key: str | None = None   # avoid in practice; env-var reference preferred
    auth_token: str | None = None


class ModelsConfig(BaseModel):
    writer: str = "qwen3.8-max"
    scanner: str = "qwen3.8-flash"
    video_long: str = "qwen3.8-max"
    council: dict[str, str] = Field(default_factory=dict)


class ThresholdsConfig(BaseModel):
    idea_gate: float = 8.0
    idea_margin: float = 0.5
    idea_samples: int = 3
    council_min_score_raw: float = 9.0
    council_margin: float = 0.3
    council_max_iterations: int = 3
    normalization_min_samples: int = 30
    preferred_max_latency_s: float = 90.0


class FeedConfig(BaseModel):
    url: str
    name: str | None = None
    category: str = "general"
    enabled: bool = True
    max_age_days: int | None = None
    max_items: int | None = None


def get_category_default_max_age_days(category: str) -> int:
    """Return empirically verified default age window in days based on publication cadence."""
    cat = (category or "").lower()
    if "company" in cat:
        return 30  # Slow-cadence engineering blogs (Stripe, Netflix, Dropbox, Spotify)
    if "newsletter" in cat or "podcast" in cat:
        return 14  # Deep-dive weekly/biweekly essays & episodes
    if "community" in cat or "tech" in cat:
        return 7   # High-frequency developer communities & aggregators (HN, dev.to, lobsters)
    return 10


class AppConfig(BaseModel):

    routes: dict[str, RouteConfig] = Field(default_factory=dict)
    route_models: dict[str, list[str]] = Field(default_factory=dict)  # model glob -> route names
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    rss_feeds: list[FeedConfig] = Field(default_factory=list)



def load_config(path: str | Path | None = None) -> AppConfig:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    if not p.exists():
        return AppConfig()
    data = json.loads(p.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)
