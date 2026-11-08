"""Owner-scoped settings API tests using disposable SQLite storage."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.http import workflow_error_response, workflow_validation_response
from content_machine.workflow.schemas import Principal
from content_machine.workflow.settings import SETTINGS_MIGRATION_STATEMENTS, list_sources
from content_machine.workflow.settings_routes import router


class SettingsApiTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory(prefix="cm-settings-")
        self.addCleanup(self.home.cleanup)
        self.path = Path(self.home.name) / "test.db"
        with closing(connect(self.path)) as conn:
            for statement in SETTINGS_MIGRATION_STATEMENTS:
                conn.execute(statement)
            conn.commit()
        self.owner = Principal(owner_id="owner-a", mode="hosted_verified")
        self.app = FastAPI()
        self.app.add_exception_handler(WorkflowError, lambda request, error: workflow_error_response(error))
        self.app.add_exception_handler(RequestValidationError, lambda request, error: workflow_validation_response(error))
        self.app.include_router(router, prefix="/api/workflow")
        self.app.state.workflow_authenticator = lambda request: self.owner
        self.transactional = False

        def factory():
            conn = connect(self.path)
            if self.transactional:
                conn.execute("BEGIN")
            return conn

        self.app.state.workflow_connection_factory = factory
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def request(self, method, path, body, key):
        return self.client.request(method, f"/api/workflow/settings{path}", json=body,
                                   headers={"Idempotency-Key": key})

    def test_blank_profiles_are_private_and_save_exact_facts(self):
        blank = self.client.get("/api/workflow/settings")
        self.assertEqual(blank.status_code, 200)
        self.assertEqual(blank.json()["profile"],
                         {"name": "", "role": "", "bio": "", "revision": 0, "updated_at": None})
        self.assertEqual(blank.json()["sources"], [])
        payload = {"name": "  Ada  ", "role": "Engineer", "bio": "First line\nSecond line  ",
                   "expected_revision": 0}
        saved = self.request("PUT", "/profile", payload, "profile-save")
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["profile"]["bio"], payload["bio"])
        self.assertEqual(saved.json()["profile"]["name"], payload["name"])
        self.assertEqual(saved.json()["profile"]["revision"], 1)
        self.assertEqual(self.request("PUT", "/profile", payload, "profile-save").json(), saved.json())
        conflict = self.request("PUT", "/profile", {**payload, "name": "Other"}, "profile-save")
        self.assertEqual((conflict.status_code, conflict.json()["code"]), (409, "idempotency_conflict"))
        stale = self.request("PUT", "/profile", payload, "stale")
        self.assertEqual((stale.status_code, stale.json()["code"]), (409, "revision_conflict"))
        self.owner = Principal(owner_id="owner-b", mode="hosted_verified")
        self.assertEqual(self.client.get("/api/workflow/settings").json()["profile"]["name"], "")
        self.assertEqual(self.client.get("/api/workflow/settings").json()["sources"], [])
        self.owner = Principal(owner_id="owner-a", mode="hosted_verified")
        self.assertEqual(self.client.get("/api/workflow/settings").json()["profile"], saved.json()["profile"])

    def test_source_updates_are_owner_scoped_and_preserve_other_sources(self):
        first = self.request("POST", "/sources", {"kind": "rss", "name": "Engineering", "url": "https://example.com/feed", "enabled": True}, "source-one")
        second = self.request("POST", "/sources", {"kind": "rss", "name": "Database", "url": "https://example.org/rss", "enabled": True}, "source-two")
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        source = first.json()["source"]
        self.assertEqual(self.request("POST", "/sources", {"kind": "rss", "name": "Engineering", "url": "https://example.com/feed", "enabled": True}, "source-one").json(), first.json())
        update = self.request("PATCH", f"/sources/{source['source_id']}",
                              {"expected_revision": 1, "enabled": False}, "disable")
        self.assertEqual(update.status_code, 200, update.text)
        self.assertFalse(update.json()["source"]["enabled"])
        self.assertEqual(update.json()["source"]["revision"], 2)
        sources = self.client.get("/api/workflow/settings").json()["sources"]
        self.assertEqual(len(sources), 2)
        self.assertEqual(next(s for s in sources if s["source_id"] == second.json()["source"]["source_id"]), second.json()["source"])
        with closing(connect(self.path)) as conn:
            self.assertEqual(len(list_sources(conn, self.owner, enabled_only=True)), 1)
        self.owner = Principal(owner_id="owner-b", mode="hosted_verified")
        denied = self.request("PATCH", f"/sources/{source['source_id']}", {"expected_revision": 2, "name": "Spoofed"}, "foreign")
        self.assertEqual((denied.status_code, denied.json()["code"]), (404, "source_not_found"))
        self.assertEqual(self.client.get("/api/workflow/settings").json()["sources"], [])

    def test_validation_rejects_bad_urls_forged_owner_and_blank_key(self):
        for url in ("file:///private", "javascript:alert(1)", "https://user:password@example.com/feed", "https://", "https://example.com/rss?client_secret=private", "https://example.com/rss?api-key=private"):
            response = self.request("POST", "/sources", {"kind": "rss", "name": "Feed", "url": url, "enabled": True}, f"bad-{url}")
            self.assertEqual(response.status_code, 422, url)
        forged = self.request("PUT", "/profile", {"name": "x", "role": "", "bio": "", "expected_revision": 0, "owner_id": "owner-b"}, "forged")
        self.assertEqual(forged.status_code, 422)
        blank = self.client.put("/api/workflow/settings/profile", json={"name": "x", "role": "", "bio": "", "expected_revision": 0})
        self.assertEqual(blank.status_code, 422)
        self.assertEqual(self.client.get("/api/workflow/settings").json()["profile"]["revision"], 0)

    def test_failed_outer_commit_rolls_back_save_and_idempotency_record(self):
        with closing(connect(self.path)) as conn:
            conn.executescript("CREATE TABLE settings_parent (id INTEGER PRIMARY KEY);"
                               "CREATE TABLE settings_child (parent_id INTEGER REFERENCES settings_parent(id) DEFERRABLE INITIALLY DEFERRED);"
                               "CREATE TRIGGER fail_profile AFTER INSERT ON workflow_profiles BEGIN INSERT INTO settings_child VALUES (999); END;")
            conn.commit()
        self.transactional = True
        payload = {"name": "Ada", "role": "", "bio": "", "expected_revision": 0}
        failed = self.request("PUT", "/profile", payload, "failed-save")
        self.assertEqual(failed.status_code, 500)
        with closing(connect(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_profiles").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_idempotency WHERE request_id = 'failed-save'").fetchone()[0], 0)
            conn.execute("DROP TRIGGER fail_profile")
            conn.commit()
        self.assertEqual(self.request("PUT", "/profile", payload, "failed-save").status_code, 200)

    def test_failed_source_commit_does_not_acknowledge_or_create_a_duplicate(self):
        with closing(connect(self.path)) as conn:
            conn.executescript("CREATE TABLE source_parent (id INTEGER PRIMARY KEY);"
                               "CREATE TABLE source_child (parent_id INTEGER REFERENCES source_parent(id) DEFERRABLE INITIALLY DEFERRED);"
                               "CREATE TRIGGER fail_source AFTER INSERT ON workflow_sources BEGIN INSERT INTO source_child VALUES (999); END;")
            conn.commit()
        self.transactional = True
        payload = {"kind": "rss", "name": "Engineering", "url": "https://example.com/feed", "enabled": True}
        self.assertEqual(self.request("POST", "/sources", payload, "failed-create").status_code, 500)
        with closing(connect(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_sources").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_idempotency WHERE request_id = 'failed-create'").fetchone()[0], 0)
            conn.execute("DROP TRIGGER fail_source")
            conn.commit()
        created = self.request("POST", "/sources", payload, "failed-create")
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(self.request("POST", "/sources", payload, "failed-create").json(), created.json())
        self.assertEqual(len(self.client.get("/api/workflow/settings").json()["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
