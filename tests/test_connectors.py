"""Tests for Oracle connectors (step 4 of §14 build order).

All tests are offline — network is mocked.  Set CONTENT_MACHINE_LIVE=1
to run live smoke tests (requires real tokens in env).
"""

from __future__ import annotations

import json
import os
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ---------------------------------------------------------------------------
# RSS connector tests
# ---------------------------------------------------------------------------

SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test feed</description>
    <item>
      <title>Item One</title>
      <link>https://example.com/1</link>
      <description>First item body</description>
      <pubDate>Thu, 04 Sep 2026 10:00:00 +0000</pubDate>
      <guid>https://example.com/1</guid>
    </item>
    <item>
      <title>Item Two</title>
      <link>https://example.com/2</link>
      <description>Second item body</description>
      <pubDate>Thu, 04 Sep 2026 11:00:00 +0000</pubDate>
      <guid>https://example.com/2</guid>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM = """\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test</title>
  <link href="https://atom.example.com"/>
  <entry>
    <id>urn:uuid:atom-1</id>
    <title>Atom Item</title>
    <link href="https://atom.example.com/a1"/>
    <summary>Atom summary</summary>
    <updated>2026-09-04T12:00:00Z</updated>
  </entry>
</feed>
"""

SAMPLE_DEVTO_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>DEV Community</title>
    <link>https://dev.to</link>
    <description>The most constructive and inclusive social network for software developers.</description>
    <item>
      <title><![CDATA[Stop Hand-Rolling Validation in Go]]></title>
      <dc:creator><![CDATA[Jane Dev]]></dc:creator>
      <description><![CDATA[<p>If you have written Go HTTP handlers, you know the pain of repetitive struct checks.</p>]]></description>
      <link>https://dev.to/janedev/stop-hand-rolling-validation-in-go-123</link>
      <guid isPermaLink="false">https://dev.to/janedev/stop-hand-rolling-validation-in-go-123</guid>
      <pubDate>Thu, 04 Sep 2026 14:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""



SAMPLE_CONTENT_ENCODED_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Cloudflare Blog</title>
    <link>https://blog.cloudflare.com</link>
    <item>
      <title>Mitigating DDoS at Anycast Edge</title>
      <link>https://blog.cloudflare.com/ddos-edge</link>
      <description>Short summary</description>
      <content:encoded><![CDATA[<p>Full in-depth engineering breakdown of our XDP pipeline and BPF filters.</p>]]></content:encoded>
      <guid>https://blog.cloudflare.com/ddos-edge</guid>
    </item>
  </channel>
</rss>
"""


def _make_http_response(body: str, status: int = 200, headers: dict | None = None):
    """Return a mock requests.Response."""
    r = MagicMock()
    r.status_code = status
    r.text = body
    r.content = body.encode()
    r.headers = headers or {}
    r.raise_for_status = MagicMock()
    return r



