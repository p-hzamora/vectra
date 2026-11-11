# `vectra sync NAME ROOT`

Purpose: make collection `NAME` match the files under `ROOT`. The collection is created on the
first sync and bound to that root. Re-running is safe: only new, changed and removed files are
processed.

```bash
vectra sync notes ~/docs/notes --json
```

Defaults: `--include "**/*.md"`; Python files are indexed only when asked for, e.g.
`--include "**/*.py"` (this replaces the default, so add `--include "**/*.md"` to keep both). Hidden folders and symbolic links are skipped. A `.md` file at
the top of ROOT matches. Names: lowercase letters, digits, `-`, `_`; 1 to 63 characters, starting
with a letter or digit.

## Options

| Option | Effect |
|---|---|
| `--include GLOB` | Glob of files to index; repeatable. Replaces the default. |
| `--exclude GLOB` | Glob of files to skip; repeatable. |
| `--dry-run` | Report the plan; write nothing, load no model. |
| `--allow-mass-delete` | Allow deleting more than half of the indexed documents. |
| `--rebuild` | Drop the collection and recreate it with the current model, then index everything. Keeps its root. |
| `--new-root` | With `--rebuild`, rebind the collection to this ROOT. Without `--rebuild`: exit 2. |
| `--json` | JSON envelope. |

## How it runs

1. Scan ROOT, hash every matching file (SHA-256 of its bytes).
2. Check the collection: same root, same model and dimension (skipped on `--rebuild`).
3. Plan: add, update (hash or chunker version changed), delete (gone from disk), unchanged.
4. Refuse if more than half of the indexed documents would be deleted (unless
   `--allow-mass-delete`; on `--dry-run` it becomes a warning instead).
5. For each added or updated file: chunk, embed, store. A failing file is retried
   `VECTRA_SYNC_MAX_RETRIES` times (default 2) with growing backoff (0.5 s, 1 s, ...), then
   reported in `failed` while the rest continues. Deleted files are removed the same way.
6. Exit 1 if any file failed, else 0.

## Output

First sync, dry run:

```json
{
  "ok": true,
  "result": {
    "collection": "demo",
    "dry_run": true,
    "created": true,
    "added": ["cats.md", "espresso.md", "sub/rust.md"],
    "updated": [],
    "deleted": [],
    "unchanged": 0,
    "failed": [],
    "warnings": [],
    "chunks_written": 0
  }
}
```

First real sync: same, with `"dry_run": false` and `"chunks_written": 3`. Running it again:

```json
{
  "ok": true,
  "result": {
    "collection": "demo", "dry_run": false, "created": false,
    "added": [], "updated": [], "deleted": [], "unchanged": 3,
    "failed": [], "warnings": [], "chunks_written": 0
  }
}
```

After editing `sub/rust.md` and deleting `espresso.md`:
`"updated": ["sub/rust.md"]`, `"deleted": ["espresso.md"]`, `"unchanged": 1`,
`"chunks_written": 1`.

`warnings` carries non-fatal notes, for example `"<path>: malformed frontmatter ignored (no
metadata for this document)"`. Text output (no `--json`):

```text
collection demo
  add 0, update 0, delete 0, unchanged 2
  chunks written: 0
```

## Failure cases

A file with an extension no chunker handles (only `.md`, `.markdown` and `.py` are supported) is
reported per file, with `attempts` 0, and the exit code is 1:

```json
"failed": [
  {
    "path": "todo.txt",
    "code": "RETRIEVAL_204_CHUNKING_FAILED",
    "message": "No chunker handles 'todo.txt'.",
    "attempts": 0
  }
]
```

| Situation | Code | Exit |
|---|---|---|
| ROOT is not a folder | `RETRIEVAL_102_SOURCE_ROOT_INVALID` | 1 |
| Collection is bound to another root | `RETRIEVAL_102_SOURCE_ROOT_INVALID` | 1 |
| Configured model or dimension differs from the collection's | `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` | 1 |
| More than half of the documents would be deleted | `RETRIEVAL_103_MASS_DELETE_REFUSED` | 1 |
| Invalid collection name | `RETRIEVAL_001_INVALID_COLLECTION_NAME` | 1 |
| `--new-root` without `--rebuild` | `INTERFACE_003_NEW_ROOT_REQUIRES_REBUILD` | 2 |

Mass delete is how a wrong or emptied root shows up. Example, syncing with
`--include "**/*.txt"` into a collection of 2 Markdown files:

```json
{
  "ok": false,
  "error": {
    "code": "RETRIEVAL_103_MASS_DELETE_REFUSED",
    "title": "Mass delete refused",
    "message": "This sync would delete 2 of 2 indexed documents.",
    "metadata": {"collection": "demo", "to_delete": 2, "indexed": 2},
    "next_steps": [
      "Check that the source folder is the right and complete one.",
      "Repeat with --allow-mass-delete if the deletions are intended."
    ]
  }
}
```

With `--dry-run` the same plan returns `ok: true` and a warning: `"The real sync would be refused
(3 of 3 indexed documents would be deleted) without --allow-mass-delete."`

To change the model: set `VECTRA_EMBEDDING_MODEL_ID` and `VECTRA_EMBEDDING_DIMENSION`, then run
`vectra sync NAME ROOT --rebuild`. To move a collection to another folder, add `--new-root`.

Performance: the model loads once per process (see [../README.md](../README.md)); a dry run does
not load it. Index large folders only on purpose, and try `--dry-run` first.
