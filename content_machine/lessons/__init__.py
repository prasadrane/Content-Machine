"""Lessons Loop subsystem (plan v2 §6).

Governance-enforced learning from editorial diffs:

    LessonsDiffer   — extract 1-3 rules from draft-vs-published diff
    LessonsStore    — propose → human approve/reject → active; conflict detect; cap
    ProposeResult   — return type of LessonsStore.propose()
"""

from content_machine.lessons.differ import LessonsDiffer
from content_machine.lessons.store import LessonsStore, ProposeResult

__all__ = ["LessonsDiffer", "LessonsStore", "ProposeResult"]
