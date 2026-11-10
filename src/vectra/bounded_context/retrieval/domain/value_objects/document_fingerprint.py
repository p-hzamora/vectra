"""What decides whether a document needs reindexing."""

from vectra.utils import FrozenObject

from .content_hash import ContentHash
from .source_path import SourcePath


class DocumentFingerprint(FrozenObject):
    """A document's path, content hash and the chunker version that produced its chunks.

    Attributes:
        path: Document path.
        content_hash: Hash of its bytes.
        chunker_version: Version of the chunker that cut it.
    """

    path: SourcePath
    content_hash: ContentHash
    chunker_version: str
