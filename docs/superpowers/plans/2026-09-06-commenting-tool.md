# LinkedIn Commenting Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and integrate a dedicated "Commenting" editorial tool under the Tools navigation group that generates Council-verified, high-signal 2–3 sentence LinkedIn comments with optional voice perspective intake and governed lessons injection.

**Architecture:** A dedicated backend subsystem `content_machine/commenting` orchestrates comment synthesis with active rules from `LessonsStore`, passes drafts through the 4-Judge Writer's Council loop with peak selection, persists runs to a new `comments` SQLite table, and serves REST endpoints to a responsive React UI tab with live mic recording and expandable judge breakdowns.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLite, React 18, Vite, Tailwind CSS, Web Speech API / MediaRecorder.

## Global Constraints
- Target length constraint: Strictly 2 to 3 sentences for generated comments.
- Zero generic praise / slop ("Spot on!", "Thanks for sharing", buzzwords, emoji overload).
- Governed lessons from `03_content-lessons.md` must be fetched via `LessonsStore.active_rules()` and injected as negative constraints.
- Writer's Council: Evaluated by the 4 judges (`qwen3.8-max` Perell, `qwen3.8-flash` Puri, `qwen3.7-plus` Housel, `qwen3.6-flash` Slop Allergist) with z-score normalization and break-with-best peak selection.
- All tests must run 100% offline using mock routers and temp SQLite databases.
- Follow TDD: Failing tests first, then implementation, then verify green.

---

### Task 1: Database Schema & Pydantic Schemas

**Files:**
- Modify: `content_machine/storage/db.py`
- Modify: `content_machine/schemas.py`
- Create: `tests/test_commenting.py`

**Interfaces:**
- Produces:
  - `CommentAngle` (Enum: `insightful`, `contrarian`, `question`)
  - `GenerateCommentRequest(post_content: str, angle: CommentAngle, perspective_text: Optional[str])`
  - `CommentRunResponse(comment_id: str, initial_draft: str, final_comment: str, iteration: int, peak_score: float, verdict: str, actions: list[str], judge_scores: dict[str, float], judge_critiques: dict[str, str])`
  - `CommentHistoryItem(...)` and `CommentHistoryResponse(...)`
  - SQLite table `comments` created automatically in `init_db(conn)`

- [ ] **Step 1: Write the failing tests for schema and database persistence**

Add test cases in `tests/test_commenting.py` verifying:
1. `CommentAngle` validation and defaults.
2. `GenerateCommentRequest` validation (e.g. min length requirement of 10 chars).
3. `init_db` creates the `comments` table with all necessary columns.

```python
import sqlite3
import unittest
from content_machine.schemas import (
    CommentAngle,
    GenerateCommentRequest,
    CommentRunResponse,
    CommentHistoryResponse,
)
from content_machine.storage.db import init_db

class TestCommentSchemasAndDB(unittest.TestCase):
    def test_schemas(self):
        req = GenerateCommentRequest(post_content="This is a test post about systems architecture.")
        self.assertEqual(req.angle, CommentAngle.INSIGHTFUL)
        self.assertIsNone(req.perspective_text)

        with self.assertRaises(Exception):
            GenerateCommentRequest(post_content="too short")

    def test_db_init_comments_table(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
        self.assertIsNotNone(cursor.fetchone())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_commenting.py`
Expected: FAIL (missing imports / table `comments` not found).

- [ ] **Step 3: Implement database migration and Pydantic schemas**

1. In `content_machine/schemas.py`, add `CommentAngle`, `GenerateCommentRequest`, `CommentRunResponse`, `CommentHistoryItem`, `CommentHistoryResponse`.
2. In `content_machine/storage/db.py`, add `CREATE TABLE IF NOT EXISTS comments (...)` inside `init_db()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_commenting.py`
Expected: PASS (all tests pass).

- [ ] **Step 5: Commit**

```bash
git add content_machine/schemas.py content_machine/storage/db.py tests/test_commenting.py
git commit -m "feat(commenting): add database table and pydantic schemas"
```

---

### Task 2: CommentingEngine Core Subsystem

**Files:**
- Create: `content_machine/commenting/__init__.py`
- Create: `content_machine/commenting/engine.py`
- Modify: `tests/test_commenting.py`

**Interfaces:**
- Consumes:
  - `LessonsStore(db_conn).active_rules()`
  - `run_council(draft, router, cfg, conn, spike_id)`
  - `ModelRouter`
  - `Config`
- Produces:
  - `CommentingEngine(router, cfg, db_conn)`
  - `CommentingEngine.synthesize_initial_draft(post_content: str, angle: str, perspective_text: Optional[str] = None) -> str`
  - `CommentingEngine.generate_comment(post_content: str, angle: str, perspective_text: Optional[str] = None) -> CommentRunResponse`
  - `CommentingEngine.get_history(limit: int = 50) -> list[CommentHistoryItem]`

- [ ] **Step 1: Write failing tests for CommentingEngine**

