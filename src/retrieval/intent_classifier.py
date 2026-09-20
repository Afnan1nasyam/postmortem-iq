"""Heuristic-based query intent classification."""

from src.models.schemas import QueryIntent

_BLAST_RADIUS_KEYWORDS = [
    "what happens if",
    "blast radius",
    "downstream",
    "goes down",
    "impact if",
    "affected if",
    "most affected",
    "what breaks",
    "cascade",
    "depends on",
]


_PATTERN_KEYWORDS = [
    "common",
    "frequent",
    "pattern",
    "trend",
    "how often",
    "recurring",
    "statistics",
    "top",
    "aggregate",
    "single point of failure",
    "single points of failure",
    "prioritize",
    "priority",
    "priorities",
    "prevent future incidents",
]


_RESOLUTION_KEYWORDS = [
    "how to fix",
    "what fixed",
    "how did we",
    "how was it",
    "fix",
    "resolve",
    "solved",
    "remediation",
    "workaround",
    "mitigation",
    "rollback",
]


_SIMILARITY_KEYWORDS = [
    "similar",
    "like this",
    "seen before",
    "happened before",
    "have we seen",
    "resembles",
    "looks like",
]


def classify_intent(query: str) -> QueryIntent:
    """Classify a user query into a QueryIntent using keyword matching."""
    q = query.lower()

    # Check blast-radius intent first so phrases such as
    # "most affected" are not incorrectly classified as pattern queries.
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

    # Similarity is the default for unclassified questions.
    return QueryIntent.SIMILARITY
