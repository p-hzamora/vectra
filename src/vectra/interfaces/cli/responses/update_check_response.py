"""`vectra update --check` output."""

from .i_renderable_response import IRenderableResponse


class UpdateCheckResponse(IRenderableResponse):
    """Installed and latest versions.

    Attributes:
        current: Installed version.
        latest: Latest release version, or `None` when none is published.
        update_available: `None` when the installed version cannot be compared.
        upgrade_command: Command that installs the latest release, or `None` without one.
    """

    current: str
    latest: str | None
    update_available: bool | None
    upgrade_command: str | None

    def render(self) -> str:
        lines: list[str] = [f"installed: {self.current}"]
        if self.latest is None:
            lines.append("latest: none published yet")
        else:
            lines.append(f"latest: {self.latest}")
        if self.update_available is True:
            lines.append("update available")
        elif self.update_available is None and self.latest is not None:
            lines.append("cannot compare: this is not a release build")
        else:
            lines.append("up to date")
        if self.upgrade_command is not None and self.update_available is not False:
            lines.append(f"upgrade: {self.upgrade_command}")
            lines.append("or run `vectra update --apply --yes`")
        return "\n".join(lines)
