import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Isolate CONTENT_MACHINE_HOME before importing content_machine modules
_TMP_DIR = tempfile.mkdtemp(prefix="cm_test_dist_hist_")
os.environ["CONTENT_MACHINE_HOME"] = _TMP_DIR

from fastapi.testclient import TestClient
from content_machine.api.app import app
from content_machine.api.app import app
from content_machine.storage.db import connect
from content_machine.storage.paths import project_dir, home_root


class TestDistributeHistory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cm_test_dist_hist_case_")
        os.environ["CONTENT_MACHINE_HOME"] = self.tmp_dir
        self.db_conn = connect()
        self.client = TestClient(app)

    def tearDown(self):
        self.db_conn.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_distribute_history_empty(self):
        res = self.client.get("/api/distribute/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["items"], [])

    def test_distribute_history_from_council_spikes(self):
        # Insert spike and iterations into DB
        self.db_conn.execute(
            "INSERT INTO spikes (id, category, hook_thesis) VALUES (?, ?, ?)",
            ("spike-perf", "engineering", "Post about Redis memory allocation"),
        )
        self.db_conn.execute(
            """
            INSERT INTO iterations (spike_id, iteration, draft_path, composite_raw, threshold_met, draft_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("spike-perf", 1, "(unsaved)", 7.5, 0, "Rough draft v1", "2026-09-01T10:00:00Z"),
        )
        self.db_conn.execute(
            """
            INSERT INTO iterations (spike_id, iteration, draft_path, composite_raw, threshold_met, draft_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("spike-perf", 2, "(unsaved)", 8.6, 1, "Peak verified post content for Redis memory", "2026-09-02T12:00:00Z"),
        )
        self.db_conn.commit()

        res = self.client.get("/api/distribute/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["slug"], "spike-perf")
        self.assertEqual(item["title"], "Post about Redis memory allocation")
        self.assertEqual(item["peak_score"], 8.6)
        self.assertEqual(item["anchor_text"], "Peak verified post content for Redis memory")
        self.assertFalse(item["has_bundle"])
        self.assertEqual(item["source"], "council")

    def test_distribute_history_from_disk_project(self):
        # Create a project on disk with distribution files
        pdir = project_dir("cloud-dns-spike", create=True)
        dist_dir = pdir / "distribution"
        (dist_dir / "anchor.md").write_text("Anchor post text about DNS incident", encoding="utf-8")
        (dist_dir / "linkedin.md").write_text("LinkedIn version of DNS post", encoding="utf-8")
        (dist_dir / "x_thread.md").write_text("1/ Thread version of DNS post", encoding="utf-8")

        res = self.client.get("/api/distribute/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["slug"], "cloud-dns-spike")
        self.assertEqual(item["anchor_text"], "Anchor post text about DNS incident")
        self.assertTrue(item["has_bundle"])
        self.assertEqual(item["source"], "distributed")
        self.assertIn("linkedin", item["available_formats"])
        self.assertIn("x_thread", item["available_formats"])
        self.assertEqual(item["bundle"]["linkedin"], "LinkedIn version of DNS post")

    def test_distribute_run_saves_anchor_and_shows_in_history(self):
        # Mock engine to return simple bundle
        with patch("content_machine.api.app.DistributionEngine") as mock_engine_cls:
            mock_engine = mock_engine_cls.return_value
            mock_engine.generate_all.return_value = {
                "linkedin": "Generated LinkedIn text",
                "x_thread": "Generated X thread text",
            }
            def fake_save_bundle(slug, bundle, anchor_post=None):
                pdir = project_dir(slug, create=True)
                ddir = pdir / "distribution"
                if anchor_post:
                    (ddir / "anchor.md").write_text(anchor_post, encoding="utf-8")
                for k, v in bundle.items():
                    (ddir / f"{k}.md").write_text(v, encoding="utf-8")
                return ddir

            mock_engine.save_bundle.side_effect = fake_save_bundle

            res = self.client.post(
                "/api/distribute/run",
                json={
                    "anchor_post": "Verified anchor post text that is long enough",
                    "project_slug": "my-dist-post",
                    "enabled_formats": ["linkedin", "x_thread"],
                },
            )
            self.assertEqual(res.status_code, 200)

        # Now verify GET /api/distribute/history returns it
        h_res = self.client.get("/api/distribute/history")
        self.assertEqual(h_res.status_code, 200)
        h_data = h_res.json()
        self.assertEqual(h_data["total"], 1)
        item = h_data["items"][0]
        self.assertEqual(item["slug"], "my-dist-post")
        self.assertEqual(item["anchor_text"], "Verified anchor post text that is long enough")
        self.assertTrue(item["has_bundle"])
        self.assertIn("linkedin", item["available_formats"])


if __name__ == "__main__":
    unittest.main()
