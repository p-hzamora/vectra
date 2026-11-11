"""Retries one unit of work and reports its failure as data."""

import asyncio
from collections.abc import Awaitable, Callable

from vectra.bounded_context.retrieval.application.dtos import FileFailureDTO
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.exceptions import AppException

UNEXPECTED_CODE: str = "RETRIEVAL_000_UNEXPECTED"


class RetryRunner:
    """Runs an operation up to `max_retries` extra times with growing backoff."""

    def __init__(
        self,
        *,
        max_retries: int,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._max_retries: int = max_retries
        self._backoff_seconds: float = backoff_seconds
        self._sleep: Callable[[float], Awaitable[None]] = sleep

    async def run[T](
        self, path: SourcePath, operation: Callable[[], Awaitable[T]]
    ) -> T | FileFailureDTO:
        """The operation's result, or the failure after the last attempt."""
        attempts: int = 0
        while True:
            attempts += 1
            try:
                return await operation()
            except Exception as error:
                if attempts > self._max_retries:
                    return FileFailureDTO(
                        path=path.value,
                        code=error.error_code
                        if isinstance(error, AppException)
                        else UNEXPECTED_CODE,
                        message=error.message if isinstance(error, AppException) else str(error),
                        attempts=attempts,
                    )
                await self._sleep(self._backoff_seconds * attempts)
