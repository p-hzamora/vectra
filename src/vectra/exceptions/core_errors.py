"""Errors raised while loading configuration."""

from .base import CoreException


class InvalidConfigurationError(CoreException):
    """A setting in the environment or the `.env` file has an invalid value."""

    __error_code__ = "CORE_001_INVALID_CONFIGURATION"
