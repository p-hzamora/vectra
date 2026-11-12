"""Port that tells how this vectra was installed."""

import abc

from vectra.bounded_context.updates.domain.value_objects import InstallMethod


class IInstallMethodDetector(abc.ABC):
    """Detects the installer that owns the running vectra."""

    @abc.abstractmethod
    def detect(self) -> InstallMethod | None:
        """The install method, or `None` when it is unknown, ambiguous, editable or unsupported."""
        ...
