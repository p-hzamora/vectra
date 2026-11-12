"""Versions, release tags, install methods and the policies over them."""

import pytest

from vectra.bounded_context.updates.domain.policies import (
    INSTALL_SCRIPT_URL,
    REPO_URL,
    UpdateAvailabilityPolicy,
    UpgradePlanPolicy,
)
from vectra.bounded_context.updates.domain.value_objects import (
    InstallerKind,
    InstallMethod,
    ReleaseTag,
    UpgradePlan,
    Version,
)
from vectra.exceptions import InvalidVersionError

pytestmark = pytest.mark.unit

HOSTILE: list[str] = [
    "",
    "1.2",
    "1.2.3.4",
    "v1.2.3",
    "1.2.3-rc.1",
    "1.2.3; x",
    "--index-url=x",
    "1.2.3\n",
]


@pytest.mark.parametrize("text", HOSTILE)
def test_version_rejects_anything_but_x_y_z(text: str) -> None:
    with pytest.raises(InvalidVersionError) as raised:
        Version.parse(text)
    assert raised.value.error_code == "UPDATES_001_INVALID_VERSION"
    assert raised.value.next_steps


@pytest.mark.parametrize("text", ["", "v1.2", "v1.2.3-rc.1", "v1.2.3; x", "--index-url=x", "1.2.3"])
def test_release_tag_rejects_anything_but_v_x_y_z(text: str) -> None:
    with pytest.raises(InvalidVersionError):
        ReleaseTag.parse(text)


def test_release_tag_round_trips() -> None:
    tag = ReleaseTag.parse("v0.10.2")
    assert (str(tag), str(tag.version)) == ("v0.10.2", "0.10.2")


def test_versions_compare_numerically() -> None:
    assert Version.parse("0.10.0").is_newer_than(Version.parse("0.9.9"))
    assert not Version.parse("1.0.0").is_newer_than(Version.parse("1.0.0"))
    assert not Version.parse("1.0.0").is_newer_than(Version.parse("1.0.1"))


def test_venv_method_needs_its_interpreter() -> None:
    with pytest.raises(ValueError, match="interpreter"):
        InstallMethod(kind=InstallerKind.VENV)


@pytest.mark.parametrize(
    ("tag_name", "prerelease", "draft", "accepted"),
    [
        ("v1.2.3", False, False, "v1.2.3"),
        ("v1.2.3", True, False, None),
        ("v1.2.3", False, True, None),
        ("1.2.3", False, False, None),
        ("v1.2.3-rc.1", False, False, None),
        ("nightly", False, False, None),
    ],
)
def test_only_published_strict_tags_are_releases(
    tag_name: str, prerelease: bool, draft: bool, accepted: str | None
) -> None:
    tag = UpdateAvailabilityPolicy().accepted_tag(
        tag_name=tag_name, prerelease=prerelease, draft=draft
    )
    assert (str(tag) if tag else None) == accepted


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("0.3.0", "v0.3.1", True),
        ("0.3.0", "v0.3.0", False),
        ("0.4.0", "v0.3.0", False),
        ("0.3.0", None, False),
        ("0.0.0+unknown", "v0.3.0", None),
        ("0.3.0.dev1", "v0.3.0", None),
        ("0.0.0+unknown", None, False),
    ],
)
def test_availability(current: str, latest: str | None, expected: bool | None) -> None:
    policy = UpdateAvailabilityPolicy()
    tag = ReleaseTag.parse(latest) if latest else None
    assert policy.availability(current=policy.current(current), latest=tag) is expected


SPEC: str = "git+https://github.com/p-hzamora/vectra@v1.2.3"


def test_plan_argv_per_method() -> None:
    policy = UpgradePlanPolicy()
    tag = ReleaseTag.parse("v1.2.3")
    uv = policy.plan(InstallMethod(kind=InstallerKind.UV), tag)
    pipx = policy.plan(InstallMethod(kind=InstallerKind.PIPX), tag)
    venv = policy.plan(InstallMethod(kind=InstallerKind.VENV, python="/v/bin/python"), tag)
    assert uv.argv == ("uv", "tool", "install", "--force", "--python", ">=3.14", SPEC)
    assert pipx.argv == ("pipx", "install", "--force", SPEC)
    assert venv.argv == ("/v/bin/python", "-m", "pip", "install", "--upgrade", SPEC)
    assert uv.command == f"uv tool install --force --python '>=3.14' {SPEC}"


def test_plan_quotes_paths_with_spaces_in_its_display() -> None:
    plan = UpgradePlan(argv=("/my venv/bin/python", "-m", "pip"))
    assert plan.command == "'/my venv/bin/python' -m pip"


def test_manual_command_pins_the_tag() -> None:
    assert UpgradePlanPolicy().manual_command(ReleaseTag.parse("v1.2.3")) == (
        f"curl -LsSf {INSTALL_SCRIPT_URL} | VECTRA_REF=v1.2.3 sh"
    )
    assert REPO_URL == "https://github.com/p-hzamora/vectra"
