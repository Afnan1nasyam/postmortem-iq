"""Semantic vector search over postmortem chunks."""

from loguru import logger

from src.storage.vector_store import VectorStore
from src.utils.embedding import EmbeddingModel


class VectorRetriever:
    """Retrieves relevant postmortem chunks via embedding similarity."""

    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """Embed the query and return the closest chunks sorted by distance."""
        query_embedding = self.embedding_model.embed_text(query)
        results = self.vector_store.search(query_embedding, top_k=top_k)
        results.sort(key=lambda r: r["distance"])
        logger.debug("Vector retrieval: {} results for query '{}'", len(results), query[:80])
        return results
