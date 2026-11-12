"""Port to where vectra publishes its releases."""

import abc

from vectra.bounded_context.updates.application.dtos import ReleaseInfoDTO


class IReleaseSource(abc.ABC):
    """Reads the latest release."""

    @abc.abstractmethod
    def latest_release(self) -> ReleaseInfoDTO | None:
        """The latest release, or `None` when none was published.

        Raises:
            ReleaseSourceUnavailableError: The source could not be read.
        """
        ...
