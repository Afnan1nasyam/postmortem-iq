"""Tests for the semantic chunker."""

from src.ingestion.chunker import chunk_postmortem, chunk_text
from src.models.schemas import PostmortemDocument


def test_basic_chunking():
    text = (
        "The server crashed at midnight causing a full outage across all regions. "
        "Engineers were paged immediately and began investigating the root cause. "
        "The root cause was traced to a memory leak in the connection pool handler. "
        "A hotfix was deployed within an hour that patched the leak and restored service. "
        "All services recovered by morning after a full cache warm-up cycle completed."
    )
    chunks = chunk_text(text, chunk_size=150, chunk_overlap=30)
    assert len(chunks) >= 2


def test_chunk_size_respected():
    text = (
        "First sentence is here. Second sentence follows. Third sentence appears. "
        "Fourth sentence now. Fifth sentence arrives. Sixth sentence concludes."
    )
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    for chunk in chunks:
        assert len(chunk) < 200, f"Chunk too large: {len(chunk)} chars"


def test_overlap_exists():
    text = (
        "Alpha service went down at noon. Beta service was affected downstream. "
        "Gamma service lost connectivity. Delta service timed out. "
        "Epsilon service recovered last."
    )
    chunks = chunk_text(text, chunk_size=120, chunk_overlap=30)
    if len(chunks) >= 2:
        assert chunks[0][-30:] in chunks[1] or chunks[1].startswith(chunks[0][-30:])


def test_empty_input():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_single_sentence():
    chunks = chunk_text("Just one sentence here.", chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == "Just one sentence here."


def test_metadata_attachment():
    doc = PostmortemDocument(
        file_path="/tmp/test.md",
        file_type="md",
        raw_text="First sentence here. Second sentence here. Third sentence here.",
    )
    results = chunk_postmortem(doc, incident_id="inc-123")
    assert len(results) >= 1
    for text, meta in results:
        assert meta.incident_id == "inc-123"
        assert meta.source_file == "/tmp/test.md"
        assert isinstance(meta.chunk_index, int)
