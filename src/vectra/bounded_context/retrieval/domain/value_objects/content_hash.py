"""SHA-256 of a document's bytes."""

import re

from pydantic import field_validator

from vectra.exceptions import InvalidRetrievalValueError
from vectra.utils import FrozenObject

_SHA256: re.Pattern[str] = re.compile(r"^[0-9a-f]{64}$")


class ContentHash(FrozenObject):
    """Lowercase hex SHA-256.

    Attributes:
        value: 64 hex characters.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _valid(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise InvalidRetrievalValueError("A content hash must be 64 lowercase hex characters.")
        return value
