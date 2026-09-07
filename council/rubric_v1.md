# Council Rubric v1 (FROZEN)

Version: 1
Status: frozen — never edit mid-loop; new versions get a new file (rubric_v2.md).
Do not mix rubric versions across iterations of one rewrite loop (plan v2 §5.1 rule 5).

## Scale

All dimension scores are 0.0–10.0. Anchors:

- 0–2: broken or absent
- 3–4: weak, generic, skippable
- 5–6: competent, unremarkable
- 7–8: strong, publishable with polish
- 9–10: exceptional — the draft carries a falsifiable point of view, concrete lived detail, and zero filler

## Dimensions

| Dimension | Evaluated by slot | Focus |
| :--- | :--- | :--- |
| narrative | perell | Hook strength, conceptual novelty, narrative spine, sentence-rhythm variation |
| velocity | puri | Punchiness, immediate visual clarity, elimination of boring paragraphs |
| depth | housel | Human psychology, timelessness of insight, avoidance of surface trends |
| slop_purity | slop_allergist | Zero AI tells: banned constructions, symmetrical clauses, passive corporate phrasing, generic platitudes |

## Judge instructions

1. You are an independent judge. Score only from the draft in front of you.
2. Judge nothing about who wrote the draft. The draft is anonymous.
3. Scores that exceed the 0–10 scale are invalid. Exceptional work scores 9–10, never more.
4. `threshold_met`: true only when the composite of your four dimensions reaches 9.0.
5. `verdict`: pass (publish now), revise (specific fixes below), reject (start over).
6. `required_actions`: 1–5 concrete, line-level directives. Never vague ("be punchier" is invalid;
   "cut the three-sentence buildup before the metric in paragraph 2" is valid).

## Output contract

Return one JSON object — structured `CouncilScores`: narrative, velocity, depth,
slop_purity (floats 0–10), threshold_met (bool), verdict (pass|revise|reject),
required_actions (JSON array, 1–5 items).
