# Author Profile & Voice Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and integrate an Author Profile & Voice Grounding subsystem that seeds Prasad Rane's empirical voice profile, enforces strict personal-thought invariants (zero company names, no false corporate employment claims, job-status agnostic senior tone, current AI builder upskilling), injects this profile into Commenting & Interview synthesis engines, and provides an in-app Profile editor tab under Tools.

**Architecture:** A dedicated subsystem `content_machine/profile` loads and serializes the structured `knowledge/02_voice-guide.md` file, serves REST endpoints (`GET /api/profile` and `POST /api/profile`), injects the active voice guide into `CommentingEngine` and `InterviewEngine`, and powers a dedicated `ProfileTab` in the React UI under Tools.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, React 18, Vite, Tailwind CSS.

## Global Constraints
- Target Author: Prasad Rane (Senior Software & AI Systems Engineer — The Bridge between Enterprise Systems and Modern AI).
- NON-NEGOTIABLE Invariant 1: Zero Company Attribution. Never cite previous company names (no Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.). All insights are delivered as personal thoughts and architectural observations.
- NON-NEGOTIABLE Invariant 2: No False Corporate Employment. Never generate statements claiming current employment at an organization (never "My company today...", "My team at work...", "At my job...").
- NON-NEGOTIABLE Invariant 3: Job-Status Agnostic Senior Technical Tone. Focus on architecture, real-world systems wisdom, trade-offs. No unsolicited mentions of layoffs or job searching.
- NON-NEGOTIABLE Invariant 4: Current Reality & Upskilling. Ground current explorations in active hands-on builder energy (Agentic AI, local model routing, modern distributed patterns).
- NON-NEGOTIABLE Invariant 5: Zero Generic Praise / Slop. Banned phrases: "Spot on!", "Thanks for sharing", "Great post!", "In today's fast-paced world".
- All tests must run 100% offline using mock routers and temp directories.
- Follow TDD: Failing tests first, then implementation, then verify green.

---

### Task 1: Seed Voice Guide & Pydantic Schemas

**Files:**
- Modify: `knowledge/02_voice-guide.md`
- Modify: `content_machine/schemas.py`
- Create: `tests/test_profile.py`

**Interfaces:**
- Produces:
  - Seed file `knowledge/02_voice-guide.md` with complete codified voice guide, persona, and negative constraints.
  - `ProfileData(name: str, headline: str, current_focus: str, technical_domains: list[str], hard_invariants: list[str], full_markdown: str)`
  - `UpdateProfileRequest(current_focus: Optional[str], technical_domains: Optional[list[str]], custom_notes: Optional[str])`

- [ ] **Step 1: Write failing tests for schemas and seed file verification**

In `tests/test_profile.py`:
- Test that `knowledge/02_voice-guide.md` exists and contains core sections ("Core Identity & Stance", "Voice Invariants & Negative Constraints", "Zero Company Attribution", "No False Corporate Employment").
- Test `ProfileData` and `UpdateProfileRequest` schema validation and instantiation.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_profile.py`
Expected: FAIL (schemas missing / assertions fail).

- [ ] **Step 3: Implement seed file and Pydantic schemas**

1. Populate `knowledge/02_voice-guide.md` with the full codified guide approved in the design spec.
2. In `content_machine/schemas.py`, add `ProfileData` and `UpdateProfileRequest`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_profile.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add knowledge/02_voice-guide.md content_machine/schemas.py tests/test_profile.py
git commit -m "feat(profile): seed voice guide and add profile pydantic schemas"
```

---

### Task 2: ProfileManager Subsystem

**Files:**
- Create: `content_machine/profile/__init__.py`
- Create: `content_machine/profile/manager.py`
- Modify: `tests/test_profile.py`

**Interfaces:**
- Consumes:
  - `knowledge/02_voice-guide.md`
  - `content_machine.storage.paths` (`home_root()`, `ensure_tree()`)
  - `ProfileData`, `UpdateProfileRequest`
- Produces:
  - `ProfileManager(home_root: Optional[Path] = None)`
  - `ProfileManager.get_profile() -> ProfileData`
  - `ProfileManager.update_profile(req: UpdateProfileRequest) -> ProfileData`
  - `ProfileManager.get_voice_guide_text() -> str`

- [ ] **Step 1: Write failing unit tests for ProfileManager**

In `tests/test_profile.py`:
- `test_get_profile_parses_markdown`: verifies default parsed fields (`name="Prasad Rane"`, `headline`, `current_focus`, `technical_domains`, `hard_invariants`).
- `test_update_profile_updates_focus_and_domains`: verifies that updating focus and domains rewrites the markdown while strictly preserving the 5 hard invariants.
- `test_get_voice_guide_text`: verifies reading raw markdown string for prompt injection.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_profile.py`
Expected: FAIL (module `content_machine.profile.manager` not found).

- [ ] **Step 3: Implement ProfileManager**

Create `content_machine/profile/__init__.py` and `content_machine/profile/manager.py`:
- Initialize with optional `home_root` (defaults to `paths.home_root()`).
- Auto-syncs seed `knowledge/02_voice-guide.md` to `home_root / "knowledge" / "02_voice-guide.md"` if not present.
- `get_profile()`: Parses markdown sections via regex or structured line parsing into `ProfileData`.
- `update_profile()`: Merges updated focus/domains/notes into the markdown template while keeping all non-negotiable negative constraints intact, writes to file atomically, and returns `ProfileData`.
- `get_voice_guide_text()`: Returns complete text of active voice guide.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_profile.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content_machine/profile/ tests/test_profile.py
git commit -m "feat(profile): implement ProfileManager for voice guide parsing and updates"
```

