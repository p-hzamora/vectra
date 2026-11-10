"""A validated semantic search request."""

from pathlib import PurePosixPath

from pydantic import field_validator

from vectra.exceptions import InvalidSearchQueryError
from vectra.utils import FrozenObject

MAX_TOP_K: int = 100


class SearchQuery(FrozenObject):
    """What to look for.

    Attributes:
        text: Natural-language query.
        top_k: Number of documents to return (1..100).
        path_prefix: Only documents whose path starts with this prefix.
        min_score: Drop hits scoring below this (0..1); None keeps all.
    """

    text: str
    top_k: int = 5
    path_prefix: str | None = None
    min_score: float | None = None

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        if not value.strip():
            raise InvalidSearchQueryError("The search text cannot be empty.")
        return value

    @field_validator("top_k")
    @classmethod
    def _top_k(cls, value: int) -> int:
        if not 1 <= value <= MAX_TOP_K:
            raise InvalidSearchQueryError(
                f"top_k must be between 1 and {MAX_TOP_K}.", {"top_k": value}
            )
        return value

    @field_validator("path_prefix")
    @classmethod
    def _prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("/") or ".." in PurePosixPath(value).parts:
            raise InvalidSearchQueryError(
                "The path prefix must be relative without '..'.", {"path_prefix": value}
            )
        return value

    @field_validator("min_score")
    @classmethod
    def _min_score(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise InvalidSearchQueryError(
                "min_score must be between 0 and 1.", {"min_score": value}
            )
        return value
