"""Errors raised by delivery adapters for invalid input."""

from .base import InterfaceException


class SkillGuideNotFoundError(InterfaceException):
    """`skills get` named a guide this version does not ship."""

    __error_code__ = "INTERFACE_001_SKILL_GUIDE_NOT_FOUND"


class ConfirmationRequiredError(InterfaceException):
    """A destructive command ran without `--yes`."""

    __error_code__ = "INTERFACE_002_CONFIRMATION_REQUIRED"
