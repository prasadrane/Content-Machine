"""Offline coverage for owner-scoped discovery and source provenance."""
from datetime import datetime, timezone
from contextlib import closing
import sqlite3
from unittest import TestCase
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from content_machine.connectors.base import ConnectorItem, ConnectorResult
from content_machine.workflow import discovery
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.discovery_routes import router
from content_machine.workflow.http import get_workflow_connection
from content_machine.workflow.schemas import Principal
from content_machine.workflow.settings import SETTINGS_MIGRATION_STATEMENTS

NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
OWNER = Principal(owner_id="owner-a", mode="hosted_verified")
SOURCES = [
    {"source_id": "source-a", "kind": "rss", "name": "First feed", "url": "https://one.example/feed", "enabled": True},
    {"source_id": "source-b", "kind": "rss", "name": "Second feed", "url": "https://two.example/feed", "enabled": True},
]


def item(title, url, body):
    return ConnectorItem(title=title, url=url, body=body, source="feed", fetched_at=NOW)


class DiscoveryTest(TestCase):
    def test_results_retain_source_text_and_partial_failure(self):
        first = ConnectorResult(source="First feed", items=[
            item("Article", "https://one.example/post", "Exact excerpt\nwith detail"),
            item("Title only", "https://one.example/title", ""),
        ])
        fetch = Mock(side_effect=[first, RuntimeError("private exception details")])
        with patch.object(discovery, "list_sources", return_value=SOURCES) as sources:
            result = discovery.refresh(None, OWNER, fetch)
        sources.assert_called_once_with(None, OWNER, enabled_only=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0], {
            "source_id": "source-a", "source_name": "First feed",
            "title": "Article", "url": "https://one.example/post",
            "excerpt": "Exact excerpt\nwith detail", "fetched_at": "2026-11-06T12:00:00.000Z",
        })
        self.assertEqual(result["items"][1]["excerpt"], "")
        self.assertEqual(result["errors"][0]["source_id"], "source-b")
        self.assertNotIn("private exception details", str(result))

    def test_unconfigured_fetcher_and_no_enabled_sources_are_distinct(self):
        with patch.object(discovery, "list_sources", return_value=SOURCES):
            result = discovery.refresh(None, OWNER, None)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["items"], [])
        with patch.object(discovery, "list_sources", return_value=[]):
            result = discovery.refresh(None, OWNER, None)
        self.assertEqual(result["status"], "no_sources")

    def test_empty_not_modified_and_unsupported_sources_are_not_misrepresented(self):
        with patch.object(discovery, "list_sources", return_value=[SOURCES[0]]):
            empty = discovery.refresh(None, OWNER, lambda source: ConnectorResult(source="feed", items=[]))
            unchanged = discovery.refresh(None, OWNER, lambda source: ConnectorResult(source="feed", not_modified=True))
        self.assertEqual(empty["status"], "empty")
        self.assertEqual(unchanged["status"], "history_unavailable")
        unsupported = {**SOURCES[0], "kind": "unknown"}
        fetch = Mock()
        with patch.object(discovery, "list_sources", return_value=[unsupported]):
            result = discovery.refresh(None, OWNER, fetch)
        self.assertEqual(result["status"], "failed")
        fetch.assert_not_called()

    def test_http_boundary_authenticates_before_access_and_uses_only_injected_fetcher(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/workflow")
        app.dependency_overrides[resolve_principal] = lambda: OWNER
        app.dependency_overrides[get_workflow_connection] = lambda: None
        fetch = Mock(return_value=ConnectorResult(source="feed", items=[item("A", "https://one.example/a", "A fact")]))
        app.state.workflow_discovery_fetcher = fetch
        with patch.object(discovery, "list_sources", return_value=[SOURCES[0]]) as sources:
            with TestClient(app) as client:
                result = client.post("/api/workflow/discovery/refresh")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["items"][0]["source_id"], "source-a")
        sources.assert_called_once_with(None, OWNER, enabled_only=True)
        fetch.assert_called_once_with(SOURCES[0])

    def test_missing_authentication_prevents_source_and_fetch_access(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/workflow")
        def reject():
            raise HTTPException(status_code=401)
        app.dependency_overrides[resolve_principal] = reject
        app.state.workflow_discovery_fetcher = Mock()
        with patch.object(discovery, "list_sources") as sources:
            with TestClient(app) as client:
                response = client.post("/api/workflow/discovery/refresh")
        self.assertEqual(response.status_code, 401)
        sources.assert_not_called()
        app.state.workflow_discovery_fetcher.assert_not_called()

    def test_bad_source_data_does_not_hide_a_good_item(self):
        batch = ConnectorResult(source="feed", items=[
            item("", "https://one.example/empty", "Unusable title"),
            item("   ", "https://one.example/blank", "Blank title"),
            item("Useful", "https://one.example/useful", "Original text"),
        ])
        with patch.object(discovery, "list_sources", return_value=[SOURCES[0]]):
            result = discovery.refresh(None, OWNER, lambda source: batch)
        self.assertEqual(result["status"], "partial")
        self.assertEqual([entry["title"] for entry in result["items"]], ["Useful"])
        self.assertEqual(result["errors"][0]["source_id"], "source-a")

    def test_unsafe_urls_and_duplicates_do_not_produce_attachable_references(self):
        batch = ConnectorResult(source="feed", items=[
            item("Bad link", "javascript:alert(1)", ""),
            item("Bad port", "https://one.example:notaport/a", ""),
            item("Bad host", "https://bad host.example/a", ""),
            item("Good link", "https://one.example/a", "A"),
            item("Duplicate", "https://one.example/a", "A"),
        ])
        with patch.object(discovery, "list_sources", return_value=[SOURCES[0]]):
            result = discovery.refresh(None, OWNER, lambda source: batch)
        self.assertEqual(result["status"], "partial")
        self.assertEqual([entry["title"] for entry in result["items"]], ["Good link"])

    def test_mixed_refresh_identifies_sources_without_retrievable_history(self):
        responses = [
            ConnectorResult(source="first", not_modified=True),
            ConnectorResult(source="second", items=[item("New", "https://two.example/a", "A")]),
        ]
        with patch.object(discovery, "list_sources", return_value=SOURCES):
            result = discovery.refresh(None, OWNER, Mock(side_effect=responses))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["unchanged_sources"], [{"source_id": "source-a", "source_name": "First feed"}])
        self.assertFalse(result["history_available"])

    def test_only_enabled_sources_owned_by_the_principal_reach_the_fetcher(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.row_factory = sqlite3.Row
            for statement in SETTINGS_MIGRATION_STATEMENTS:
                conn.execute(statement)
            conn.executemany(
                "INSERT INTO workflow_sources (source_id, owner_id, kind, name, url, "
                "enabled, revision, created_at, updated_at) VALUES (?, ?, 'rss', ?, ?, ?, 1, ?, ?)",
                [
                    ("a", "owner-a", "Owned enabled", "https://one.example/feed", 1, "now", "now"),
                    ("b", "owner-a", "Owned disabled", "https://two.example/feed", 0, "now", "now"),
                    ("c", "owner-b", "Other owner", "https://three.example/feed", 1, "now", "now"),
                ],
            )
            fetch = Mock(return_value=ConnectorResult(source="feed"))
            self.assertEqual(discovery.refresh(conn, OWNER, fetch)["status"], "empty")
            self.assertEqual([call.args[0]["source_id"] for call in fetch.call_args_list], ["a"])
