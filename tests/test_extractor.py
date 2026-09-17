"""Tests for the LLM-based extractor. All require Groq API access."""

import pytest

from src.models.schemas import PostmortemDocument


@pytest.mark.slow
def test_extract_valid_output(sample_postmortem_text):
    from src.ingestion.extractor import PostmortemExtractor

    doc = PostmortemDocument(file_path="/tmp/test.md", file_type="md", raw_text=sample_postmortem_text)
    extractor = PostmortemExtractor()
    result = extractor.extract(doc)
    assert result.title and result.title != "EXTRACTION_FAILED"


@pytest.mark.slow
def test_extract_garbage_input():
    from src.ingestion.extractor import PostmortemExtractor

    doc = PostmortemDocument(
        file_path="/tmp/garbage.md", file_type="md",
        raw_text="asdf qwerty 12345 random noise nothing useful here at all",
    )
    extractor = PostmortemExtractor()
    result = extractor.extract(doc)
    assert result is not None


@pytest.mark.slow
def test_extract_batch(sample_postmortem_text):
    from src.ingestion.extractor import PostmortemExtractor

    docs = [
        PostmortemDocument(file_path="/tmp/a.md", file_type="md", raw_text=sample_postmortem_text),
        PostmortemDocument(file_path="/tmp/b.md", file_type="md", raw_text=sample_postmortem_text),
    ]
    extractor = PostmortemExtractor()
    results = extractor.extract_batch(docs)
    assert len(results) == 2
