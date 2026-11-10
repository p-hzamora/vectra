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

    __error_code__ = "RETRIEVAL_003_INDEX_PROFILE_MISMATCH"


class InvalidSearchQueryError(DomainException):
    """A search request has empty text or an out-of-range parameter."""

    __error_code__ = "RETRIEVAL_004_INVALID_SEARCH_QUERY"


class EmbeddingDimensionMismatchError(DomainException):
    """An embedding is empty, or its length differs from the profile's dimension."""

    __error_code__ = "RETRIEVAL_005_EMBEDDING_DIMENSION_MISMATCH"


class InvalidRetrievalValueError(DomainException):
    """A hash, chunk id or model id is malformed (extra code, no approved equivalent)."""

    __error_code__ = "RETRIEVAL_006_INVALID_VALUE"


class CollectionNotFoundError(ApplicationException):
    """No collection has that name."""

    __error_code__ = "RETRIEVAL_101_COLLECTION_NOT_FOUND"


class SourceRootInvalidError(ApplicationException):
    """The source root is relative, missing, unreadable, or differs from the collection's root."""

    __error_code__ = "RETRIEVAL_102_SOURCE_ROOT_INVALID"


class MassDeleteRefusedError(ApplicationException):
    """A sync would delete more than half of the indexed documents."""

    __error_code__ = "RETRIEVAL_103_MASS_DELETE_REFUSED"


class VectorStoreError(InfrastructureException):
    """The vector store failed to read or write."""

    __error_code__ = "RETRIEVAL_201_VECTOR_STORE_UNAVAILABLE"


class EmbeddingModelError(InfrastructureException):
    """The embedding model could not be loaded or failed to embed."""

    __error_code__ = "RETRIEVAL_202_EMBEDDER_UNAVAILABLE"


class DocumentReadError(InfrastructureException):
    """A source document could not be read or decoded."""

    __error_code__ = "RETRIEVAL_203_DOCUMENT_UNREADABLE"


class ChunkingFailedError(InfrastructureException):
    """A document could not be chunked (for example no chunker handles its extension)."""

    __error_code__ = "RETRIEVAL_204_CHUNKING_FAILED"
