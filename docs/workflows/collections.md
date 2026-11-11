# `vectra collections list | drop`

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
