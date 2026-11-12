# `vectra update [--check | --apply --yes]`

Purpose: find out whether a newer release of vectra exists, and reinstall at it. This is the
only command that talks to the network on its own, and only when you run it: no other command
checks for updates. Your configuration and indexes are never touched.

Source: `bounded_context/updates/`, wired in `interfaces/cli/bootstrap.py` (`build_updates`).

## `vectra update` / `vectra update --check`

One unauthenticated HTTPS `GET https://api.github.com/repos/p-hzamora/vectra/releases/latest`
(10 second timeout, header `User-Agent: vectra/<version>`, no token). Only a published GitHub
Release whose tag is exactly `vX.Y.Z` counts: pre-releases, drafts, other tags and tags without
a Release are ignored.

```json
{
  "ok": true,
  "result": {
    "current": "0.3.0",
    "latest": "0.4.0",
    "update_available": true,
    "upgrade_command": "uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@v0.4.0"
  }
}
```

- `latest` is `null` and `update_available` is `false` when no release exists yet (exit 0, not
  an error); `upgrade_command` is then `null`.
- `update_available` is `false` when the installed version is newer than the latest release.
- `update_available` is `null` when the installed version is not `X.Y.Z` (a dev or source
  build), because it cannot be compared.
- `upgrade_command` is the command for the detected install method, or the manual
  `install.sh` command when the method is not detected (checking never fails for that).

Text output:

```text
installed: 0.3.0
latest: 0.4.0
update available
upgrade: uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@v0.4.0
or run `vectra update --apply --yes`
```

## `vectra update --apply --yes`

Resolves the latest release as above, then reinstalls at its tag with the installer that owns
this install. `install.sh` is never executed.

| Detected install | Command run (argv list, no shell, output captured) |
|---|---|
| uv tool (`.../uv/tools/vectra`) | `uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@<tag>` |
| pipx (`.../pipx/venvs/vectra`) | `pipx install --force --python <vectra's interpreter> git+https://github.com/p-hzamora/vectra@<tag>` |
| private venv (`$VECTRA_HOME/venv`, default `~/.local/share/vectra/venv`) | `<venv>/bin/python -m pip install --upgrade git+https://github.com/p-hzamora/vectra@<tag>` |

These match what `install.sh` runs; a test compares them against the script.

```json
{
  "ok": true,
  "result": {
    "current": "0.3.0",
    "latest": "0.4.0",
    "applied": true,
    "upgrade_command": "uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@v0.4.0",
    "next_steps": ["Run `vectra collections check` in case the new version changed the embedding settings."]
  }
}
```

When the installed version is not older than the latest release nothing runs: `applied` is
`false`, `upgrade_command` is `null`, exit 0. After a real update run
`vectra collections check`.

## Failures

| Situation | Code | Exit |
|---|---|---|
| `--apply` without `--yes` | `INTERFACE_002_CONFIRMATION_REQUIRED` | 2 |
| `--check` together with `--apply` | `INTERFACE_004_USAGE_ERROR` | 2 |
| GitHub unreachable, timeout, HTTP error (rate limit, 403) or bad JSON | `UPDATES_201_RELEASE_SOURCE_UNAVAILABLE` | 1 |
| `--apply` and no usable release | `UPDATES_102_NO_RELEASE_PUBLISHED` | 1 |
| `--apply` on a dev build (installed version is not `X.Y.Z`) | `UPDATES_001_INVALID_VERSION` | 1 |
| `--apply` on an editable or source checkout, on Windows, or when more than one installer matches | `UPDATES_101_INSTALLER_NOT_DETECTED` | 1 |
| The installer exited non-zero or could not start | `UPDATES_202_UPGRADE_FAILED` (`metadata.stderr_tail`) | 1 |

`UPDATES_101` carries the manual command in `next_steps`:
`curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | VECTRA_REF=<tag> sh`.
Windows is not supported by `--apply`.
