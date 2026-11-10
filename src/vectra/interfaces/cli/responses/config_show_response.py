"""`vectra config show` output."""

from .i_renderable_response import IRenderableResponse


class ConfigShowResponse(IRenderableResponse):
    """The configuration this invocation resolved.

    Attributes:
        env_file: The `.env` file read.
        env_file_exists: Whether that file exists (a missing file means defaults only).
        data_dir: Where vectra keeps its data.
    """

    env_file: str
    env_file_exists: bool
    data_dir: str

    def render(self) -> str:
        missing: str = "" if self.env_file_exists else " (missing: defaults only)"
        return f"env file: {self.env_file}{missing}\ndata dir: {self.data_dir}"
