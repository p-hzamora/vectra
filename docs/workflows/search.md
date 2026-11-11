# `vectra search NAME QUERY`

Purpose: semantic search in one collection. Returns one hit per document (its best chunk),
best first.

```bash
vectra search demo "how do I make coffee" --top-k 2 --json
```

## Options

| Option | Default | Effect |
|---|---|---|
| `--top-k N` | 5 | Documents to return; 1 to 100. |
| `--path-prefix P` | none | Only documents whose path starts with `P` (relative, no `..`, not starting with `/`). |
| `--min-score S` | none | Drop hits scoring below `S` (0 to 1). |
| `--json` | off | JSON envelope. |

## Output

```json
{
  "ok": true,
  "result": {
    "collection": "demo",
    "query": "how do I make coffee",
    "hits": [
      {
        "path": "espresso.md",
        "score": 0.6696174740791321,
        "heading_path": ["Espresso"],
        "snippet": "Espresso is brewed by forcing hot water through finely ground coffee at high pressure.",
        "chunk_id": "7ced23f735e1609c33c7000530e12e89ba1b10ba0a601beb3360a8d6350de91c"
      },
      {
        "path": "cats.md",
        "score": 0.4171818494796753,
        "heading_path": ["Cats", "Care"],
        "snippet": "Cats need fresh water, a clean litter box and regular vet visits.",
        "chunk_id": "8f6ea6f1f1b167513d996901b1af829e5657f80a590a9365f4bb2dfeda36675c"
      }
    ]
  }
}
```

- `score` is `1 - cosine distance`, clamped to 0..1, higher is better. It is only comparable
  within one collection and model.
- `snippet` is the chunk text cut to 300 characters (with `...` when cut).
- `heading_path` lists the headings above the chunk; it is empty for text before the first heading.
- No hits gives `"hits": []`.

Text output, `vectra search demo "memory safety" --path-prefix sub/`:

```text
sub/rust.md  0.696  [Rust > Ownership]
  Rust enforces memory safety through ownership and borrowing without a garbage collector.
```

With no hits the text is `no results`.

## How it runs

Check the collection exists and that the configured model matches it, embed the query, fetch
`top_k * 4` nearest chunks (filtered by `--path-prefix` before the search), apply `--min-score`,
keep the best chunk per document, and return the first `top_k`.

Performance: about 4.7 s per call, of which about 2.8 s is importing torch; the LanceDB search
is about 0.01 s. The model loads once per process and is read offline when cached.

## Failure cases

| Situation | Code | Exit |
|---|---|---|
| No collection with that name | `RETRIEVAL_101_COLLECTION_NOT_FOUND` | 1 |
| Configured model or dimension differs from the collection's | `RETRIEVAL_003_INDEX_PROFILE_MISMATCH` | 1 |
| Empty query, `--top-k` outside 1..100, bad `--path-prefix`, `--min-score` outside 0..1 | `RETRIEVAL_004_INVALID_SEARCH_QUERY` | 1 |
| Model cannot load (bad id, no network on first download) | `RETRIEVAL_202_EMBEDDER_UNAVAILABLE` | 1 |

```json
{
  "ok": false,
  "error": {
    "code": "RETRIEVAL_003_INDEX_PROFILE_MISMATCH",
    "title": "Embedding profile mismatch",
    "message": "Collection demo was built with BAAI/bge-small-en-v1.5:384, not BAAI/bge-small-en-v1.5:768.",
    "metadata": {"collection": "demo", "expected": "BAAI/bge-small-en-v1.5:384", "actual": "BAAI/bge-small-en-v1.5:768"},
    "next_steps": ["Set the embedding model back, or drop the collection and sync it again."]
  }
}
```
