from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    env: str = "dev"
    log_level: str = "INFO"
    tenants: str = "demo"  # comma-separated

    # OpenAI / LangSmith
    openai_api_key: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str = "aoro"
    langsmith_tracing: bool = True

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4jpassword"

    # Pinecone
    pinecone_api_key: str | None = None
    pinecone_environment: str | None = None
    pinecone_index: str = "aoro-case-studies"

    # Database (optional)
    database_url: str | None = None

    # ServiceTitan (tenant-specific in prod; single-tenant convenience in dev)
    servicetitan_client_id: str | None = None
    servicetitan_client_secret: str | None = None
    servicetitan_app_key: str | None = None
    servicetitan_base_url: str | None = None
    servicetitan_tenant_id: str | None = None

    def tenant_list(self) -> list[str]:
        return [t.strip() for t in self.tenants.split(",") if t.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


