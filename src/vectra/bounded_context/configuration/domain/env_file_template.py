"""The text of a fresh env file."""

ENV_FILE_TEMPLATE: str = """\
# vectra configuration. Never commit a real .env.
# Environment variables with the same names override values in this file.
# Uncomment a line to change it; the values shown are the defaults.

# Where vectra keeps its data, including the vector index.
# VECTRA_DATA_DIR=~/.local/share/vectra

# Embedding model (a collection keeps the model and dimension it was created with).
# Any sentence-transformers model works; browse them at
# https://huggingface.co/models?library=sentence-transformers
# Set the dimension to the one the chosen model outputs.
# VECTRA_EMBEDDING_MODEL_ID=BAAI/bge-small-en-v1.5
# VECTRA_EMBEDDING_DIMENSION=384

# Extra attempts per file during `vectra sync` (minimum 0).
# VECTRA_SYNC_MAX_RETRIES=2
"""
