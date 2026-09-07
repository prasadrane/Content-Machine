import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from content_machine.connectors.base import ConnectorItem, ConnectorResult
from content_machine.connectors.linkedin_session import LinkedInSessionManager


def test_session_manager_save_and_load(tmp_path):
    session_file = tmp_path / "linkedin_session.json"
    mgr = LinkedInSessionManager(session_file=session_file)

    assert mgr.get_saved_cookie() is None

    mgr.save_session("test-li-at-cookie-12345")
    assert mgr.get_saved_cookie() == "test-li-at-cookie-12345"

    # Verify JSON file structure
    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert data["li_at"] == "test-li-at-cookie-12345"
    assert "saved_at" in data


def test_session_manager_validation_success(tmp_path):
    session_file = tmp_path / "linkedin_session.json"
    mgr = LinkedInSessionManager(session_file=session_file)
    mgr.save_session("valid-cookie")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("requests.get", return_value=mock_resp):
        assert mgr.is_valid() is True
        assert mgr.get_valid_cookie() == "valid-cookie"


def test_session_manager_validation_failure_clears_invalid(tmp_path):
    session_file = tmp_path / "linkedin_session.json"
    mgr = LinkedInSessionManager(session_file=session_file)
    mgr.save_session("expired-cookie")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("requests.get", return_value=mock_resp):
        assert mgr.is_valid() is False
        assert mgr.get_valid_cookie() is None
from content_machine.connectors.linkedin_public import (
    LinkedInPublicBridge,
    normalize_linkedin_target,
    parse_public_posts_html,
)


def test_normalize_linkedin_target():
    assert normalize_linkedin_target("satyanadella") == "https://www.linkedin.com/in/satyanadella/recent-activity/all/"
    assert normalize_linkedin_target("in/satyanadella") == "https://www.linkedin.com/in/satyanadella/recent-activity/all/"
    assert normalize_linkedin_target("company/cloudflare") == "https://www.linkedin.com/company/cloudflare/posts/"
    assert normalize_linkedin_target("https://www.linkedin.com/in/satyanadella") == "https://www.linkedin.com/in/satyanadella/recent-activity/all/"
    assert normalize_linkedin_target("https://www.linkedin.com/company/netflix/posts") == "https://www.linkedin.com/company/netflix/posts/"


def test_parse_public_posts_html():
    sample_html = """
    <div class="feed-shared-update-v2" data-urn="urn:li:activity:71234567890">
      <div class="update-components-text">
        <span>Excited to announce our new memory allocator in Rust. We reduced p99 latency by 45%.</span>
      </div>
      <a class="app-aware-link" href="https://www.linkedin.com/feed/update/urn:li:activity:71234567890">View post</a>
    </div>
    <div class="feed-shared-update-v2" data-urn="urn:li:activity:71234567891">
      <div class="update-components-text">
        <span>Scaling an engineering org from 10 to 100 requires strict ownership boundaries.</span>
      </div>
      <a class="app-aware-link" href="https://www.linkedin.com/feed/update/urn:li:activity:71234567891">View post</a>
    </div>
    """
    items = parse_public_posts_html(sample_html, source="linkedin:satyanadella")
    assert len(items) == 2
    assert "Rust" in items[0].title or "Rust" in items[0].body
    assert "71234567890" in items[0].url
    assert items[0].source == "linkedin:satyanadella"
    assert "Scaling" in items[1].title or "Scaling" in items[1].body


def test_public_bridge_fetch_with_mocked_crawler():
    bridge = LinkedInPublicBridge("satyanadella")
    mock_items = [
        ConnectorItem(
            title="AI Systems Architecture",
            url="https://www.linkedin.com/feed/update/urn:li:activity:9999",
            body="Detailed insights on GPU clustering and transformer memory.",
            source="linkedin:satyanadella",
            fetched_at=None,
        )
    ]
    with patch.object(bridge, "_crawl_public_page", return_value=mock_items):
        res = bridge.fetch()
        assert len(res.items) == 1
        assert res.items[0].title == "AI Systems Architecture"
        assert res.source == "linkedin:satyanadella"
from content_machine.connectors.linkedin import LinkedInConnector
from content_machine.storage.db import connect


def test_linkedin_connector_auto_loads_saved_session(tmp_path):
    session_file = tmp_path / "linkedin_session.json"
    mgr = LinkedInSessionManager(session_file=session_file)
    mgr.save_session("session-cookie-xyz")

    with patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.is_valid", return_value=True), \
         patch("content_machine.connectors.linkedin.LinkedInSessionManager", return_value=mgr):
        connector = LinkedInConnector(li_at=None, profile=None)
        assert connector.li_at == "session-cookie-xyz"
        assert connector._public_bridge is None


def test_linkedin_connector_falls_back_to_public_bridge_when_no_cookie(tmp_path):
    mgr = LinkedInSessionManager(session_file=tmp_path / "empty.json")

    with patch("content_machine.connectors.linkedin.LinkedInSessionManager", return_value=mgr):
        # Should not raise ValueError when profile is given!
        connector = LinkedInConnector(li_at=None, profile="satyanadella")
        assert connector.li_at is None
        assert connector._public_bridge is not None
        assert connector._public_bridge.target == "satyanadella"


def test_linkedin_connector_deduplicates_via_db():
    conn = connect(":memory:")
    c = LinkedInConnector(li_at="dummy-cookie", profile="test-creator", db_conn=conn)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "elements": [
            {
                "urn": "urn:li:activity:111",
                "commentary": {"text": {"text": "Post 1: Systems engineering in Rust."}},
            },
            {
                "urn": "urn:li:activity:222",
                "commentary": {"text": {"text": "Post 2: Scaling teams to 50 engineers."}},
            },
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        res1 = c.fetch()
        assert len(res1.items) == 2

        # Check DB recorded both
        guids = {r["guid"] for r in conn.execute("SELECT guid FROM seen_feed_items").fetchall()}
        assert "urn:li:activity:111" in guids
        assert "urn:li:activity:222" in guids

        # Second fetch with a new instance on same DB:
        c2 = LinkedInConnector(li_at="dummy-cookie", profile="test-creator", db_conn=conn)
        res2 = c2.fetch()
        # Both posts were seen in DB, so 0 duplicates!
        assert len(res2.items) == 0
