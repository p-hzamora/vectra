# `config show`, `skills`, and settings

## Choosing the env file

Every invocation reads one env file: `$XDG_CONFIG_HOME/vectra/.env`, normally
`~/.config/vectra/.env` (`core/configurations/paths.py`). A missing file is fine; defaults
apply. `--env-file PATH` replaces it. It is a global option, so it goes before the subcommand:

```bash
vectra --env-file ./work.env search notes "query" --json
```

Environment variables with the same names override values in the file. Unknown keys in the file
are ignored. There are no profiles and no sessions.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `VECTRA_DATA_DIR` | `$XDG_DATA_HOME/vectra`, normally `~/.local/share/vectra` | Data folder; the index lives in its `index/` subfolder. |
| `VECTRA_EMBEDDING_MODEL_ID` | `BAAI/bge-small-en-v1.5` | Sentence-transformers model. |
| `VECTRA_EMBEDDING_DIMENSION` | `384` | Vector length of that model; must be above 0. |
| `VECTRA_SYNC_MAX_RETRIES` | `2` | Extra attempts per file in a sync; at least 0. |

A collection keeps the model and dimension it was created with. The first use of a model
downloads it; after that it is read from the cache offline. An invalid value fails with
`CORE_001_INVALID_CONFIGURATION`, whose `metadata.problems` lists `VARIABLE: reason` lines.
`.env.example` in the repo root documents the same variables.

## `vectra config show`

Purpose: show which env file this invocation read and where data lives. Loads no model.

```json
{
  "ok": true,
  "result": {
    "env_file": "/tmp/vectra-demo/demo.env",
    "env_file_exists": true,
    "data_dir": "/tmp/vectra-demo/data"
  }
}
```

Text output:

```text
env file: /tmp/vectra-demo/demo.env
data dir: /tmp/vectra-demo/data
```

When the file is missing the text adds ` (missing: defaults only)` after the path.

## `vectra skills list | get NAME`

Purpose: serve the agent guides that ship with this vectra version, so an installed skill stub
can load the guide that matches the CLI (`vectra skills get vectra`). Guides live in
`skill_guides/` and are packaged with the wheel.

`vectra skills list --json`:

```json
{"ok": true, "result": {"guides": [{"name": "vectra", "title": "vectra: guide for agents", "content": ""}]}}
```

`vectra skills get vectra --json` returns the same fields with the whole Markdown in `content`;
without `--json` it prints the Markdown. An unknown name fails with
`INTERFACE_001_SKILL_GUIDE_NOT_FOUND` (exit 2); `metadata.available` lists the names.

## `vectra --version`

Prints `vectra <version>` (for example `vectra 0.1.0`).
