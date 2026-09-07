"""Base types for all Oracle connectors (plan v2 §2.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ConnectorItem:
    """A single ingested item from any source (bookmark, issue, post, etc.)."""

    title: str
    url: str
    body: str
    source: str                     # e.g. "blog.example.com" or "github:org/repo"
    fetched_at: datetime
    guid: Optional[str] = None      # dedup key; defaults to url if absent
    published_at: Optional[datetime] = None



@dataclass
class ConnectorResult:
    """Output of one connector fetch run."""

    source: str
    items: list[ConnectorItem] = field(default_factory=list)
    not_modified: bool = False      # True when server returned 304


class BaseConnector(ABC):
    """Abstract base for every ingestion connector."""

    @abstractmethod
    def fetch(self, **kwargs) -> ConnectorResult:
        """Pull new items since the last fetch.

        Implementations must be idempotent and handle their own
        state (ETags, since timestamps, seen-GUIDs) between calls.
        """
