"""Folder a collection indexes, bound when the collection is created."""

from pathlib import PurePosixPath

from pydantic import field_validator

from vectra.exceptions import InvalidRetrievalValueError
from vectra.utils import FrozenObject


class SourceRoot(FrozenObject):
    """Absolute POSIX-style path of the indexed folder.

    Attributes:
        value: The absolute, normalized path.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute():
            raise InvalidRetrievalValueError(
                f"A source root must be absolute: {value!r}.", {"root": value}
            )
        return path.as_posix()
