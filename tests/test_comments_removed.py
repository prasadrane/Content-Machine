"""Retirement contract for the unused LinkedIn comments feature."""

import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

# Storage must be isolated before importing application/storage modules.
os.environ["CONTENT_MACHINE_HOME"] = tempfile.mkdtemp(prefix="cm_retired_comments_")


class TestCommentsRemoved(unittest.TestCase):
    def test_comments_endpoints_are_unavailable(self):
        from fastapi.testclient import TestClient
        from content_machine.api.app import app

        client = TestClient(app)
        self.assertEqual(client.get("/api/comments/history").status_code, 404)
        self.assertIn(client.post("/api/comments/generate", json={"post_content": "An engineering post."}).status_code, (404, 405))
        self.assertFalse(any(path.startswith("/api/comments") for path in app.openapi()["paths"]))

    def test_comments_command_is_unavailable(self):
        from content_machine.__main__ import _build_parser

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            _build_parser().parse_args(["comment", "--post", "An engineering post."])
        self.assertEqual(raised.exception.code, 2)

    def test_fresh_storage_has_no_comments_table(self):
        from content_machine.storage.db import connect

        conn = connect(":memory:")
        try:
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name = 'comments'").fetchone())
        finally:
            conn.close()

    def test_existing_comment_history_is_preserved(self):
        from content_machine.storage.db import init_db

        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE comments (id TEXT PRIMARY KEY, final_comment TEXT, created_at TEXT)")
            conn.execute("INSERT INTO comments VALUES ('old', 'Historical content', '2026-01-01')")
            init_db(conn)
            self.assertEqual(conn.execute("SELECT final_comment FROM comments WHERE id = 'old'").fetchone()[0], "Historical content")
        finally:
            conn.close()

    def test_demo_seed_does_not_reintroduce_comments(self):
        from content_machine.storage.db import connect
        from content_machine.demo_seed import seed_demo

        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"CONTENT_MACHINE_HOME": home}):
            conn = connect(":memory:")
            try:
                self.assertNotIn("comments", seed_demo(conn))
                self.assertNotIn("comments", seed_demo(conn))
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name = 'comments'").fetchone())
            finally:
                conn.close()

    def test_comment_humanize_channel_is_unavailable(self):
        from pydantic import ValidationError
        from content_machine.schemas import HumanizeRequest

        with self.assertRaises(ValidationError):
            HumanizeRequest(text="An engineering post.", channel="linkedin_comment")
