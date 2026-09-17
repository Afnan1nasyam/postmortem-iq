"""Sentence-transformer embedding helper with lazy loading."""

from loguru import logger

from src.config import settings


class EmbeddingModel:
    """Lazy-loaded sentence-transformers wrapper."""

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None

    def _load(self):
        if self._model is None:
            logger.info("Loading embedding model: {}", self._model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        self._load()
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        self._load()
        return self._model.encode(texts, convert_to_numpy=True).tolist()


_instance: EmbeddingModel | None = None


def get_embedding_model() -> EmbeddingModel:
    """Return a cached singleton EmbeddingModel instance."""
    global _instance
    if _instance is None:
        _instance = EmbeddingModel()
    return _instance
