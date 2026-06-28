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
    memory_db_path: str = "./memory.sqlite3"

    # LLM
    llm_provider: Literal["fake", "anthropic"] = "fake"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Embeddings / vector index
    embedder: Literal["hash", "anthropic", "openai"] = "hash"
    embedding_dim: int = 256
    vector_backend: Literal["memory", "fake_pinecone"] = "memory"
    reranker: Literal["fake", "none"] = "fake"
    enable_query_rewrite: bool = True
    enable_rag_safety: bool = True

    # Agent limits
    agent_token_budget: int = Field(default=8000, ge=100)
    agent_enable_memory: bool = True

    # Mock partner APIs
    mock_api_base_url: str = "http://127.0.0.1:9000"

    # Connector credentials (default to the mock API's accepted values)
    pulseads_token: str = "pulse-demo-token"
    novareach_api_key: str = "nova-demo-key"
    creativebox_user: str = "creativebox"
    creativebox_password: str = "creativebox-secret"

    # Agent
    agent_max_steps: int = Field(default=8, ge=1, le=50)

    # Online eval sampling (0.0 = disabled)
    online_eval_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # API authentication (disabled when unset)
    api_key: str | None = None

    # AWS / LocalStack
    aws_endpoint_url: str | None = "http://127.0.0.1:4566"
    aws_region: str = "us-east-1"
    s3_creatives_bucket: str = "aih-creatives"
    sqs_approvals_queue: str = "aih-approvals"

    # Observability / OpenTelemetry (disabled by default to stay offline-first).
    # When enabled, in-process run spans are exported to an OTLP collector
    # (e.g. Jaeger). Requires the optional ``otel`` extra to be installed; if the
    # packages are missing the exporter degrades to a silent no-op.
    otel_enabled: bool = False
    otel_service_name: str = "aih"
    otel_endpoint: str = "http://127.0.0.1:4317"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def validate_settings(settings: Settings | None = None) -> list[str]:
    """Return configuration warnings (empty when healthy)."""
    s = settings or get_settings()
    warnings: list[str] = []
    if s.llm_provider == "anthropic" and not s.anthropic_api_key:
        warnings.append("AIH_LLM_PROVIDER=anthropic but AIH_ANTHROPIC_API_KEY is unset")
    if s.agent_token_budget < 500:
        warnings.append("AIH_AGENT_TOKEN_BUDGET is very low; agent may stop early")
    if not s.mock_api_base_url.startswith("http"):
        warnings.append("AIH_MOCK_API_BASE_URL should be an http(s) URL")
    return warnings
