"""Storage smoke tests — plain asserts, no pytest dependency.

Run: python tests/test_storage.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["CONTENT_MACHINE_HOME"] = tempfile.mkdtemp(prefix="cm_test_")

from content_machine.storage import db, paths  # noqa: E402


def test_tree() -> None:
    dirs = paths.ensure_tree()
    assert dirs["root"] == paths.home_root()
    for name in ("knowledge", "archive", "projects"):
        assert dirs[name].is_dir(), name
    # seeds copied
    assert (dirs["knowledge"] / "03_content-lessons.md").exists()
    # idempotent
    paths.ensure_tree()


def test_project_dir() -> None:
    d = paths.project_dir("2026-09-04_spike-01")
    assert (d / "iterations").is_dir()
    assert (d / "distribution").is_dir()
    for bad in ("../x", ".hidden", "a/b", ""):
        try:
            paths.project_dir(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"slug accepted: {bad!r}")


def test_schema_and_crud() -> None:
    conn = db.connect()
    conn.execute(
        "INSERT INTO spikes(id, category, hook_thesis) VALUES (?, ?, ?)",
        ("spike-01", "internal", "killing our top feature cut churn"),
    )
    conn.execute(
        "INSERT INTO transcripts(spike_id, path, word_count) VALUES (?, ?, ?)",
        ("spike-01", "projects/x/raw_transcript.md", 1200),
    )
    conn.execute(
        "INSERT INTO iterations(spike_id, iteration, draft_path, composite_raw, threshold_met)"
        " VALUES (?, ?, ?, ?, ?)",
        ("spike-01", 1, "projects/x/iterations/draft_v1.md", 8.2, 0),
    )
    conn.execute(
        "INSERT INTO judge_score_history(judge_slot, model_config, dimension, raw_score)"
        " VALUES (?, ?, ?, ?)",
        ("perell", "qwen3.7-plus", "narrative", 8.5),
    )
    conn.execute(
        "INSERT INTO lessons(rule_text, category, provenance_project)"
        " VALUES (?, ?, ?)",
        ("Never summarize the thesis in the final sentence.", "negative_constraint", "2026-09-04_spike-01"),
    )
    db.log_event(conn, "test_event", "detail")
    conn.commit()

    rows = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()
    assert rows["n"] >= 1
    row = conn.execute("SELECT composite_raw FROM iterations WHERE spike_id='spike-01'").fetchone()
    assert abs(row["composite_raw"] - 8.2) < 1e-9

    # FK enforced
    try:
        conn.execute("INSERT INTO transcripts(spike_id, path) VALUES ('ghost', 'x')")
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("FK not enforced")

    # lessons rule_text unique
    try:
        conn.execute(
            "INSERT INTO lessons(rule_text) VALUES (?)",
            ("Never summarize the thesis in the final sentence.",),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("lessons UNIQUE not enforced")
    conn.close()


def test_feed_cache_and_seen_items() -> None:
    conn = db.connect()
    # Feed cache CRUD
    db.update_feed_cache(conn, "https://example.com/rss", "etag-123", "Wed, 03 Sep 2026 00:00:00 GMT")
    etag, last_mod = db.get_feed_cache(conn, "https://example.com/rss")
    assert etag == "etag-123"
    assert last_mod == "Wed, 03 Sep 2026 00:00:00 GMT"

    # Seen guids
    db.record_seen_guids(conn, "https://example.com/rss", ["guid-1", "guid-2"])
    seen = db.get_seen_guids_for_feed(conn, "https://example.com/rss")
    assert seen == {"guid-1", "guid-2"}

    # Duplicate guid insert is safely ignored
    db.record_seen_guids(conn, "https://example.com/rss", ["guid-1", "guid-3"])
    seen = db.get_seen_guids_for_feed(conn, "https://example.com/rss")
    assert seen == {"guid-1", "guid-2", "guid-3"}
    conn.close()


def main() -> None:
    for fn in (test_tree, test_project_dir, test_schema_and_crud, test_feed_cache_and_seen_items):
        fn()
        print(f"PASS {fn.__name__}")
    print(f"ALL PASS (home={paths.home_root()})")



if __name__ == "__main__":
    main()
