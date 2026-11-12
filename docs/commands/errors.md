# Error codes and exit codes

Exit codes (`exceptions/exit_code_enum.py`): `0` ok, `1` the operation failed (including domain
validation such as `RETRIEVAL_001` or `RETRIEVAL_004`), `2` command-line usage errors and
`INTERFACE_*` errors only.

Every deliberate error has a stable `code`, a `title`, a `message`, `metadata` and `next_steps`.
With `--json` the envelope goes to stdout:

```json
{"ok": false, "error": {"code": "...", "title": "...", "message": "...", "metadata": {}, "next_steps": []}}
```

Without `--json` a text block goes to stderr:

```text
error [RETRIEVAL_101_COLLECTION_NOT_FOUND]: No collection named 'demo'.
  collection: demo
  next: Run `vectra collections list`, or `vectra sync` to create it.
```

Branch on `code`, not on the message. Code groups: `CORE_` configuration,
`INTERFACE_` bad input at the CLI, `RETRIEVAL_0xx` domain rules, `RETRIEVAL_1xx` use cases,
`RETRIEVAL_2xx` external systems. Sources: `exceptions/*.py`.

## Catalogue

| Code | Exit | Meaning | Raised by |
|---|---|---|---|
| `CORE_001_INVALID_CONFIGURATION` | 1 | A setting in the env file or environment is invalid; `metadata.problems` lists them. | Any command that loads settings |
| `CONFIGURATION_101_ENV_FILE_EXISTS` | 1 | `config init` found a file at the target; pass `--force` to overwrite. | `config init` |
| `INTERFACE_001_SKILL_GUIDE_NOT_FOUND` | 2 | `skills get` named a guide this version does not ship. | `skills get` |
| `INTERFACE_002_CONFIRMATION_REQUIRED` | 2 | `collections drop` without `--yes`. | `collections drop` |
| `INTERFACE_003_NEW_ROOT_REQUIRES_REBUILD` | 2 | `--new-root` without `--rebuild`. | `sync` |
| `INTERFACE_004_USAGE_ERROR` | 2 | Missing argument, unknown option or bad option value; `message` is Typer's. | any command |
| `RETRIEVAL_001_INVALID_COLLECTION_NAME` | 1 | Name is not lowercase letters, digits, `-`, `_` (1 to 63 characters, first one a letter or digit). | `sync`, `search`, `collections drop` |
| `RETRIEVAL_002_INVALID_SOURCE_PATH` | 1 | A document path is not relative, POSIX-style and free of `..`. | `sync` |
| `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` | 1 | Configured model or dimension differs from the collection's. Fix: restore the setting, or `sync --rebuild`. | `sync`, `search` |
| `RETRIEVAL_004_INVALID_SEARCH_QUERY` | 1 | Empty text, `--top-k` outside 1..100, bad `--path-prefix`, `--min-score` outside 0..1. | `search` |
| `RETRIEVAL_005_EMBEDDING_DIMENSION_MISMATCH` | 1 | An embedding is empty or its length differs from the configured dimension (for example `VECTRA_EMBEDDING_DIMENSION` does not match the model). | `sync` |
| `RETRIEVAL_006_INVALID_VALUE` | 1 | A hash, chunk id or model id is malformed. | internal checks |
| `RETRIEVAL_101_COLLECTION_NOT_FOUND` | 1 | No collection with that name. | `search`, `collections drop` |
| `RETRIEVAL_102_SOURCE_ROOT_INVALID` | 1 | ROOT is not a folder, is relative, or differs from the collection's root. | `sync` |
| `RETRIEVAL_103_MASS_DELETE_REFUSED` | 1 | The sync would delete more than half of the indexed documents. Fix: check ROOT, then `--allow-mass-delete`. | `sync` |
| `RETRIEVAL_201_VECTOR_STORE_UNAVAILABLE` | 1 | LanceDB failed to read or write. | all retrieval commands |
| `RETRIEVAL_202_EMBEDDER_UNAVAILABLE` | 1 | The model could not be loaded or failed to embed. | `sync`, `search` |
| `RETRIEVAL_203_DOCUMENT_UNREADABLE` | 1 | A file could not be read or decoded as UTF-8. | `sync` (per file) |
| `RETRIEVAL_204_CHUNKING_FAILED` | 1 | No chunker handles the file extension. | `sync` (per file) |

Also, `RETRIEVAL_000_UNEXPECTED` appears only in a sync's `failed` list, for a file that failed
with an exception that is not a vectra error (`retry_runner.py`).

## Per-file failures in `sync`

`RETRIEVAL_2xx` codes for one file do not stop the sync. They appear in `result.failed` as
`{path, code, message, attempts}`, and the command exits 1 when the list is not empty. A file
with an unsupported extension has `attempts` 0 (it is never tried).

## Usage errors

Mistakes Typer catches (missing argument, unknown option, bad option value) are reported as
`INTERFACE_004_USAGE_ERROR` in the envelope on stdout when `--json` is anywhere on the command
line; `message` is Typer's own message. Without `--json` Typer's usage text goes to stderr. Both
exit 2.
