"""Application-wide exception hierarchy and exit codes."""

from .base import (
    AppException,
    ApplicationException,
    CoreException,
    DomainException,
    InfrastructureException,
    InterfaceException,
)
from .configuration_errors import EnvFileExistsError
from .core_errors import InvalidConfigurationError
from .exit_code_enum import ExitCodeEnum
from .interface_errors import (
    ConfirmationRequiredError,
    NewRootRequiresRebuildError,
    SkillGuideNotFoundError,
    UsageError,
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
from .updates_errors import (
    InstallerNotDetectedError,
    InvalidVersionError,
    NoReleasePublishedError,
    ReleaseSourceUnavailableError,
    UpgradeFailedError,
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
    "EnvFileExistsError",
    "ExitCodeEnum",
    "InfrastructureException",
    "InstallerNotDetectedError",
    "InterfaceException",
    "InvalidCollectionNameError",
    "InvalidConfigurationError",
    "InvalidRetrievalValueError",
    "InvalidSearchQueryError",
    "InvalidSourcePathError",
    "InvalidVersionError",
    "MassDeleteRefusedError",
    "NewRootRequiresRebuildError",
    "NoReleasePublishedError",
    "ReleaseSourceUnavailableError",
    "SkillGuideNotFoundError",
    "SourceRootInvalidError",
    "UpgradeFailedError",
    "UsageError",
    "VectorStoreError",
]
