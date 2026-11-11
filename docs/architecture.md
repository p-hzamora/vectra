# Architecture

vectra follows tactical DDD with a hexagonal (ports and adapters) layout. All paths below are
relative to `src/vectra/`.

```text
core/            settings and env loading (env.py is the only entry; configurations/ holds the classes)
exceptions/      AppException tree, error codes, exit codes
shared_kernel/   IHandler, JsonValue types
utils/           FrozenObject (immutable pydantic base)
bounded_context/
  retrieval/     the only context
    domain/          entities, value objects, policies, write repository ports
    application/     handlers, DTOs, services, ports (chunking, embedding, source, uow, read_repositories)
    infrastructure/outbound/   adapters: vector_store, embedding, chunking, source
interfaces/cli/  Typer app, commands, responses, output.py, bootstrap.py (the composition root)
```

`interfaces/cli/bootstrap.py` is the only place that picks concrete adapters
(`build_retrieval`). Commands call handlers through it.

## Layers and contracts

Contracts are import-linter rules in `pyproject.toml` (`make imports`):

- Nothing in `bounded_context`, `core`, `exceptions`, `shared_kernel` or `utils` imports
  `interfaces`.
- `interfaces` reads configuration only through `vectra.core.env` (not `core.configurations`
  or `pydantic_settings`).
- `bounded_context` and `shared_kernel` import no `typer`, no `pydantic_settings`, no `vectra.core`.
- Retrieval layers point inward: infrastructure -> application -> domain.
- Retrieval domain and application import no `lancedb`, `pyarrow`, `sentence_transformers`,
  `torch`, `transformers`, `yaml`, `typer`, nor infrastructure.
- Only `outbound/vector_store` imports `lancedb` and `pyarrow`; only `outbound/embedding`
  imports `sentence_transformers`, `torch` and `transformers`; only `outbound/chunking`
  imports `yaml`.
- The four adapter packages (`vector_store`, `embedding`, `chunking`, `source`) are independent
  of each other.
- `interfaces` reaches retrieval domain and infrastructure only through `bootstrap`.

## Retrieval ports and adapters

| Port | File (under `bounded_context/retrieval/`) | Adapter |
|---|---|---|
| `IDocumentSource` | `application/ports/source/i_document_source.py` | `FilesystemDocumentSourceAdapter` (`infrastructure/outbound/source/`) |
| `IChunker` | `application/ports/chunking/i_chunker.py` | `MarkdownChunkerAdapter`, `PythonChunkerAdapter` (`.../chunking/`) |
| `IEmbedder` | `application/ports/embedding/i_embedder.py` | `SentenceTransformersEmbedderAdapter` (`.../embedding/`) |
| `IRetrievalUnitOfWork` | `application/ports/uow/i_retrieval_unit_of_work.py` | `LanceDbRetrievalUnitOfWorkAdapter` (`.../vector_store/`) |
| `ICollectionRepository` | `domain/repositories/i_collection_repository.py` | `LanceDbCollectionRepositoryAdapter` |
| `IIndexedDocumentRepository` | `domain/repositories/i_indexed_document_repository.py` | `LanceDbIndexedDocumentRepositoryAdapter` |
| `ICollectionReadRepository` | `application/ports/read_repositories/i_collection_read_repository.py` | `LanceDbCollectionReadRepositoryAdapter` |
| `IManifestReadRepository` | `application/ports/read_repositories/i_manifest_read_repository.py` | `LanceDbManifestReadRepositoryAdapter` |
| `IChunkSearchReadRepository` | `application/ports/read_repositories/i_chunk_search_read_repository.py` | `LanceDbChunkSearchReadRepositoryAdapter` |

Writes go through the aggregates `Collection` and `IndexedDocument` (`domain/entities/`) and the
unit of work; reads (CQRS query side) use the read repositories. The LanceDB store sits behind
these ports: `vector_store/lancedb_store.py` (`LanceDbStore`) owns the connection, table names
and schemas, and turns foreign failures into `VectorStoreError`.

