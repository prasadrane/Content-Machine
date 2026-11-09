"""Idempotency-key bounds, strict consent, stale-tab CAS, RSS limits and source caps."""
import os
import time
import unittest
from unittest.mock import Mock, patch

from workflow_action_fixtures import ActionApiFixture
import test_workflow_settings
import test_workflow_preferences
import test_workflow_postgres_repository

from content_machine.api.app import app
from content_machine.connectors.base import ConnectorResult
from content_machine.workflow import discovery, safe_rss, safe_rss_process
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.postgres_repository import PostgresWorkflowRepository
from content_machine.workflow.schemas import ItemCreate, ItemPatch, Principal

LONG_KEY = "k" * 201


class LongKeyTest(ActionApiFixture, unittest.TestCase):
    def test_oversized_key_is_rejected_before_any_row_or_provider_call(self):
        previous = getattr(app.state, "workflow_reviewer", None)
        self.addCleanup(setattr, app.state, "workflow_reviewer", previous)
        provider = Mock()
        app.state.workflow_reviewer = provider
        item, _ = self.saved_item()
        item_id = item["item_id"]
        before = (self.fixture._count("workflow_operations"), self._counts())
        for name in ("review", "skip-review"):
            response = self.action(item_id, name, {"expected_revision": 2}, LONG_KEY)
            self.assertEqual(response.status_code, 422, (name, response.text))
            self.assertEqual(response.json()["code"], "idempotency_key_too_long")
        self.assertEqual((self.fixture._count("workflow_operations"), self._counts()), before)
        provider.assert_not_called()
        ok = self.action(item_id, "skip-review", {"expected_revision": 2}, "k" * 200)
        self.assertEqual(ok.status_code, 200, ok.text)


class StrictConsentTest(ActionApiFixture, unittest.TestCase):
    def test_consent_and_revision_must_be_real_json_types(self):
        item, text = self.saved_item()
        item_id = item["item_id"]
        digest = self._digest([text])
        for label, override in (("str1", {"consent": "1"}), ("strtrue", {"consent": "true"}),
                                ("int1", {"consent": 1}), ("rev", {"expected_revision": "2"}),
                                ("revfloat", {"expected_revision": 2.0})):
            body = {"expected_revision": 2, "artifact_digest": digest, "consent": True, **override}
            response = self.action(item_id, "approve", body, f"strict-{label}")
            self.assertEqual(response.status_code, 422, (label, response.text))
        self.assertIsNone(self._item(item_id)["active_approval_id"])
        accepted = self._approve(item_id, 2, [text], "strict-ok")
        self.assertEqual(accepted.status_code, 200, accepted.text)


class StaleTabTest(ActionApiFixture, unittest.TestCase):
    def test_optional_expected_updated_at_guards_title_stage_approve_and_skip(self):
        item, text = self.saved_item()
        item_id, stamp = item["item_id"], item["updated_at"]
        time.sleep(0.01)
        other = self.fixture._patch(item_id, {"expected_revision": 2, "title": "Other tab"})
        self.assertEqual(other.status_code, 200, other.text)
        self.assertEqual(other.json()["item"]["working_revision"], 2)
        # Backward compatible: without expected_updated_at a plain save still works.
        legacy = self.fixture._patch(item_id, {"expected_revision": 2, "title": "Legacy"})
        self.assertEqual(legacy.status_code, 200)
        current = self._item(item_id)
        stale = self.fixture._patch(item_id, {"expected_revision": 2, "title": "Stale",
                                              "expected_updated_at": stamp})
        self.assertEqual((stale.status_code, stale.json()["code"]), (409, "revision_conflict"))
        self.assertEqual(stale.json()["updated_at"], current["updated_at"])
        self.assertEqual(self._item(item_id)["title"], "Legacy")
        stale_stage = self.fixture._patch(item_id, {"expected_revision": 2, "stage": "approve",
                                                    "expected_updated_at": stamp})
        self.assertEqual(stale_stage.status_code, 409)
        body = {"expected_revision": 2, "artifact_digest": self._digest([text]), "consent": True,
                "expected_updated_at": stamp}
        self.assertEqual(self.action(item_id, "approve", body, "stale-approve").status_code, 409)
        stale_skip = self.action(item_id, "skip-review",
                                 {"expected_revision": 2, "expected_updated_at": stamp}, "stale-skip")
        self.assertEqual(stale_skip.status_code, 409)
        self.assertEqual(self._item(item_id)["stage"], "draft_review")
        fresh = self.fixture._patch(item_id, {"expected_revision": 2, "title": "Fresh",
                                              "expected_updated_at": current["updated_at"]})
        self.assertEqual(fresh.status_code, 200, fresh.text)
        now = fresh.json()["item"]["updated_at"]
        skipped = self.action(item_id, "skip-review",
                              {"expected_revision": 2, "expected_updated_at": now}, "fresh-skip")
        self.assertEqual(skipped.status_code, 200, skipped.text)


