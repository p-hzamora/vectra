"""A file a sync could not index."""

from vectra.utils import FrozenObject


class FileFailureDTO(FrozenObject):
    """Why one file failed, after retries.

    Attributes:
        path: Document path.
        code: Stable error code of the last failure.
        message: What went wrong.
        attempts: Times the file was tried (1 + retries used).
    """

    path: str
    code: str
    message: str
    attempts: int
