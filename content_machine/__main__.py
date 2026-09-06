"""Content Machine CLI — python -m content_machine <subcommand>

Subcommands
-----------
oracle      Pull connectors, score ideas, print ranked candidates.
council     Run Writer's Council on a draft file.
transcribe  Batch-transcribe an audio file with faster-whisper.
lessons     Manage the governed lessons store.
comment     Synthesize and vet senior-level LinkedIn comments.

Examples
--------
    python -m content_machine oracle --rss https://example.com/feed
    python -m content_machine oracle --github org/repo
    python -m content_machine council projects/2026-09-04_ai-ops/iterations/draft_v1.md
    python -m content_machine transcribe recordings/interview.wav --model small
    python -m content_machine lessons diff draft_v1.md published_final.md
    python -m content_machine lessons list
    python -m content_machine lessons approve 12
    python -m content_machine lessons reject 12
    python -m content_machine comment --post "Scaling MySQL to 10M rows" --angle insightful
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---- subsystem imports (each imported at top so patch() works in tests) ----
from content_machine.asr.batch import BatchTranscriber
from content_machine.commenting.engine import CommentingEngine
from content_machine.connectors.github import GitHubConnector
from content_machine.connectors.linkedin import LinkedInConnector
from content_machine.connectors.rss import RSSConnector
from content_machine.council.loop import run_council
from content_machine.distribution.engine import DistributionEngine
from content_machine.lessons.differ import LessonsDiffer
from content_machine.lessons.store import LessonsStore
from content_machine.oracle.oracle import OracleOrchestrator
from content_machine.oracle.scorer import IdeaScorer


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_router():
    """Build a ModelRouter from config.json / environment."""
    from content_machine.config import load_config
    from content_machine.router.base import ModelRouter, Route
    from content_machine.router.messages_adapter import MessagesAdapter

    cfg = load_config()

    routes: dict = {}
    for name, rc in cfg.routes.items():
        base_url = os.environ.get(rc.base_url_env, "") if rc.base_url_env else rc.base_url or ""
        auth_token = os.environ.get(rc.auth_token_env, "") if rc.auth_token_env else rc.auth_token or ""
        api_key = os.environ.get(rc.api_key_env, "") if rc.api_key_env else rc.api_key or ""
        adapter = MessagesAdapter(
            base_url=base_url,
            auth_token=auth_token or api_key,
        )
        routes[name] = Route(name=name, protocol=rc.protocol, adapter=adapter)

    return ModelRouter(
        routes=routes,
        route_models=cfg.route_models,
        preferred_max_latency_s=cfg.thresholds.preferred_max_latency_s,
    )


def _make_db():
    """Open the live SQLite database."""
    from content_machine.storage.db import connect
    return connect()


# ---------------------------------------------------------------------------
# oracle
# ---------------------------------------------------------------------------

def _cmd_oracle(args: argparse.Namespace) -> int:
    from content_machine.config import load_config
    cfg = load_config()

    db_conn = None if getattr(args, "no_persist", False) else _make_db()
    connectors = []
    max_age_days = getattr(args, "max_age_days", None)
    max_items_per_feed = getattr(args, "max_items_per_feed", 25)

    if args.rss:
        for url in args.rss:
            connectors.append(
                RSSConnector(
                    url=url,
                    db_conn=db_conn,
                    max_age_days=max_age_days,
                    max_items=max_items_per_feed,
                )
            )
    if args.github:
        pat = os.environ.get("GITHUB_PAT", "")
        for repo in args.github:
            connectors.append(GitHubConnector(repo=repo, pat=pat))
    if getattr(args, "linkedin", None):
        li_cookie = getattr(args, "li_at", None) or os.environ.get("LINKEDIN_LI_AT", "")
        for target in args.linkedin:
            profile = None if target.lower() in ("feed", "home", "me") else target
            connectors.append(LinkedInConnector(li_at=li_cookie, profile=profile))
    if getattr(args, "from_config", False):
        from content_machine.config import get_category_default_max_age_days
        for f in getattr(cfg, "rss_feeds", []):
            if getattr(f, "enabled", True):
                feed_max_age = f.max_age_days if getattr(f, "max_age_days", None) is not None else max_age_days
                if feed_max_age is None:
                    feed_max_age = get_category_default_max_age_days(getattr(f, "category", ""))
                feed_max_items = f.max_items if getattr(f, "max_items", None) is not None else max_items_per_feed
                connectors.append(
                    RSSConnector(
                        url=f.url,
                        source_name=getattr(f, "name", None),
                        db_conn=db_conn,
                        max_age_days=feed_max_age,
                        max_items=feed_max_items,
                    )
                )


    if not connectors:
        print("error: provide at least one source: --rss <url>, --github <owner/repo>, --linkedin <profile/feed>, or --from-config",
              file=sys.stderr)
        return 1

    if getattr(args, "fetch_only", False):
        all_items = []
        for c in connectors:
            res = c.fetch()
            for it in res.items:
                all_items.append(it)
        if not all_items:
            print("No items fetched.")
            return 0
        print(f"\n{'#':>3}  {'Source':14}  Title")
        print("-" * 80)
        for i, it in enumerate(all_items, 1):
            print(f"{i:>3}  {it.source[:14]:14}  {it.title[:58]}")
        print(f"\nTotal ingested items: {len(all_items)}\n")
        return 0

    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()

    scorer = IdeaScorer(
        router=router,
        scanner_model=cfg.models.scanner,
        n_samples=cfg.thresholds.idea_samples,
        idea_gate=cfg.thresholds.idea_gate,
        idea_margin=cfg.thresholds.idea_margin,
    )
    db_conn = _make_db() if not args.no_persist else None
    orch = OracleOrchestrator(connectors=connectors, scorer=scorer, db_conn=db_conn)

    include_rejected = getattr(args, "all", False)
    limit = getattr(args, "limit", None)
    results = orch.run(include_rejected=include_rejected, max_items=limit)

    if not results:
        print("No candidates found (all rejected or no items fetched).")
        return 0

    width = 60
    print(f"\n{'#':>3}  {'Score':>6}  {'Verdict':8}  Title")
    print("-" * (width + 24))
    for i, r in enumerate(results, 1):
        title = r.item.title[:width]
        print(f"{i:>3}  {r.median_composite:>6.2f}  {r.verdict:8}  {title}")
    print()
    return 0


# ---------------------------------------------------------------------------
# council
# ---------------------------------------------------------------------------

def _cmd_council(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft)
    if not draft_path.exists():
        print(f"error: file not found: {draft_path}", file=sys.stderr)
        return 1

    draft_text = draft_path.read_text(encoding="utf-8")

    from content_machine.config import load_config

    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()

    result = run_council(
        draft=draft_text,
        router=router,
        cfg=cfg,
        db_conn=db_conn,
        spike_id=getattr(args, "spike_id", None) or "cli-session",
    )

    print(f"\nCouncil result — iteration {result.iteration}")
    print(f"  Verdict  : {result.verdict}")
    print(f"  Score    : {result.composite_normalized:.3f} (normalized)")
    if result.required_actions:
        print("  Actions  :")
        for action in result.required_actions:
            print(f"    • {action}")
    print()
    return 0


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

def _cmd_transcribe(args: argparse.Namespace) -> int:
    bt = BatchTranscriber(model=args.model)
    try:
        transcript = bt.transcribe(args.audio)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"\nTranscript ({transcript.model}, {transcript.word_count} words)")
    print("-" * 60)
    print(transcript.text)
    print()

    if args.save:
        out = Path(args.save)
        transcript.save(out)
        print(f"Saved to: {out}")
    return 0


# ---------------------------------------------------------------------------
# lessons
# ---------------------------------------------------------------------------

def _cmd_lessons(args: argparse.Namespace) -> int:
    action = args.lessons_action

    db_conn = _make_db()
    store = LessonsStore(db_conn=db_conn)

    if action == "list":
        rules = store.active_rules()
        if not rules:
            print("No active lessons yet.")
            return 0
        print(f"\n{'ID':>4}  Rule")
        print("-" * 70)
        for row in rules:
            print(f"{row['id']:>4}  {row['rule_text']}")
        print()

    elif action == "approve":
        store.approve(int(args.rule_id))
        print(f"Rule {args.rule_id} approved (status → active).")

    elif action == "reject":
        store.reject(int(args.rule_id))
        print(f"Rule {args.rule_id} rejected.")

    elif action == "diff":
        draft_path = Path(args.draft_file)
        pub_path = Path(args.published_file)
        if not draft_path.exists():
            print(f"error: file not found: {draft_path}", file=sys.stderr)
            return 1
        if not pub_path.exists():
            print(f"error: file not found: {pub_path}", file=sys.stderr)
            return 1

        draft_text = draft_path.read_text(encoding="utf-8")
        pub_text = pub_path.read_text(encoding="utf-8")
        project_id = getattr(args, "project_id", None) or draft_path.stem

        router = _make_router()
        from content_machine.config import load_config
        cfg = load_config()
        differ = LessonsDiffer(router=router, model=cfg.models.scanner)

        rules = differ.extract(draft=draft_text, published=pub_text,
                               project_id=project_id)

        print(f"\nExtracted {len(rules)} rule(s):\n")
        for i, rule in enumerate(rules, 1):
            result = store.propose(rule=rule, project_id=project_id)
            status = f"[id={result.rule_id}]"
            if result.merge_required:
                status += " ⚠ MERGE REQUIRED (cap reached)"
            elif result.is_conflict:
                status += f" ⚠ CONFLICT with rule #{result.conflict_rule_id}"
                print(f"  {i}. {rule}  {status}  — conflict")
                continue
            print(f"  {i}. {rule}  {status}")

        print("\nRun `lessons approve <id>` or `lessons reject <id>` to review pending rules.")

    return 0


# ---------------------------------------------------------------------------
# distribute
# ---------------------------------------------------------------------------

def _cmd_distribute(args: argparse.Namespace) -> int:
    post_path = Path(args.post_file)
    if not post_path.exists():
        print(f"error: file not found: {post_path}", file=sys.stderr)
        return 1

    anchor_text = post_path.read_text(encoding="utf-8")
    slug = args.slug or post_path.stem

    from content_machine.config import load_config
    cfg = load_config()
    router = _make_router()
    engine = DistributionEngine(router=router, model=cfg.models.scanner)

    print(f"\nTransforming anchor post '{slug}' into derivative formats...")
    bundle = engine.generate_all(anchor_text)

    if args.save:
        out_dir = engine.save_bundle(project_slug=slug, bundle=bundle)
        print(f"Saved platform assets to: {out_dir}\n")

    print("=== 1. X (Twitter) Thread ===")
    print(bundle["x_thread"][:300] + ("...\n" if len(bundle["x_thread"]) > 300 else "\n"))
    print("=== 2. Short-Form Video Script ===")
    print(bundle["video_script"][:300] + ("...\n" if len(bundle["video_script"]) > 300 else "\n"))
    print("=== 3. Executive Newsletter Digest ===")
    print(bundle["newsletter"][:300] + ("...\n" if len(bundle["newsletter"]) > 300 else "\n"))

    return 0


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------

def _cmd_serve(args: argparse.Namespace) -> int:
    """Launch the FastAPI backend with uvicorn."""
    import uvicorn
    uvicorn.run(
        "content_machine.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


# ---------------------------------------------------------------------------
# comment
# ---------------------------------------------------------------------------

def _cmd_comment(args: argparse.Namespace) -> int:
    from content_machine.config import load_config
    from content_machine.schemas import CommentAngle

    post_content = getattr(args, "post", None)
    if not post_content:
        print("error: --post cannot be empty", file=sys.stderr)
        return 1

    angle_raw = getattr(args, "angle", "insightful")
    try:
        angle = CommentAngle(angle_raw.lower())
    except (ValueError, AttributeError):
        angle = CommentAngle.INSIGHTFUL

    perspective = getattr(args, "perspective", None)

    cfg = load_config()
    router = _make_router()
    db_conn = _make_db()

    engine = CommentingEngine(router=router, cfg=cfg, db_conn=db_conn)
    result = engine.generate_comment(
        post_content=post_content,
        angle=angle,
        perspective_text=perspective,
    )

    print(f"\nPolished Comment ({result.verdict} — peak score: {result.peak_score:.2f}, iteration: {result.iteration}):")
    print("-" * 60)
    print(result.final_comment)
    print("-" * 60)
    if result.judge_scores:
        print("Council Breakdown:")
        for judge, score in result.judge_scores.items():
            critique = result.judge_critiques.get(judge, "")
            if critique:
                print(f"  * {judge}: {score:.2f} — {critique}")
            else:
                print(f"  * {judge}: {score:.2f}")
    if result.actions:
        print("Required Actions:")
        for action in result.actions:
            print(f"  - {action}")
    print()
    return 0



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="content_machine",
        description="Content Machine — AI-augmented content pipeline.",
    )
    sub = parser.add_subparsers(dest="command")

    # oracle
    p_oracle = sub.add_parser("oracle", help="Pull connectors, score ideas.")
    p_oracle.add_argument("--rss", metavar="URL", action="append",
                          help="RSS/Atom feed URL (repeatable).")
    p_oracle.add_argument("--github", metavar="OWNER/REPO", action="append",
                          help="GitHub repo slug (repeatable). Reads GITHUB_PAT from env.")
    p_oracle.add_argument("--linkedin", metavar="PROFILE_OR_FEED", action="append",
                          help="LinkedIn profile slug (e.g. 'jane-founder') or 'feed' (repeatable). Reads LINKEDIN_LI_AT.")
    p_oracle.add_argument("--li-at", metavar="COOKIE",
                          help="LinkedIn li_at session cookie value (or set LINKEDIN_LI_AT env var).")
    p_oracle.add_argument("--all", action="store_true",
                          help="Include rejected ideas in output.")
    p_oracle.add_argument("--no-persist", action="store_true",
                          help="Skip DB persistence (dry-run).")
    p_oracle.add_argument("--from-config", action="store_true",
                          help="Pull from all enabled RSS and LinkedIn proxy feeds configured in config.json.")
    p_oracle.add_argument("--fetch-only", action="store_true",
                          help="Fetch and display raw items without running LLM scoring.")
    p_oracle.add_argument("--limit", type=int, default=None,
                          help="Maximum number of items to score.")
    p_oracle.add_argument("--max-age-days", type=int, default=None,
                          help="Filter out items older than this many days (default: category-aware).")
    p_oracle.add_argument("--max-items-per-feed", type=int, default=25,
                          help="Maximum items to ingest per RSS feed source (default: 25).")




    # council
    p_council = sub.add_parser("council", help="Run Writer's Council on a draft.")
    p_council.add_argument("draft", metavar="DRAFT_FILE",
                           help="Path to the draft Markdown file.")
    p_council.add_argument("--spike-id", metavar="ID",
                           help="Associate with an existing spike (default: cli-session).")

    # transcribe
    p_tx = sub.add_parser("transcribe", help="Batch-transcribe audio with faster-whisper.")
    p_tx.add_argument("audio", metavar="AUDIO_FILE",
                      help="Path to audio file (WAV/MP3/M4A).")
    p_tx.add_argument("--model", default="small",
                      choices=["tiny", "base", "small", "medium", "large-v3"],
                      help="Whisper model size (default: small).")
    p_tx.add_argument("--save", metavar="PATH",
                      help="Save transcript to this path as Markdown.")

    # lessons
    p_lessons = sub.add_parser("lessons", help="Manage the governed lessons store.")
    lessons_sub = p_lessons.add_subparsers(dest="lessons_action")

    lessons_sub.add_parser("list", help="List active lessons.")

    p_approve = lessons_sub.add_parser("approve", help="Approve a pending rule.")
    p_approve.add_argument("rule_id", metavar="ID", help="Lesson rule ID.")

    p_reject = lessons_sub.add_parser("reject", help="Reject a pending rule.")
    p_reject.add_argument("rule_id", metavar="ID", help="Lesson rule ID.")

    p_diff = lessons_sub.add_parser("diff",
                                    help="Extract lessons from draft vs published diff.")
    p_diff.add_argument("draft_file", metavar="DRAFT_FILE")
    p_diff.add_argument("published_file", metavar="PUBLISHED_FILE")
    p_diff.add_argument("--project-id", metavar="ID",
                        help="Project slug for provenance (default: draft filename stem).")

    # distribute
    p_dist = sub.add_parser("distribute", help="Transform anchor post into X thread, video script, and newsletter.")
    p_dist.add_argument("post_file", metavar="POST_FILE", help="Path to published anchor post markdown.")
    p_dist.add_argument("--slug", metavar="SLUG", help="Project slug to save output under (default: post file stem).")
    p_dist.add_argument("--no-save", action="store_true", help="Skip saving files to disk.")

    # serve
    p_serve = sub.add_parser("serve", help="Run the FastAPI backend and UI server.")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload for dev.")

    # comment
    p_comment = sub.add_parser("comment", help="Synthesize and vet senior-level LinkedIn comments.")
    p_comment.add_argument("--post", required=True, help="Content of the target LinkedIn post.")
    p_comment.add_argument("--angle", default="insightful",
                           choices=["insightful", "contrarian", "question"],
                           help="Comment angle: insightful, contrarian, question (default: insightful).")
    p_comment.add_argument("--perspective", default=None,
                           help="Operator's lived perspective or grounding context.")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Resolve save flag for distribute
    if hasattr(args, "no_save"):
        args.save = not args.no_save

    dispatch = {
        "oracle": _cmd_oracle,
        "council": _cmd_council,
        "transcribe": _cmd_transcribe,
        "lessons": _cmd_lessons,
        "distribute": _cmd_distribute,
        "serve": _cmd_serve,
        "comment": _cmd_comment,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
