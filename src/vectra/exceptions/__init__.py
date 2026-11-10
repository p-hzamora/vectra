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
from .interface_errors import (
    ConfirmationRequiredError,
    NewRootRequiresRebuildError,
    SkillGuideNotFoundError,
)
from .retrieval_errors import (
    ChunkingFailedError,
    CollectionNotFoundError,
    DocumentReadError,
    EmbeddingDimensionMismatchError,
    EmbeddingModelError,
    EmbeddingProfileMismatchError,
    InvalidCollectionNameError,
    InvalidRetrievalValueError,
    InvalidSearchQueryError,
    InvalidSourcePathError,
    MassDeleteRefusedError,
    SourceRootInvalidError,
    VectorStoreError,
)

__all__ = [
    "AppException",
    "ApplicationException",
    "ChunkingFailedError",
    "CollectionNotFoundError",
    "ConfirmationRequiredError",
    "CoreException",
    "DocumentReadError",
    "DomainException",
    "EmbeddingDimensionMismatchError",
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
    "NewRootRequiresRebuildError",
    "SkillGuideNotFoundError",
    "SourceRootInvalidError",
    "VectorStoreError",
]
