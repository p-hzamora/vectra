"""The commands that install a release; they mirror what `install.sh` runs."""

from vectra.bounded_context.updates.domain.value_objects import (
    InstallerKind,
    InstallMethod,
    ReleaseTag,
    UpgradePlan,
)

REPO_URL: str = "https://github.com/p-hzamora/vectra"
INSTALL_SCRIPT_URL: str = "https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh"


class UpgradePlanPolicy:
    """Builds the argv per install method and the manual command for the rest."""

    def plan(self, method: InstallMethod, tag: ReleaseTag) -> UpgradePlan:
        """The command that reinstalls vectra at `tag` with the method that owns the install."""
        spec: str = f"git+{REPO_URL}@{tag}"
        match method.kind:
            case InstallerKind.UV:
                argv: tuple[str, ...] = (
                    "uv", "tool", "install", "--force", "--python", ">=3.14", spec,
                )  # fmt: skip
            case InstallerKind.PIPX:
                argv = ("pipx", "install", "--force", "--python", str(method.python), spec)
            case InstallerKind.VENV:
                argv = (str(method.python), "-m", "pip", "install", "--upgrade", spec)
        return UpgradePlan(argv=argv)

    def manual_command(self, tag: ReleaseTag) -> str:
        """The `install.sh` one-liner pinned to `tag`, for installs vectra cannot upgrade itself."""
        return f"curl -LsSf {INSTALL_SCRIPT_URL} | VECTRA_REF={tag} sh"