---

### Task 3: REST API Endpoints for Profile

**Files:**
- Modify: `content_machine/api/app.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `ProfileManager`
  - `UpdateProfileRequest`
- Produces:
  - `GET /api/profile -> ProfileData`
  - `POST /api/profile -> ProfileData`

- [ ] **Step 1: Write failing tests for profile API endpoints**

In `tests/test_api.py`:
- `test_get_profile`: Call `client.get("/api/profile")`, assert 200, verify `name == "Prasad Rane"` and `hard_invariants` presence.
- `test_post_profile_update`: Call `client.post("/api/profile", json={"current_focus": "Fine-tuning local models"})`, assert 200, verify updated focus in response.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_api.py`
Expected: FAIL (404 Not Found for `/api/profile`).

- [ ] **Step 3: Implement endpoints in `content_machine/api/app.py`**

Add:
```python
@app.get("/api/profile", response_model=ProfileData)
def profile_get():
    manager = ProfileManager()
    return manager.get_profile()

@app.post("/api/profile", response_model=ProfileData)
def profile_update(req: UpdateProfileRequest):
    manager = ProfileManager()
    return manager.update_profile(req)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_api.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content_machine/api/app.py tests/test_api.py
git commit -m "feat(profile): add REST API endpoints GET and POST /api/profile"
```

---

### Task 4: Dynamic Engine Grounding

**Files:**
- Modify: `content_machine/commenting/engine.py`
- Modify: `content_machine/interview/engine.py`
- Modify: `tests/test_commenting.py`
- Modify: `tests/test_interview.py`

**Interfaces:**
- Consumes:
  - `ProfileManager().get_voice_guide_text()`
- Produces:
  - Injected author voice section in `CommentingEngine._build_synthesis_prompt`.
  - Injected author voice section in `InterviewEngine.synthesize_draft`.
  - Verification that generated drafts and comments contain the negative constraints against company attribution and false corporate employment.

- [ ] **Step 1: Write failing tests for engine prompt grounding**

- In `tests/test_commenting.py`: Test that `CommentingEngine._build_synthesis_prompt` contains `# AUTHOR VOICE & GROUNDING`, mentions Prasad Rane's persona, and includes "Zero Company Attribution" and "No False Corporate Employment".
- In `tests/test_interview.py`: Test that `InterviewEngine.synthesize_draft` prompt includes the author voice guide context.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests/test_commenting.py tests/test_interview.py`
Expected: FAIL (author voice guide section missing from prompt).

- [ ] **Step 3: Implement engine prompt grounding**

1. In `content_machine/commenting/engine.py`:
   - Import `ProfileManager`.
   - In `_build_synthesis_prompt`, fetch `voice_guide = ProfileManager().get_voice_guide_text()`.
   - Append `# AUTHOR VOICE & GROUNDING (Prasad Rane)` with core invariants to the synthesis prompt.
2. In `content_machine/interview/engine.py`:
   - Fetch active voice guide and inject into article synthesis prompt.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests/test_commenting.py tests/test_interview.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content_machine/commenting/engine.py content_machine/interview/engine.py tests/test_commenting.py tests/test_interview.py
git commit -m "feat(profile): inject author voice guide and negative constraints into commenting and interview engines"
```

---

### Task 5: Frontend UI ProfileTab

**Files:**
- Modify: `ui/src/App.jsx`

**Interfaces:**
- Consumes:
  - `GET /api/profile`
  - `POST /api/profile`
- Produces:
  - `Profile` tab button under Tools navigation group with `User` icon.
  - `ProfileTab` component with:
    - Persona & Headline display.
    - Editable Current Upskilling Focus textarea.
    - Core Technical Domains interactive tags.
    - Non-Negotiable Invariants card with shield badges.
    - Live Voice Guide Markdown Preview.
    - "Save & Sync Voice Profile" action with instant feedback.

- [ ] **Step 1: Implement ProfileTab component and Navigation tab**

In `ui/src/App.jsx`:
1. Import `User` icon from `lucide-react`.
2. Add `Profile` button in Tools navigation header:
   ```jsx
   <TabBtn 
     active={activeTab === 'profile'} 
     onClick={() => setActiveTab('profile')}
     icon={<User className="w-3.5 h-3.5" />}
     label="Profile" 
   />
   ```
3. Wire route `{activeTab === 'profile' && <ProfileTab />}` into `<main>`.
4. Build `ProfileTab`:
   - Fetches profile on mount via `GET /api/profile`.
   - Editable fields for `current_focus` and `technical_domains`.
   - Displays hard invariants clearly with security/shield icons.
   - Live rendered preview of the markdown.
   - Save handler posting to `POST /api/profile` with toast confirmation.

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
git commit -m "feat(ui): add ProfileTab under Tools with focus editor and voice guide preview"
```

---

### Task 6: End-to-End Regression & Verification

**Files:**
- All repository files

- [ ] **Step 1: Run complete offline test suite**

Run: `python -m unittest discover -s tests`
Expected: 100% PASS across all unit tests.

- [ ] **Step 2: Re-index codebase memory**

Run `index_repository` on `C-Users-mamat-Github-Content-Machine`.

- [ ] **Step 3: Final Commit**

```bash
git commit -am "feat(profile): complete author profile and voice grounding subsystem"
```
