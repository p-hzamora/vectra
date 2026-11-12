"""The git tag of a release."""

from typing import Self

from vectra.exceptions import InvalidVersionError
from vectra.utils import FrozenObject

from .version import Version


class ReleaseTag(FrozenObject):
    """A tag spelled `vX.Y.Z` and nothing else, so it is safe to pass to an installer.

    Attributes:
        version: The version the tag names.
    """

    version: Version

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read `text` as a release tag.

        Raises:
            InvalidVersionError: `text` is not exactly `vX.Y.Z`.
        """
        if not text.startswith("v"):
            raise InvalidVersionError(
                f"{text!r} is not a release tag (expected vX.Y.Z).",
                {"tag": text},
                next_steps=["Release tags look like v1.2.3."],
            )
        return cls(version=Version.parse(text[1:]))

    def __str__(self) -> str:
        return f"v{self.version}"