class SafeRssLimitsTest(unittest.TestCase):
    def test_only_ports_80_and_443_are_allowed(self):
        for url in ("http://93.184.216.34/f", "https://93.184.216.34/f",
                    "https://93.184.216.34:443/f", "http://93.184.216.34:80/f"):
            safe_rss._parse_url(url)
        for url in ("http://93.184.216.34:8080/f", "https://93.184.216.34:8443/f",
                    "http://93.184.216.34:22/f", "http://93.184.216.34:65535/f"):
            with self.assertRaises(safe_rss.FetchError, msg=url):
                safe_rss._parse_url(url)

    def test_child_environment_passes_tls_and_path_variables_only_off_windows(self):
        env = {"SSL_CERT_FILE": "/c/ca.pem", "SSL_CERT_DIR": "/c", "LANG": "C.UTF-8", "PATH": "/bin",
               "SECRET_TOKEN": "x", "HTTPS_PROXY": "http://p"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(safe_rss_process.os, "name", "posix"):
                posix = safe_rss_process._environment()
            with patch.object(safe_rss_process.os, "name", "nt"):
                windows = safe_rss_process._environment()
        self.assertEqual(posix, {k: env[k] for k in ("SSL_CERT_FILE", "SSL_CERT_DIR", "LANG", "PATH")})
        self.assertEqual(windows, {})


class SourceCapTest(test_workflow_settings.SettingsApiTest):
    def test_twenty_sources_per_owner_then_clear_error(self):
        for index in range(20):
            created = self.request("POST", "/sources", {"kind": "rss", "name": f"Feed {index}",
                                   "url": f"https://f{index}.example/rss", "enabled": True}, f"src-{index}")
            self.assertEqual(created.status_code, 201, created.text)
        extra = self.request("POST", "/sources", {"kind": "rss", "name": "One more",
                             "url": "https://extra.example/rss", "enabled": True}, "src-extra")
        self.assertEqual((extra.status_code, extra.json()["code"]), (422, "source_limit_reached"))
        self.assertEqual(len(self.client.get("/api/workflow/settings").json()["sources"]), 20)


def _sources(count):
    return [{"source_id": f"s{i}", "kind": "rss", "name": f"Feed {i}",
             "url": f"https://f{i}.example/r", "enabled": True} for i in range(count)]


class DiscoveryDeadlineTest(unittest.TestCase):
    owner = Principal(owner_id="owner-a", mode="hosted_verified")

    def test_deadline_stops_fetching_and_flags_partial_results(self):
        ticks = iter([0.0, 1.0, 50.0, 50.0, 50.0])
        fetch = Mock(return_value=ConnectorResult(source="Feed 0", items=[]))
        with patch.object(discovery, "list_sources", return_value=_sources(3)):
            result = discovery.refresh(None, self.owner, fetch, deadline_seconds=45.0,
                                       clock=lambda: next(ticks))
        self.assertEqual(fetch.call_count, 1)
        self.assertTrue(result["incomplete"])
        self.assertEqual([e["source_id"] for e in result["errors"]], ["s1", "s2"])

    def test_fast_refresh_is_not_flagged(self):
        fetch = Mock(return_value=ConnectorResult(source="Feed", items=[]))
        with patch.object(discovery, "list_sources", return_value=_sources(1)):
            result = discovery.refresh(None, self.owner, fetch)
        self.assertNotIn("incomplete", result)


class LongKeyFamiliesTest(ActionApiFixture, unittest.TestCase):
    def test_restore_and_adapt_reject_oversized_key_without_rows(self):
        item, _ = self.saved_item()
        before = self._counts()
        restore = self.action(item["item_id"], "restore",
                              {"expected_revision": 2, "version_id": "ver_x"}, LONG_KEY)
        adapt = self.action(item["item_id"], "adapt", {"source_version_id": "ver_x",
                            "destination": "instagram", "format": "instagram_caption"}, LONG_KEY)
        for response in (restore, adapt):
            self.assertEqual((response.status_code, response.json()["code"]),
                             (422, "idempotency_key_too_long"))
        self.assertEqual(self._counts(), before)


class LongKeyPreferencesTest(test_workflow_preferences.PreferencesApiTest):
    def test_oversized_key_writes_no_preference(self):
        response = self.post("", {"text": "Prefer concrete examples.", "consent": True}, LONG_KEY)
        self.assertEqual((response.status_code, response.json()["code"]),
                         (422, "idempotency_key_too_long"))
        self.assertEqual(self.listing(), [])


class LongKeyPostgresTest(unittest.TestCase):
    def test_repository_rejects_oversized_key_before_any_sql(self):
        conn = test_workflow_postgres_repository.ScriptedConnection()
        repo = PostgresWorkflowRepository(conn)
        principal = Principal(owner_id=test_workflow_postgres_repository.OWNER, mode="hosted_verified")
        payload = ItemCreate(title="Idea", destination="linkedin", format="linkedin_post")
        with self.assertRaises(WorkflowError) as caught:
            repo.create_item(principal, payload, request_id=LONG_KEY)
        self.assertEqual(caught.exception.code, "idempotency_key_too_long")
        with self.assertRaises(WorkflowError):
            repo.save_item(principal, "item-1", ItemPatch(expected_revision=1, title="T"), request_id=LONG_KEY)
        self.assertEqual(conn.events, [])
