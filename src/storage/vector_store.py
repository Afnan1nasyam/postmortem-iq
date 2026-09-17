"""ChromaDB vector store wrapper for postmortem chunks."""

from uuid import uuid4

from loguru import logger

from src.config import settings


class VectorStore:
    """Persistent ChromaDB collection for postmortem chunk embeddings."""

    COLLECTION_NAME = "postmortem_chunks"

    def __init__(self):
        import chromadb

        self._client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore ready ({} chunks)", self._collection.count())

    def add_chunks(
        self,
        chunks: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Add chunks with precomputed embeddings."""
        ids = [str(uuid4()) for _ in chunks]
        self._collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info("Added {} chunks to vector store", len(chunks))

    def search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> list[dict]:
        """Semantic search returning [{text, metadata, distance}]."""
        top_k = top_k or settings.VECTOR_TOP_K
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return out

    def get_by_incident(self, incident_id: str) -> list[dict]:
        """Retrieve all chunks for a given incident ID."""
        results = self._collection.get(
            where={"incident_id": incident_id},
            include=["documents", "metadatas"],
        )
        out = []
        for i in range(len(results["ids"])):
            out.append({
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
            })
        return out

    def count(self) -> int:
        """Return total number of stored chunks."""
        return self._collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection."""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore reset")
