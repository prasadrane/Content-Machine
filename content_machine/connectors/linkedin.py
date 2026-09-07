"""LinkedIn connector: extract post updates via Voyager API with session cookie authentication.

Auth requirement:
    `li_at` cookie from your logged-in LinkedIn browser session.
    Can be passed directly or set via `LINKEDIN_LI_AT` environment variable.

Design principles:
    - Zero third-party service dependencies
    - Inherits BaseConnector (returns ConnectorItem / ConnectorResult)
    - Directly usable by OracleOrchestrator for idea scoring & council drafting
"""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import requests

from content_machine.connectors.base import BaseConnector, ConnectorItem, ConnectorResult
from content_machine.connectors.linkedin_public import LinkedInPublicBridge
from content_machine.connectors.linkedin_session import LinkedInSessionManager
from content_machine.storage.db import get_seen_guids_for_feed, record_seen_guids

_VOYAGER_BASE = "https://www.linkedin.com/voyager/api"


def _extract_title(text: str, max_chars: int = 80) -> str:
    """Extract a concise title from the first sentence or snippet of the post."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "Untitled LinkedIn Update"
    
    # Split on sentence enders
    parts = re.split(r"[.!?]\s+", cleaned, maxsplit=1)
    title = parts[0].strip()
    if len(title) > max_chars:
        return title[:max_chars].rstrip() + "..."
    return title


class LinkedInConnector(BaseConnector):
    """Fetches recent post updates from LinkedIn using browser session cookies or zero-auth public bridge.

    Args:
        li_at:   The `li_at` cookie value from a logged-in browser session.
                 If omitted, reads from saved session or `LINKEDIN_LI_AT` environment variable.
        profile: Optional public profile username / vanity slug (e.g. 'satyanadella' or 'company/cloudflare').
                 If None and no cookie exists, raises ValueError.
        db_conn: Optional SQLite connection to record and filter seen post GUIDs across runs.
    """

    def __init__(
        self,
        li_at: str | None = None,
        profile: str | None = None,
        db_conn: Optional[sqlite3.Connection] = None,
    ):
        self.profile = profile.strip() if profile else None
        self._db_conn = db_conn
        self.csrf_token = "ajax:1234567890123456789"
        self._seen_urns: set[str] = set()

        cookie = (li_at or os.environ.get("LINKEDIN_LI_AT", "")).strip()
        if not cookie:
            # Attempt to auto-load saved browser session
            try:
                mgr = LinkedInSessionManager()
                cookie = mgr.get_valid_cookie() or ""
            except Exception:
                cookie = ""

        if cookie:
            self.li_at: str | None = cookie.strip()
            self._public_bridge: Optional[LinkedInPublicBridge] = None
        else:
            self.li_at = None
            if self.profile:
                self._public_bridge = LinkedInPublicBridge(self.profile)
            else:
                raise ValueError(
                    "li_at cookie is required for home feed. Pass li_at='...', set LINKEDIN_LI_AT, "
                    "or provide a profile handle for public bridge mode."
                )

        if self._db_conn is not None:
            source_name = f"linkedin:{self.profile}" if self.profile else "linkedin:feed"
            self._seen_urns.update(get_seen_guids_for_feed(self._db_conn, source_name))

    def _build_headers(self) -> dict[str, str]:
        if not self.li_at:
            return {}
        return {
            "Cookie": f'li_at={self.li_at}; JSESSIONID="{self.csrf_token}"',
            "csrf-token": self.csrf_token,
            "x-restli-protocol-version": "2.0.0",
            "x-li-lang": "en_US",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
        }

    def _get_target_url(self) -> str:
        if self.profile:
            # Fetch profile shares/updates
            return f"{_VOYAGER_BASE}/identity/profileUpdatesV2?count=20&q=memberShareFeed&profileUrn=urn:li:fsd_profile:{self.profile}"
        # Fetch user's home feed
        return f"{_VOYAGER_BASE}/feed/updates?count=20"

    def fetch(self, **kwargs) -> ConnectorResult:
        """Fetch recent posts and return a ConnectorResult of ConnectorItems."""
        source_name = f"linkedin:{self.profile}" if self.profile else "linkedin:feed"

        # Mode C: Zero-auth public bridge
        if self._public_bridge is not None:
            res = self._public_bridge.fetch(**kwargs)
            filtered_items: list[ConnectorItem] = []
            new_guids: list[str] = []
            for item in res.items:
                guid = item.guid or item.url
                if guid in self._seen_urns:
                    continue
                self._seen_urns.add(guid)
                new_guids.append(guid)
                filtered_items.append(item)

            if self._db_conn is not None and new_guids:
                record_seen_guids(self._db_conn, source_name, new_guids)

            return ConnectorResult(source=source_name, items=filtered_items)

        # Mode B / Explicit: Voyager API with session cookie
        url = self._get_target_url()
        headers = self._build_headers()

        try:
            resp = requests.get(url, headers=headers, timeout=25)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # Fallback for vanity URL or alternative profile update endpoint
            if self.profile and ("profileUpdatesV2" in url):
                alt_url = f"{_VOYAGER_BASE}/identity/profiles/{self.profile}/updates?count=20"
                try:
                    resp = requests.get(alt_url, headers=headers, timeout=25)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    data = {}
            else:
                data = {}

        elements = data.get("elements", [])
        items: list[ConnectorItem] = []
        new_guids: list[str] = []
        now = datetime.now(tz=timezone.utc)

        for el in elements:
            if not isinstance(el, dict):
                continue
            urn = el.get("urn") or el.get("entityUrn") or ""
            if not urn or urn in self._seen_urns:
                continue

            # Commentary text extract
            commentary = el.get("commentary", {})
            text = ""
            if isinstance(commentary, dict):
                text_obj = commentary.get("text", {})
                if isinstance(text_obj, dict):
                    text = text_obj.get("text", "")
                elif isinstance(text_obj, str):
                    text = text_obj

            if not text:
                # Alternate schema fields
                text = el.get("text", {}).get("text", "") if isinstance(el.get("text"), dict) else ""

            if not text.strip():
                continue

            self._seen_urns.add(urn)
            new_guids.append(urn)
            title = _extract_title(text)
            post_url = f"https://www.linkedin.com/feed/update/{urn}"

            items.append(
                ConnectorItem(
                    title=title,
                    url=post_url,
                    body=text,
                    source=source_name,
                    fetched_at=now,
                    guid=urn,
                )
            )

        if self._db_conn is not None and new_guids:
            record_seen_guids(self._db_conn, source_name, new_guids)

        return ConnectorResult(source=source_name, items=items)

