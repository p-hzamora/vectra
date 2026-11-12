"""`vectra update --apply --yes` output."""

from .i_renderable_response import IRenderableResponse


class UpdateApplyResponse(IRenderableResponse):
    """What the update did.

    Attributes:
        current: Version installed before.
        latest: Latest release version.
        applied: Whether an installer ran.
        upgrade_command: The command that ran, or `None` when nothing ran.
        next_steps: What to do now.
    """

    current: str
    latest: str
    applied: bool
    upgrade_command: str | None
    next_steps: tuple[str, ...] = ()

    def render(self) -> str:
        if not self.applied:
            return f"already up to date: {self.current} (latest: {self.latest})"
        lines: list[str] = [f"updated {self.current} -> {self.latest}"]
        lines += [f"next: {step}" for step in self.next_steps]
        return "\n".join(lines)
