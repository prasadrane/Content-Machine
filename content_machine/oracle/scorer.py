"""IdeaScorer: N-sample idea scoring with median aggregation (plan v2 §2.2).

Key design decisions from the evidence register:
- P2-F8: single unsampled scores are statistically unreliable (α 0.26–0.79).
  Never gate on one sample. Use N-sample median or temp-0 + margin band.
- IdeaScore schema already in schemas.py; router enforces it via Pydantic.
- Verdict bands:
    pass   : median >= gate
    review : gate - margin <= median < gate  (operator sees it, makes call)
    reject : median < gate - margin
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Literal

from content_machine.connectors.base import ConnectorItem
from content_machine.schemas import IdeaScore

# Scoring rubric injected into every scanner prompt.
_SCORE_SYSTEM = """\
You are an idea-scoring engine for a content creator.  Your job is to evaluate
whether a raw content idea has the ingredients for a high-performing post based
on the operator's rubric.  Score each dimension honestly on a 0–10 scale.
Never award scores above 10 or below 0.  Apply the generic-abstraction penalty
when the idea is a well-known cliché with no novel angle.
Return ONLY a valid JSON object matching the schema — no prose, no markdown fences.
""".strip()

_SCORE_PROMPT_TEMPLATE = """\
## Idea to evaluate

Title: {title}

Raw content:
{body}

## Rubric dimensions (weight in parentheses)

- pov (0.30): Strong Point of View — Does the topic demonstrate a clear, opinionated stance rather than neutral information? Does this idea have a clear, falsifiable, contrarian thesis?
- lived_experience (0.30): Storytelling & Lived Experience — Does it contain a personal anecdote or specific narrative grounded in concrete operational reality the author lived?
- specificity (0.25): Specific Examples — Does it provide concrete details, use cases, or evidence that support the argument (referencing real dates, metrics, dialogue, or named entities)?
- counter_intuitive (0.15): Does it disrupt a standard assumption the audience holds?
- generic_penalty_applied: Is this idea a well-known business cliché (e.g. "communicate better",
  "trust your team", "work smarter not harder") with no novel angle? If yes, composite -= 0.50.

## Composite formula (for your reference)
composite = pov*0.30 + lived_experience*0.30 + specificity*0.25 + counter_intuitive*0.15
            - (0.50 if generic_penalty_applied else 0)
Clamp result to [0, 10].

Respond with ONLY the JSON object.
""".strip()


from content_machine.oracle.classifier import classify_content_topic, TOPIC_GENERAL


@dataclass
class ScoredIdea:
    """Result of scoring one ConnectorItem across N samples."""

    item: ConnectorItem
    samples: list[IdeaScore]
    median_composite: float
    verdict: Literal["pass", "review", "reject"]
    topic_tag: str = TOPIC_GENERAL

    @property
    def body_snippet(self) -> str:
        """First ~250 characters of the raw item body."""
        if not self.item or not self.item.body:
            return ""
        return self.item.body.strip()[:250]

    @property
    def dimension_scores(self) -> dict[str, float]:
        """Dimension scores aggregated across samples."""
        if not self.samples:
            return {}
        dims: dict[str, float] = {}
        for dim in ("pov", "lived_experience", "specificity", "counter_intuitive", "composite"):
            vals = [getattr(s, dim) for s in self.samples if hasattr(s, dim) and getattr(s, dim) is not None]
            if vals:
                dims[dim] = round(float(statistics.median(vals)), 2)

        if "pov" in dims:
            dims["relevance"] = dims["pov"]
        if "counter_intuitive" in dims:
            dims["novelty"] = dims["counter_intuitive"]
            dims["originality"] = dims["counter_intuitive"]

        for attr in ("relevance", "novelty", "originality"):
            vals = [getattr(s, attr) for s in self.samples if hasattr(s, attr) and getattr(s, attr) is not None]
            if vals:
                dims[attr] = round(float(statistics.median(vals)), 2)

        return dims



class IdeaScorer:
    """Score a ConnectorItem by calling the scanner model N times and aggregating.

    Args:
        router:         ModelRouter instance (or compatible mock).
        scanner_model:  Model name to pass to router.complete.
        n_samples:      Number of independent scoring calls (plan v2 §2.2 fix 2a).
        idea_gate:      Pass threshold on the composite scale [0, 10]. Default 8.0.
        idea_margin:    Half-width of the 'review' band around the gate. Default 0.5.
                        review iff gate-margin <= median < gate;
                        reject iff median < gate-margin.
    """

    def __init__(
        self,
        router,
        scanner_model: str,
        n_samples: int = 3,
        idea_gate: float = 8.0,
        idea_margin: float = 0.5,
    ):
        self.router = router
        self.scanner_model = scanner_model
        self.n_samples = n_samples
        self.idea_gate = idea_gate
        self.idea_margin = idea_margin

    def _build_prompt(self, item: ConnectorItem) -> str:
        return _SCORE_PROMPT_TEMPLATE.format(title=item.title, body=item.body)

    def _verdict(self, median: float) -> Literal["pass", "review", "reject"]:
        if median >= self.idea_gate:
            return "pass"
        if median >= self.idea_gate - self.idea_margin:
            return "review"
        return "reject"

    def score_item(self, item: ConnectorItem) -> ScoredIdea:
        """Call the scanner model n_samples times and return a ScoredIdea.

        Each call uses IdeaScore as the output schema so the router validates
        the response with Pydantic before returning it.
        """
        from concurrent.futures import ThreadPoolExecutor

        prompt = self._build_prompt(item)

        def get_sample(_):
            return self.router.complete(
                [self.scanner_model],
                prompt=prompt,
                system=_SCORE_SYSTEM,
                schema=IdeaScore,
            )

        if self.n_samples > 1:
            with ThreadPoolExecutor(max_workers=self.n_samples) as pool:
                samples = list(pool.map(get_sample, range(self.n_samples)))
        else:
            samples = [get_sample(0)]

        composites = [s.composite for s in samples]
        median = statistics.median(composites)

        topic = classify_content_topic(item.title, item.body, item.source)
        return ScoredIdea(
            item=item,
            samples=samples,
            median_composite=median,
            verdict=self._verdict(median),
            topic_tag=topic,
        )
