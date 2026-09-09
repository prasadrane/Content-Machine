"""Subsystem 6: Cross-Channel Distribution Engine (plan v2 §7).

Transforms the approved, human-edited published anchor post into
platform-specific derivative formats:
1. LinkedIn Post: punchy hook, high-readability spacing, operational takeaways, hashtags
2. X (Twitter) Thread: hook + 6-8 numbered insight cards + summary
3. Short-Form Video Script: 60-90s spoken script with [Visual Cue] production markers (Reels, TikTok, Shorts)
4. Long-Form Video Script: 5-10m YouTube deep dive with chapter markers, b-roll, and code overlays
5. Email / Newsletter Digest: 300-400 word executive briefing with markdown headers

Strict constraint:
    The model is explicitly forbidden from inventing new facts, data points,
    or narrative arcs not present in the verified anchor text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TypedDict

from content_machine.editorial import (
    ANTI_FINGERPRINT_RULES,
    VOICE_RULE,
    WORD_COUNT_RULE,
)
from content_machine.humanize import (
    HumanizeChannel,
    HumanizeTone,
    HumanizeTransformer,
)
from content_machine.storage.paths import project_dir



class DistributionBundle(TypedDict, total=False):
    linkedin: str
    x_thread: str
    video_script: str
    video_script_short: str
    video_script_long: str
    newsletter: str


_LINKEDIN_SYSTEM = f"""\
You are an elite LinkedIn content creator and tech executive ghostwriter.
Your goal is to transform the provided anchor post into a high-performing, authentic LinkedIn post.

