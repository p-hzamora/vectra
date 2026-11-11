"""`--verbose`: progress lines and a spinner on stderr, so stdout stays machine-readable."""

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.status import Status

from vectra.bounded_context.retrieval.application.ports.progress import IProgress, NullProgress


class ConsoleProgress(IProgress):
    """Prints each message as a line above a spinner that shows the current step."""

    def __init__(self, console: Console, status: Status) -> None:
        self._console: Console = console
        self._status: Status = status

    def report(self, message: str) -> None:
        self._console.print(message, markup=False, highlight=False)
        self._status.update(message)


@contextmanager
def progress_scope(verbose: bool) -> Iterator[IProgress]:
    """A console reporter while the block runs when `verbose`, otherwise one that discards."""
    if not verbose:
        yield NullProgress()
        return
    console = Console(stderr=True)
    with console.status("working...") as status:
        yield ConsoleProgress(console, status)