- Filesystem source: walks the root in sorted order, skips hidden folders and symbolic links,
  matches `--include` / `--exclude` globs against the relative POSIX path, and hashes each
  matching file with SHA-256.
- Markdown chunker (`chunker_version` `markdown-1`, extensions `.md` and `.markdown`): YAML
  frontmatter becomes chunk metadata (malformed frontmatter is dropped with a warning); the
  body is split by headings (headings inside code fences are text); a section over 400 tokens
  (4 characters per token) is cut at paragraph boundaries, without overlap.
- Python chunker (`chunker_version` `python-1`, extension `.py`): parses with stdlib `ast`; one
  chunk per top-level function, class and method, with the heading path (module, class, method)
  and the source text including decorators and docstring. A class chunk holds its header,
  docstring and class-level statements; the module docstring, imports and top-level statements
  form one `module` chunk. A unit over 400 tokens (4 characters per token) is cut at line
  boundaries, without overlap. Source that does not parse (`SyntaxError`) does not fail: it is
  split at blank lines under the same cap and a warning is returned.
- Embedder: loads the model on the first call, encodes in a thread with normalized vectors.
  Models whose id contains `bge` get the prefix `Represent this sentence for searching relevant
  passages: ` on queries only.
- Storage: a LanceDB database under `<VECTRA_DATA_DIR>/index` with tables `collections`,
  `manifest` and one `chunks_<collection>` table per collection.
- A `ChunkerResolver` (`application/services/`) maps a file extension to a chunker; an unknown
  extension is a `RETRIEVAL_204_CHUNKING_FAILED` for that file. Both chunkers are wired in
  `bootstrap.py`; `.py` files are only indexed when `--include` selects them.

## Chunk ids

`domain/policies/stable_chunk_id_policy.py`:

```text
chunk_id = sha256("<collection>|<path>|<heading path>|<sha256(text)[:16]>")
```

The second and later chunks with the same heading path and text of one document get `|<n>`
appended before hashing (n = 1, 2, ...). So editing one section does not change the ids of the
others, and adding a duplicate never renames an existing chunk.

## Incremental sync

`SyncPlanningPolicy` (`domain/policies/sync_planning_policy.py`) compares the scanned files with
the manifest. A document is stale when its content hash (SHA-256 of the file bytes) or its
chunker version differs. Result groups: `add` (not indexed), `update` (stale), `delete` (indexed,
no longer on disk), `unchanged`. `SyncCollectionHandler` then indexes each added or updated
document (chunk, embed, store) and removes each deleted one. Each document is its own unit of
work, so one failing file does not stop the rest. The store has no cross-table transaction:
the manifest entry is written last, so a crash leaves the document stale and the next sync
repairs it. See [commands/sync.md](commands/sync.md).

## Score semantics

Search is a cosine nearest-neighbour query. A chunk's score is `1 - cosine distance`, clamped to
0..1; higher is better (`lancedb_chunk_search_read_repository_adapter.py`). The handler fetches
`top_k * 4` chunks, applies `--min-score`, keeps the best chunk of each document, sorts by score
(ties by path), and returns the first `top_k` with a snippet of at most 300 characters
(`application/services/document_hit_grouper.py`). Scores depend on the model; compare them only
within one collection and model.

## Collections

A collection (`domain/entities/collection.py`) has a name, an immutable embedding profile
(model id and dimension), the source root it was created for, and a creation time. A later sync
must use the same root and the same profile, otherwise it fails; `--rebuild` drops and recreates
the collection with the current profile.

## Output and errors

`interfaces/cli/output.py` prints either text or the envelope `{"ok": true, "result": ...}` /
`{"ok": false, "error": {code, title, message, metadata, next_steps}}`. Deliberate errors are
`AppException`s with a stable `__error_code__` and an exit code. The catalogue is in
[commands/errors.md](commands/errors.md).
