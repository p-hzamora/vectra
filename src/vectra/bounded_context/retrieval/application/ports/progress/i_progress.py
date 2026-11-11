"""Port to whoever wants to watch a long operation."""

import abc


class IProgress(abc.ABC):
    """Receives one human-readable line per step of a long operation."""

    @abc.abstractmethod
    def report(self, message: str) -> None:
        """Announce what is happening now."""
        ...


class NullProgress(IProgress):
    """Discards every message."""

    def report(self, message: str) -> None:
        return None