Rules:
- Strictly anchor in the source text. NEVER invent facts, metrics, or anecdotes not in the text. NEVER fabricate corporate production crashes.
- Length: {WORD_COUNT_RULE}
- Voice: {VOICE_RULE}
- Lived specificity: Name concrete failure modes (HTTP 429s, partial responses, payload validation edge cases, schema drift) instead of generic phrases like "debugging edge cases".
- Hook (first 1-2 lines): High impact opening that creates natural curiosity before the "...see more" cutoff. No cheesy clickbait.
- Anti-fingerprint:
{ANTI_FINGERPRINT_RULES}
- Body: Connect technical mechanics directly (e.g. explain why mocks fail and immediately position integration tests as the remedy).
- Conclusion: Direct, honest operational statement. Close on an unvarnished statement of technical reality.
- Hashtags: End with exactly 2-3 hyper-relevant technical hashtags (e.g. #SoftwareEngineering #AIEngineering #TestDrivenDevelopment).
- Return plain text.
""".strip()

_X_THREAD_SYSTEM = """\
You are an elite ghostwriter specializing in high-performing X (Twitter) threads.
Your goal is to transform the provided anchor post into a crisp, compelling thread.

Rules:
- Strictly anchor in the source text. NEVER invent facts, metrics, or anecdotes not in the text.
- Tweet 1: Powerful, punchy single-line hook with concrete numbers highlighted.
- Tweets 2 through 7 (or 8): Numbered insight cards (e.g. "1/", "2/"). Clean line breaks, zero fluff.
- Final Tweet: One operational takeaway summary.
- Return plain text with tweets separated by double newlines.
""".strip()

_VIDEO_SCRIPT_SHORT_SYSTEM = """\
You are a short-form video director and scriptwriter (for TikTok, YouTube Shorts, Reels).
Your goal is to transform the provided anchor post into a 60-90 second spoken script.

Rules:
- Strictly anchor in the source text. No invented facts.
- Include bracketed production and visual cues: [Visual Cue: ...], [Camera Zoom], [On-screen Text: ...], [Pause].
- Conversational spoken-word rhythm with immediate pattern interrupts.
- Return plain text of the script.
""".strip()

_VIDEO_SCRIPT_LONG_SYSTEM = """\
You are a YouTube technical video director and scriptwriter.
Your goal is to transform the provided anchor post into a comprehensive 5-10 minute deep dive video script (~700-1200 words).

Rules:
- Strictly anchor in the source text. NEVER invent facts or hallucinate claims.
- Structure with clear time-stamped chapter headers:
  - [Chapter 1: The Hook & The Paradox - 0:00]
  - [Chapter 2: The Technical Architecture & Root Cause - 1:30]
  - [Chapter 3: The Benchmark & Memory/Performance Math - 4:00]
  - [Chapter 4: The Operational Playbook - 7:00]
  - [Chapter 5: Outro & Takeaway - 8:30]
- Include detailed production and direction markers:
  - [Visual Cue: ...]
  - [Screen Recording: ...]
  - [Code Overlay: ...]
  - [B-Roll: ...]
  - [Camera Zoom]
- Voiceover text clearly labeled as Speaker / Host.
- Return plain text of the full script.
""".strip()

_NEWSLETTER_SYSTEM = """\
You are an executive newsletter editor.
Your goal is to condense the provided anchor post into a 300-400 word executive briefing.

Rules:
- Strictly anchor in the source text. No hallucinated claims.
- Structure:
  - Compelling H2 headline: "## Executive Briefing: ..."
  - 1-2 concise narrative paragraphs setting context
  - H3 header: "### Core Takeaways" with bulleted operational takeaways
  - 1 concluding sentence addressing the reader directly
- Return clean Markdown.
""".strip()


class DistributionEngine:
    """Transforms published anchor content into platform-specific assets.

    Args:
        router: ModelRouter instance.
        model:  Model configuration to use (defaults to cheap scanner/derivative class).
    """

    def __init__(
        self,
        router,
        model: str = "qwen3.8-flash",
        model_long: str = "qwen3.8-max",
    ):
        self.router = router
        self.model = model
        self.model_long = model_long
        self.humanizer = HumanizeTransformer(router=self.router, model=self.model)

    def generate_linkedin_post(
        self,
        anchor_post: str,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> str:
        """Transform anchor post into an authentic, high-engagement LinkedIn post."""
        prompt = f"Transform this anchor post into a high-performing LinkedIn post:\n\n{anchor_post.strip()}"
        res = self.router.complete(
            [self.model],
            prompt=prompt,
            system=_LINKEDIN_SYSTEM,
        )
        raw = str(res).strip()
        if humanize:
            tone_enum = HumanizeTone(tone) if isinstance(tone, str) else tone
            h_res = self.humanizer.humanize_post(raw, tone=tone_enum)
            return h_res.humanized_text
        return raw

    def generate_x_thread(
        self,
        anchor_post: str,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> str:
        """Transform anchor post into a numbered X (Twitter) thread."""
        prompt = f"Transform this anchor post into an X thread:\n\n{anchor_post.strip()}"
        res = self.router.complete(
            [self.model],
            prompt=prompt,
            system=_X_THREAD_SYSTEM,
        )
        raw = str(res).strip()
        if humanize:
            tone_enum = HumanizeTone(tone) if isinstance(tone, str) else tone
            h_res = self.humanizer.transform(raw, channel=HumanizeChannel.X_THREAD, tone=tone_enum)
            return h_res.humanized_text
        return raw

    def generate_video_script_short(
        self,
        anchor_post: str,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> str:
        """Transform anchor post into a 60-90s short-form video script with visual cues."""
        prompt = f"Transform this anchor post into a short-form video script:\n\n{anchor_post.strip()}"
        res = self.router.complete(
            [self.model],
            prompt=prompt,
            system=_VIDEO_SCRIPT_SHORT_SYSTEM,
        )
        raw = str(res).strip()
        if humanize:
            tone_enum = HumanizeTone(tone) if isinstance(tone, str) else tone
            h_res = self.humanizer.transform(raw, channel=HumanizeChannel.VIDEO_SCRIPT, tone=tone_enum)
            return h_res.humanized_text
        return raw

    def generate_video_script(
        self,
        anchor_post: str,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> str:
        """Backward-compatible alias for short-form video script."""
        return self.generate_video_script_short(anchor_post, humanize=humanize, tone=tone)

    def generate_video_script_long(self, anchor_post: str) -> str:
        """Transform anchor post into a 5-10m YouTube deep dive script with chapter markers."""
        prompt = f"Transform this anchor post into a long-form YouTube deep dive video script:\n\n{anchor_post.strip()}"
        res = self.router.complete(
            [self.model_long],
            prompt=prompt,
            system=_VIDEO_SCRIPT_LONG_SYSTEM,
        )
        return str(res).strip()

    def generate_newsletter_digest(self, anchor_post: str) -> str:
        """Transform anchor post into a 300-400 word executive briefing."""
        prompt = f"Transform this anchor post into an executive newsletter briefing:\n\n{anchor_post.strip()}"
        res = self.router.complete(
            [self.model],
            prompt=prompt,
            system=_NEWSLETTER_SYSTEM,
        )
        return str(res).strip()

    def generate_all(
        self,
        anchor_post: str,
        formats: Optional[list[str]] = None,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> dict[str, str]:
        """Run transformations for requested platforms.

        Default formats (if None): ['linkedin', 'x_thread', 'video_script', 'newsletter'].
        """
        if formats is None:
            formats = ["linkedin", "x_thread", "video_script", "newsletter"]

        bundle: dict[str, str] = {}
        for fmt in formats:
            if fmt == "linkedin":
                bundle["linkedin"] = self.generate_linkedin_post(anchor_post, humanize=humanize, tone=tone)
            elif fmt == "x_thread":
                bundle["x_thread"] = self.generate_x_thread(anchor_post, humanize=humanize, tone=tone)
            elif fmt in ("video_script", "video_script_short"):
                script = self.generate_video_script_short(anchor_post, humanize=humanize, tone=tone)
                bundle["video_script"] = script
                bundle["video_script_short"] = script
            elif fmt == "video_script_long":
                bundle["video_script_long"] = self.generate_video_script_long(anchor_post)
            elif fmt == "newsletter":
                bundle["newsletter"] = self.generate_newsletter_digest(anchor_post)

        return bundle


    def save_bundle(
        self,
        project_slug: str,
        bundle: dict[str, str],
        anchor_post: Optional[str] = None,
    ) -> Path:
        """Save bundle assets to projects/{slug}/distribution/{channel}.md."""
        pdir = project_dir(project_slug, create=True)
        dist_dir = pdir / "distribution"
        dist_dir.mkdir(parents=True, exist_ok=True)

        if anchor_post:
            (dist_dir / "anchor.md").write_text(anchor_post, encoding="utf-8")

        for key, text in bundle.items():
            if not text:
                continue
            filename = f"{key}.md"
            (dist_dir / filename).write_text(text, encoding="utf-8")

        return dist_dir