class TestRSSConnector(unittest.TestCase):

    def _make_connector(self, url: str = "https://example.com/feed.rss"):
        from content_machine.connectors.rss import RSSConnector
        return RSSConnector(url=url)

    def test_fetch_returns_items_from_rss_feed(self):
        """Fetching a valid RSS feed yields one ConnectorResult per <item>."""
        conn = self._make_connector()
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            result = conn.fetch()
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].title, "Item One")
        self.assertEqual(result.items[0].url, "https://example.com/1")
        self.assertIsNotNone(result.items[0].body)

    def test_fetch_returns_items_from_atom_feed(self):
        """Fetching a valid Atom feed also yields items."""
        conn = self._make_connector(url="https://atom.example.com/feed")
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_ATOM)
            result = conn.fetch()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, "Atom Item")

    def test_fetch_parses_devto_style_feed(self):
        """Fetching a dev.to style CDATA and namespace RSS feed extracts title and body."""
        conn = self._make_connector(url="https://dev.to/feed")
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_DEVTO_RSS)
            result = conn.fetch()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, "Stop Hand-Rolling Validation in Go")
        self.assertIn("Go HTTP handlers", result.items[0].body)
        self.assertEqual(result.source, "dev.to")

    def test_fetch_parses_content_encoded_in_engineering_blogs(self):
        """Fetching feeds with content:encoded prefers full content over short summary."""
        conn = self._make_connector(url="https://blog.cloudflare.com/rss")
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_CONTENT_ENCODED_RSS)
            result = conn.fetch()
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, "Mitigating DDoS at Anycast Edge")
        self.assertIn("Full in-depth engineering breakdown of our XDP pipeline", result.items[0].body)


    def test_fetch_sends_etag_on_second_call(self):
        """Second fetch sends If-None-Match header when ETag was returned."""
        conn = self._make_connector()
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            # First call returns an ETag
            mock_get.return_value = _make_http_response(
                SAMPLE_RSS, headers={"ETag": '"abc123"'}
            )
            conn.fetch()
            # Second call
            mock_get.return_value = _make_http_response(
                SAMPLE_RSS, headers={"ETag": '"abc123"'}
            )
            conn.fetch()

        _, kwargs = mock_get.call_args
        headers_sent = kwargs.get("headers", {})
        self.assertIn("If-None-Match", headers_sent)
        self.assertEqual(headers_sent["If-None-Match"], '"abc123"')

    def test_fetch_304_returns_empty_items(self):
        """HTTP 304 Not Modified returns an empty item list (feed unchanged)."""
        conn = self._make_connector()
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response("", status=304)
            result = conn.fetch()
        self.assertEqual(result.items, [])
        self.assertTrue(result.not_modified)

    def test_fetch_deduplicates_by_guid(self):
        """Items with a guid already seen in a previous fetch are skipped."""
        conn = self._make_connector()
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            first = conn.fetch()
            # Second fetch with same feed — same GUIDs
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            second = conn.fetch()

        self.assertEqual(len(first.items), 2)
        self.assertEqual(len(second.items), 0)  # all already seen

    def test_source_name_defaults_to_hostname(self):
        """source attribute is derived from the feed URL hostname."""
        conn = self._make_connector("https://blog.example.com/rss")
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            result = conn.fetch()
        self.assertEqual(result.source, "blog.example.com")

    def test_clean_html_content_strips_tags_and_decodes_entities(self):
        """clean_html_content cleans html tags and decodes entities properly."""
        from content_machine.connectors.rss import clean_html_content
        raw = "<p>Here is an <b>exciting</b> story &amp; lesson!</p><script>alert(1)</script><img src='pixel.png'/>"
        cleaned = clean_html_content(raw)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("alert(1)", cleaned)
        self.assertIn("Here is an exciting story & lesson!", cleaned)

    def test_clean_html_content_strips_boilerplate(self):
        """clean_html_content strips common feed disclaimers/boilerplates."""
        from content_machine.connectors.rss import clean_html_content
        raw = "Real insight here.<p>The post Title appeared first on TechBlog.</p>"
        cleaned = clean_html_content(raw)
        self.assertIn("Real insight here.", cleaned)
        self.assertNotIn("appeared first on", cleaned)

    def test_clean_html_applied_to_feed_items(self):
        """ConnectorItem.body has clean_html_content applied."""
        conn = self._make_connector()
        html_rss = SAMPLE_RSS.replace("First item body", "<p>First <b>item</b> body &amp; more.</p>")
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(html_rss)
            result = conn.fetch()
        self.assertEqual(result.items[0].body, "First item body & more.")

    def test_fetch_includes_user_agent_header(self):
        """RSSConnector sends a browser-compatible User-Agent to avoid 429 rate limiting."""
        conn = self._make_connector()
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            conn.fetch()
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            headers = call_kwargs.get("headers", {})
            self.assertIn("User-Agent", headers)
            self.assertIn("ContentMachine", headers["User-Agent"])

    def test_persistent_seen_guids_across_instances(self):
        """Using db_conn, a second RSSConnector instance skips items already seen by the first."""
        from content_machine.connectors.rss import RSSConnector
        from content_machine.storage.db import connect
        db_conn = connect(":memory:")

        # First instance fetches SAMPLE_RSS
        conn1 = RSSConnector("https://example.com/feed.rss", db_conn=db_conn)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            res1 = conn1.fetch()
        self.assertEqual(len(res1.items), 2)

        # Brand new instance with same db_conn fetches again
        conn2 = RSSConnector("https://example.com/feed.rss", db_conn=db_conn)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS)
            res2 = conn2.fetch()
        self.assertEqual(len(res2.items), 0)

    def test_persistent_feed_cache_sends_stored_etag(self):
        """Using db_conn, a second RSSConnector instance loads etag from db and sends If-None-Match."""
        from content_machine.connectors.rss import RSSConnector
        from content_machine.storage.db import connect
        db_conn = connect(":memory:")

        conn1 = RSSConnector("https://example.com/feed.rss", db_conn=db_conn)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(SAMPLE_RSS, headers={"ETag": '"etag-xyz"'})
            conn1.fetch()

        conn2 = RSSConnector("https://example.com/feed.rss", db_conn=db_conn)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response("", status=304)
            conn2.fetch()
            _, kwargs = mock_get.call_args
            self.assertEqual(kwargs.get("headers", {}).get("If-None-Match"), '"etag-xyz"')

    def test_parse_feed_date_parses_rfc2822_and_iso(self):
        """parse_feed_date correctly handles RFC 2822 and ISO 8601 timestamps."""
        from content_machine.connectors.rss import parse_feed_date
        d1 = parse_feed_date("Thu, 04 Sep 2026 10:00:00 +0000")
        self.assertIsNotNone(d1)
        self.assertEqual(d1.year, 2026)
        self.assertEqual(d1.month, 9)
        self.assertEqual(d1.day, 4)

        d2 = parse_feed_date("2026-08-30T15:30:00Z")
        self.assertIsNotNone(d2)
        self.assertEqual(d2.year, 2026)
        self.assertEqual(d2.day, 30)

        self.assertIsNone(parse_feed_date("not-a-date"))
        self.assertIsNone(parse_feed_date(None))

    def test_rss_connector_filters_by_max_age_days(self):
        """Items older than max_age_days are filtered out."""
        from content_machine.connectors.rss import RSSConnector
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S +0000")
        old_date = (now - timedelta(days=25)).strftime("%a, %d %b %Y %H:%M:%S +0000")

        xml_feed = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Date Test</title>
    <item>
      <title>Recent Post</title>
      <link>https://example.com/recent</link>
      <description>Recent</description>
      <pubDate>{recent_date}</pubDate>
      <guid>1</guid>
    </item>
    <item>
      <title>Old Post</title>
      <link>https://example.com/old</link>
      <description>Old</description>
      <pubDate>{old_date}</pubDate>
      <guid>2</guid>
    </item>
  </channel>
