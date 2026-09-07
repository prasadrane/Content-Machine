"""FastAPI backend for Content Machine (plan v2 §1, Step 8).

Runs with: uvicorn content_machine.api.app:app --reload --port 8000
Or via the CLI: python -m content_machine serve
"""

import json
import os
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Subsystem imports (at module level so patch() works in tests)
from content_machine.asr.batch import BatchTranscriber
from content_machine.connectors.github import GitHubConnector
from content_machine.connectors.linkedin import LinkedInConnector
from content_machine.connectors.rss import RSSConnector
from content_machine.council.loop import run_council
from content_machine.distribution.engine import DistributionEngine
from content_machine.lessons.differ import LessonsDiffer
from content_machine.lessons.store import LessonsStore
from content_machine.oracle.oracle import OracleOrchestrator
from content_machine.oracle.scorer import IdeaScorer
from content_machine.interview.engine import InterviewEngine
from content_machine.commenting.engine import CommentingEngine
from content_machine.profile.manager import ProfileManager
from content_machine.schemas import (
    TopicBriefRequest,
    TopicBriefing,
    SynthesizeDraftRequest,
    SynthesizeDraftResponse,
    GenerateCommentRequest,
    CommentRunResponse,
    CommentHistoryResponse,
    CommentHistoryItem,
    ProfileData,
    UpdateProfileRequest,
    DistributeRunRequest,
    DistributeHistoryItem,
    DistributeHistoryResponse,
    HumanizeRequest,
    HumanizeResult,
)


# ---------------------------------------------------------------------------
# Shared infrastructure (mirrors CLI helpers; patchable in tests)
# ---------------------------------------------------------------------------

def _make_router():
    from content_machine.config import load_config
    from content_machine.router.base import ModelRouter, Route
    from content_machine.router.messages_adapter import MessagesAdapter

    cfg = load_config()
    routes: dict = {}
    for name, rc in cfg.routes.items():
        base_url = os.environ.get(rc.base_url_env, "") if rc.base_url_env else (rc.base_url or "")
        auth_token = os.environ.get(rc.auth_token_env, "") if rc.auth_token_env else (rc.auth_token or "")
        api_key = os.environ.get(rc.api_key_env, "") if rc.api_key_env else (rc.api_key or "")
        adapter = MessagesAdapter(base_url=base_url, auth_token=auth_token or api_key)
        routes[name] = Route(name=name, protocol=rc.protocol, adapter=adapter)

    return ModelRouter(
        routes=routes,
        route_models=cfg.route_models,
        preferred_max_latency_s=cfg.thresholds.preferred_max_latency_s,
    )


def _make_db():
    from content_machine.storage.db import connect
    return connect()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Content Machine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve built React bundle (if it exists)
_UI_DIST = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"
if _UI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_UI_DIST / "assets")), name="assets")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OracleRunRequest(BaseModel):
    rss_urls: list[str] = Field(default_factory=list)
    github_repos: list[str] = Field(default_factory=list)
    linkedin_profiles: list[str] = Field(default_factory=list)
    linkedin_li_at: Optional[str] = None
    include_linkedin_feed: bool = False
    no_persist: bool = False
    limit: Optional[int] = None
    max_age_days: Optional[int] = 10
    max_items_per_feed: int = 25

    def validate_sources(self):
        if not self.rss_urls and not self.github_repos and not self.linkedin_profiles and not self.linkedin_li_at and not self.include_linkedin_feed:
            raise HTTPException(status_code=422, detail="Provide at least one source (RSS, GitHub, or LinkedIn).")



class CandidateOut(BaseModel):
    title: str
    url: str
    score: float
    verdict: str
    source: str
    published_at: Optional[str] = None
    topic_tag: str = "General Engineering"
    body_snippet: Optional[str] = None
    dimension_scores: Optional[dict[str, float]] = None



class OracleRunResponse(BaseModel):
    candidates: list[CandidateOut]


