# vectra

Chunk files, embed them into a vector store, and serve semantic search to agents and tools
(for example noesis) through one CLI.

Status: skeleton. The interface layer, configuration and tooling are in place; the domain
(chunking, embedding, storage, search) is still to be designed.

## Develop

```bash
make init          # uv sync
make run ARGS="--help"
make check         # lint, format, mypy --strict, import contracts, tests with coverage
```

Every command accepts `--json` and `--help`. Exit codes: 0 ok, 1 the operation failed,
2 invalid command line.
