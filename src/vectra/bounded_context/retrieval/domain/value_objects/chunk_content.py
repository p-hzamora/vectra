"""A chunk as produced by a chunker, before it has an id or an embedding."""

from vectra.shared_kernel.domain import JsonObject
from vectra.utils import FrozenObject

from .heading_path import HeadingPath


class ChunkContent(FrozenObject):
    """Text of one section piece with its place and metadata.

    Attributes:
        heading_path: Headings above the chunk.
        text: Chunk text.
        metadata: Document metadata (frontmatter) copied onto the chunk.
    """

    heading_path: HeadingPath
    text: str
    metadata: JsonObject = {}  # noqa: RUF012 - pydantic copies the default per instance
