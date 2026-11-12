# vectra

Chunk files, embed them into a vector store, and serve semantic search to agents and tools
(for example noesis) through one CLI.

Status: working CLI. `sync`, `search`, `collections`, `config`, `skills` and `update` are implemented
(Markdown chunking, local embeddings, LanceDB storage).

## Install

```bash
curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | sh
vectra config show                          # the env file read and the data folder
vectra update                               # is there a newer release? ([docs](docs/commands/update.md))
```

The installer uses `uv` if you have it, otherwise `pipx`, otherwise a private virtual
environment built with Python 3.14+. From a checkout, `./install.sh` installs that checkout.
Options, manual installs and uninstalling: [docs/install.md](docs/install.md).

### Install the agent skill

The skill teaches coding agents (Claude Code, Codex, Cursor, ...) how to use the CLI. It needs
the `vectra` command installed first (above). Install it with the
[`skills`](https://github.com/vercel-labs/skills) CLI, which only needs Node (`npx`):

```bash
npx skills add p-hzamora/vectra --skill vectra -g   # every project, for your user
npx skills add p-hzamora/vectra --skill vectra      # this project only
npx skills add ./path/to/vectra --skill vectra -g   # from a local checkout
```

It asks which agents to install for. More options (manual copy for Claude Code, other agents):
[docs/install.md](docs/install.md).

## Develop

```bash
make init          # uv sync
make run ARGS="--help"
make check         # lint, format, mypy --strict, import contracts, tests with coverage
```

Record every user-visible change under `Unreleased` in [CHANGELOG.md](CHANGELOG.md); the file
explains how to cut a release.

Every command accepts `--json` and `--help`; command groups (`config`, `collections`, `skills`)
take `--json` on their subcommands (`vectra collections list --json`), not on the group. `--json`
goes after the subcommand; `--env-file`
is a global flag and goes before it (`vectra --env-file x.env search demo "q" --json`).
Exit codes: 0 ok, 1 the operation failed (including domain validation), 2 command-line usage
errors and `INTERFACE_*` errors.

## Docs

- [docs/](docs/README.md): what vectra does, architecture, one page per command, error codes.
- [skills/vectra/SKILL.md](skills/vectra/SKILL.md): discovery stub for agents; the command
  reference they load is `skill_guides/vectra.md` (`vectra skills get vectra`).
