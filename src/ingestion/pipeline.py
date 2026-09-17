"""Orchestrates the full ingestion flow: load, extract, chunk, embed, persist."""

import time
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table

from src.ingestion.chunker import chunk_postmortem
from src.ingestion.extractor import PostmortemExtractor
from src.ingestion.loader import load_document
from src.models.schemas import IncidentExtraction
from src.storage.graph_store import KnowledgeGraph
from src.storage.sql_store import SQLStore
from src.storage.vector_store import VectorStore
from src.utils.embedding import get_embedding_model

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}


class IngestionPipeline:
    """End-to-end pipeline: file → extraction → graph + vectors + SQL."""

    def __init__(self):
        self.embedding_model = get_embedding_model()
        self.extractor = PostmortemExtractor()
        self.vector_store = VectorStore()
        self.graph = KnowledgeGraph()
        self.sql_store = SQLStore()
        logger.info("IngestionPipeline initialized")

    def ingest_file(self, file_path: Path) -> IncidentExtraction:
        """Ingest a single postmortem file through the full pipeline."""
        t0 = time.time()

        t = time.time()
        doc = load_document(file_path)
        logger.info("  Load: {:.2f}s", time.time() - t)

        t = time.time()
        extraction = self.extractor.extract(doc)
        logger.info("  Extract: {:.2f}s", time.time() - t)

        t = time.time()
        self.sql_store.save_incident(extraction, source_file=str(file_path))
        logger.info("  SQL save: {:.2f}s", time.time() - t)

        t = time.time()
        self.graph.add_incident(extraction)
        logger.info("  Graph build: {:.2f}s", time.time() - t)

        t = time.time()
        chunk_pairs = chunk_postmortem(doc, extraction.incident_id)
        logger.info("  Chunk: {:.2f}s ({} chunks)", time.time() - t, len(chunk_pairs))

        if chunk_pairs:
            t = time.time()
            texts = [text for text, _ in chunk_pairs]
            metadatas = [meta.model_dump() for _, meta in chunk_pairs]
            embeddings = self.embedding_model.embed_batch(texts)
            logger.info("  Embed: {:.2f}s", time.time() - t)

            t = time.time()
            self.vector_store.add_chunks(texts, metadatas, embeddings)
            logger.info("  Vector store: {:.2f}s", time.time() - t)

        self.graph.save()
        logger.info("Ingested {} in {:.2f}s total", file_path.name, time.time() - t0)
        return extraction

    def ingest_directory(self, dir_path: Path) -> list[IncidentExtraction]:
        """Ingest all supported files in a directory."""
        files = sorted(
            f for f in dir_path.iterdir()
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
        )

        if not files:
            logger.warning("No supported files found in {}", dir_path)
            return []

        logger.info("Found {} files to ingest in {}", len(files), dir_path)
        t0 = time.time()
        results: list[IncidentExtraction] = []
        failed = 0

        for i, f in enumerate(files, 1):
            logger.info("Processing {}/{}: {}", i, len(files), f.name)
            try:
                extraction = self.ingest_file(f)
                results.append(extraction)
            except Exception as exc:
                logger.error("Failed to ingest {}: {}", f.name, exc)
                failed += 1

        elapsed = time.time() - t0
        console = Console()
        table = Table(title="Ingestion Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total files", str(len(files)))
        table.add_row("Succeeded", str(len(results)))
        table.add_row("Failed", str(failed))
        table.add_row("Total time", f"{elapsed:.1f}s")
        console.print(table)

        return results

    def get_stats(self) -> dict:
        """Combined stats from all three stores."""
        return {
            "graph": self.graph.get_stats(),
            "vectors": {"total_chunks": self.vector_store.count()},
            "sql": {
                "total_incidents": len(self.sql_store.get_all_incidents()),
                "query_stats": self.sql_store.get_query_stats(),
            },
        }
