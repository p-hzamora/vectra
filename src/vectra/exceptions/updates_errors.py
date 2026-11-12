"""Errors of the updates context. Codes: 0xx domain, 1xx application, 2xx infrastructure."""

from .base import ApplicationException, DomainException, InfrastructureException


class InvalidVersionError(DomainException):
    """A version or release tag is not a strict `X.Y.Z` / `vX.Y.Z`."""

    __error_code__ = "UPDATES_001_INVALID_VERSION"


class InstallerNotDetectedError(ApplicationException):
    """`update --apply` cannot tell how vectra was installed, or the install is not upgradable."""

    __error_code__ = "UPDATES_101_INSTALLER_NOT_DETECTED"


class NoReleasePublishedError(ApplicationException):
    """`update --apply` found no usable release to install."""

    __error_code__ = "UPDATES_102_NO_RELEASE_PUBLISHED"


class ReleaseSourceUnavailableError(InfrastructureException):
    """The releases of vectra could not be read (network, HTTP status or payload)."""

    __error_code__ = "UPDATES_201_RELEASE_SOURCE_UNAVAILABLE"


class UpgradeFailedError(InfrastructureException):
    """The installer ran and failed, or could not be started."""

    __error_code__ = "UPDATES_202_UPGRADE_FAILED"
