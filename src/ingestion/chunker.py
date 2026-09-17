"""Semantic chunking with sentence-level splitting and configurable overlap."""

import re

from loguru import logger

from src.config import settings
from src.models.schemas import ChunkMetadata, PostmortemDocument

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!])\s+(?=[A-Z\n])")


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """Split text into chunks by sentence boundaries with character-level overlap."""
    if not text or not text.strip():
        return []

    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    if len(chunks) <= 1:
        return chunks

    overlapped: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        overlap_text = prev[-chunk_overlap:] if len(prev) >= chunk_overlap else prev
        overlapped.append(f"{overlap_text} {chunks[i]}".strip())

    logger.debug("Chunked {} chars into {} chunks (size={}, overlap={})",
                 len(text), len(overlapped), chunk_size, chunk_overlap)
    return overlapped


def chunk_postmortem(
    doc: PostmortemDocument,
    incident_id: str,
) -> list[tuple[str, ChunkMetadata]]:
    """Chunk a postmortem document and attach metadata to each chunk."""
    chunks = chunk_text(doc.raw_text)
    results = []
    for i, chunk in enumerate(chunks):
        meta = ChunkMetadata(
            incident_id=incident_id,
            chunk_index=i,
            source_file=doc.file_path,
        )
        results.append((chunk, meta))
    logger.info("Chunked {} into {} pieces", doc.file_path, len(results))
    return results
