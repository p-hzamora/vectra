"""How the retrieval context embeds and retries."""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from .base_settings import AppBaseSettings

DEFAULT_EMBEDDING_MODEL_ID: str = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIMENSION: int = 384
DEFAULT_SYNC_MAX_RETRIES: int = 2


class RetrievalSettings(AppBaseSettings):
    """Retrieval tuning.

    Attributes:
        embedding_model_id: Sentence-transformers model (`VECTRA_EMBEDDING_MODEL_ID`).
        embedding_dimension: Vector length of that model (`VECTRA_EMBEDDING_DIMENSION`).
        sync_max_retries: Extra attempts per file in a sync, at least 0 (`VECTRA_SYNC_MAX_RETRIES`).
    """

    model_config = SettingsConfigDict(env_prefix="VECTRA_")

    embedding_model_id: str = DEFAULT_EMBEDDING_MODEL_ID
    embedding_dimension: int = Field(default=DEFAULT_EMBEDDING_DIMENSION, gt=0)
    sync_max_retries: int = Field(default=DEFAULT_SYNC_MAX_RETRIES, ge=0)
