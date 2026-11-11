"""`vectra collections` output."""

from datetime import datetime

from vectra.utils import FrozenObject

from .i_renderable_response import IRenderableResponse


class CollectionResponse(FrozenObject):
    """One collection.

    Attributes:
        name: Collection name.
        model_id: Embedding model.
        dimension: Vector length.
        source_root: Folder indexed.
        created_at: Creation time.
        document_count: Indexed documents.
        chunk_count: Stored chunks.
    """

    name: str
    model_id: str
    dimension: int
    source_root: str
    created_at: datetime
    document_count: int
    chunk_count: int


class CollectionListResponse(IRenderableResponse):
    """`vectra collections list`.

    Attributes:
        collections: Collections sorted by name.
    """

    collections: tuple[CollectionResponse, ...]

    def render(self) -> str:
        if not self.collections:
            return "no collections"
        return "\n".join(
            f"{item.name}  {item.document_count} documents, {item.chunk_count} chunks  "
            f"{item.model_id}:{item.dimension}  {item.source_root}"
            for item in self.collections
        )


class DropResponse(IRenderableResponse):
    """`vectra collections drop`.

    Attributes:
        name: Collection removed.
        documents: Documents it held.
        chunks: Chunks it held.
    """

    name: str
    documents: int
    chunks: int

    def render(self) -> str:
        return f"dropped {self.name} ({self.documents} documents, {self.chunks} chunks)"


class CollectionCheckResponse(FrozenObject):
    """One collection compared with the configured model.

    Attributes:
        name: Collection name.
        model_id: Model the collection was built with.
        dimension: Vector length the collection was built with.
        configured_model_id: Model the settings ask for.
        configured_dimension: Vector length the settings ask for.
        in_sync: Whether both match.
    """

    name: str
    model_id: str
    dimension: int
    configured_model_id: str
    configured_dimension: int
    in_sync: bool


class CollectionCheckListResponse(IRenderableResponse):
    """`vectra collections check`.

    Attributes:
        in_sync: Whether every collection matches the configured model.
        collections: Checked collections sorted by name.
    """

    in_sync: bool
    collections: tuple[CollectionCheckResponse, ...]

    def render(self) -> str:
        if not self.collections:
            return "no collections"
        return "\n".join(
            f"{item.name}  ok  {item.model_id}:{item.dimension}"
            if item.in_sync
            else f"{item.name}  MISMATCH  built with {item.model_id}:{item.dimension}, "
            f"configured {item.configured_model_id}:{item.configured_dimension}"
            for item in self.collections
        )
