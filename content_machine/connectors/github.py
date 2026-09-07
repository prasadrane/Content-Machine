"""GitHub connector — fetches closed issues and PRs via REST API (plan v2 §2.1).

Auth: Personal Access Token (PAT) with `repo` (read) scope.
Rate limit: 5,000 req/hr authenticated.  Daily pull uses < 1% of budget.
Pagination: follows Link: rel="next" headers automatically.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import requests

from content_machine.connectors.base import BaseConnector, ConnectorItem, ConnectorResult

_GH_API = "https://api.github.com"
_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _parse_link_next(link_header: str) -> Optional[str]:
    """Extract the 'next' URL from a GitHub Link header, or None."""
    m = _LINK_RE.search(link_header)
    return m.group(1) if m else None


def _iso(dt: datetime) -> str:
    """Format a datetime as ISO 8601 UTC string for the GitHub API."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GitHubConnector(BaseConnector):
    """Fetches closed issues and pull requests from a single GitHub repo.

    Args:
        repo: The ``owner/repo`` slug.
        pat:  A GitHub Personal Access Token with read access to the repo.
    """

    def __init__(self, repo: str, pat: str):
        self.repo = repo
        self._pat = pat

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get_all_pages(
        self, url: str, params: dict
    ) -> list[dict]:
        """GET url with params, following pagination until no 'next' link."""
        items: list[dict] = []
        current_url: Optional[str] = url
        current_params: Optional[dict] = params

        while current_url:
            resp = requests.get(
                current_url,
                headers=self._headers(),
                params=current_params,
                timeout=30,
            )
            resp.raise_for_status()
            items.extend(resp.json())

            link = resp.headers.get("Link", "")
            next_url = _parse_link_next(link)
            # After the first page, params are encoded in the URL
            current_url = next_url
            current_params = None  # params already in next_url query string

        return items

    def fetch(self, since: Optional[datetime] = None, **_kwargs) -> ConnectorResult:
        """Return closed issues and PRs updated since *since* (or all if None).

        Args:
            since: Only return items updated at or after this timestamp.
        """
        url = f"{_GH_API}/repos/{self.repo}/issues"
        params: dict = {
            "state": "closed",
            "per_page": 100,
        }
        if since is not None:
            params["since"] = _iso(since)

        raw_items = self._get_all_pages(url, params)
        source = f"github:{self.repo}"
        now = datetime.now(tz=timezone.utc)

        connector_items: list[ConnectorItem] = []
        for raw in raw_items:
            connector_items.append(
                ConnectorItem(
                    title=raw.get("title", ""),
                    url=raw.get("html_url", ""),
                    body=raw.get("body") or "",
                    source=source,
                    fetched_at=now,
                    guid=raw.get("html_url", ""),
                )
            )

        return ConnectorResult(source=source, items=connector_items)
