"""Central configuration, read from environment variables (or ai/.env).

pydantic-settings maps env vars to fields case-insensitively, e.g. LLM_MODEL -> llm_model.
Every external dependency (LLM, storage, models) is configurable so the same code runs
on a laptop, in docker-compose and in Kubernetes.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

AI_ROOT = Path(__file__).resolve().parent.parent  # .../ai


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (Ollama's OpenAI-compatible endpoint by default) ---
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"  # Ollama ignores it; hosted providers need a real key
    llm_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.3
    llm_timeout_seconds: int = 180  # CPU inference of a 7B model is slow

    # --- RAG ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_dir: str = str(AI_ROOT / "data" / "chroma")
    chunk_size: int = 500
    chunk_overlap: int = 80

    # --- ASR ---
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- object storage (MinIO locally, AWS S3 in the cloud) ---
    s3_endpoint_url: str | None = "http://localhost:9000"  # set empty for real AWS S3
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "mockai"
    s3_region: str = "us-east-1"
    storage_enabled: bool = True

    # --- trained models ---
    models_dir: str = str(AI_ROOT / "models")

    # --- service-to-service auth (API -> AI). Empty = disabled (local dev). ---
    internal_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
