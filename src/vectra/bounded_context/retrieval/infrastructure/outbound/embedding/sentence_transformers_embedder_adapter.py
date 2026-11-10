"""Embeddings from a local sentence-transformers model."""

import asyncio
from collections.abc import Sequence
from typing import Any

from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.domain.value_objects import Embedding, EmbeddingProfile
from vectra.exceptions import EmbeddingModelError

BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "
BATCH_SIZE: int = 32


class SentenceTransformersEmbedderAdapter(IEmbedder):
    """Loads the model on first use (so `--help` and dry runs stay fast) and encodes in a thread.

    BGE models get their query instruction prefix on queries only; vectors are normalized.
    """

    def __init__(self, model_id: str, dimension: int, query_prefix: str | None = None) -> None:
        self._profile: EmbeddingProfile = EmbeddingProfile(model_id=model_id, dimension=dimension)
        self._query_prefix: str = (
            query_prefix
            if query_prefix is not None
            else (BGE_QUERY_PREFIX if "bge" in model_id.lower() else "")
        )
        self._model: Any = None

    @property
    def profile(self) -> EmbeddingProfile:
        return self._profile

    async def embed_documents(self, texts: Sequence[str]) -> list[Embedding]:
        if not texts:
            return []
        return await self._encode(list(texts))

    async def embed_query(self, text: str) -> Embedding:
        return (await self._encode([self._query_prefix + text]))[0]

    async def _encode(self, texts: list[str]) -> list[Embedding]:
        try:
            vectors: Any = await asyncio.to_thread(self._encode_blocking, texts)
        except EmbeddingModelError:
            raise
        except Exception as error:
            raise EmbeddingModelError(
                f"The embedding model {self._profile.model_id!r} failed: {error}",
                {"model_id": self._profile.model_id},
                next_steps=["Check the model id and network access for the first download."],
            ) from error
        return [Embedding(values=tuple(float(value) for value in vector)) for vector in vectors]

    def _encode_blocking(self, texts: list[str]) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._profile.model_id)
        return self._model.encode(
            texts, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False
        )
