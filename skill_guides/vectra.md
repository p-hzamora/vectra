# vectra: guide for agents

vectra chunks files, embeds the chunks into a vector store, and answers semantic searches.
This guide matches the installed vectra version. Use `vectra <command> --help` for anything
not covered here.

## Rules

- Always add `--json`. Parse the envelope: `{"ok": true, "result": ...}` or
  `{"ok": false, "error": {"code", "message", "next_steps"}}`. Branch on `error.code`.
- Exit codes: 0 ok, 1 the operation failed, 2 invalid command line.
- Retrieval error codes start with `RETRIEVAL_`; `next_steps` says how to recover.
- Never guess commands or flags. If something is not in this guide, run `--help`.

## Commands

- `vectra sync <name> <root> --json`: index the changes of a folder into collection `<name>`
  (created on first use and bound to that root; another root fails with
  `RETRIEVAL_102_SOURCE_ROOT_INVALID`). Only `**/*.md` by default; repeat `--include` /
  `--exclude` globs to change that. Hidden folders and symlinks are skipped. Re-running is safe:
  unchanged files are not touched. Options:
  - `--dry-run`: report what would be added/updated/deleted and write nothing.
  - `--rebuild`: drop the collection and recreate it with the current embedding model and this
    root, then index everything (the way out of `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` or a root
    change). With `--dry-run` nothing is dropped.
  - `--allow-mass-delete`: needed when more than half of the indexed documents disappeared
    (`RETRIEVAL_103_MASS_DELETE_REFUSED` otherwise; check the root first). With `--dry-run` it is
    not refused: the plan is returned with a `result.warnings` entry saying the real sync would be.
  - A file that keeps failing is retried `VECTRA_SYNC_MAX_RETRIES` times (default 2), then listed in
    `result.failed` (`path`, `code`, `message`, `attempts`) while the rest continues; the exit code
    is 1 if any file failed. `result.warnings` carries non-fatal notes such as ignored malformed
    frontmatter.
- `vectra search <name> "<query>" --json`: semantic search, one hit per document, best first
  (`path`, `score` 0..1, `heading_path`, `snippet`, `chunk_id`). Options: `--top-k` (default 5),
  `--path-prefix <dir/>`, `--min-score`. Fails with `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` if the
  configured embedding model differs from the one the collection was built with.
- `vectra collections list --json`: collections with model, dimension, source root and counts.
- `vectra collections drop <name> --yes --json`: delete a collection and its index (without `--yes`
  it exits 2 and deletes nothing).
- `vectra config show --json`: the configuration file read and the data folder.
- `vectra skills list --json` / `vectra skills get <name> --json`: the guides this version ships.

## Settings

`VECTRA_EMBEDDING_MODEL_ID` (default `BAAI/bge-small-en-v1.5`), `VECTRA_EMBEDDING_DIMENSION`
(default 384), `VECTRA_SYNC_MAX_RETRIES` (default 2, at least 0) and `VECTRA_DATA_DIR`. The first
embedding downloads the model. A collection keeps the model and dimension it was created with.
