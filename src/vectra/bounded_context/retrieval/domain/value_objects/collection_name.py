"""Name of a collection."""

import re

from pydantic import field_validator

from vectra.exceptions import InvalidCollectionNameError
from vectra.utils import FrozenObject

_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class CollectionName(FrozenObject):
    """Lowercase letters, digits, `-` and `_`; 1 to 63 characters, starting alphanumeric.

    Attributes:
        value: The name.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _valid(cls, value: str) -> str:
        if not _PATTERN.fullmatch(value):
            raise InvalidCollectionNameError(
                f"Invalid collection name {value!r}.",
                {"name": value},
                next_steps=["Use lowercase letters, digits, '-' and '_' (max 63 characters)."],
            )
        return value

    def __str__(self) -> str:
        return self.value
