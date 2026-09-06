import sqlite3
import unittest
from pydantic import ValidationError

from content_machine.schemas import (
    CommentAngle,
    GenerateCommentRequest,
    CommentRunResponse,
    CommentHistoryItem,
    CommentHistoryResponse,
)
from content_machine.storage.db import connect, init_db


class TestCommentSchemasAndDB(unittest.TestCase):
    def test_comment_angle_enum(self):
        self.assertEqual(CommentAngle.INSIGHTFUL.value, "insightful")
        self.assertEqual(CommentAngle.CONTRARIAN.value, "contrarian")
        self.assertEqual(CommentAngle.QUESTION.value, "question")
        self.assertEqual(CommentAngle.INSIGHTFUL, "insightful")

    def test_generate_comment_request_defaults_and_validation(self):
        req = GenerateCommentRequest(post_content="This is a test post about systems architecture.")
        self.assertEqual(req.angle, CommentAngle.INSIGHTFUL)
        self.assertIsNone(req.perspective_text)
        self.assertEqual(req.post_content, "This is a test post about systems architecture.")

        # Custom angle and perspective text
        req2 = GenerateCommentRequest(
            post_content="Another valid post content with sufficient length.",
            angle=CommentAngle.CONTRARIAN,
            perspective_text="In my experience as a distributed systems engineer...",
        )
        self.assertEqual(req2.angle, CommentAngle.CONTRARIAN)
        self.assertEqual(req2.perspective_text, "In my experience as a distributed systems engineer...")

        # String angle parsing
        req3 = GenerateCommentRequest(
            post_content="Another valid post content with sufficient length.",
            angle="question",
        )
        self.assertEqual(req3.angle, CommentAngle.QUESTION)

        # Min length validation (post_content < 10 characters)
        with self.assertRaises(ValidationError):
            GenerateCommentRequest(post_content="too short")

    def test_comment_run_response_schema(self):
        resp = CommentRunResponse(
            comment_id="comm-001",
            initial_draft="First draft of the comment.",
            final_comment="Polished final comment.",
            iteration=2,
            peak_score=8.75,
            verdict="pass",
            actions=["Sharpen the first sentence."],
            judge_scores={"perell": 8.5, "puri": 9.0},
            judge_critiques={"perell": "Strong narrative hook."},
        )
        self.assertEqual(resp.comment_id, "comm-001")
        self.assertEqual(resp.iteration, 2)
        self.assertEqual(resp.peak_score, 8.75)
        self.assertEqual(resp.verdict, "pass")
        self.assertEqual(len(resp.actions), 1)
        self.assertEqual(resp.judge_scores["puri"], 9.0)

    def test_comment_history_item_and_response(self):
        item = CommentHistoryItem(
            id="comm-001",
            post_content="Source post content goes here with good context.",
            angle="insightful",
            perspective_text=None,
            final_comment="Great observation on decoupling modules.",
            iteration_count=1,
            peak_score=9.1,
            verdict="pass",
            created_at="2026-09-06T00:00:00Z",
        )
        self.assertEqual(item.id, "comm-001")
        self.assertIsNone(item.perspective_text)

        history = CommentHistoryResponse(items=[item], total=1)
        self.assertEqual(history.total, 1)
        self.assertEqual(len(history.items), 1)
        self.assertEqual(history.items[0].id, "comm-001")

    def test_db_init_comments_table(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
        self.assertIsNotNone(cursor.fetchone())

        # Verify all columns exist in comments table
        cursor.execute("PRAGMA table_info(comments)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        expected_columns = {
            "id": "TEXT",
            "post_content": "TEXT",
            "angle": "TEXT",
            "perspective_text": "TEXT",
            "initial_draft": "TEXT",
            "final_comment": "TEXT",
            "iteration_count": "INTEGER",
            "peak_score": "REAL",
            "verdict": "TEXT",
            "judge_critiques": "TEXT",
            "created_at": "TEXT",
        }
        for col, col_type in expected_columns.items():
            self.assertIn(col, columns)
            self.assertEqual(columns[col].upper(), col_type)

        # Test inserting and reading a record
        cursor.execute(
            """
            INSERT INTO comments (
                id, post_content, angle, perspective_text, initial_draft,
                final_comment, iteration_count, peak_score, verdict, judge_critiques
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "c-test-1",
                "Original post text...",
                "insightful",
                "My note",
                "Draft v1",
                "Final v2",
                2,
                8.4,
                "pass",
                '{"perell": "Good"}',
            ),
        )
        conn.commit()

        cursor.execute("SELECT * FROM comments WHERE id = ?", ("c-test-1",))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        conn.close()

    def test_connect_creates_comments_table(self):
        conn = connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()


if __name__ == "__main__":
    unittest.main()
