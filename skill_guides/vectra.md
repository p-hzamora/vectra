# vectra: guide for agents

vectra chunks files, embeds the chunks into a vector store, and answers semantic searches.
This guide matches the installed vectra version. Use `vectra <command> --help` for anything
not covered here.

## Rules

- Always add `--json`. Parse the envelope: `{"ok": true, "result": ...}` or
  `{"ok": false, "error": {"code", "message", "next_steps"}}`. Branch on `error.code`.
- Exit codes: 0 ok; 1 the operation failed, including domain validation
  (`RETRIEVAL_001_INVALID_COLLECTION_NAME`, `RETRIEVAL_004_INVALID_SEARCH_QUERY` for a bad
  `--top-k` / `--min-score`); 2 only for command-line usage errors and `INTERFACE_*` errors.
- Error codes start with `RETRIEVAL_` (indexing and search), `CORE_` (configuration, e.g.
  `CORE_001_INVALID_CONFIGURATION`) or `INTERFACE_` (command line: `INTERFACE_001`..`004`;
  `INTERFACE_004_USAGE_ERROR` is a missing argument, unknown option or bad value, and is an
  envelope when `--json` is present). `next_steps` says how to recover. Full list:
  `docs/commands/errors.md`.
- `--env-file <path>` is global: it goes before the subcommand; `--json` goes after it.
- Collection names: lowercase letters, digits, `-`, `_`; 1 to 63 characters; first one a letter or
  digit (otherwise `RETRIEVAL_001_INVALID_COLLECTION_NAME`).
- Never guess commands or flags. If something is not in this guide, run `--help`.

## Commands

- `vectra sync <name> [<root>] --json`: index the changes of a folder into collection `<name>`
  (created on first use and bound to that root; another root fails with
  `RETRIEVAL_102_SOURCE_ROOT_INVALID`). `<root>` may be omitted for an existing collection: it
  defaults to the collection's own root. Only `**/*.md` by default; repeat `--include` /
  `--exclude` globs to change that (`--include "**/*.py"` adds Python; it replaces the default). Hidden folders and symlinks are skipped. Re-running is safe:
  unchanged files are not touched. Options:
  - `--dry-run`: report what would be added/updated/deleted and write nothing.
  - `--rebuild`: drop the collection and recreate it with the current embedding model, then index
    everything (the way out of `RETRIEVAL_003_INDEX_PROFILE_MISMATCH`). It keeps the collection's
    root: another root fails with `RETRIEVAL_102_SOURCE_ROOT_INVALID` unless `--new-root` is given.
    With `--dry-run` nothing is dropped.
  - `--new-root`: with `--rebuild`, rebind the collection to this root. Without `--rebuild` it exits
    2 (`INTERFACE_003_NEW_ROOT_REQUIRES_REBUILD`).
  - `--verbose` / `-v`: progress on stderr; stdout stays parseable with `--json`.
  - `--allow-mass-delete`: needed when more than half of the indexed documents disappeared
    (`RETRIEVAL_103_MASS_DELETE_REFUSED` otherwise; check the root first). With `--dry-run` it is
    not refused: the plan is returned with a `result.warnings` entry saying the real sync would be.
  - A file that keeps failing is retried `VECTRA_SYNC_MAX_RETRIES` times (default 2), then listed in
    `result.failed` (`path`, `code`, `message`, `attempts`) while the rest continues; the exit code
    is 1 if any file failed. Per-file codes: `RETRIEVAL_203_DOCUMENT_UNREADABLE`,
    `RETRIEVAL_204_CHUNKING_FAILED`, `RETRIEVAL_000_UNEXPECTED` (a non-vectra exception). A file
    with an unsupported extension is listed as `RETRIEVAL_204_CHUNKING_FAILED` with `attempts` 0.
    Files are also reindexed when the chunker version changes. `result.warnings` carries non-fatal notes such as ignored malformed
    frontmatter or a Python file that does not parse (split at blank lines instead).
