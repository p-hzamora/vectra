"""Immutable, self-validating values of the updates domain."""

from .install_method import InstallerKind, InstallMethod
from .release_tag import ReleaseTag
from .upgrade_plan import UpgradePlan
from .version import Version

__all__ = ["InstallMethod", "InstallerKind", "ReleaseTag", "UpgradePlan", "Version"]
