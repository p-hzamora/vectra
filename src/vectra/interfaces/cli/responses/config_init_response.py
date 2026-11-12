"""`vectra config init` output."""

from .i_renderable_response import IRenderableResponse


class ConfigInitResponse(IRenderableResponse):
    """The env file `config init` wrote.

    Attributes:
        env_file: The file written.
        overwritten: Whether a file was already there and was replaced.
    """

    env_file: str
    overwritten: bool

    def render(self) -> str:
        return f"{'overwrote' if self.overwritten else 'wrote'} {self.env_file}"
