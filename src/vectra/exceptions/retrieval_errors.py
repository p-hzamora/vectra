"""Errors of the retrieval context. Codes: 0xx domain, 1xx application, 2xx infrastructure."""

from .base import ApplicationException, DomainException, InfrastructureException


class InvalidCollectionNameError(DomainException):
    """A collection name is not lowercase letters, digits, `-` or `_`."""

    __error_code__ = "RETRIEVAL_001_INVALID_COLLECTION_NAME"


class InvalidSourcePathError(DomainException):
    """A document path is not relative, POSIX-style and free of `..`."""

    __error_code__ = "RETRIEVAL_002_INVALID_SOURCE_PATH"


class EmbeddingProfileMismatchError(DomainException):
    """The embedding model or dimension differs from the one the collection was built with."""

    __error_code__ = "RETRIEVAL_003_EMBEDDING_PROFILE_MISMATCH"


class InvalidSearchQueryError(DomainException):
    """A search request has empty text or an out-of-range parameter."""

    __error_code__ = "RETRIEVAL_004_INVALID_SEARCH_QUERY"


class InvalidRetrievalValueError(DomainException):
    """A hash, chunk id, embedding, profile or source root value is malformed."""

    __error_code__ = "RETRIEVAL_005_INVALID_VALUE"


class CollectionNotFoundError(ApplicationException):
    """No collection has that name."""

    __error_code__ = "RETRIEVAL_101_COLLECTION_NOT_FOUND"


class SourceRootMismatchError(ApplicationException):
    """The collection is bound to a different source root."""

    __error_code__ = "RETRIEVAL_102_SOURCE_ROOT_MISMATCH"


class MassDeleteRefusedError(ApplicationException):
    """A sync would delete more than half of the indexed documents."""

    __error_code__ = "RETRIEVAL_103_MASS_DELETE_REFUSED"


class ChunkerNotFoundError(ApplicationException):
    """No chunker handles the file extension."""

    __error_code__ = "RETRIEVAL_104_CHUNKER_NOT_FOUND"


class SourceRootNotFoundError(InfrastructureException):
    """The source root is missing or is not a folder."""

    __error_code__ = "RETRIEVAL_201_SOURCE_ROOT_NOT_FOUND"


class VectorStoreError(InfrastructureException):
    """The vector store failed to read or write."""

    __error_code__ = "RETRIEVAL_202_VECTOR_STORE_FAILURE"


class EmbeddingModelError(InfrastructureException):
    """The embedding model could not be loaded or failed to embed."""

    __error_code__ = "RETRIEVAL_203_EMBEDDING_MODEL_FAILURE"


class DocumentReadError(InfrastructureException):
    """A source document could not be read or decoded."""

    __error_code__ = "RETRIEVAL_204_DOCUMENT_READ_FAILURE"
