import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

from content_machine.storage.db import connect
from content_machine.api.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_history.db"
    conn = connect(test_db)
    
    # Insert test spike
    conn.execute(
        "INSERT INTO spikes (id, category, hook_thesis, scores_json, status) VALUES (?, ?, ?, ?, ?)",
        ("test-spike", "test", "test thesis", "{}", "in_council"),
    )
    
    # Insert two iterations: iter 1 has lower score, iter 2 has higher score
    review_iter1 = {
        "iteration": 1,
        "draft": "Draft version 1 text",
        "scores": {"perell": {"narrative": 7.0, "velocity": 7.0, "depth": 7.0, "slop_purity": 7.0}},
        "required_actions": ["action 1"],
    }
    review_iter2 = {
        "iteration": 2,
        "draft": "Draft version 2 peak text",
        "scores": {"perell": {"narrative": 9.0, "velocity": 9.0, "depth": 9.0, "slop_purity": 9.0}},
        "required_actions": [],
    }
    
    conn.execute(
        """
        INSERT INTO iterations (spike_id, iteration, draft_path, council_review_json, composite_raw, threshold_met, draft_content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("test-spike", 1, "(unsaved) iteration 1", json.dumps(review_iter1), 7.25, 0, "Draft version 1 text"),
    )
    conn.execute(
        """
        INSERT INTO iterations (spike_id, iteration, draft_path, council_review_json, composite_raw, threshold_met, draft_content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("test-spike", 2, "(unsaved) iteration 2", json.dumps(review_iter2), 8.85, 0, "Draft version 2 peak text"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("content_machine.api.app._make_db", lambda: connect(test_db))
    return TestClient(app)


def test_council_history_endpoint(client):
    res = client.get("/api/council/history/test-spike")
    assert res.status_code == 200
    data = res.json()
    assert data["spike_id"] == "test-spike"
    assert data["best"] is not None
    assert data["best"]["iteration"] == 2
    assert data["best"]["score"] == 8.85
    assert data["best"]["draft"] == "Draft version 2 peak text"
    assert len(data["history"]) == 2


def test_council_history_not_found(client):
    res = client.get("/api/council/history/non-existent-spike")
    assert res.status_code == 200
    data = res.json()
    assert data["spike_id"] == "non-existent-spike"
    assert data["best"] is None
    assert len(data["history"]) == 0


def test_council_spikes_list(client):
    res = client.get("/api/council/spikes")
    assert res.status_code == 200
    spikes = res.json()
    assert any(s["spike_id"] == "test-spike" and s["peak_score"] == 8.85 for s in spikes)
