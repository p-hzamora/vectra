"""Facts about one collection."""

from datetime import datetime

from vectra.utils import FrozenObject


class CollectionStatusDTO(FrozenObject):
    """A collection as listed.

    Attributes:
        name: Collection name.
        model_id: Embedding model it was built with.
        dimension: Vector length.
        source_root: Folder it indexes.
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
