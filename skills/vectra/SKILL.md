---
name: vectra
description: Index folders of Markdown files into a local vector store and search them semantically with the `vectra` CLI.
when_to_use: Use when the user asks to index or sync a folder, search indexed notes or documents by meaning, list or drop collections, or check vectra's configuration.
argument-hint: "[sync <name> <root> | search <name> <query> | collections list|drop | config show]"
---

# vectra

This stub finds the CLI, finds the env file it will use, and loads the guide that matches the
installed version.

## 1. Resolve the CLI

Run `vectra --version`. If it fails with "command not found", tell the user vectra is not
installed (`uv tool install <path-to-the-vectra-repo>`) and stop. Do not try other
executables and do not guess commands.

## 2. Check which config applies

vectra reads one env file per invocation. It holds the data folder (`VECTRA_DATA_DIR`), the
embedding model and the sync retries. Environment variables with the same names override it.

1. By default the file is `$XDG_CONFIG_HOME/vectra/.env`, normally `~/.config/vectra/.env`.
   A missing file is fine: vectra then uses its defaults.
2. Pass `--env-file <path>` only when the user asks for a specific file. It is a global flag,
   so it goes before the subcommand: `vectra --env-file <path> search notes "query"`.
3. Run `vectra config show --json` to see the file read, whether it exists, and the data folder.

## 3. Load the version-matched guide before running any other vectra command

```text
vectra skills get vectra
```

Follow that guide. Prefer `--json`; use `vectra <command> --help` for anything it does not
cover. If `skills get` is unknown, the installed vectra is too old: say so and use `--help`
for read-only discovery only.

## Safety

Never sync a large folder (for example a whole notes vault) unless the user asks for it:
indexing embeds every file and can take a long time. Suggest `--dry-run` first; it lists what
would be added, updated and deleted and writes nothing.
