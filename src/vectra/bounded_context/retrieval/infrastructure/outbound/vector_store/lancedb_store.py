"""Shared LanceDB access: connection, table names, schemas and the thread bridge."""

import asyncio
from collections.abc import Callable
from pathlib import Path

import lancedb
import pyarrow as pa
from lancedb.table import Table

from vectra.exceptions import AppException, VectorStoreError

COLLECTIONS_TABLE: str = "collections"
MANIFEST_TABLE: str = "manifest"
CHUNKS_PREFIX: str = "chunks_"

COLLECTIONS_SCHEMA: pa.Schema = pa.schema(
    [
        ("name", pa.string()),
        ("model_id", pa.string()),
        ("dimension", pa.int32()),
        ("source_root", pa.string()),
        ("created_at", pa.timestamp("us", tz="UTC")),
    ]
)
MANIFEST_SCHEMA: pa.Schema = pa.schema(
    [
        ("collection", pa.string()),
        ("path", pa.string()),
        ("content_hash", pa.string()),
        ("chunker_version", pa.string()),
        ("chunk_ids", pa.list_(pa.string())),
    ]
)


def chunks_schema(dimension: int) -> pa.Schema:
    """Schema of a collection's chunk table."""
    return pa.schema(
        [
            ("chunk_id", pa.string()),
            ("path", pa.string()),
            ("heading_path", pa.list_(pa.string())),
            ("text", pa.string()),
            ("metadata", pa.string()),
            ("vector", pa.list_(pa.float32(), dimension)),
        ]
    )


def literal(value: str) -> str:
    """A SQL string literal for a LanceDB filter."""
    return "'" + value.replace("'", "''") + "'"


class LanceDbStore:
    """One LanceDB database folder; every adapter of the vector store shares it.

    Calls are synchronous inside `run`, which moves them off the event loop.
    """

    def __init__(self, directory: Path) -> None:
        self._directory: Path = directory
        self._connection: lancedb.DBConnection | None = None

    async def run[T](self, operation: Callable[[], T]) -> T:
        """Run a blocking store call in a thread; foreign failures become `VectorStoreError`."""
        try:
            return await asyncio.to_thread(operation)
        except AppException:
            raise
        except Exception as error:
            raise VectorStoreError(
                f"The vector store failed: {error}", {"directory": str(self._directory)}
            ) from error

    def connection(self) -> lancedb.DBConnection:
        """The open database, created on first use."""
        if self._connection is None:
            self._directory.mkdir(parents=True, exist_ok=True)
            self._connection = lancedb.connect(self._directory)
        return self._connection

    def exists(self, name: str) -> bool:
        """Whether the table exists."""
        return name in self.connection().list_tables().tables

    def table(self, name: str, schema: pa.Schema) -> Table:
        """Open the table, creating it with `schema` when missing."""
        connection = self.connection()
        if self.exists(name):
            return connection.open_table(name)
        return connection.create_table(name, schema=schema)

    def open_chunks(self, collection: str) -> Table | None:
        """The collection's chunk table, or None when it does not exist."""
        name: str = CHUNKS_PREFIX + collection
        return self.connection().open_table(name) if self.exists(name) else None
