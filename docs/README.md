# vectra docs

vectra is a command-line tool that cuts Markdown files into chunks, turns each chunk into a
vector with a local embedding model, stores the vectors in a local LanceDB database, and
answers natural-language searches over them. Everything runs on your machine. Every command
can print a JSON envelope (`--json`), so agents and scripts can use it as a retrieval backend.

- [install.md](install.md): the install script, manual installs, the agent skill, uninstalling.
- [architecture.md](architecture.md): layers, the `retrieval` context, ports and adapters,
  chunk ids, incremental sync, scores, import contracts.
- [commands/](commands/README.md): one page per command group, with real output.
  - [sync](commands/sync.md), [search](commands/search.md),
    [collections](commands/collections.md), [config and skills](commands/config-and-skills.md)
  - [errors](commands/errors.md): every error code and exit code.

The agent-facing command reference is `skill_guides/vectra.md` (served by
`vectra skills get vectra`); the discovery stub is `skills/vectra/SKILL.md`. These docs do not
repeat it.

## Performance

- The embedding model loads once per process, so every `search` pays it: about 4.7 s in total,
  of which about 2.8 s is importing torch. The LanceDB search itself takes about 0.01 s.
- When the model is already in the Hugging Face cache, vectra sets `HF_HUB_OFFLINE=1` for the
  process (unless you set it) and makes no network call. Only the first use downloads it.
- `--help`, `--dry-run`, `config`, `skills` and `collections` never load the model.
