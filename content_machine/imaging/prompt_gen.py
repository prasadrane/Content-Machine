"""ImagePromptGenerator: fill master-prompt §28 template per Windmill post.

Reads fact-checked drafts (IDEAS) + packaging metadata (PACKAGING) from the
Windmill Idea Bank xlsx, calls the router (qwen3.8-max, thinking high) to
fill the §28 POST-SPECIFIC INPUT TEMPLATE, validates structure, flags
fabricated numbers, writes back to PACKAGING column F, exports markdown.

The filled template is the per-post half of the image prompt; the design
system half lives in docs/linkedin_engineering_visual_master_prompt_v2.md
and is applied separately by the operator.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

logger = logging.getLogger(__name__)

REQUIRED_HEADERS = [
    "## POST TITLE",
    "## POST CONTENT / IDEA",
    "## CATEGORY",
    "## CORE ENGINEERING PROBLEM",
    "## TRIGGER",
    "## MECHANISM TO VISUALIZE",
    "## CONSEQUENCE",
    "## BETTER STATE / SOLUTION",
    "## IMPORTANT TECHNICAL LABELS",
    "## OPTIONAL TECHNICAL ARTIFACT",
    "## EXACT FACTS THAT MAY APPEAR",
]

SYSTEM_PROMPT = """You fill the POST-SPECIFIC INPUT TEMPLATE of the LinkedIn Engineering Visual System master prompt for one post. The template feeds an image generator; the design system (style, colors, layout) is supplied separately, so you write ONLY post-specific content.

Output ONLY the filled template below — exactly these 11 markdown headers in this order, each with content, nothing else (no preamble, no code fences):

## POST TITLE
## POST CONTENT / IDEA
## CATEGORY
## CORE ENGINEERING PROBLEM
## TRIGGER
## MECHANISM TO VISUALIZE
## CONSEQUENCE
## BETTER STATE / SOLUTION
## IMPORTANT TECHNICAL LABELS
## OPTIONAL TECHNICAL ARTIFACT
## EXACT FACTS THAT MAY APPEAR

Field rules:
- POST TITLE: the supplied final title, verbatim.
- POST CONTENT / IDEA: concise 2-4 sentence summary of the draft.
- CATEGORY: exactly one of AI ENGINEERING, DISTRIBUTED SYSTEMS, DATABASES, PERFORMANCE, SYSTEM DESIGN, CLOUD ENGINEERING, OBSERVABILITY, .NET, EVENT-DRIVEN SYSTEMS (or another clearly relevant engineering category), uppercase.
- CORE ENGINEERING PROBLEM / TRIGGER / MECHANISM TO VISUALIZE / CONSEQUENCE: short phrases (1-2 lines each), grounded strictly in the draft. MECHANISM describes how the problem happens internally.
- BETTER STATE / SOLUTION: only if the draft discusses a correction or alternative; otherwise write (none).
- IMPORTANT TECHNICAL LABELS: exact technical identifiers from the draft (e.g. .Result, UUIDv4, WCU, DLQ, traceparent); otherwise (none).
- OPTIONAL TECHNICAL ARTIFACT: exact code/log text ONLY if literally present in the draft; otherwise (none). Never invent code, command output, timings, metrics, error messages, or percentages.
- EXACT FACTS THAT MAY APPEAR: every exact number, version, model name, or command present in the draft that the image may use; otherwise (none).
- ZERO invented facts: any number, name, or value you write must appear literally in the supplied material. If a precise value is absent, stay qualitative ("high latency", "queue builds")."""

USER_PROMPT_TEMPLATE = """FINAL TITLE: {final_title}

IDEA TITLE: {idea_title}

THUMBNAIL RECOMMENDATION (composition hint only): {thumbnail_rec}

POST DRAFT:
{draft}"""

RETRY_SUFFIX = (
    "\n\nYour previous output was invalid: {problems}. "
    "Output ONLY the filled template with all 11 headers, each with content."
)

_NUMBER_RE = re.compile(r"\d+(?:[.,-]\d+)*")


@dataclass
class PostRow:
    row: int
    idea_title: str
    draft: str
    final_title: str
    thumbnail_rec: str


@dataclass
class GeneratedImagePrompt:
    row: int
    final_title: str
    text: str
    warnings: list[str] = field(default_factory=list)


def load_posts(
    xlsx_path: str | Path,
    first_row: int = 2,
    last_row: int | None = None,
) -> list[PostRow]:
    """Read row-aligned posts: IDEAS (title, draft) + PACKAGING (final title, thumbnail rec).

    Skips rows where both IDEAS title and draft are empty. Row numbers are
    preserved so write-back lands on the same sheet row.
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"Idea Bank Excel file not found at: {path}")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if "IDEAS" not in wb.sheetnames:
        raise ValueError(f"Sheet 'IDEAS' not found in workbook: {path}")

    ws_ideas = wb["IDEAS"]
    ws_pack = wb["PACKAGING"] if "PACKAGING" in wb.sheetnames else None

    end = last_row if last_row is not None else ws_ideas.max_row
    posts: list[PostRow] = []
    for row in range(first_row, end + 1):
        idea_title = ws_ideas.cell(row=row, column=1).value
        draft = ws_ideas.cell(row=row, column=2).value
        idea_title = str(idea_title).strip() if idea_title else ""
        draft = str(draft).strip() if draft else ""
        if not idea_title and not draft:
            continue

        final_title, thumbnail_rec = "", ""
        if ws_pack is not None:
            ft = ws_pack.cell(row=row, column=1).value
            tr = ws_pack.cell(row=row, column=5).value
            final_title = str(ft).strip() if ft else ""
            thumbnail_rec = str(tr).strip() if tr else ""

        posts.append(
            PostRow(
                row=row,
                idea_title=idea_title,
                draft=draft,
                final_title=final_title or idea_title,
                thumbnail_rec=thumbnail_rec,
            )
        )
    wb.close()
    return posts


