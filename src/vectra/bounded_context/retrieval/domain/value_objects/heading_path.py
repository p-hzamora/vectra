"""Headings leading to a chunk."""

from vectra.utils import FrozenObject

SEPARATOR: str = " > "


class HeadingPath(FrozenObject):
    """Ancestor headings from the document's top to the chunk's section (empty before any heading).

    Attributes:
        parts: Heading titles, outermost first.
    """

    parts: tuple[str, ...] = ()

    def as_text(self) -> str:
        """The headings joined with ` > `."""
        return SEPARATOR.join(self.parts)
