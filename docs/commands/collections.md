# `vectra collections list | check | drop`

## `collections list`

Purpose: show every collection with its model, size and source root, sorted by name.

```bash
vectra collections list --json
```

```json
{
  "ok": true,
  "result": {
    "collections": [
      {
        "name": "demo",
        "model_id": "BAAI/bge-small-en-v1.5",
        "dimension": 384,
        "source_root": "/private/tmp/vectra-demo/notes",
        "created_at": "2026-11-11T06:46:04.234710Z",
        "document_count": 3,
        "chunk_count": 3
      }
    ]
  }
}
```

`source_root` is the resolved absolute path (on macOS `/tmp` resolves to `/private/tmp`). With
none, the result is `"collections": []` and the text output is `no collections`. The command
does not load the model.

## `collections drop NAME --yes`

Purpose: delete a collection with all its chunks and its manifest. It cannot be undone, so
`--yes` is required.

```bash
vectra collections drop demo --yes --json
```

```json
{"ok": true, "result": {"name": "demo", "documents": 2, "chunks": 2}}
```

Text output: `dropped demo (2 documents, 2 chunks)`. Source files are never touched.

### Failure cases

| Situation | Code | Exit |
|---|---|---|
| Missing `--yes` (nothing is deleted) | `INTERFACE_002_CONFIRMATION_REQUIRED` | 2 |
| No collection with that name | `RETRIEVAL_101_COLLECTION_NOT_FOUND` | 1 |
| Invalid collection name | `RETRIEVAL_001_INVALID_COLLECTION_NAME` | 1 |

```json
{
  "ok": false,
  "error": {
    "code": "INTERFACE_002_CONFIRMATION_REQUIRED",
    "title": "Confirmation required",
    "message": "Dropping 'demo' deletes its index and cannot be undone.",
    "metadata": {"collection": "demo"},
    "next_steps": ["Run `vectra collections drop demo --yes`."]
  }
}
```

## `collections check [NAME]`

Purpose: verify that collections were built with the embedding model the settings ask for.
Without `NAME` it checks every collection. `search` runs the same check and fails with
`RETRIEVAL_003_INDEX_PROFILE_MISMATCH` when the model differs. The command does not load the
model. Exit 1 when any collection is out of sync.

```bash
vectra collections check --json
```

```json
{
  "ok": true,
  "result": {
    "in_sync": false,
    "collections": [
      {
        "name": "demo",
        "model_id": "BAAI/bge-small-en-v1.5",
        "dimension": 384,
        "configured_model_id": "other/model",
        "configured_dimension": 768,
        "in_sync": false
      }
    ]
  }
}
```

Fix a mismatch by setting the model back, or rebuild with `--fix --yes`. An unknown `NAME` fails
with `RETRIEVAL_101_COLLECTION_NOT_FOUND`.

### `--fix --yes`

Drops and re-embeds every out-of-sync collection (or just `NAME`) from its own stored root, with
the default include globs. Collections already in sync are untouched. A collection whose root no
longer exists is skipped and left as it was; the output lists it under `skipped` and the exit
code is 1. `--yes` is required (`INTERFACE_002_CONFIRMATION_REQUIRED`, exit 2).

```bash
vectra collections check --fix --yes --json
```

```json
{"ok": true, "result": {"repaired": [{"collection": "demo", "created": true, "added": ["a.md"]}], "skipped": []}}
```

(`repaired` items are full sync results; trimmed here.)

Add `--verbose` (`-v`) to see progress on stderr while it rebuilds: which collection is being
rebuilt and why, then each file as it is embedded. stdout is unchanged.
