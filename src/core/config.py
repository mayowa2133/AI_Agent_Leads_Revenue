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

    # Regulatory listener settings
    regulatory_rss_feeds: str = ""  # Comma-separated RSS feed URLs
    regulatory_update_frequency_hours: int = 24
    regulatory_llm_enabled: bool = True  # Use LLM for content processing

    # Enrichment pipeline settings
    enable_enrichment: bool = True  # Master switch for enrichment
    geocoding_provider: str = "nominatim"  # Geocoding service choice
    apollo_api_key: str | None = None  # Apollo API key (free tier: 110 credits/month)
    hunter_api_key: str | None = None  # Hunter.io API key (free tier: 50 credits/month)
    clearbit_api_key: str | None = None  # Clearbit API key (optional)
    enrichment_provider_priority: str = "auto"  # "hunter", "apollo", or "auto"
    enrichment_dry_run: bool = True  # Dry-run mode (default: True for safety)
    max_credits_per_run: int = 3  # Maximum Hunter credits per run (safety limit)
    max_apollo_credits_per_run: int = 10  # Maximum Apollo credits per run (free tier: 110/month)
    enrichment_cache_enabled: bool = True  # Enable geocoding/company caching

    def tenant_list(self) -> list[str]:
        return [t.strip() for t in self.tenants.split(",") if t.strip()]

    def regulatory_feed_list(self) -> list[str]:
        """Parse comma-separated RSS feed URLs."""
        return [f.strip() for f in self.regulatory_rss_feeds.split(",") if f.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


