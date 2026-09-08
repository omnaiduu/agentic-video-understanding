from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data"
_TWO_GIB = 2 * 1024 * 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://video:video@localhost:5432/video"
    data_dir: Path = _DEFAULT_DATA_DIR
    max_upload_bytes: int = Field(default=_TWO_GIB, ge=1)
    brain: str = "fake"
    vllm_base_url: str = ""
    vllm_api_key: str = "EMPTY"
    vllm_model: str = "google/gemma-4-E4B-it"
    ingest: str = "fake"
    embedder: str = "fake"
    whisper_model: str = "turbo"
    embed_model: str = "intfloat/e5-small-v2"
    ingest_secret: str = ""
    public_base_url: str = ""
    modal_ingest_app: str = "agentic-video-ingest"


@lru_cache
def get_settings() -> Settings:
    return Settings()
