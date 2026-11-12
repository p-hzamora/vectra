"""Model and vector size a collection's embeddings come from."""

from collections.abc import Sequence

from pydantic import field_validator

from vectra.exceptions import (
    EmbeddingDimensionMismatchError,
    EmbeddingProfileMismatchError,
    InvalidRetrievalValueError,
)
from vectra.utils import FrozenObject

from .embedding import Embedding


class EmbeddingProfile(FrozenObject):
    """Embeddings are only comparable when produced by the same model and dimension.

    Attributes:
        model_id: Embedding model identifier.
        dimension: Vector length.
    """

    model_id: str
    dimension: int

    @field_validator("model_id")
    @classmethod
    def _model(cls, value: str) -> str:
        if not value.strip():
            raise InvalidRetrievalValueError(
                "An embedding profile needs a model id.",
                next_steps=[
                    "Set VECTRA_EMBEDDING_MODEL_ID in the .env file, "
                    "or remove the variable to use the default."
                ],
            )
        return value

    @field_validator("dimension")
    @classmethod
    def _dimension(cls, value: int) -> int:
        if value <= 0:
            raise EmbeddingDimensionMismatchError("An embedding dimension must be positive.")
        return value

    @property
    def fingerprint(self) -> str:
        """`model_id:dimension`, the identity compared between runs."""
        return f"{self.model_id}:{self.dimension}"

    def assert_matches(self, stored: EmbeddingProfile, collection: str) -> None:
        """Fail unless this profile equals the one `collection` was built with.

        Args:
            stored: The collection's profile.
            collection: Collection name, for the message.

        Raises:
            EmbeddingProfileMismatchError: Model or dimension differs.
        """
        if self != stored:
            raise EmbeddingProfileMismatchError(
                f"Collection {collection} was built with {stored.fingerprint}, "
                f"not {self.fingerprint}.",
                {
                    "collection": collection,
                    "expected": stored.fingerprint,
                    "actual": self.fingerprint,
                },
                next_steps=[
                    "Set the embedding model back, or drop the collection and sync it again."
                ],
            )

    def assert_embeddings(self, embeddings: Sequence[Embedding], expected: int, path: str) -> None:
        """Fail unless `embeddings` are `expected` vectors of this profile's dimension.

        Args:
            embeddings: What the embedder returned.
            expected: How many vectors were asked for.
            path: Document path, for the message.

        Raises:
            EmbeddingDimensionMismatchError: Wrong count or wrong vector length.
        """
        if len(embeddings) != expected or any(
            embedding.dimension != self.dimension for embedding in embeddings
        ):
            raise EmbeddingDimensionMismatchError(
                f"The embedder returned vectors that do not match {self.fingerprint}.",
                {"path": path},
            )