In `tests/test_commenting.py`, add unit tests:
1. `test_prompt_construction`: Verifies active rules from `LessonsStore`, angle instructions, and operator perspective are correctly assembled into the writer prompt.
2. `test_generate_comment_end_to_end`: Uses a mock router to simulate draft synthesis and Council review, verifying output structure, length sanitization, and DB insertion into `comments`.
3. `test_get_history`: Verifies retrieving stored comment records ordered by `created_at DESC`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_commenting.py`
Expected: FAIL (`content_machine.commenting.engine` does not exist).

- [ ] **Step 3: Implement CommentingEngine**

Create `content_machine/commenting/__init__.py` and `content_machine/commenting/engine.py`:
- Initialize with `router`, `cfg`, `db_conn`.
- `_build_synthesis_prompt(...)`: Injects angle instructions, perspective notes, governed lessons, and strict 2–3 sentence formatting rules.
- `synthesize_initial_draft(...)`: Queries router route `writer` (`qwen3.8-max`).
- `generate_comment(...)`:
  - Synthesizes initial comment draft.
  - Calls `run_council()` with generated draft and `spike_id=f"comment_{uuid4().hex[:8]}"`.
  - Extracts peak iteration from DB or council result.
  - Persists comment record to SQLite `comments` table.
  - Returns `CommentRunResponse`.
- `get_history(...)`: Queries `comments` table and returns formatted items.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_commenting.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content_machine/commenting/ tests/test_commenting.py
git commit -m "feat(commenting): implement CommentingEngine and council orchestration"
```

---

### Task 3: REST API Endpoints

**Files:**
- Modify: `content_machine/api/app.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `CommentingEngine`
  - `GenerateCommentRequest`
- Produces:
  - `POST /api/comments/generate -> CommentRunResponse`
  - `GET /api/comments/history -> CommentHistoryResponse`

- [ ] **Step 1: Write failing tests for comment API endpoints**

In `tests/test_api.py`:
1. `test_comments_generate_success`: Mock `CommentingEngine.generate_comment` to return a `CommentRunResponse` and verify HTTP 200 and response schema.
2. `test_comments_generate_validation_error`: Send empty or sub-10 character post content and assert HTTP 422.
3. `test_comments_history`: Mock `CommentingEngine.get_history` and assert HTTP 200 list response.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_api.py`
Expected: FAIL (404 Not Found for `/api/comments/generate`).

- [ ] **Step 3: Implement API endpoints in `content_machine/api/app.py`**

Add:
```python
@app.post("/api/comments/generate", response_model=CommentRunResponse)
def comments_generate(req: GenerateCommentRequest):
    ...

@app.get("/api/comments/history", response_model=CommentHistoryResponse)
def comments_history():
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_api.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content_machine/api/app.py tests/test_api.py
git commit -m "feat(commenting): add REST API endpoints for comment generation and history"
```

---

### Task 4: Frontend UI CommentingTab

**Files:**
- Modify: `ui/src/App.jsx`

**Interfaces:**
- Consumes:
  - `POST /api/comments/generate`
  - `GET /api/comments/history`
  - `POST /api/interview/transcribe` (audio transcription fallback)
  - Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`)
- Produces:
  - `Commenting` tab button under Tools navigation group.
  - `CommentingTab` full-featured component.

- [ ] **Step 1: Implement CommentingTab component and Navigation tab**

In `ui/src/App.jsx`:
1. In the header navigation under `Tools`, add the `Commenting` tab button with `MessageSquare` icon.
2. Build `CommentingTab`:
   - State for `postContent`, `angle` ('insightful', 'contrarian', 'question'), `perspectiveText`, `isRecording`, `isDeliberating`, `commentResult`, `history`, `copySuccess`.
   - Post content textarea with character counter.
   - Angle pill selectors (`💡 Nuanced Insight`, `⚖️ Respectful Contrarian`, `❓ High-Signal Question`).
   - Perspective textarea with integrated `🎙️ Speak Perspective` microphone button (using Web Speech API with MediaRecorder fallback).
   - "Generate Comment & Run Council Round" primary action button with loading iteration feedback.
   - Editorial Polish Card:
     - Prominent polished comment text.
     - Sentence count and character count badges.
     - One-click copy button with checkmark animation.
     - Council Verdict Badge (score, PASS/BREAK status).
     - Expandable Accordion with individual judge scores & feedback (David Perell, Puri, Morgan Housel, Slop Allergist).
   - Recent Comments drawer displaying past comments with quick re-copy action.

- [ ] **Step 2: Build frontend to verify zero build or syntax errors**

Run:
```powershell
cd ui
npm run build
cd ..
```
Expected: Build passes with 0 errors, outputs clean bundle in `ui/dist`.

- [ ] **Step 3: Commit**

```bash
git add ui/src/App.jsx ui/dist/
git commit -m "feat(ui): add CommentingTab under Tools with mic input and council breakdown"
```

---

### Task 5: End-to-End Regression & Verification

**Files:**
- All repository files

- [ ] **Step 1: Run complete offline test suite**

Run: `python -m unittest discover -s tests`
Expected: 100% PASS with 0 failures and 0 errors across all 130+ unit tests.

- [ ] **Step 2: Verify CLI entrypoint (optional convenience flag)**

Add optional CLI subcommand: `python -m content_machine comment --post "..." --angle insightful` to `content_machine/__main__.py`.
Run: `python tests/test_cli.py` to ensure CLI regressions pass.

- [ ] **Step 3: Final Commit**

```bash
git commit -am "feat(commenting): complete LinkedIn commenting tool with council verification"
```
