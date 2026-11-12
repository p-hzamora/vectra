"""The command that upgrades vectra."""

import shlex

from vectra.utils import FrozenObject


class UpgradePlan(FrozenObject):
    """A program and its arguments; never a shell string.

    Attributes:
        argv: Program followed by its arguments.
    """

    argv: tuple[str, ...]

    @property
    def command(self) -> str:
        """The plan as a line a person can paste into a shell."""
        return shlex.join(self.argv)
