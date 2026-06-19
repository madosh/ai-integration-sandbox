"""Application configuration via pydantic-settings (12-factor env vars).

All settings have offline-safe defaults so the sandbox runs with zero real
credentials. Real adapters are opt-in via the relevant env vars.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration, sourced from env vars (prefix ``AIH_``)."""

    model_config = SettingsConfigDict(
        env_prefix="AIH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    env: Literal["local", "ci", "prod"] = "local"
    log_level: str = "INFO"
    run_ledger_path: str = "./run_ledger.sqlite3"

    # LLM
    llm_provider: Literal["fake", "anthropic"] = "fake"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Embeddings
    embedder: Literal["hash", "anthropic", "openai"] = "hash"
    embedding_dim: int = 256

    # Mock partner APIs
    mock_api_base_url: str = "http://127.0.0.1:9000"

    # Connector credentials (default to the mock API's accepted values)
    pulseads_token: str = "pulse-demo-token"
    novareach_api_key: str = "nova-demo-key"
    creativebox_user: str = "creativebox"
    creativebox_password: str = "creativebox-secret"

    # Agent
    agent_max_steps: int = Field(default=8, ge=1, le=50)

    # AWS / LocalStack
    aws_endpoint_url: str | None = "http://127.0.0.1:4566"
    aws_region: str = "us-east-1"
    s3_creatives_bucket: str = "aih-creatives"
    sqs_approvals_queue: str = "aih-approvals"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
