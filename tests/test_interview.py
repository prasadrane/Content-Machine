"""Tests for Subsystem 2: Topic Briefing & Interview / Perspective Intake (plan v2 §3).

Tests verify:
- Topic briefing generation (summary + persona questions)
- Fallback question handling
- Grounded draft synthesis with persona responses, notes, and active lessons
- Transcript persistence to disk and SQLite
- FastAPI /api/interview/* endpoints
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from content_machine.schemas import (
    InterviewQuestion,
    TopicBriefing,
)


class TestInterviewEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        os.environ["CONTENT_MACHINE_HOME"] = self.tmp_dir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_generate_briefing_returns_structured_briefing(self):
        """generate_briefing calls router with TopicBriefing schema and returns structured briefing."""
        from content_machine.interview.engine import InterviewEngine

        mock_router = MagicMock()
        mock_briefing = TopicBriefing(
            summary="Engineers are debating whether to ditch microservices for modular monoliths.",
            core_conflict="Operational overhead vs distributed team autonomy.",
            questions=[
                InterviewQuestion(
                    persona="Tim Ferriss",
                    focus="Tactical mechanics",
                    question="What exact infrastructure tool or migration step proved most difficult?",
                ),
                InterviewQuestion(
                    persona="Larry King",
                    focus="Bottom line",
                    question="What was the single biggest metric change after the architecture pivot?",
                ),
            ],
        )
        mock_router.complete.return_value = mock_briefing

        engine = InterviewEngine(router=mock_router, scanner_model="qwen3.8-flash")
        result = engine.generate_briefing(
            title="Why We Migrated Back to Monolith",
            url="https://example.com/monolith",
            body="Article body about microservices latency and maintenance cost.",
            topic_tag="Architecture",
        )

        self.assertEqual(result.summary, mock_briefing.summary)
        self.assertEqual(result.core_conflict, mock_briefing.core_conflict)
        self.assertEqual(len(result.questions), 2)
        self.assertEqual(result.questions[0].persona, "Tim Ferriss")

    def test_synthesize_draft_incorporates_operator_perspective(self):
        """synthesize_draft merges briefing, operator responses, and notes into an initial draft."""
        from content_machine.interview.engine import InterviewEngine

        mock_router = MagicMock()
        mock_router.complete.return_value = (
            "# Why Microservices Burned Our Team\n\n"
            "Last quarter we killed 14 microservices and saved $18,000/mo in AWS NAT gateway fees.\n\n"
            "Here is the exact migration playbook we executed."
        )

        engine = InterviewEngine(router=mock_router, writer_model="qwen3.8-max")

        responses = [
            {
                "persona": "Tim Ferriss",
                "question": "What exact tool caused the most pain?",
                "answer": "Kafka partition rebalancing during deploys.",
            },
            {
                "persona": "Larry King",
                "question": "What was the final metric?",
                "answer": "P99 latency dropped from 420ms to 48ms.",
            },
        ]

        result = engine.synthesize_draft(
            topic_title="Microservices Migration",
            topic_summary="Companies are moving away from distributed complexity.",
            responses=responses,
            raw_notes="We had 3 people managing Kubernetes for an app with 5,000 DAU.",
            spike_id="test-spike-01",
        )

        self.assertIn("Why Microservices Burned Our Team", result["draft"])
        self.assertGreater(result["word_count"], 10)
        self.assertEqual(result["spike_id"], "test-spike-01")

        # Verify router was invoked with a prompt containing the operator's answers
        call_args = mock_router.complete.call_args
        prompt_used = call_args[1].get("prompt") if "prompt" in call_args[1] else call_args[0][1]
        self.assertIn("Kafka partition rebalancing", prompt_used)
        self.assertIn("P99 latency dropped from 420ms", prompt_used)
        self.assertIn("5,000 DAU", prompt_used)

    def test_synthesize_draft_persists_raw_transcript(self):
        """synthesize_draft persists raw_transcript.md to project directory and DB if provided."""
        from content_machine.interview.engine import InterviewEngine
        from content_machine.storage.db import connect

        db_conn = connect()

        # Seed spike in DB
        db_conn.execute(
            "INSERT INTO spikes (id, category, hook_thesis) VALUES (?, ?, ?)",
            ("spike-persist-test", "Architecture", "Monoliths win"),
        )
        db_conn.commit()

        mock_router = MagicMock()
        mock_router.complete.return_value = "Grounded draft content..."

        engine = InterviewEngine(router=mock_router, db_conn=db_conn)
        res = engine.synthesize_draft(
            topic_title="Monoliths Win",
            topic_summary="Monolith advantages.",
            responses=[{"persona": "Larry King", "question": "Bottom line?", "answer": "Simple wins."}],
            raw_notes="My raw note",
            spike_id="spike-persist-test",
        )

        # Check transcript recorded in DB
        row = db_conn.execute(
            "SELECT spike_id, word_count, path FROM transcripts WHERE spike_id = ?",
            ("spike-persist-test",),
        ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["spike_id"], "spike-persist-test")
        self.assertTrue(os.path.exists(row["path"]))

    def test_synthesize_draft_includes_voice_guide(self):
        """synthesize_draft includes author voice guide in prompt passed to router."""
        from content_machine.interview.engine import InterviewEngine

        mock_router = MagicMock()
        mock_router.complete.return_value = "Grounded draft content based on author voice guide."

        engine = InterviewEngine(router=mock_router, writer_model="qwen3.8-max")
        result = engine.synthesize_draft(
            topic_title="Distributed Systems Lessons",
            topic_summary="Key takeaways from high throughput architectures.",
            responses=[{"persona": "Tim Ferriss", "question": "What tools?", "answer": "Kafka and .NET Core."}],
            raw_notes="Zero company mentions required.",
            spike_id="test-voice-spike",
        )

        mock_router.complete.assert_called_once()
        call_args = mock_router.complete.call_args
        prompt_used = call_args[1].get("prompt") if "prompt" in call_args[1] else call_args[0][1]
        self.assertIn("# Author Voice & Persona Guide", prompt_used)
        self.assertIn("Zero Company Attribution", prompt_used)
        self.assertIn("No False Corporate Employment", prompt_used)


class TestInterviewAPI(unittest.TestCase):


    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        os.environ["CONTENT_MACHINE_HOME"] = self.tmp_dir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_api_brief_endpoint(self):
        """POST /api/interview/brief returns 200 with summary and questions."""
        from fastapi.testclient import TestClient
        from content_machine.api.app import app

        client = TestClient(app)

        with patch("content_machine.interview.engine.InterviewEngine.generate_briefing") as mock_gen:
            mock_gen.return_value = TopicBriefing(
                summary="AI coding assistants are changing dev velocity.",
                core_conflict="Code quality vs generation speed.",
                questions=[
                    InterviewQuestion(persona="Tim Ferriss", focus="Mechanics", question="What IDE extensions?"),
                ],
            )

            res = client.post(
                "/api/interview/brief",
                json={
                    "title": "State of AI Coding",
                    "url": "https://example.com/ai",
                    "body": "Article text",
                    "topic_tag": "AI/ML",
                },
            )

            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("summary", data)
            self.assertIn("questions", data)
            self.assertEqual(len(data["questions"]), 1)

    def test_api_synthesize_endpoint(self):
        """POST /api/interview/synthesize returns 200 with draft and word_count."""
        from fastapi.testclient import TestClient
        from content_machine.api.app import app

        client = TestClient(app)

        with patch("content_machine.interview.engine.InterviewEngine.synthesize_draft") as mock_synth:
            mock_synth.return_value = {
                "draft": "# AI Coding in Production\n\nHere is our real benchmark.",
                "word_count": 8,
                "spike_id": "test-spike",
            }

            res = client.post(
                "/api/interview/synthesize",
                json={
                    "topic_title": "State of AI Coding",
                    "topic_summary": "Summary of article",
                    "responses": [
                        {"persona": "Tim Ferriss", "question": "Tools?", "answer": "VS Code + custom scripts"}
                    ],
                    "raw_notes": "We saw 30% speedup",
                    "spike_id": "test-spike",
                },
            )

            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("draft", data)
            self.assertEqual(data["word_count"], 8)

    def test_api_transcribe_endpoint(self):
        """POST /api/interview/transcribe accepts an audio file and returns transcribed text."""
        from fastapi.testclient import TestClient
        from content_machine.api.app import app
        from content_machine.asr.transcript import Transcript

        client = TestClient(app)

        with patch("content_machine.asr.batch.BatchTranscriber.transcribe") as mock_transcribe:
            mock_transcribe.return_value = Transcript(
                text="In our Kubernetes cluster we had three partition rebalance issues.",
                model="faster-whisper/small",
                audio_path="dummy.wav",
                duration_s=4.2,
            )

            dummy_wav = b"RIFF....WAVEfmt ...."
            res = client.post(
                "/api/interview/transcribe",
                files={"audio": ("recording.wav", dummy_wav, "audio/wav")},
            )

            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("text", data)
            self.assertEqual(data["text"], "In our Kubernetes cluster we had three partition rebalance issues.")
            self.assertEqual(data["duration_s"], 4.2)
