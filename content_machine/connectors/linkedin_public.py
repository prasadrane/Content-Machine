"""LinkedIn Public Bridge: Zero-auth public extractor for creators and company posts."""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from content_machine.connectors.base import BaseConnector, ConnectorItem, ConnectorResult

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    cleaned = _TAG_RE.sub(" ", raw)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split()).strip()


def normalize_linkedin_target(target: str) -> str:
    """Normalise any username, company slug, or URL into a direct LinkedIn activity URL."""
    t = target.strip()
    if t.startswith("http://") or t.startswith("https://"):
        # Strip trailing slashes
        clean_url = t.rstrip("/")
        if "/company/" in clean_url:
            return f"{clean_url}/posts/" if not clean_url.endswith("/posts") else f"{clean_url}/"
        if "/in/" in clean_url:
            if "/recent-activity" in clean_url:
                return f"{clean_url}/" if clean_url.endswith("/all") else f"{clean_url}/all/"
            return f"{clean_url}/recent-activity/all/"
        return f"{clean_url}/"

    clean_slug = t.lstrip("/")
    if clean_slug.startswith("company/"):
        return f"https://www.linkedin.com/{clean_slug.rstrip('/')}/posts/"
    if clean_slug.startswith("in/"):
        return f"https://www.linkedin.com/{clean_slug.rstrip('/')}/recent-activity/all/"
    return f"https://www.linkedin.com/in/{clean_slug}/recent-activity/all/"


def parse_public_posts_html(html_text: str, source: str = "linkedin:public") -> list[ConnectorItem]:
    """Parse public LinkedIn HTML feed page into a list of ConnectorItems."""
    from content_machine.connectors.linkedin import _extract_title

    items: list[ConnectorItem] = []
    now = datetime.now(tz=timezone.utc)

    # Strategy 1: Look for container blocks with data-urn
    container_pattern = re.compile(
        r'<div[^>]*data-urn=["\'](urn:li:activity:\d+)["\'][^>]*>(.*?)</div>\s*(?=<div[^>]*data-urn=|$)',
        re.DOTALL | re.IGNORECASE,
    )
    matches = container_pattern.findall(html_text)

    if matches:
        for urn, block in matches:
            body = _clean_text(block)
            if not body or len(body) < 15:
                continue
            title = _extract_title(body)
            url = f"https://www.linkedin.com/feed/update/{urn}"
            items.append(
                ConnectorItem(
                    title=title,
                    url=url,
                    body=body,
                    source=source,
                    fetched_at=now,
                )
            )

    # Strategy 2: Fallback for generic public post articles
    if not items:
        article_pattern = re.compile(
            r'<(?:article|div)[^>]*class=["\'][^"\']*(?:base-card|feed-shared-update-v2|main-feed-activity-card)[^"\']*["\'][^>]*>(.*?)</(?:article|div)>',
            re.DOTALL | re.IGNORECASE,
        )
        article_matches = article_pattern.findall(html_text)
        for idx, block in enumerate(article_matches):
            body = _clean_text(block)
            if not body or len(body) < 20:
                continue
            title = _extract_title(body)
            # Try to extract href inside block
            link_match = re.search(r'href=["\'](https://www\.linkedin\.com/feed/update/urn:li:activity:\d+)[^"\']*["\']', block)
            url = link_match.group(1) if link_match else f"https://www.linkedin.com/feed/update/item-{idx}"
            items.append(
                ConnectorItem(
                    title=title,
                    url=url,
                    body=body,
                    source=source,
                    fetched_at=now,
                )
            )

    return items


class LinkedInPublicBridge(BaseConnector):
    """Zero-auth public creator and company post extractor using headless Playwright."""

    def __init__(self, target: str, max_items: int = 20):
        self.target = target.strip()
        self.url = normalize_linkedin_target(self.target)
        self.max_items = max_items
        self._source_name = f"linkedin:{self.target}"

    def _crawl_public_page(self) -> list[ConnectorItem]:
        """Crawl the public LinkedIn activity page using headless Playwright."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright is not available for LinkedInPublicBridge.")
            return []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                })
                page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                # Scroll down slightly to trigger hydration
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(2000)
                html_content = page.content()
                browser.close()
                return parse_public_posts_html(html_content, source=self._source_name)
        except Exception as e:
            logger.warning("LinkedIn public crawl failed for %s: %s", self.url, e)
            return []

    def fetch(self, **_kwargs) -> ConnectorResult:
        """Fetch latest public posts."""
        items = self._crawl_public_page()
        if self.max_items and len(items) > self.max_items:
            items = items[:self.max_items]
        return ConnectorResult(source=self._source_name, items=items)
