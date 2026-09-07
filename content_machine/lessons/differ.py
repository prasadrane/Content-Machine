"""LessonsDiffer: extract declarative rules from draft-vs-published diff (plan v2 §6).

Calls the analytical model with both texts and a structured prompt.
Returns 1–3 declarative rules for human review.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedRules(BaseModel):
    """Structured output from the diff model."""

    rules: list[str] = Field(
        min_length=0,
        max_length=5,
        description="1-3 declarative rules derived from the editorial diff",
    )


_DIFF_SYSTEM = """\
You are an editorial learning engine.  You compare an AI-generated draft with the
version the human operator actually published, and extract concrete, falsifiable
rules about what makes writing better in this operator's voice.

Rules must be:
- Declarative and specific (e.g. "Open with a concrete date and event" not "be specific")
- Derived from observable differences between draft and published text
- Generalisable to future drafts — not one-off corrections
- Written in the imperative voice

Return ONLY a valid JSON object with a 'rules' array of 1–3 strings.
""".strip()

_DIFF_PROMPT = """\
## Draft text (AI-generated, before operator edit)

{draft}

## Published text (operator's final version)

{published}

Extract 1-3 declarative style rules that explain the pattern of edits the operator made.
Respond with ONLY the JSON object.
""".strip()


class LessonsDiffer:
    """Analyse a draft/published diff and extract declarative style rules.

    Args:
        router:  ModelRouter instance.
        model:   Model to use for extraction (cheap scanner-class is fine).
    """

    def __init__(self, router, model: str = "qwen3.8-flash"):
        self.router = router
        self.model = model

    def extract(self, draft: str, published: str, project_id: str) -> list[str]:
        """Compare draft and published, return up to 3 declarative rules.

        Args:
            draft:      The AI-generated draft text.
            published:  The operator's final published text.
            project_id: Source project slug (for provenance, not used here).

        Returns:
            List of rule strings (length 1–3).
        """
        prompt = _DIFF_PROMPT.format(draft=draft.strip(), published=published.strip())

        result: ExtractedRules = self.router.complete(
            [self.model],
            prompt=prompt,
            system=_DIFF_SYSTEM,
            schema=ExtractedRules,
        )

        # Cap at 3 regardless of what the model returns
        return list(result.rules)[:3]
