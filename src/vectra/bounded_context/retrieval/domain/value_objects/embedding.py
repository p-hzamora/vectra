"""One embedding vector."""

from pydantic import field_validator

from vectra.exceptions import InvalidRetrievalValueError
from vectra.utils import FrozenObject


class Embedding(FrozenObject):
    """A non-empty vector of floats.

    Attributes:
        values: The components.
    """

    values: tuple[float, ...]

    @field_validator("values")
    @classmethod
    def _non_empty(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        if not values:
            raise InvalidRetrievalValueError("An embedding cannot be empty.")
        return values

    @property
    def dimension(self) -> int:
        """Vector length."""
        return len(self.values)
