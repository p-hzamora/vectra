"""Write payload of one chunk: never held by an aggregate root."""

from vectra.shared_kernel.domain import JsonObject
from vectra.utils import FrozenObject

from .chunk_id import ChunkId
from .embedding import Embedding
from .heading_path import HeadingPath


class EmbeddedChunk(FrozenObject):
    """A chunk ready to be stored.

    Attributes:
        chunk_id: Stable id.
        text: Chunk text.
        heading_path: Headings above the chunk.
        metadata: Document metadata copied onto the chunk.
        embedding: The text's vector.
    """

    chunk_id: ChunkId
    text: str
    heading_path: HeadingPath
    metadata: JsonObject = {}  # noqa: RUF012 - pydantic copies the default per instance
    embedding: Embedding