</rss>
"""
        conn = RSSConnector("https://example.com/feed.rss", max_age_days=10)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(xml_feed)
            res = conn.fetch()

        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].title, "Recent Post")
        self.assertIsNotNone(res.items[0].published_at)

    def test_rss_connector_caps_at_max_items(self):
        """RSSConnector returns at most max_items items."""
        from content_machine.connectors.rss import RSSConnector

        items_xml = "".join(
            f"<item><title>Item {i}</title><link>https://example.com/{i}</link><description>d</description><guid>{i}</guid></item>"
            for i in range(35)
        )
        xml_feed = f'<?xml version="1.0"?><rss version="2.0"><channel>{items_xml}</channel></rss>'

        conn = RSSConnector("https://example.com/feed.rss", max_items=25)
        with patch("content_machine.connectors.rss.requests.get") as mock_get:
            mock_get.return_value = _make_http_response(xml_feed)
            res = conn.fetch()

        self.assertEqual(len(res.items), 25)




# ---------------------------------------------------------------------------
# GitHub connector tests
# ---------------------------------------------------------------------------

SAMPLE_ISSUE = {
    "number": 42,
    "title": "Fix the thing",
    "html_url": "https://github.com/org/repo/issues/42",
    "body": "Detailed description of the bug.",
    "state": "closed",
    "closed_at": "2026-09-04T09:00:00Z",
    "updated_at": "2026-09-04T09:00:00Z",
    "pull_request": None,
}

SAMPLE_PR = {
    "number": 99,
    "title": "Add feature X",
    "html_url": "https://github.com/org/repo/pull/99",
    "body": "Implements feature X.",
    "state": "closed",
    "closed_at": "2026-09-04T08:00:00Z",
    "updated_at": "2026-09-04T08:00:00Z",
    "pull_request": {"url": "https://api.github.com/repos/org/repo/pulls/99"},
}


def _make_github_response(items: list, status: int = 200, link_next: str | None = None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = items
    r.raise_for_status = MagicMock()
    headers = {}
    if link_next:
        headers["Link"] = f'<{link_next}>; rel="next"'
    r.headers = headers
    return r


class TestGitHubConnector(unittest.TestCase):

    def _make_connector(self, repo: str = "org/repo", pat: str = "ghp_fake"):
        from content_machine.connectors.github import GitHubConnector
        return GitHubConnector(repo=repo, pat=pat)

    def test_fetch_returns_closed_issues_and_prs(self):
        """Fetching a repo returns closed issues and PRs as ConnectorItems."""
        conn = self._make_connector()
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response(
                [SAMPLE_ISSUE, SAMPLE_PR]
            )
            result = conn.fetch()
        self.assertEqual(len(result.items), 2)
        titles = {item.title for item in result.items}
        self.assertIn("Fix the thing", titles)
        self.assertIn("Add feature X", titles)

    def test_fetch_sends_authorization_header(self):
        """PAT is sent as Authorization: Bearer <token>."""
        conn = self._make_connector(pat="ghp_secret")
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response([])
            conn.fetch()
        _, kwargs = mock_get.call_args
        self.assertIn("Authorization", kwargs["headers"])
        self.assertIn("ghp_secret", kwargs["headers"]["Authorization"])

    def test_fetch_filters_by_since(self):
        """since parameter is forwarded to the GitHub API as a query param."""
        since = datetime(2026, 9, 1, tzinfo=timezone.utc)
        conn = self._make_connector()
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response([])
            conn.fetch(since=since)
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        self.assertIn("since", params)
        self.assertIn("2026-09-01", params["since"])

    def test_fetch_follows_pagination(self):
        """Connector follows Link: rel='next' headers to retrieve all pages."""
        conn = self._make_connector()
        page2_url = "https://api.github.com/repos/org/repo/issues?page=2"
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.side_effect = [
                _make_github_response([SAMPLE_ISSUE], link_next=page2_url),
                _make_github_response([SAMPLE_PR]),
            ]
            result = conn.fetch()
        self.assertEqual(len(result.items), 2)
        self.assertEqual(mock_get.call_count, 2)

    def test_source_name_is_repo_slug(self):
        """source attribute is the repo slug 'org/repo'."""
        conn = self._make_connector(repo="myorg/myrepo")
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response([])
            result = conn.fetch()
        self.assertEqual(result.source, "github:myorg/myrepo")

    def test_item_url_is_html_url(self):
        """ConnectorItem.url points to the human-readable GitHub page."""
        conn = self._make_connector()
        with patch("content_machine.connectors.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response([SAMPLE_ISSUE])
            result = conn.fetch()
        self.assertEqual(result.items[0].url, SAMPLE_ISSUE["html_url"])


# ---------------------------------------------------------------------------
# Base schema tests
# ---------------------------------------------------------------------------

class TestConnectorResult(unittest.TestCase):

    def test_connector_result_has_required_fields(self):
        """ConnectorResult must carry source, items list, and not_modified flag."""
        from content_machine.connectors.base import ConnectorResult, ConnectorItem
        item = ConnectorItem(
            title="T", url="https://x.com", body="b", source="s",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        result = ConnectorResult(source="test", items=[item])
        self.assertEqual(result.source, "test")
        self.assertEqual(len(result.items), 1)
        self.assertFalse(result.not_modified)

    def test_connector_item_requires_title_url_body(self):
        """ConnectorItem must have title, url, and body fields."""
        from content_machine.connectors.base import ConnectorItem
        item = ConnectorItem(
            title="Hello",
            url="https://example.com",
            body="content",
            source="rss",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        self.assertEqual(item.title, "Hello")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestConnectorResult, TestRSSConnector, TestGitHubConnector]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    for t in result.skipped:
        print(f"SKIP {t[0].id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)
