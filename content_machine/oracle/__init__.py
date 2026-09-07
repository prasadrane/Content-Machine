"""Oracle subsystem: ingestion scoring (plan v2 §2).

The Oracle pulls ideas from all connectors, deduplicates, scores them
with N-sample aggregation, and returns sorted candidates to the operator.

Public API:
    IdeaScorer          — score a single ConnectorItem (N samples, median)
    ScoredIdea          — result dataclass
    OracleOrchestrator  — connector pull + dedup + score + persist
"""

from content_machine.oracle.scorer import IdeaScorer, ScoredIdea
from content_machine.oracle.oracle import OracleOrchestrator

__all__ = ["IdeaScorer", "ScoredIdea", "OracleOrchestrator"]
