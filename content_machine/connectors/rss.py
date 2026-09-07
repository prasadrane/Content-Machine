"""RSS / Atom feed connector (plan v2 §2.1).

Fetches a single feed URL, respects ETag / If-Modified-Since for
conditional requests, and deduplicates items by GUID across calls.
Requires: requests (stdlib xml.etree.ElementTree for parsing).
"""

from __future__ import annotations

import email.utils
import html
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlparse

import requests

from content_machine.connectors.base import BaseConnector, ConnectorItem, ConnectorResult

# Atom and Content modules namespaces
_ATOM_NS = "http://www.w3.org/2005/Atom"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_DC_DATE_NS = "http://purl.org/dc/elements/1.1/"

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style|svg)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_BOILERPLATE_PATTERNS = [
    re.compile(r"The post .*? appeared first on .*?\.?", re.IGNORECASE),
    re.compile(r"This article appeared first on .*?\.?", re.IGNORECASE),
]


def parse_feed_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse RFC 2822 or ISO 8601 feed date string into a UTC datetime."""
    if not date_str:
        return None
    date_str = date_str.strip()
    # RFC 2822 (RSS 2.0 pubDate)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # ISO 8601 (Atom updated/published or dc:date)
    try:
        iso_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    return None



def clean_html_content(raw_html: str) -> str:
    """Strip HTML markup, decode entities, and remove RSS syndication boilerplate."""
    if not raw_html:
        return ""
    text = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    for pat in _BOILERPLATE_PATTERNS:
        text = pat.sub(" ", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)
    return clean_text.strip()


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if len(el) > 0:
        inner = (el.text or "") + "".join(
            ET.tostring(child, encoding="unicode") for child in el
        )
        return inner.strip()
    return (el.text or "").strip()



def _parse_rss(root: ET.Element) -> list[dict]:
    """Extract items from an RSS 2.0 document."""
    items = []
    for item in root.findall(".//item"):
        encoded_el = item.find(f"{{{_CONTENT_NS}}}encoded")
        body = _text(encoded_el) if encoded_el is not None else ""
        if not body:
            body = _text(item.find("description"))
        date_el = item.find("pubDate")
        if date_el is None:
            date_el = item.find(f"{{{_DC_DATE_NS}}}date")
        pub_date = parse_feed_date(_text(date_el)) if date_el is not None else None
        guid_el = item.find("guid")
        if guid_el is None:
            guid_el = item.find("link")
        guid = _text(guid_el)
        items.append(
            {
                "title": _text(item.find("title")),
                "url": _text(item.find("link")),
                "body": body,
                "guid": guid,
                "published_at": pub_date,
            }
        )
    return items


def _parse_atom(root: ET.Element) -> list[dict]:
    """Extract entries from an Atom 1.0 document."""
    items = []
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        link_el = entry.find(f"{{{_ATOM_NS}}}link")
        url = link_el.get("href", "") if link_el is not None else ""
        id_el = entry.find(f"{{{_ATOM_NS}}}id")
        guid = _text(id_el) if id_el is not None else url
        summary_el = entry.find(f"{{{_ATOM_NS}}}summary")
        if summary_el is None:
            summary_el = entry.find(f"{{{_ATOM_NS}}}content")
        summary = _text(summary_el)
        date_el = entry.find(f"{{{_ATOM_NS}}}published")
        if date_el is None:
            date_el = entry.find(f"{{{_ATOM_NS}}}updated")
        pub_date = parse_feed_date(_text(date_el)) if date_el is not None else None
        items.append(
            {
                "title": _text(entry.find(f"{{{_ATOM_NS}}}title")),
                "url": url,
                "body": summary,
                "guid": guid,
                "published_at": pub_date,
            }
        )
    return items




def _parse_feed(xml_text: str) -> list[dict]:
    """Auto-detect RSS vs Atom and return a normalised list of item dicts."""
    root = ET.fromstring(xml_text)
    # Atom feeds have the Atom namespace on the root <feed> element
    if root.tag == f"{{{_ATOM_NS}}}feed" or root.tag == "feed":
        return _parse_atom(root)
    return _parse_rss(root)


class RSSConnector(BaseConnector):
    """Fetches a single RSS or Atom feed with conditional-GET support.

    Supports SQLite persistence for seen GUIDs and ETags across runs when
    db_conn is passed.
    """

    def __init__(
        self,
        url: str,
        source_name: Optional[str] = None,
        db_conn: Optional[sqlite3.Connection] = None,
        max_age_days: Optional[int] = None,
        max_items: int = 25,
    ):
        self.url = url
        self._source_name: str = source_name or urlparse(url).hostname or url
        self._db_conn = db_conn
        self.max_age_days = max_age_days
        self.max_items = max_items
        self._etag: Optional[str] = None
        self._last_modified: Optional[str] = None
        self._seen_guids: set[str] = set()

        if self._db_conn is not None:
            from content_machine.storage.db import get_feed_cache, get_seen_guids_for_feed
            etag, last_mod = get_feed_cache(self._db_conn, self.url)
            self._etag = etag
            self._last_modified = last_mod
            self._seen_guids = get_seen_guids_for_feed(self._db_conn, self.url)

    def fetch(
        self,
        max_age_days: Optional[int] = None,
        max_items: Optional[int] = None,
        **_kwargs,
    ) -> ConnectorResult:
        """Pull new items from the feed.

        Filters items older than max_age_days (when present) and caps
        the total items returned to max_items.
        """
        effective_max_age = max_age_days if max_age_days is not None else self.max_age_days
        effective_max_items = max_items if max_items is not None else self.max_items
        cutoff = (
            datetime.now(tz=timezone.utc) - timedelta(days=effective_max_age)
            if effective_max_age is not None
            else None
        )

        headers: dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 ContentMachine/2.0"
            )
        }
        if self._etag:
            headers["If-None-Match"] = self._etag
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified

        resp = requests.get(self.url, headers=headers, timeout=30)

        if resp.status_code == 304:
            return ConnectorResult(source=self._source_name, items=[], not_modified=True)

        resp.raise_for_status()

        # Cache conditional-GET tokens
        if "ETag" in resp.headers:
            self._etag = resp.headers["ETag"]
        if "Last-Modified" in resp.headers:
            self._last_modified = resp.headers["Last-Modified"]

        if self._db_conn is not None:
            from content_machine.storage.db import update_feed_cache
            update_feed_cache(self._db_conn, self.url, self._etag, self._last_modified)

        raw_items = _parse_feed(resp.text)
        now = datetime.now(tz=timezone.utc)
        new_items: list[ConnectorItem] = []
        new_guids: list[str] = []

        for raw in raw_items:
            guid = raw["guid"] or raw["url"]
            if guid in self._seen_guids:
                continue

            pub_dt = raw.get("published_at")
            if cutoff is not None and pub_dt is not None and pub_dt < cutoff:
                continue

            self._seen_guids.add(guid)
            new_guids.append(guid)
            cleaned_body = clean_html_content(raw["body"])
            new_items.append(
                ConnectorItem(
                    title=raw["title"],
                    url=raw["url"],
                    body=cleaned_body,
                    source=self._source_name,
                    fetched_at=now,
                    guid=guid,
                    published_at=pub_dt,
                )
            )
            if len(new_items) >= effective_max_items:
                break

        if self._db_conn is not None and new_guids:
            from content_machine.storage.db import record_seen_guids
            record_seen_guids(self._db_conn, self.url, new_guids)

        return ConnectorResult(source=self._source_name, items=new_items)


