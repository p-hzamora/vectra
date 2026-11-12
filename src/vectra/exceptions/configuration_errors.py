"""Errors of the configuration context. Codes: 0xx domain, 1xx application, 2xx infrastructure."""

from .base import ApplicationException


class EnvFileExistsError(ApplicationException):
    """`config init` found a file where it would write the template."""

    __error_code__ = "CONFIGURATION_101_ENV_FILE_EXISTS"