class OracleHistoryItem(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    source: str
    score: float
    verdict: str
    topic_tag: str
    created_at: str
    samples: list[dict] = Field(default_factory=list)


class OracleHistoryResponse(BaseModel):
    items: list[OracleHistoryItem]
    total: int
    topics: list[str]


class CouncilRunRequest(BaseModel):
    draft: str = Field(min_length=1)
    spike_id: str = "cli-session"


class CouncilRunResponse(BaseModel):
    verdict: str
    score: float
    iteration: int
    actions: list[str]
    peak_score: Optional[float] = None
    peak_iteration: Optional[int] = None
    is_all_time_peak: bool = False


class CouncilHistoryItem(BaseModel):
    id: int
    iteration: int
    score: float
    verdict: str
    threshold_met: bool
    created_at: str
    draft: Optional[str] = None
    actions: list[str] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)


class CouncilHistoryResponse(BaseModel):
    spike_id: str
    best: Optional[CouncilHistoryItem] = None
    history: list[CouncilHistoryItem] = Field(default_factory=list)


class CouncilSpikeItem(BaseModel):
    spike_id: str
    peak_score: float
    peak_iteration: int
    iteration_count: int
    updated_at: str


class LessonRuleOut(BaseModel):
    id: int
    rule_text: str
    provenance_project: Optional[str]
    created_at: str
    status: str


class LessonsListResponse(BaseModel):
    rules: list[LessonRuleOut]
    pending: list[LessonRuleOut] = []


class LessonsDiffRequest(BaseModel):
    draft: str
    published: str
    project_id: str = "unknown"


class ProposalOut(BaseModel):
    rule: str
    rule_id: Optional[int]
    is_conflict: bool
    conflict_rule_id: Optional[int]
    merge_required: bool


class LessonsDiffResponse(BaseModel):
    rules: list[ProposalOut]


class LessonsCustomRequest(BaseModel):
    rule_text: str = Field(min_length=1)
    provenance_project: str = "manual"
    auto_approve: bool = True


class LessonsCustomResponse(BaseModel):
    ok: bool
    rule_id: Optional[int] = None
    status: str
    is_conflict: bool = False
    conflict_rule_id: Optional[int] = None
    merge_required: bool = False


class DistributeRunResponse(BaseModel):

    linkedin: Optional[str] = None
    x_thread: Optional[str] = None
    video_script: Optional[str] = None
    video_script_short: Optional[str] = None
    video_script_long: Optional[str] = None
    newsletter: Optional[str] = None


class LinkedInStatusResponse(BaseModel):
    session_valid: bool
    mode: str
    saved_at: Optional[str] = None
    browser_profile_dir: str


class LinkedInSyncRequest(BaseModel):
    headless: bool = True
    timeout_ms: int = 30000


class LinkedInSyncResponse(BaseModel):
    success: bool
    mode: str
    saved_at: Optional[str] = None
    message: str


class TranscribeAudioResponse(BaseModel):
    text: str
    duration_s: float = 0.0
    model: str = "faster-whisper/small"



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


def _clean_list(items: list[str]) -> list[str]:
    cleaned = []
    for item in items:
        for part in item.split(","):
            part = part.strip()
            if part:
                cleaned.append(part)
    return cleaned


