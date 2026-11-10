"""One manifest row as read by a sync."""

from vectra.utils import FrozenObject


class ManifestEntryDTO(FrozenObject):
    """What is recorded about an indexed document.

    Attributes:
        path: Document path relative to the source root.
        content_hash: Hash of the indexed bytes.
        chunker_version: Chunker that produced its chunks.
    """

    path: str
    content_hash: str
    chunker_version: str
