"""HumanizeTransformer engine: prompt-tier LLM rewrite + deterministic sanitizer."""

from __future__ import annotations

import logging
import re
from typing import Optional

from content_machine.profile.manager import ProfileManager
from content_machine.schemas import (
    HumanizeChannel,
    HumanizeResult,
    HumanizeTone,
)
from .constants import CHANNEL_PROMPTS, TONE_SYSTEM_PROMPTS
from .sanitizer import (
    calculate_burstiness,
    check_author_invariants,
    sanitize_text,
)

logger = logging.getLogger(__name__)


class HumanizeTransformer:
    def __init__(
        self,
        router: any,
        model: str = "qwen3.8-max",
        voice_guide: Optional[str] = None,
    ):
        self.router = router
        self.model = model
        if voice_guide is not None:
            self.voice_guide = voice_guide
        else:
            try:
                self.voice_guide = ProfileManager().get_voice_guide_text()
            except Exception:
                self.voice_guide = ""

    def transform(
        self,
        text: str,
        channel: HumanizeChannel = HumanizeChannel.LINKEDIN_POST,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
        max_sentences: Optional[int] = None,
    ) -> HumanizeResult:
        """Transform text into human-level craft, purging AI tells and enforcing voice."""
        original = text.strip() if text else ""
        if not original:
            return HumanizeResult(
                original_text=text or "",
                humanized_text="",
                channel=channel,
                tone=tone,
                sentence_count=0,
                was_modified=False,
            )

        # 1. Assemble prompt
        tone_sys = TONE_SYSTEM_PROMPTS.get(
            tone,
            TONE_SYSTEM_PROMPTS[HumanizeTone.PRAGMATIC_ARCHITECT],
        )
        chan_prompt = CHANNEL_PROMPTS.get(
            channel,
            CHANNEL_PROMPTS[HumanizeChannel.GENERAL],
        )

        system = f"{tone_sys}\n\nCHANNEL CONSTRAINT:\n{chan_prompt}"
        if self.voice_guide:
            system += f"\n\nAUTHOR VOICE & NEGATIVE CONSTRAINTS:\n{self.voice_guide}"

        prompt = (
            f"Rewrite the following draft to make it sound completely human and authentic.\n"
            f"Rules:\n"
            f"1. Break uniform sentence lengths; vary cadence dramatically (high burstiness).\n"
            f"2. Use contractions (don't, it's, we've) and concrete mechanical verbs.\n"
            f"3. Eliminate ALL AI tells: no 'delve', 'tapestry', 'pivotal', 'testament', or em-dashes (—).\n"
            f"4. Never hallucinate facts or mention unverified employers.\n"
            f"5. Output ONLY the rewritten text. No meta-commentary, code fences, or preamble.\n\n"
            f"DRAFT TO HUMANIZE:\n{original}"
        )

        humanized_raw = ""
        try:
            res = self.router.complete(
                [self.model],
                prompt=prompt,
                system=system,
            )
            humanized_raw = str(res).strip() if res else ""
            if not humanized_raw:
                humanized_raw = original
        except Exception as e:
            logger.warning("HumanizeTransformer LLM call failed, falling back to sanitizer: %s", e)
            humanized_raw = original

        # 2. Deterministic sanitize pass
        cleaned, purged = sanitize_text(humanized_raw)

        # 3. Enforce author invariants
        invariants = check_author_invariants(cleaned)
        if invariants:
            logger.warning("Author invariant warning in humanized text: %s", invariants)

        # 4. Optional sentence clamping
        if max_sentences is not None and max_sentences > 0:
            sentences = re.split(r"(?<=[.!?])\s+", cleaned)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) > max_sentences:
                cleaned = " ".join(sentences[:max_sentences])

        # 5. Metrics calculation
        burstiness = calculate_burstiness(cleaned)
        sent_count = len([s for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()])

        return HumanizeResult(
            original_text=original,
            humanized_text=cleaned,
            channel=channel,
            tone=tone,
            banned_words_purged=purged,
            burstiness_score=burstiness,
            sentence_count=sent_count,
            was_modified=(cleaned != original),
        )

    def humanize_comment(
        self,
        comment: str,
        tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT,
        max_sentences: int = 3,
    ) -> HumanizeResult:
        return self.transform(
            comment,
            channel=HumanizeChannel.LINKEDIN_COMMENT,
            tone=tone,
            max_sentences=max_sentences,
        )

    def humanize_post(
        self,
        post: str,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> HumanizeResult:
        return self.transform(
            post,
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=tone,
        )
