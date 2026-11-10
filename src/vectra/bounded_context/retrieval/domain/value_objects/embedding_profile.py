"""Model and vector size a collection's embeddings come from."""

from pydantic import field_validator

from vectra.exceptions import EmbeddingProfileMismatchError, InvalidRetrievalValueError
from vectra.utils import FrozenObject


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
            raise InvalidRetrievalValueError("An embedding profile needs a model id.")
        return value

    @field_validator("dimension")
    @classmethod
    def _dimension(cls, value: int) -> int:
        if value <= 0:
            raise InvalidRetrievalValueError("An embedding dimension must be positive.")
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
