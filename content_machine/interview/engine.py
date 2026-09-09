"""InterviewEngine: Subsystem 2 Topic Briefing & Perspective Intake (plan v2 §3).

Features:
- Generates 2-3 sentence executive topic briefings & tailored persona questions.
- Synthesizes raw operator answers and notes into grounded initial drafts.
- Injects style guides, voice constraints, and governed lessons.
- Saves raw_transcript.md to project directory and tracks in SQLite transcripts table.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from content_machine.profile.manager import ProfileManager
from content_machine.schemas import (
    InterviewQuestion,
    TopicBriefing,
)
from content_machine.storage.paths import home_root


logger = logging.getLogger(__name__)

_BRIEFING_SYSTEM = """\
You are an executive editorial researcher and interviewer for a technical content creator.
Your job is to read an ingested topic/signal and provide:
1. A concise 2-3 sentence executive briefing summarizing what happened and why it matters to engineers.
2. The core debate, trade-off, or tension (core_conflict).
3. 2-3 sharp, probing interrogation questions from distinct interviewer personas:
   - Tim Ferriss: Tactical mechanics, exact tools, step-by-step sequence.
   - Larry King: Bottom-line metric or single biggest takeaway.
   - Barbara Walters: Friction, team mistakes, vulnerability, or failure points.
   - Joe Rogan: First-principles reality check, challenging industry buzzwords.

Return ONLY valid JSON matching the TopicBriefing schema.
""".strip()

_BRIEFING_PROMPT = """\
Topic Title: {title}
Source URL: {url}
Topic Tag: {topic_tag}

Content / Body:
{body}

Generate the executive briefing, core conflict, and 2-3 persona interrogation questions.
""".strip()

_SYNTHESIZE_SYSTEM = """\
You are an elite technical ghostwriter and editorial partner.
Your mission is to turn the creator's real lived experience, direct answers, and raw notes into a high-signal, concise technical post (LinkedIn/X style, strictly 120–280 words) written as an authentic developer field note.

