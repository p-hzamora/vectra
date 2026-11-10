"""vectra: chunk files, embed them into a vector store, and serve semantic search."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("vectra")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0+unknown"
