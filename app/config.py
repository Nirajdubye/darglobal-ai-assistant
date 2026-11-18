"""Central configuration. Every value can be overridden with an environment variable."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FREE_ROUTER_MODEL = "openrouter/free"


def is_free_model(model: str) -> bool:
    """Only OpenRouter's free router or explicit ':free' variants are allowed."""
    model = model.strip()
    return model == FREE_ROUTER_MODEL or model.endswith(":free")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    # --- OpenRouter -------------------------------------------------------
    openrouter_api_key: str = Field(default="", repr=False)
    openrouter_model: str = FREE_ROUTER_MODEL
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.1
    llm_max_tokens: int = 700

    # --- Paths ------------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"

    # --- Ingestion --------------------------------------------------------
    chunk_size: int = 900          # characters
    chunk_overlap: int = 150       # characters
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    collection_name: str = "real_estate"

    # --- Retrieval --------------------------------------------------------
    top_k: int = 6
    min_similarity: float = 0.30   # below this, we answer "not in my data" without calling the LLM
    history_turns: int = 4

    # --- Scraping ---------------------------------------------------------
    request_delay_seconds: float = 2.0
    request_timeout_seconds: float = 20.0
    user_agent: str = "DarGlobalAssignmentBot/1.0 (educational research; respects robots.txt)"

    # --- API / UI ---------------------------------------------------------
    api_url: str = "http://localhost:8000"
    admin_token: str = Field(default="", repr=False)
    max_question_chars: int = 1000

    @field_validator("openrouter_model")
    @classmethod
    def _only_free_models(cls, v: str) -> str:
        if not is_free_model(v):
            raise ValueError(
                f"OPENROUTER_MODEL='{v}' is not a free model. Use 'openrouter/free' or a model id ending in ':free'."
            )
        return v.strip()

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def html_dir(self) -> Path:
        return self.raw_dir / "html"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma_db"

    @property
    def documents_path(self) -> Path:
        return self.processed_dir / "documents.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