CORE INVARIANTS:
1. Ground every single claim in the creator's actual answers, metrics, and notes below.
2. Concrete mechanical specificity over generic hand-waving: cite exact failure modes (e.g., HTTP 429s, partial responses, payload validation edge cases, schema drift) instead of generic phrases like "debugging edge cases".
3. NEVER hallucinate metrics, imaginary colleagues, or fabricated corporate production outages (no 3 AM payment crashes).
4. Strict length constraint: strictly between 120 and 280 words total. Never write long essays or walls of text.
5. Conversational practitioner voice: write in first person ("I've started treating...", "What works better for me:"). Keep it slightly messier and practical rather than an immaculate, sanitized lecture.
6. Aphorism density cap: limit to at most ONE takeaway or summary observation. NEVER string consecutive quotable epigrams together.
7. Ban AI rhetorical contrast formulas: do NOT use "X feels fast until Y...", "You aren't saving X, you're just Y...", or "The problem isn't X, it's how we Y...". State observations directly.
8. Ban manufactured metaphors: NEVER use dramatic phrases like "the workflow that stops the bleeding" or "pure velocity".
9. Natural paragraph grouping (NO broetry): group related premise, mechanics, and friction into cohesive mini-paragraphs (2–3 sentences). Avoid 1-sentence staccato lines unless presenting an operational action list.
10. Connect technical mechanics directly: when citing a failure mode (like mocks staying green during drift), connect it directly to the concrete remedy.
11. Zero formulaic aphorisms or engagement bait: do NOT use the "X isn't Y, it's Z" fortune-cookie mic-drop template. NEVER end with cheesy questions ("What do you think?", "Comment below"). Close on an unvarnished statement of technical reality.
12. Hashtag hygiene: include exactly 2–3 hyper-relevant technical hashtags at the footer.
13. Obey all negative constraints and style rules: no generic corporate buzzwords ("delve", "leverage", "testament", "tapestry", "game-changer").
""".strip()


class InterviewEngine:
    """Orchestrates topic briefing and perspective intake prior to Writer's Council."""

    def __init__(
        self,
        router=None,
        scanner_model: str = "qwen3.8-flash",
        writer_model: str = "qwen3.8-max",
        db_conn=None,
    ):
        self.router = router
        self.scanner_model = scanner_model
        self.writer_model = writer_model
        self.db_conn = db_conn

    def generate_briefing(
        self,
        title: str,
        url: str | None = None,
        body: str | None = None,
        topic_tag: str = "General Engineering",
    ) -> TopicBriefing:
        """Generate an executive summary and persona interrogation questions."""
        content_snippet = (body or "").strip()
        if not content_snippet:
            content_snippet = f"Discussion on '{title}' ({topic_tag})."

        prompt = _BRIEFING_PROMPT.format(
            title=title,
            url=url or "N/A",
            topic_tag=topic_tag,
            body=content_snippet[:3000],
        )

        if self.router:
            try:
                briefing: TopicBriefing = self.router.complete(
                    [self.scanner_model],
                    prompt=prompt,
                    system=_BRIEFING_SYSTEM,
                    schema=TopicBriefing,
                )
                if isinstance(briefing, TopicBriefing):
                    return briefing
            except Exception as e:
                logger.warning("Router failed to generate structured briefing, falling back to default: %s", e)

        # Fallback default questions if router fails or is not provided
        summary = (
            f"Analysis of '{title}'. This topic addresses critical technical patterns and operational "
            f"trade-offs in {topic_tag}. Examining the real-world implications reveals where conventional wisdom breaks down."
        )
        core_conflict = "Immediate implementation velocity vs long-term maintainability and operational debt."
        questions = [
            InterviewQuestion(
                persona="Tim Ferriss",
                focus="Tactical mechanics",
                question=f"What specific tool, architecture choice, or technical sequence did you implement regarding '{title}'?",
            ),
            InterviewQuestion(
                persona="Larry King",
                focus="Bottom-line impact",
                question="What was the single most concrete metric or quantifiable result you observed?",
            ),
            InterviewQuestion(
                persona="Barbara Walters",
                focus="Operational friction",
                question="What went wrong, caused friction with your team, or surprised you along the way?",
            ),
        ]
        return TopicBriefing(summary=summary, core_conflict=core_conflict, questions=questions)

    def synthesize_draft(
        self,
        topic_title: str,
        topic_summary: str,
        responses: list[dict[str, Any]],
        raw_notes: str | None = None,
        spike_id: str = "cli-session",
    ) -> dict[str, Any]:
        """Synthesize operator interview responses and raw notes into a grounded draft."""
        # Assemble interview responses
        qa_sections = []
        for r in responses:
            persona = r.get("persona", "Interviewer")
            q = r.get("question", "")
            ans = r.get("answer", "").strip()
            if ans:
                qa_sections.append(f"### {persona} Prompt:\nQ: {q}\nA: {ans}\n")

        qa_text = "\n".join(qa_sections) if qa_sections else "No structured answers provided."
        notes_text = (raw_notes or "").strip() or "No additional freeform notes."

        # Fetch full editorial context (styles, voice guide, governed rules)
        from content_machine.knowledge.provider import get_editorial_context
        editorial_ctx = get_editorial_context(conn=self.db_conn)
        style_prompt = editorial_ctx["style_section"]
        voice_guide_prompt = editorial_ctx["voice_section"]
        rules_prompt = editorial_ctx["rules_section"]

        prompt = f"""\
# Topic Context
Title: {topic_title}
Executive Summary: {topic_summary}

# Operator's Lived Perspective (INTERVIEW TRANSCRIPT)
{qa_text}

# Operator's Freeform Notes & Observations
{notes_text}
{style_prompt}{voice_guide_prompt}{rules_prompt}
Write the initial draft based strictly on the above evidence. Return only the draft content in markdown format.
"""

        draft_content = ""
        if self.router:
            try:
                out = self.router.complete([self.writer_model], prompt=prompt, system=_SYNTHESIZE_SYSTEM)
                if isinstance(out, str):
                    draft_content = out.strip()
                    if draft_content.startswith("```"):
                        lines = draft_content.splitlines()
                        if lines and lines[-1].strip() == "```":
                            draft_content = "\n".join(lines[1:-1]).strip()
            except Exception as e:
                logger.error("Router draft synthesis failed: %s", e)

        if draft_content:
            from content_machine.humanize.sanitizer import sanitize_text
            draft_content, _ = sanitize_text(draft_content)

        if not draft_content:
            # Fallback draft template constructed directly from user input
            draft_content = f"# {topic_title}\n\n"
            if raw_notes:
                draft_content += f"{raw_notes}\n\n"
            if responses:
                for r in responses:
                    if r.get("answer"):
                        draft_content += f"## {r.get('persona', 'Perspective')} Insight\n{r['answer']}\n\n"

        word_count = len(draft_content.split())

        # Persist raw transcript to disk
        try:
            transcript_content = f"# Interview Transcript — {topic_title}\n\n"
            transcript_content += f"Spike ID: {spike_id}\n\n"
            transcript_content += f"## Briefing\n{topic_summary}\n\n"
            transcript_content += f"## Interview Responses\n{qa_text}\n\n"
            transcript_content += f"## Freeform Notes\n{notes_text}\n"

            proj_dir = home_root() / "projects" / spike_id
            proj_dir.mkdir(parents=True, exist_ok=True)
            transcript_path = proj_dir / "raw_transcript.md"
            transcript_path.write_text(transcript_content, encoding="utf-8")

            if self.db_conn:
                try:
                    self.db_conn.execute(
                        "INSERT INTO transcripts (spike_id, path, word_count) VALUES (?, ?, ?)",
                        (spike_id, str(transcript_path), len(transcript_content.split())),
                    )
                    self.db_conn.commit()
                except Exception as e:
                    logger.warning("Could not persist transcript to SQLite: %s", e)
        except Exception as e:
            logger.warning("Could not persist raw_transcript.md to disk: %s", e)

        return {
            "draft": draft_content,
            "word_count": word_count,
            "spike_id": spike_id,
        }
