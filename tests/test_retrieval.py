"""Tests for the intent classifier."""

from src.models.schemas import QueryIntent
from src.retrieval.intent_classifier import classify_intent


def test_intent_similarity():
    assert classify_intent("Have we seen this before?") == QueryIntent.SIMILARITY


def test_intent_blast_radius():
    assert classify_intent("What happens if Redis goes down?") == QueryIntent.BLAST_RADIUS


def test_intent_pattern():
    assert classify_intent("What's our most common root cause?") == QueryIntent.PATTERN


def test_intent_resolution():
    assert classify_intent("How did we fix the connection pool issue?") == QueryIntent.RESOLUTION


def test_intent_default():
    assert classify_intent("Tell me about the outage") == QueryIntent.SIMILARITY
