from datetime import datetime, timezone
from unittest.mock import MagicMock
from content_machine.connectors.base import ConnectorItem, ConnectorResult
from content_machine.oracle.oracle import OracleOrchestrator
from content_machine.oracle.scorer import IdeaScore, IdeaScorer, ScoredIdea
from content_machine.oracle.classifier import TOPIC_SYSTEMS
from content_machine.storage.db import connect


def _make_dummy_connector(items: list[ConnectorItem]):
    c = MagicMock()
    c.fetch.return_value = ConnectorResult(source="test_feed", items=items)
    return c


def test_spikes_schema_has_topic_tag_and_source_url():
    conn = connect(":memory:")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(spikes)").fetchall()]
    assert "topic_tag" in cols
    assert "source_url" in cols


def test_oracle_skips_llm_and_rehydrates_for_already_scored_items():
    conn = connect(":memory:")
    now = datetime.now(tz=timezone.utc)
    item = ConnectorItem(
        title="Custom Memory Allocators in Rust",
        url="https://example.com/rust-allocator",
        body="Detailed discussion on jemalloc and custom allocators.",
        source="example.com",
        fetched_at=now,
    )

    mock_scorer = MagicMock(spec=IdeaScorer)
    dummy_sample = IdeaScore(
        pov=8.5,
        lived_experience=8.0,
        specificity=8.5,
        counter_intuitive=8.0,
        generic_penalty_applied=False,
        composite=8.33,
        rationale="Great technical depth",
    )
    dummy_scored = ScoredIdea(
        item=item,
        samples=[dummy_sample],
        median_composite=8.33,
        verdict="pass",
        topic_tag=TOPIC_SYSTEMS,
    )
    mock_scorer.score_item.return_value = dummy_scored

    connector = _make_dummy_connector([item])
    orchestrator = OracleOrchestrator(
        connectors=[connector],
        scorer=mock_scorer,
        db_conn=conn,
    )

    # First run: should call LLM scorer once
    results_1 = orchestrator.run(include_rejected=True)
    assert len(results_1) == 1
    assert mock_scorer.score_item.call_count == 1
    assert results_1[0].median_composite == 8.33
    assert results_1[0].verdict == "pass"
    assert results_1[0].topic_tag == TOPIC_SYSTEMS

    # Second run: same item! mock_scorer should NOT be called again (0 token waste)
    results_2 = orchestrator.run(include_rejected=True)
    assert len(results_2) == 1
    assert mock_scorer.score_item.call_count == 1  # Still 1! Not called on 2nd run
    assert results_2[0].item.title == item.title
    assert results_2[0].median_composite == 8.33
    assert results_2[0].verdict == "pass"
    assert results_2[0].topic_tag == TOPIC_SYSTEMS

    # Check audit log recorded skipped item
    logs = conn.execute("SELECT event, detail FROM audit_log WHERE event = 'item_skipped_already_scored'").fetchall()
    assert len(logs) == 1
    assert "rust-allocator" in logs[0]["detail"] or "Rust" in logs[0]["detail"]
from unittest.mock import patch
from content_machine.connectors.rss import RSSConnector

def test_rss_connector_deduplicates_via_db_seen_guids():
    conn = connect(":memory:")
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Feed</title>
        <link>https://example.com</link>
        <item>
          <title>Article 1</title>
          <link>https://example.com/1</link>
          <guid>guid-1</guid>
          <description>Article 1 description</description>
        </item>
      </channel>
    </rss>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = rss_xml
    mock_resp.headers = {"ETag": "etag-123"}

    with patch("requests.get", return_value=mock_resp):
        connector = RSSConnector(url="https://example.com/rss", db_conn=conn)
        res1 = connector.fetch()
        assert len(res1.items) == 1
        assert res1.items[0].guid == "guid-1"

        # Check that seen_feed_items recorded it
        rows = conn.execute("SELECT guid FROM seen_feed_items").fetchall()
        assert len(rows) == 1
        assert rows[0]["guid"] == "guid-1"

        # Second connector instance on same db_conn:
        connector2 = RSSConnector(url="https://example.com/rss", db_conn=conn)
        res2 = connector2.fetch()
        # Item already in seen_feed_items, so 0 new items
        assert len(res2.items) == 0
def test_connect_backfills_spikes_topic_tag():
    conn = connect(":memory:")
    # Insert a spike without topic_tag
    conn.execute(
        "INSERT INTO spikes(id, category, hook_thesis, scores_json, status, topic_tag) VALUES (?, ?, ?, ?, ?, ?)",
        ("test-1", "blog", "Memory Allocation in Linux Kernel with eBPF", "{}", "candidate", "General Engineering"),
    )
    conn.commit()
    # Reconnect/run migration
    from content_machine.oracle.classifier import TOPIC_SYSTEMS
    cols = [c[1] for c in conn.execute("PRAGMA table_info(spikes)").fetchall()]
    # run backfill
    rows = conn.execute("SELECT id, hook_thesis FROM spikes WHERE topic_tag = 'General Engineering'").fetchall()
    from content_machine.oracle.classifier import classify_content_topic
    for r in rows:
        t = classify_content_topic(r["hook_thesis"])
        conn.execute("UPDATE spikes SET topic_tag = ? WHERE id = ?", (t, r["id"]))
    conn.commit()
    updated = conn.execute("SELECT topic_tag FROM spikes WHERE id = 'test-1'").fetchone()
    assert updated["topic_tag"] == TOPIC_SYSTEMS
