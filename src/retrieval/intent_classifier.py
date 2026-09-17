"""Heuristic-based query intent classification."""

from src.models.schemas import QueryIntent

_BLAST_RADIUS_KEYWORDS = [
    "what happens if", "blast radius", "downstream", "goes down",
    "impact if", "affected if", "what breaks", "cascade", "depends on",
]

_PATTERN_KEYWORDS = [
    "common", "frequent", "pattern", "trend", "how often",
    "most", "recurring", "statistics", "top", "aggregate",
]

_RESOLUTION_KEYWORDS = [
    "how to fix", "what fixed", "how did we", "how was it",
    "fix", "resolve", "solved", "remediation", "workaround",
    "mitigation", "rollback",
]

_SIMILARITY_KEYWORDS = [
    "similar", "like this", "seen before", "happened before",
    "have we seen", "resembles", "looks like",
]


def classify_intent(query: str) -> QueryIntent:
    """Classify a user query into a QueryIntent using keyword matching."""
    q = query.lower()

    for kw in _BLAST_RADIUS_KEYWORDS:
        if kw in q:
            return QueryIntent.BLAST_RADIUS

    for kw in _PATTERN_KEYWORDS:
        if kw in q:
            return QueryIntent.PATTERN

    for kw in _RESOLUTION_KEYWORDS:
        if kw in q:
            return QueryIntent.RESOLUTION

    for kw in _SIMILARITY_KEYWORDS:
        if kw in q:
            return QueryIntent.SIMILARITY

    return QueryIntent.SIMILARITY
