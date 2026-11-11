# vectra

Chunk files, embed them into a vector store, and serve semantic search to agents and tools
(for example noesis) through one CLI.

Status: working CLI. `sync`, `search`, `collections`, `config` and `skills` are implemented
(Markdown chunking, local embeddings, LanceDB storage).

## Develop

```bash
make init          # uv sync
make run ARGS="--help"
make check         # lint, format, mypy --strict, import contracts, tests with coverage
```

Every command accepts `--json` and `--help`. `--json` goes after the subcommand; `--env-file`
is a global flag and goes before it (`vectra --env-file x.env search demo "q" --json`).
Exit codes: 0 ok, 1 the operation failed (including domain validation), 2 command-line usage
errors and `INTERFACE_*` errors.

## Docs

- [docs/](docs/README.md): what vectra does, architecture, one page per command, error codes.
- [skills/vectra/SKILL.md](skills/vectra/SKILL.md): discovery stub for agents; the command
  reference they load is `skill_guides/vectra.md` (`vectra skills get vectra`).
