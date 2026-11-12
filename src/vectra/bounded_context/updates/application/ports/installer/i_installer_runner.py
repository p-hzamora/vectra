"""Port that executes an upgrade."""

import abc

from vectra.bounded_context.updates.domain.value_objects import UpgradePlan


class IInstallerRunner(abc.ABC):
    """Runs an upgrade plan."""

    @abc.abstractmethod
    def run(self, plan: UpgradePlan) -> None:
        """Execute `plan` and return when it succeeded.

        Raises:
            UpgradeFailedError: The installer failed or could not be started.
        """
        ...
