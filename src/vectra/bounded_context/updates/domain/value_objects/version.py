"""A released version of vectra."""

import re
from typing import Self

from vectra.exceptions import InvalidVersionError
from vectra.utils import FrozenObject

_PATTERN: re.Pattern[str] = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")


class Version(FrozenObject):
    """Strict `MAJOR.MINOR.PATCH`; pre-release, dev and local suffixes are not versions here.

    Attributes:
        major: Major number.
        minor: Minor number.
        patch: Patch number.
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read `text` as a version.

        Raises:
            InvalidVersionError: `text` is not exactly `X.Y.Z`.
        """
        found: re.Match[str] | None = _PATTERN.fullmatch(text)
        if found is None:
            raise InvalidVersionError(
                f"{text!r} is not a release version (expected X.Y.Z).",
                {"version": text},
                next_steps=["Use a released version such as 1.2.3."],
            )
        return cls(major=int(found[1]), minor=int(found[2]), patch=int(found[3]))

    def is_newer_than(self, other: Version) -> bool:
        """Whether this version is strictly greater than `other`."""
        return self._key() > other._key()

    def _key(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