def flag_fabricated_numbers(generated: str, source: str) -> list[str]:
    """Warn about numeric tokens in the generated template absent from source material.

    Pure guardrail: warnings are surfaced for human review, never silently dropped.
    """
    source_numbers = set(_NUMBER_RE.findall(source))
    generated_numbers = _NUMBER_RE.findall(generated)
    warnings: list[str] = []
    seen: set[str] = set()
    for n in generated_numbers:
        if n not in source_numbers and n not in seen:
            seen.add(n)
            warnings.append(f"number '{n}' appears in generated prompt but not in post source material")
    return warnings


def validate_template(text: str) -> list[str]:
    """Return list of structural problems; empty list = valid."""
    problems: list[str] = []
    for header in REQUIRED_HEADERS:
        if header not in text:
            problems.append(f"missing header: {header}")
    if problems:
        return problems

    # Each section must carry non-whitespace content.
    positions = [(text.index(h), h) for h in REQUIRED_HEADERS]
    positions.sort()
    for i, (pos, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[pos + len(header):end].strip()
        if not body:
            problems.append(f"empty section: {header}")
    return problems


def _strip_fences(text: str) -> str:
    """Remove a wrapping code fence if the model added one."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def export_markdown(results: list[GeneratedImagePrompt], out_path: str | Path) -> Path:
    """Write consolidated copy-paste export: one fenced §28 block per post."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# Windmill 25 Posts — Per-Post Image Prompts (§28 filled templates)",
        "",
        f"Generated: {now}",
        "",
        "Usage: paste the master design system (docs/linkedin_engineering_visual_master_prompt_v2.md,",
        "sections 1-27) into the image generator first, then paste one fenced block below per image.",
        "",
        "---",
        "",
    ]
    for r in results:
        parts.append(f"## Row {r.row} — {r.final_title}")
        parts.append("")
        if r.warnings:
            parts.append("**Review warnings:**")
            for w in r.warnings:
                parts.append(f"- {w}")
            parts.append("")
        parts.append("```text")
        parts.append(r.text)
        parts.append("```")
        parts.append("")
        parts.append("---")
        parts.append("")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


class ImagePromptGenerator:
    """Generates filled §28 templates via the router, with validation + one retry."""

    def __init__(self, router, model: str, max_workers: int = 4):
        self.router = router
        self.model = model
        self.max_workers = max_workers

    def generate_one(self, post: PostRow) -> GeneratedImagePrompt:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            final_title=post.final_title,
            idea_title=post.idea_title,
            thumbnail_rec=post.thumbnail_rec or "(none supplied)",
            draft=post.draft,
        )
        source_material = " ".join(
            [post.draft, post.final_title, post.idea_title, post.thumbnail_rec]
        )

        text = ""
        problems: list[str] = []
        for attempt in range(2):
            prompt = user_prompt
            if attempt == 1:
                prompt = user_prompt + RETRY_SUFFIX.format(problems="; ".join(problems))
            raw = self.router.complete(
                [self.model],
                prompt,
                system=SYSTEM_PROMPT,
                max_tokens=6000,
                thinking={"type": "enabled", "budget_tokens": 4096},
                extra_body={"reasoning_effort": "high"},
            )
            text = _strip_fences(str(raw))
            problems = validate_template(text)
            if not problems:
                break
            logger.warning("Row %d attempt %d invalid: %s", post.row, attempt + 1, problems)

        if problems:
            raise ValueError(
                f"Row {post.row}: §28 template still invalid after 2 attempts: {'; '.join(problems)}"
            )

        warnings = flag_fabricated_numbers(text, source_material)
        return GeneratedImagePrompt(
            row=post.row, final_title=post.final_title, text=text, warnings=warnings
        )

    def generate_all(self, posts: list[PostRow]) -> list[GeneratedImagePrompt]:
        if not posts:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(self.generate_one, posts))