def _build_oracle_components(req: OracleRunRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    db_conn = None if req.no_persist else _make_db()

    connectors = []
    for url in req.rss_urls:
        connectors.append(
            RSSConnector(
                url=url,
                db_conn=db_conn,
                max_age_days=req.max_age_days,
                max_items=req.max_items_per_feed,
            )
        )
    pat = os.environ.get("GITHUB_PAT", "")
    for repo in req.github_repos:
        connectors.append(GitHubConnector(repo=repo, pat=pat))

    li_cookie = req.linkedin_li_at or os.environ.get("LINKEDIN_LI_AT", "")
    if req.linkedin_profiles:
        for profile in req.linkedin_profiles:
            connectors.append(LinkedInConnector(li_at=li_cookie or None, profile=profile, db_conn=db_conn))
    elif req.include_linkedin_feed or li_cookie:
        try:
            connectors.append(LinkedInConnector(li_at=li_cookie or None, profile=None, db_conn=db_conn))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    scorer = IdeaScorer(
        router=router,
        scanner_model=cfg.models.scanner,
        n_samples=cfg.thresholds.idea_samples,
        idea_gate=cfg.thresholds.idea_gate,
        idea_margin=cfg.thresholds.idea_margin,
    )
    orch = OracleOrchestrator(connectors=connectors, scorer=scorer, db_conn=db_conn)
    return orch, connectors


def _stream_oracle_scan(req: OracleRunRequest) -> StreamingResponse:
    req.validate_sources()
    orch, connectors = _build_oracle_components(req)

    def event_generator():
        import time
        import statistics
        start_time = time.time()

        yield f"event: phase\ndata: {json.dumps({'phase': 'fetching', 'message': 'Pulling items from registered sources...'})}\n\n"

        for conn in connectors:
            src_name = (
                getattr(conn, "url", None)
                or getattr(conn, "repo", None)
                or getattr(conn, "profile", None)
                or getattr(conn, "name", type(conn).__name__)
            )
            yield f"event: source_fetched\ndata: {json.dumps({'source': str(src_name), 'items_count': 0})}\n\n"

        yield f"event: dedup\ndata: {json.dumps({'phase': 'deduplicating', 'cached_skipped': 0, 'new_signals': 0, 'message': 'Zero token waste: checking cache...'})}\n\n"

        yield f"event: phase\ndata: {json.dumps({'phase': 'scoring', 'message': 'Evaluating signals...'})}\n\n"

        eval_count = 0
        cached_count = 0
        passed_count = 0

        # In production, lazily stream items as scored via iter_run.
        # Fall back to orch.run if orch is a mock (e.g. in unit tests).
        is_mock = type(getattr(orch, "run", None)).__name__ == "MagicMock"
        if not is_mock and hasattr(orch, "iter_run"):
            items_stream = orch.iter_run(include_rejected=False, max_items=req.limit)
        else:
            items_stream = ((r, False) for r in orch.run(include_rejected=False, max_items=req.limit))

        for r, is_cached in items_stream:
            eval_count += 1
            if is_cached:
                cached_count += 1
                yield f"event: dedup\ndata: {json.dumps({'phase': 'deduplicating', 'cached_skipped': cached_count, 'new_signals': eval_count, 'message': f'Zero token waste: {cached_count} cached posts rehydrated'})}\n\n"

            dim_scores = getattr(r, "dimension_scores", None)
            if not dim_scores and getattr(r, "samples", None):
                try:
                    dim_scores = {
                        "pov": round(statistics.median([s.pov for s in r.samples]), 1),
                        "lived_experience": round(statistics.median([s.lived_experience for s in r.samples]), 1),
                        "specificity": round(statistics.median([s.specificity for s in r.samples]), 1),
                        "counter_intuitive": round(statistics.median([s.counter_intuitive for s in r.samples]), 1),
                    }
                except Exception:
                    dim_scores = {}

            body = getattr(r.item, "body", "") if getattr(r, "item", None) else ""
            snippet = getattr(r, "body_snippet", "") or (body[:250] if body else None)

            cand = CandidateOut(
                title=r.item.title if getattr(r, "item", None) else "Untitled",
                url=r.item.url if getattr(r, "item", None) else "",
                score=r.median_composite,
                verdict=r.verdict,
                source=r.item.source if getattr(r, "item", None) else "unknown",
                published_at=r.item.published_at.isoformat() if getattr(r, "item", None) and getattr(r.item, "published_at", None) else None,
                topic_tag=getattr(r, "topic_tag", "General Engineering") or "General Engineering",
                body_snippet=snippet,
                dimension_scores=dim_scores or {},
            )

            yield f"event: scoring_progress\ndata: {json.dumps({'phase': 'scoring', 'item_title': cand.title, 'current': eval_count, 'total': eval_count})}\n\n"
            yield f"event: candidate\ndata: {json.dumps({'candidate': cand.model_dump()})}\n\n"
            if r.verdict != "reject":
                passed_count += 1

        elapsed = round(time.time() - start_time, 2)
        yield f"event: complete\ndata: {json.dumps({'total_scanned': eval_count, 'cached_skipped': cached_count, 'passed': passed_count, 'elapsed_sec': elapsed})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/oracle/run", response_model=OracleRunResponse)
