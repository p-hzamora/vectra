# Workflows per command

What each `vectra` command does, its options, real output, and how it fails. Read
[../architecture.md](../architecture.md) first for the layers.

Common to every command:

- `--json` goes after the subcommand and prints the envelope; without it you get text.
  Success: `{"ok": true, "result": {...}}` on stdout. Failure: `{"ok": false, "error": {...}}`
  on stdout with `--json`, or a text block on stderr without it.
- `--env-file <path>` is global and goes before the subcommand. See
  [config-and-skills.md](config-and-skills.md).
- Exit codes: 0 ok, 1 the operation failed (including domain validation), 2 command-line usage
  errors and `INTERFACE_*` errors. See [errors.md](errors.md).
- Command-line mistakes caught by Typer itself (missing argument, unknown option) give the
  envelope with `INTERFACE_004_USAGE_ERROR` when `--json` is present, Typer's usage text
  otherwise; the exit code is 2.
- Examples use a throwaway folder `/tmp/vectra-demo/notes` with `cats.md`, `espresso.md` and
  `sub/rust.md`, and the default model `BAAI/bge-small-en-v1.5`.

Index:

1. [`sync NAME ROOT`](sync.md)
2. [`search NAME QUERY`](search.md)
3. [`collections list | drop`](collections.md)
4. [`config show`, `skills list | get`, settings](config-and-skills.md)
5. [Error codes and exit codes](errors.md)