- `vectra search <name> "<query>" --json`: semantic search, one hit per document, best first
  (`path`, `score` 0..1, `heading_path`, `snippet`, `chunk_id`). Options: `--top-k` (default 5, range 1..100),
  `--path-prefix <dir/>`, `--min-score` (0..1). Out of range is
  `RETRIEVAL_004_INVALID_SEARCH_QUERY`. Fails with `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` if the
  configured embedding model differs from the one the collection was built with.
- `vectra collections list --json`: collections with model, dimension, source root and counts.
- `vectra collections check [<name>] --json`: read-only; compare each collection's model and
  dimension with the configured ones (`in_sync`, `configured_model_id`, `configured_dimension`).
  Loads no model. Exit 1 when any collection is out of sync. Run it after changing
  `VECTRA_EMBEDDING_MODEL_ID` or `VECTRA_EMBEDDING_DIMENSION`, and before searching if unsure.
  - `--fix --yes`: drop and re-embed every out-of-sync collection (or only `<name>`) from its
    stored root with the default include globs. In-sync collections are untouched. A collection
    whose root no longer exists is listed under `skipped` and left as it was (exit 1). Without
    `--yes` it exits 2 (`INTERFACE_002_CONFIRMATION_REQUIRED`). Custom `--include` globs are not
    kept: for those, use `sync <name> --rebuild --include ...` per collection.
  - `--verbose` / `-v`: progress on stderr.
- `vectra collections drop <name> --yes --json`: delete a collection and its index (without `--yes`
  it exits 2 and deletes nothing).
- `vectra config show --json`: the configuration file read and the data folder.
- `vectra config init --json`: write a commented env file template; fails with
  `CONFIGURATION_101_ENV_FILE_EXISTS` if one exists (`--force` overwrites; only when the user asks).
- `vectra skills list --json` / `vectra skills get <name> --json`: the guides this version ships.

## Chunks and `heading_path`

- Markdown (`.md`, `.markdown`): `heading_path` is the headings above the chunk.
- Python (`.py`, only via `--include`): one chunk per function, class and method; `heading_path`
  is `[module, Class, method]` or `[module, function]`; `[module]` is the module docstring,
  imports and top-level statements.

## What to index

Index curated folders (conventions, templates, examples), never whole repos: every file is
embedded and noise buries the useful hits. For the structure of a repo use graphify, not vectra.

## Standard collections

```bash
vectra sync conventions <path-to-conventions> --json
vectra sync tools <path-to-tools> --json
vectra sync <project> <path-to-project-docs> --include "**/*.md" --include "**/*.py" --json
```

One collection per project, named after it. Add `--dry-run` first on a new folder.

## Changing the embedding model

1. Set the new `VECTRA_EMBEDDING_MODEL_ID` and `VECTRA_EMBEDDING_DIMENSION` together.
2. `vectra collections check --json` to see which collections are out of sync.
3. One collection: `vectra sync <name> --rebuild --json` (add `--dry-run` first). All of them:
   `vectra collections check --fix --yes --json`.

`--rebuild`, `--fix` and `drop` delete the existing index and re-embed everything, which can be
slow. Source files are never touched. Ask the user before running any of them.

## Settings

`VECTRA_EMBEDDING_MODEL_ID` (default `BAAI/bge-small-en-v1.5`), `VECTRA_EMBEDDING_DIMENSION`
(default 384), `VECTRA_SYNC_MAX_RETRIES` (default 2, at least 0) and `VECTRA_DATA_DIR`. The first
embedding downloads the model. A collection keeps the model and dimension it was created with.
Other whole-command failures: `RETRIEVAL_005_EMBEDDING_DIMENSION_MISMATCH` (dimension setting
does not match the model), `RETRIEVAL_201_VECTOR_STORE_UNAVAILABLE`,
`RETRIEVAL_202_EMBEDDER_UNAVAILABLE`.
