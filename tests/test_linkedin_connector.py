"""Tests for LinkedIn connector (session cookie li_at based).

All tests are offline — HTTP requests to LinkedIn's API are mocked.
Follows TDD principles: tests written first.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


SAMPLE_VOYAGER_UPDATES_RESPONSE = {
    "elements": [
        {
            "urn": "urn:li:activity:7123456789012345678",
            "commentary": {
                "text": {
                    "text": "Most founders obsess over raising capital. I spent 3 years building in silence. Here is what happened to our churn rate: it dropped by 42% in 6 months."
                }
            },
            "actor": {
                "name": {
                    "text": "Jane Founder"
                }
            },
            "created": {
                "time": 1725450000000
            }
        },
        {
            "urn": "urn:li:activity:7123456789012345679",
            "commentary": {
                "text": {
                    "text": "Remote work didn't kill culture. Bad async communication did."
                }
            },
            "actor": {
                "name": {
                    "text": "Jane Founder"
                }
            },
            "created": {
                "time": 1725460000000
            }
        }
    ]
}


def _make_response(json_data: dict, status: int = 200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    r.text = json.dumps(json_data)
    r.raise_for_status = MagicMock()
    return r


class TestLinkedInConnector(unittest.TestCase):

    def _make_connector(self, li_at: str = "AQEDA_fake_cookie", profile: str | None = "jane-founder"):
        from content_machine.connectors.linkedin import LinkedInConnector
        return LinkedInConnector(li_at=li_at, profile=profile)

    def test_missing_li_at_raises_value_error(self):
        """Connector raises ValueError if li_at is empty or None."""
        from content_machine.connectors.linkedin import LinkedInConnector
        with self.assertRaises(ValueError):
            LinkedInConnector(li_at="")

    def test_headers_include_cookie_and_csrf_token(self):
        """Requests must include li_at cookie, JSESSIONID, and matching csrf-token."""
        conn = self._make_connector(li_at="my_secret_li_at")
        headers = conn._build_headers()
        self.assertIn("Cookie", headers)
        self.assertIn("li_at=my_secret_li_at", headers["Cookie"])
        self.assertIn("csrf-token", headers)
        self.assertIn("JSESSIONID", headers["Cookie"])
        self.assertEqual(headers["csrf-token"], conn.csrf_token)

    def test_fetch_profile_posts_parses_connector_items(self):
        """fetch() extracts posts into standard ConnectorItem objects."""
        conn = self._make_connector(profile="jane-founder")
        with patch("content_machine.connectors.linkedin.requests.get") as mock_get:
            mock_get.return_value = _make_response(SAMPLE_VOYAGER_UPDATES_RESPONSE)
            result = conn.fetch()

        self.assertEqual(len(result.items), 2)
        item1 = result.items[0]
        self.assertEqual(item1.guid, "urn:li:activity:7123456789012345678")
        self.assertIn("raising capital", item1.body)
        self.assertTrue(len(item1.title) > 0)
        self.assertEqual(result.source, "linkedin:jane-founder")

    def test_fetch_feed_when_no_profile_specified(self):
        """If profile is None, source becomes 'linkedin:feed' and feed endpoint is called."""
        conn = self._make_connector(profile=None)
        with patch("content_machine.connectors.linkedin.requests.get") as mock_get:
            mock_get.return_value = _make_response(SAMPLE_VOYAGER_UPDATES_RESPONSE)
            result = conn.fetch()

        self.assertEqual(result.source, "linkedin:feed")
        called_url = mock_get.call_args[0][0]
        self.assertIn("feed", called_url)

    def test_fetch_handles_empty_or_malformed_response_gracefully(self):
        """Malformed or empty elements list returns empty items list without crashing."""
        conn = self._make_connector()
        with patch("content_machine.connectors.linkedin.requests.get") as mock_get:
            mock_get.return_value = _make_response({"elements": []})
            result = conn.fetch()
        self.assertEqual(result.items, [])

    def test_fetch_deduplicates_within_run(self):
        """Duplicate URNs in elements list are deduplicated."""
        conn = self._make_connector()
        dup_data = {
            "elements": [
                SAMPLE_VOYAGER_UPDATES_RESPONSE["elements"][0],
                SAMPLE_VOYAGER_UPDATES_RESPONSE["elements"][0],
            ]
        }
        with patch("content_machine.connectors.linkedin.requests.get") as mock_get:
            mock_get.return_value = _make_response(dup_data)
            result = conn.fetch()
        self.assertEqual(len(result.items), 1)


if __name__ == "__main__":
    unittest.main()