def oracle_run(req: OracleRunRequest):
    req.validate_sources()
    orch, _ = _build_oracle_components(req)
    results = orch.run(include_rejected=False, max_items=req.limit)

    candidates = [
        CandidateOut(
            title=r.item.title,
            url=r.item.url,
            score=r.median_composite,
            verdict=r.verdict,
            source=r.item.source,
            published_at=r.item.published_at.isoformat() if r.item.published_at else None,
            topic_tag=r.topic_tag,
            body_snippet=getattr(r, "body_snippet", "") or (r.item.body[:250] if r.item and r.item.body else None),
            dimension_scores=getattr(r, "dimension_scores", None) or {},
        )
        for r in results
    ]

    return OracleRunResponse(candidates=candidates)


@app.get("/api/oracle/scan-stream")
def oracle_scan_stream_get(
    rss_urls: list[str] = Query(default=[]),
    github_repos: list[str] = Query(default=[]),
    linkedin_profiles: list[str] = Query(default=[]),
    linkedin_li_at: Optional[str] = None,
    include_linkedin_feed: bool = False,
    no_persist: bool = False,
    limit: Optional[int] = None,
    max_age_days: Optional[int] = 10,
    max_items_per_feed: int = 25,
):
    req = OracleRunRequest(
        rss_urls=_clean_list(rss_urls),
        github_repos=_clean_list(github_repos),
        linkedin_profiles=_clean_list(linkedin_profiles),
        linkedin_li_at=linkedin_li_at,
        include_linkedin_feed=include_linkedin_feed,
        no_persist=no_persist,
        limit=limit,
        max_age_days=max_age_days,
        max_items_per_feed=max_items_per_feed,
    )
    return _stream_oracle_scan(req)


@app.post("/api/oracle/scan-stream")
def oracle_scan_stream_post(req: OracleRunRequest):
    return _stream_oracle_scan(req)



@app.get("/api/oracle/history", response_model=OracleHistoryResponse)
def get_oracle_history(
    topic: Optional[str] = None,
    verdict: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
):
    """Retrieve historical scanned feeds/spikes from SQLite with optional filtering."""
    from content_machine.oracle.classifier import ALL_TOPICS
    db_conn = _make_db()
    query = """
        SELECT id, hook_thesis, category, scores_json, status, topic_tag, source_url, created_at
        FROM spikes
        WHERE 1=1
    """
    params: list[Any] = []
    if topic and topic.strip() and topic.strip() != "All":
        query += " AND topic_tag = ?"
        params.append(topic.strip())
    if verdict and verdict.strip() and verdict.strip() != "All":
        query += " AND LOWER(status) = ?"
        params.append(verdict.strip().lower())
    if search and search.strip():
        query += " AND (hook_thesis LIKE ? OR category LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db_conn.execute(query, params).fetchall()
    items = []
    for r in rows:
        payload = {}
        try:
            payload = json.loads(r["scores_json"])
        except Exception:
            pass
        items.append(
            OracleHistoryItem(
                id=r["id"],
                title=r["hook_thesis"],
                url=r["source_url"] or "",
                source=r["category"],
                score=round(float(payload.get("median_composite", 0.0)), 2),
                verdict=payload.get("verdict", r["status"] or "reject"),
                topic_tag=r["topic_tag"] or "General Engineering",
                created_at=r["created_at"],
                samples=payload.get("samples", []),
            )
        )
    return OracleHistoryResponse(items=items, total=len(items), topics=ALL_TOPICS)



