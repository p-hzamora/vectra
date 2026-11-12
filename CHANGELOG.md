# Changelog

All notable changes to vectra are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/) (before 1.0, a minor bump may include breaking
changes).

Add every user-visible change under `Unreleased` as you make it. To release: rename
`Unreleased` to the new version and date, bump `version` in `pyproject.toml`, run `uv lock`,
commit, and tag `vX.Y.Z`.

## [Unreleased]

## [0.4.4] - 2026-11-12

### Added

- `vectra update` (`--check`, the default): one explicit HTTPS call to GitHub's latest release of
  `p-hzamora/vectra`, returning `current`, `latest`, `update_available` and `upgrade_command`.
  Only published `vX.Y.Z` releases count; no release yet is not an error. No other command
  checks for updates.
- `vectra update --apply --yes`: reinstalls at the latest release with the installer that owns
  the install (uv tool, pipx or the private venv), never by running `install.sh`. Without
  `--yes` it exits 2 (`INTERFACE_002_CONFIRMATION_REQUIRED`); editable, Windows or undetectable
  installs are refused with the manual command. Config and indexes are untouched; run
  `vectra collections check` afterwards.
- Error codes `UPDATES_001_INVALID_VERSION`, `UPDATES_101_INSTALLER_NOT_DETECTED`,
  `UPDATES_102_NO_RELEASE_PUBLISHED`, `UPDATES_201_RELEASE_SOURCE_UNAVAILABLE` and
  `UPDATES_202_UPGRADE_FAILED`, each with `next_steps`.
- `updates` bounded context with its own import-linter contracts.
- Documentation `docs/commands/update.md`; agent guide and skill trigger phrases.

### Fixed

- `vectra config init` writes every setting commented out at its default again, as documented;
  the template had them active, with an unexpanded `~` in `VECTRA_DATA_DIR`.

## [0.3.0] - 2026-11-12

### Added

- `vectra collections check [NAME]`: reports whether each collection was built with the
  configured embedding model and dimension; exit 1 when any is out of sync. Loads no model.
- `vectra collections check --fix --yes`: drops and re-embeds out-of-sync collections from their
  stored root; collections whose root is gone are skipped and reported.
- `vectra sync NAME` accepts an omitted `ROOT` for an existing collection (defaults to its own
  root).
- `--verbose` / `-v` on `sync` and `collections check --fix`: progress on stderr, stdout stays
  parseable.
- `vectra config init [--force]`: writes a commented env file template
  (`CONFIGURATION_101_ENV_FILE_EXISTS` when one exists).
- Configuration bounded context with its own import-linter contracts.
- Agent guide covers `collections check`, `--fix`, the `ROOT` default, `--verbose` and the
  steps for changing the embedding model.

### Changed

- `rich` is now a declared dependency.

## [0.2.0] - 2026-11-11

### Added

- Python chunker: `.py` files are indexed with `--include "**/*.py"`, one chunk per function,
  class and method.
- `install.sh`: installs the CLI with `uv`, `pipx` or a private virtual environment, and
  uninstalls it; `VECTRA_SOURCE`, `VECTRA_REF` and `VECTRA_INSTALLER` select the source and
  installer.
- Usage errors are reported as the JSON envelope (`INTERFACE_004_USAGE_ERROR`) when `--json` is
  given.
- Discovery stub `skills/vectra/SKILL.md` and one documentation page per command.
- Install guide, including installing the agent skill with `npx skills`.

### Changed

- Sync logic moved out of the handler into collaborating services (no behavior change).
- Documentation corrected for exit codes and error-code prefixes.

### Fixed

- `--json` leaves stderr empty: embedding SDK output is silenced.

## [0.1.0] - 2026-11-10

### Added

- `vectra sync NAME ROOT`: incremental indexing of a folder into a collection, with `--include`,
  `--exclude`, `--dry-run`, `--allow-mass-delete` and `--rebuild` / `--new-root`.
- `vectra search NAME "QUERY"`: semantic search, one hit per document, with `--top-k`,
  `--path-prefix` and `--min-score`.
- `vectra collections list` and `vectra collections drop NAME --yes`.
- `vectra config show` and `vectra skills list | get`.
- Markdown chunking, local sentence-transformers embeddings, LanceDB storage.
- Collections bound to one source root and one embedding profile;
  `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` when the configured model differs.
- JSON output envelope with error codes and `next_steps`; exit codes 0, 1 and 2.
- Per-file retries during sync (`VECTRA_SYNC_MAX_RETRIES`).

### Fixed

- `--rebuild` drops the collection only when requested and keeps its root unless `--new-root`
  is given.
- `--dry-run` warns about a mass delete instead of refusing it.

[Unreleased]: https://github.com/p-hzamora/vectra/compare/v0.4.4...HEAD
[0.4.4]: https://github.com/p-hzamora/vectra/compare/v0.3.0...v0.4.4
[0.3.0]: https://github.com/p-hzamora/vectra/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/p-hzamora/vectra/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/p-hzamora/vectra/releases/tag/v0.1.0
