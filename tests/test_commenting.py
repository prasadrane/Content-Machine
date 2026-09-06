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


class TestCommentingEngine(unittest.TestCase):
    def setUp(self):
        from unittest.mock import MagicMock
        from content_machine.config import AppConfig, ModelsConfig, ThresholdsConfig

        self.conn = connect(":memory:")
        self.cfg = AppConfig(
            models=ModelsConfig(writer="qwen3.8-max", council={"perell": "m1", "puri": "m2"}),
            thresholds=ThresholdsConfig(council_min_score_raw=9.0),
        )
        self.router = MagicMock()

    def tearDown(self):
        self.conn.close()

    def test_build_synthesis_prompt(self):
        from content_machine.commenting import CommentingEngine

        engine = CommentingEngine(router=self.router, cfg=self.cfg, db_conn=self.conn)

        # 1. Check insightful angle (default)
        prompt_insightful = engine._build_synthesis_prompt(
            post_content="Post about distributed databases and raft consensus.",
            angle=CommentAngle.INSIGHTFUL,
        )
        self.assertIn("Post about distributed databases and raft consensus.", prompt_insightful)
        self.assertIn("Add a concrete, real-world observation or metric extending the author's point. Avoid platitudes.", prompt_insightful)
        self.assertIn("Strictly 2 to 3 sentences", prompt_insightful)
        self.assertIn("Zero empty praise", prompt_insightful)
        self.assertNotIn("OPERATOR'S PERSPECTIVE", prompt_insightful)
        self.assertNotIn("GOVERNED EDITORIAL RULES", prompt_insightful)

        # 2. Check contrarian angle (string or enum)
        prompt_contrarian = engine._build_synthesis_prompt(
            post_content="Post about agile vs waterfall.",
            angle="contrarian",
        )
        self.assertIn("Respectfully challenge an unstated assumption or introduce a critical counter-intuitive edge case from experience.", prompt_contrarian)

        # 3. Check question angle
        prompt_question = engine._build_synthesis_prompt(
            post_content="Post about AI agent reliability.",
            angle=CommentAngle.QUESTION,
        )
        self.assertIn("Pose a sharp, senior-level question that advances the conversation beyond superficial agreement.", prompt_question)

        # 4. Check perspective text injection
        prompt_perspective = engine._build_synthesis_prompt(
            post_content="Post about Kafka streaming.",
            angle="insightful",
            perspective_text="We hit partition rebalance storms at 50k partitions.",
        )
        self.assertIn("OPERATOR'S PERSPECTIVE / LIVED ANGLE (primary grounding)", prompt_perspective)
        self.assertIn("We hit partition rebalance storms at 50k partitions.", prompt_perspective)

        # 5. Check governed rules injection from LessonsStore
        self.conn.execute(
            "INSERT INTO lessons (rule_text, category, status) VALUES (?, ?, ?)",
            ("Never start comments with 'As someone who'", "negative_constraint", "active"),
        )
        self.conn.commit()

        prompt_rules = engine._build_synthesis_prompt(
            post_content="Post about engineering leadership.",
            angle="insightful",
        )
        self.assertIn("GOVERNED EDITORIAL RULES (must obey)", prompt_rules)
        self.assertIn("Never start comments with 'As someone who'", prompt_rules)

    def test_synthesize_initial_draft(self):
        from content_machine.commenting import CommentingEngine

        self.router.complete.return_value = "At scale, naive consensus models fail on cross-region latency. Decoupling write paths yielded a 40% p99 latency drop in our clusters."
        engine = CommentingEngine(router=self.router, cfg=self.cfg, db_conn=self.conn)

        draft = engine.synthesize_initial_draft(
            post_content="We should use Paxos for everything.",
            angle="contrarian",
            perspective_text="Paxos has high wide-area overhead.",
        )
        self.assertEqual(
            draft,
            "At scale, naive consensus models fail on cross-region latency. Decoupling write paths yielded a 40% p99 latency drop in our clusters.",
        )
        self.router.complete.assert_called_once()
        args, kwargs = self.router.complete.call_args
        self.assertEqual(args[0], ["qwen3.8-max"])

        # Test stripping code fences
        self.router.complete.return_value = "```\nStripped comment text.\n```"
        draft_fenced = engine.synthesize_initial_draft(post_content="Another post with enough chars.")
        self.assertEqual(draft_fenced, "Stripped comment text.")

    def test_generate_comment_end_to_end(self):
        from unittest.mock import patch
        from content_machine.commenting import CommentingEngine
        from content_machine.council.loop import CouncilDecision
        from content_machine.schemas import CouncilScores

        self.router.complete.return_value = "Initial draft comment."
        mock_decision = CouncilDecision(
            iteration=1,
            threshold_met=True,
            gate_basis="raw",
            composite_raw=9.25,
            composite_normalized=None,
            judge_scores={
                "perell": CouncilScores(
                    narrative=9.5,
                    velocity=9.0,
                    depth=9.0,
                    slop_purity=9.5,
                    threshold_met=True,
                    verdict="pass",
                    required_actions=["Sharpen the second sentence."],
                )
            },
            required_actions=["Sharpen the second sentence."],
            draft="Polished final 2-sentence comment.",
            notes=[],
        )

        with patch("content_machine.commenting.engine.run_council", return_value=mock_decision) as mock_council:
            engine = CommentingEngine(router=self.router, cfg=self.cfg, db_conn=self.conn)
            resp = engine.generate_comment(
                post_content="Comprehensive post on database indexing techniques and B-tree optimization.",
                angle="insightful",
                perspective_text="B-tree index depth caused I/O bottlenecks in our migration.",
            )

            self.assertIsInstance(resp, CommentRunResponse)
            self.assertEqual(resp.initial_draft, "Initial draft comment.")
            self.assertEqual(resp.final_comment, "Polished final 2-sentence comment.")
            self.assertEqual(resp.iteration, 1)
            self.assertEqual(resp.peak_score, 9.25)
            self.assertEqual(resp.verdict, "PASS")
            self.assertEqual(resp.actions, ["Sharpen the second sentence."])
            self.assertIn("perell", resp.judge_scores)
            self.assertEqual(resp.judge_scores["perell"], 9.25)

            # Verify DB insertion
            cur = self.conn.execute("SELECT * FROM comments WHERE id = ?", (resp.comment_id,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["post_content"], "Comprehensive post on database indexing techniques and B-tree optimization.")
            self.assertEqual(row["angle"], "insightful")
            self.assertEqual(row["perspective_text"], "B-tree index depth caused I/O bottlenecks in our migration.")
            self.assertEqual(row["initial_draft"], "Initial draft comment.")
            self.assertEqual(row["final_comment"], "Polished final 2-sentence comment.")
            self.assertEqual(row["iteration_count"], 1)
            self.assertEqual(row["peak_score"], 9.25)
            self.assertEqual(row["verdict"], "PASS")

    def test_get_history(self):
        from content_machine.commenting import CommentingEngine

        engine = CommentingEngine(router=self.router, cfg=self.cfg, db_conn=self.conn)
        self.conn.execute(
            """
            INSERT INTO comments (id, post_content, angle, perspective_text, initial_draft,
                                  final_comment, iteration_count, peak_score, verdict, judge_critiques, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("c1", "Post 1 content here", "insightful", None, "Draft 1", "Comment 1", 1, 9.1, "PASS", "{}", "2026-09-06T00:00:00Z"),
        )
        self.conn.execute(
            """
            INSERT INTO comments (id, post_content, angle, perspective_text, initial_draft,
                                  final_comment, iteration_count, peak_score, verdict, judge_critiques, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("c2", "Post 2 content here", "contrarian", "My perspective", "Draft 2", "Comment 2", 2, 8.8, "REVISE", "{}", "2026-09-06T00:05:00Z"),
        )
        self.conn.commit()

        history = engine.get_history(limit=10)
        self.assertEqual(len(history), 2)
        # Verify ordering: most recent first (c2 created at 00:05:00Z)
        self.assertEqual(history[0].id, "c2")
        self.assertEqual(history[0].angle, "contrarian")
        self.assertEqual(history[0].perspective_text, "My perspective")
        self.assertEqual(history[1].id, "c1")
        self.assertIsNone(history[1].perspective_text)

        # Test limit
        history_limited = engine.get_history(limit=1)
        self.assertEqual(len(history_limited), 1)
        self.assertEqual(history_limited[0].id, "c2")


if __name__ == "__main__":
    unittest.main()

