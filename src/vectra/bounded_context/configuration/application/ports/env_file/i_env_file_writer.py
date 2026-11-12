"""Port to the place env files live."""

import abc
from pathlib import Path


class IEnvFileWriter(abc.ABC):
    """Checks for and writes an env file."""

    @abc.abstractmethod
    def exists(self, path: Path) -> bool:
        """Whether `path` already holds a file."""
        ...

    @abc.abstractmethod
    def write(self, path: Path, content: str) -> None:
        """Write `content` to `path`, creating missing parent folders and replacing any file."""
        ...
