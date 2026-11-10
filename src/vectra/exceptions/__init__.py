"""Application-wide exception hierarchy and exit codes."""

from .base import (
    AppException,
    ApplicationException,
    CoreException,
    DomainException,
    InfrastructureException,
    InterfaceException,
)
from .core_errors import InvalidConfigurationError
from .exit_code_enum import ExitCodeEnum
from .interface_errors import ConfirmationRequiredError, SkillGuideNotFoundError
from .retrieval_errors import (
    ChunkerNotFoundError,
    CollectionNotFoundError,
    DocumentReadError,
    EmbeddingModelError,
    EmbeddingProfileMismatchError,
    InvalidCollectionNameError,
    InvalidRetrievalValueError,
    InvalidSearchQueryError,
    InvalidSourcePathError,
    MassDeleteRefusedError,
    SourceRootMismatchError,
    SourceRootNotFoundError,
    VectorStoreError,
)

__all__ = [
    "AppException",
    "ApplicationException",
    "ChunkerNotFoundError",
    "CollectionNotFoundError",
    "ConfirmationRequiredError",
    "CoreException",
    "DocumentReadError",
    "DomainException",
    "EmbeddingModelError",
    "EmbeddingProfileMismatchError",
    "ExitCodeEnum",
    "InfrastructureException",
    "InterfaceException",
    "InvalidCollectionNameError",
    "InvalidConfigurationError",
    "InvalidRetrievalValueError",
    "InvalidSearchQueryError",
    "InvalidSourcePathError",
    "MassDeleteRefusedError",
    "SkillGuideNotFoundError",
    "SourceRootMismatchError",
    "SourceRootNotFoundError",
    "VectorStoreError",
]
