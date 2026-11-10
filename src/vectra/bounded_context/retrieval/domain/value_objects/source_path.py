"""Path of a document relative to the collection's source root."""

from pathlib import PurePosixPath

from pydantic import field_validator

from vectra.exceptions import InvalidSourcePathError
from vectra.utils import FrozenObject


class SourcePath(FrozenObject):
    """Relative POSIX path without `..` segments.

    Attributes:
        value: The path, e.g. `notes/a.md`.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _valid(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or "\\" in value or path.is_absolute() or ".." in path.parts:
            raise InvalidSourcePathError(
                f"Invalid source path {value!r}.",
                {"path": value},
                next_steps=["Use a relative POSIX path without '..'."],
            )
        return path.as_posix()

    def __str__(self) -> str:
        return self.value