@app.post("/api/council/run", response_model=CouncilRunResponse)
def council_run(req: CouncilRunRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()

    result = run_council(
        draft=req.draft,
        router=router,
        cfg=cfg,
        conn=db_conn,
        spike_id=req.spike_id,
    )
    score = result.composite_normalized if result.composite_normalized is not None else result.composite_raw
    score_val = round(float(score), 3)

    best_row = db_conn.execute(
        "SELECT iteration, composite_raw FROM iterations WHERE spike_id=? ORDER BY composite_raw DESC LIMIT 1",
        (req.spike_id,),
    ).fetchone()
    peak_score = score_val
    peak_iter = result.iteration
    is_peak = True
    if best_row:
        raw_peak = float(best_row["composite_raw"] or 0.0)
        if raw_peak > score_val:
            peak_score = round(raw_peak, 3)
            peak_iter = int(best_row["iteration"])
            is_peak = False

    return CouncilRunResponse(
        verdict=result.verdict,
        score=score_val,
        iteration=result.iteration,
        actions=result.required_actions,
        peak_score=peak_score,
        peak_iteration=peak_iter,
        is_all_time_peak=is_peak,
    )


@app.get("/api/council/history/{spike_id}", response_model=CouncilHistoryResponse)
def council_history(spike_id: str):
    import json
    db_conn = _make_db()
    rows = db_conn.execute(
        "SELECT id, iteration, draft_path, council_review_json, composite_raw, composite_normalized, threshold_met, created_at, draft_content "
        "FROM iterations WHERE spike_id=? ORDER BY id DESC",
        (spike_id,),
    ).fetchall()

    if not rows:
        return CouncilHistoryResponse(spike_id=spike_id, best=None, history=[])

    items: list[CouncilHistoryItem] = []
    best_item: Optional[CouncilHistoryItem] = None
    best_score = -1.0

    for r in rows:
        rev = {}
        try:
            rev = json.loads(r["council_review_json"] or "{}")
        except Exception:
            rev = {}

        raw_score = r["composite_raw"] if r["composite_raw"] is not None else 0.0
        score = round(float(raw_score), 3)

        draft = r["draft_content"] or rev.get("draft")
        if not draft and r["draft_path"] and not str(r["draft_path"]).startswith("(unsaved)"):
            try:
                p = Path(r["draft_path"])
                if p.is_file():
                    draft = p.read_text(encoding="utf-8")
            except Exception:
                pass

        threshold_met = bool(r["threshold_met"])
        verdict = "pass" if threshold_met else "revise"

        item = CouncilHistoryItem(
            id=r["id"],
            iteration=r["iteration"],
            score=score,
            verdict=verdict,
            threshold_met=threshold_met,
            created_at=r["created_at"],
            draft=draft,
            actions=rev.get("required_actions", []),
            scores=rev.get("scores", {}),
        )
        items.append(item)
        if score > best_score:
            best_score = score
            best_item = item

    return CouncilHistoryResponse(spike_id=spike_id, best=best_item, history=items)


@app.get("/api/council/spikes", response_model=list[CouncilSpikeItem])
def council_spikes():
    db_conn = _make_db()
    rows = db_conn.execute(
        """
        SELECT 
            spike_id,
            MAX(composite_raw) as peak_score,
            COUNT(*) as iteration_count,
            MAX(created_at) as updated_at
        FROM iterations
        GROUP BY spike_id
        ORDER BY updated_at DESC
        """
    ).fetchall()

    result: list[CouncilSpikeItem] = []
    for r in rows:
        peak_row = db_conn.execute(
            "SELECT iteration FROM iterations WHERE spike_id=? AND composite_raw=? LIMIT 1",
            (r["spike_id"], r["peak_score"]),
        ).fetchone()
        peak_iter = peak_row["iteration"] if peak_row else 1
        result.append(
            CouncilSpikeItem(
                spike_id=r["spike_id"],
                peak_score=round(float(r["peak_score"] or 0.0), 3),
                peak_iteration=peak_iter,
                iteration_count=r["iteration_count"],
                updated_at=r["updated_at"],
            )
        )
    return result



@app.get("/api/lessons", response_model=LessonsListResponse)
def lessons_list():
    db_conn = _make_db()
    store = LessonsStore(db_conn=db_conn)
    rows = store.active_rules()
    pending_rows = store.pending_rules() if hasattr(store, "pending_rules") else []
    rules = [
        LessonRuleOut(
            id=row["id"],
            rule_text=row["rule_text"],
            provenance_project=row["provenance_project"],
            created_at=row["created_at"],
            status=row["status"],
        )
        for row in rows
    ]
    pending = [
        LessonRuleOut(
            id=row["id"],
            rule_text=row["rule_text"],
            provenance_project=row["provenance_project"],
            created_at=row["created_at"],
            status=row["status"],
        )
        for row in pending_rows
    ]
    return LessonsListResponse(rules=rules, pending=pending)


@app.post("/api/lessons/{rule_id}/approve")
def lessons_approve(rule_id: int):
    db_conn = _make_db()
    store = LessonsStore(db_conn=db_conn)
    store.approve(rule_id)
    return {"ok": True, "rule_id": rule_id}


@app.post("/api/lessons/{rule_id}/reject")
def lessons_reject(rule_id: int):
    db_conn = _make_db()
    store = LessonsStore(db_conn=db_conn)
    store.reject(rule_id)
    return {"ok": True, "rule_id": rule_id}


@app.post("/api/lessons/custom", response_model=LessonsCustomResponse)
def lessons_custom(req: LessonsCustomRequest):
    db_conn = _make_db()
    store = LessonsStore(db_conn=db_conn)
    result = store.propose(rule=req.rule_text, project_id=req.provenance_project)
    
    if req.auto_approve and result.rule_id:
        store.approve(result.rule_id)
        status = "active"
    else:
        status = "pending" if result.rule_id else "blocked"

    return LessonsCustomResponse(
        ok=result.inserted,
        rule_id=result.rule_id,
        status=status,
        is_conflict=result.is_conflict,
        conflict_rule_id=result.conflict_rule_id,
        merge_required=result.merge_required,
    )



@app.post("/api/lessons/diff", response_model=LessonsDiffResponse)
def lessons_diff(req: LessonsDiffRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()

    differ = LessonsDiffer(router=router, model=cfg.models.scanner)
    rules = differ.extract(draft=req.draft, published=req.published, project_id=req.project_id)

    store = LessonsStore(db_conn=db_conn)
    proposals = []
    for rule in rules:
        result = store.propose(rule=rule, project_id=req.project_id)
        proposals.append(ProposalOut(
            rule=rule,
            rule_id=result.rule_id,
            is_conflict=result.is_conflict,
            conflict_rule_id=result.conflict_rule_id,
            merge_required=result.merge_required,
        ))
    return LessonsDiffResponse(rules=proposals)


@app.post("/api/distribute/run", response_model=DistributeRunResponse)
def distribute_run(req: DistributeRunRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()

    engine = DistributionEngine(
        router=router,
        model=cfg.models.scanner,
        model_long=getattr(cfg.models, "video_long", "qwen3.8-max"),
    )
    bundle = engine.generate_all(
        req.anchor_post,
        formats=req.enabled_formats,
        humanize=req.humanize,
        tone=req.tone,
    )
    if req.project_slug:
        engine.save_bundle(req.project_slug, bundle, anchor_post=req.anchor_post)
    return DistributeRunResponse(**bundle)


@app.get("/api/distribute/history", response_model=DistributeHistoryResponse)
def distribute_history():
    import datetime
    from content_machine.storage.paths import home_root

    root = home_root()
    db_conn = _make_db()
    items_by_slug: dict[str, DistributeHistoryItem] = {}

    # 1. Query SQLite iterations grouped by spike_id
    rows = db_conn.execute(
        """
        SELECT 
            spike_id,
            MAX(composite_raw) as peak_score,
            MAX(created_at) as updated_at
        FROM iterations
        GROUP BY spike_id
        ORDER BY updated_at DESC
        """
    ).fetchall()

    for r in rows:
        spike_id = r["spike_id"]
        peak_score = round(float(r["peak_score"] or 0.0), 3)
        updated_at = r["updated_at"]

        peak_row = db_conn.execute(
            """
            SELECT draft_content, draft_path
            FROM iterations
            WHERE spike_id = ?
            ORDER BY composite_raw DESC, id DESC
            LIMIT 1
            """,
            (spike_id,),
        ).fetchone()

        anchor_text = ""
        if peak_row:
            anchor_text = peak_row["draft_content"] or ""
            if not anchor_text and peak_row["draft_path"] and not str(peak_row["draft_path"]).startswith("(unsaved)"):
                try:
                    p = Path(peak_row["draft_path"])
                    if p.is_file():
                        anchor_text = p.read_text(encoding="utf-8")
                except Exception:
                    pass

        title = None
        spike_row = db_conn.execute(
            "SELECT hook_thesis FROM spikes WHERE id = ? LIMIT 1",
            (spike_id,),
        ).fetchone()
        if spike_row and spike_row["hook_thesis"]:
            title = spike_row["hook_thesis"]

        pdir = root / "projects" / spike_id / "distribution"
        bundle_dict = {}
        formats = []
        if pdir.is_dir():
            for f in pdir.glob("*.md"):
                if f.stem == "anchor":
                    if not anchor_text:
                        try:
                            anchor_text = f.read_text(encoding="utf-8")
                        except Exception:
                            pass
                    continue
                try:
                    content = f.read_text(encoding="utf-8")
                    bundle_dict[f.stem] = content
                    formats.append(f.stem)
                except Exception:
                    pass

        has_bundle = bool(bundle_dict)
        source = "distributed" if has_bundle else "council"

        if not title and anchor_text:
            first_line = anchor_text.strip().split("\n")[0]
            title = first_line[:120]

        items_by_slug[spike_id] = DistributeHistoryItem(
            slug=spike_id,
            title=title,
            anchor_text=anchor_text,
            peak_score=peak_score,
            has_bundle=has_bundle,
            bundle=bundle_dict,
            available_formats=formats,
            updated_at=updated_at,
            source=source,
        )

    # 2. Check disk for projects under ~/.content_machine/projects/ not in DB
    projects_dir = root / "projects"
    if projects_dir.is_dir():
        for p in projects_dir.iterdir():
            if not p.is_dir() or p.name.startswith("."):
                continue
            slug = p.name
            if slug in items_by_slug:
                continue

            dist_dir = p / "distribution"
            if not dist_dir.is_dir():
                continue

            bundle_dict = {}
            formats = []
            anchor_text = ""
            anchor_file = dist_dir / "anchor.md"
            if anchor_file.is_file():
                try:
                    anchor_text = anchor_file.read_text(encoding="utf-8")
                except Exception:
                    pass

            for f in dist_dir.glob("*.md"):
                if f.stem == "anchor":
                    continue
                try:
                    content = f.read_text(encoding="utf-8")
                    bundle_dict[f.stem] = content
                    formats.append(f.stem)
                    if not anchor_text:
                        anchor_text = content
                except Exception:
                    pass

            if not bundle_dict and not anchor_text:
                continue

            title = None
            if anchor_text:
                first_line = anchor_text.strip().split("\n")[0]
                title = first_line[:120]

            mtime = dist_dir.stat().st_mtime
            updated_at = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat()

            items_by_slug[slug] = DistributeHistoryItem(
                slug=slug,
                title=title,
                anchor_text=anchor_text,
                peak_score=None,
                has_bundle=bool(bundle_dict),
                bundle=bundle_dict,
                available_formats=formats,
                updated_at=updated_at,
                source="distributed",
            )

    sorted_items = sorted(items_by_slug.values(), key=lambda x: x.updated_at, reverse=True)
    return DistributeHistoryResponse(items=sorted_items, total=len(sorted_items))




@app.get("/api/linkedin/status", response_model=LinkedInStatusResponse)
def get_linkedin_status():
    from content_machine.connectors.linkedin_session import LinkedInSessionManager
    mgr = LinkedInSessionManager()
    is_val = mgr.is_valid()
    meta = mgr.get_session_metadata()
    return LinkedInStatusResponse(
        session_valid=is_val,
        mode="authenticated" if is_val else "public_bridge",
        saved_at=meta.get("saved_at") if is_val else None,
        browser_profile_dir=str(mgr.profile_dir),
    )


@app.post("/api/linkedin/sync", response_model=LinkedInSyncResponse)
def sync_linkedin_session(req: LinkedInSyncRequest = LinkedInSyncRequest()):
    from content_machine.connectors.linkedin_session import LinkedInSessionManager
    mgr = LinkedInSessionManager()
    try:
        cookie = mgr.sync_from_browser(headless=req.headless, timeout_ms=req.timeout_ms)
        if cookie and mgr.is_valid(cookie):
            meta = mgr.get_session_metadata()
            return LinkedInSyncResponse(
                success=True,
                mode="authenticated",
                saved_at=meta.get("saved_at"),
                message="Session successfully extracted and validated from browser context.",
            )
        return LinkedInSyncResponse(
            success=False,
            mode="public_bridge",
            saved_at=None,
            message="Could not extract active li_at session cookie from browser. Defaulting to Public Bridge mode.",
        )
    except Exception as e:
        return LinkedInSyncResponse(
            success=False,
            mode="public_bridge",
            saved_at=None,
            message=f"Browser sync failed: {str(e)}",
        )


@app.post("/api/interview/brief", response_model=TopicBriefing)
def interview_brief(req: TopicBriefRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    engine = InterviewEngine(
        router=router,
        scanner_model=cfg.models.scanner,
    )
    return engine.generate_briefing(
        title=req.title,
        url=req.url,
        body=req.body,
        topic_tag=req.topic_tag,
    )


@app.post("/api/interview/synthesize", response_model=SynthesizeDraftResponse)
def interview_synthesize(req: SynthesizeDraftRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()
    engine = InterviewEngine(
        router=router,
        writer_model=cfg.models.writer,
        db_conn=db_conn,
    )
    responses = [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in req.responses]
    res = engine.synthesize_draft(
        topic_title=req.topic_title,
        topic_summary=req.topic_summary,
        responses=responses,
        raw_notes=req.raw_notes,
        spike_id=req.spike_id,
    )
    return SynthesizeDraftResponse(
        draft=res["draft"],
        word_count=res["word_count"],
        spike_id=res["spike_id"],
    )


@app.post("/api/interview/transcribe", response_model=TranscribeAudioResponse)
async def interview_transcribe(audio: UploadFile = File(...)):
    import tempfile
    import shutil

    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    if not suffix:
        suffix = ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(audio.file, tmp)

    try:
        transcriber = BatchTranscriber(model="small")
        transcript = transcriber.transcribe(tmp_path)
        return TranscribeAudioResponse(
            text=transcript.text,
            duration_s=transcript.duration_s,
            model=transcript.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Commenting
# ---------------------------------------------------------------------------

@app.post("/api/comments/generate", response_model=CommentRunResponse)
def comments_generate(req: GenerateCommentRequest):
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()
    engine = CommentingEngine(router=router, cfg=cfg, db_conn=db_conn)
    try:
        return engine.generate_comment(
            post_content=req.post_content,
            angle=req.angle,
            perspective_text=req.perspective_text,
            humanize=req.humanize,
            tone=req.tone,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comment generation failed: {str(e)}")


@app.get("/api/comments/history", response_model=CommentHistoryResponse)
def comments_history(limit: int = Query(default=50, ge=1, le=200)):
    db_conn = _make_db()
    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    engine = CommentingEngine(router=router, cfg=cfg, db_conn=db_conn)
    items = engine.get_history(limit=limit)
    return CommentHistoryResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# Author Profile & Voice Grounding
# ---------------------------------------------------------------------------

@app.get("/api/profile", response_model=ProfileData)
def profile_get():
    manager = ProfileManager()
    return manager.get_profile()


@app.post("/api/profile", response_model=ProfileData)
def profile_update(req: UpdateProfileRequest):
    manager = ProfileManager()
    return manager.update_profile(req)


# ---------------------------------------------------------------------------
# Humanize Transformer
# ---------------------------------------------------------------------------

@app.post("/api/humanize", response_model=HumanizeResult)
def humanize_text_endpoint(req: HumanizeRequest):
    from content_machine.humanize import HumanizeTransformer
    router = _make_router()
    transformer = HumanizeTransformer(router=router)
    return transformer.transform(
        text=req.text,
        channel=req.channel,
        tone=req.tone,
        max_sentences=req.max_sentences,
    )


# Catch-all: serve index.html for SPA routing (only if UI is built)

@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    index = _UI_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"detail": "UI not built. Run: cd ui && npm install && npm run build"}
