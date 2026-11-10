"""Write repository contracts of the retrieval aggregates."""

from .i_collection_repository import ICollectionRepository
from .i_indexed_document_repository import IIndexedDocumentRepository

__all__ = ["ICollectionRepository", "IIndexedDocumentRepository"]
