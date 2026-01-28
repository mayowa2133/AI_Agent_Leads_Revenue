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
    apollo_enabled: bool = False  # Enable Apollo usage (default off for production)
    apollo_api_key: str | None = None  # Apollo API key (free tier: 110 credits/month)
    hunter_api_key: str | None = None  # Hunter.io API key (free tier: 50 credits/month)
    clearbit_api_key: str | None = None  # Clearbit API key (optional)
    opencorporates_api_key: str | None = None  # OpenCorporates API key (optional)
    enrichment_provider_priority: str = "auto"  # "hunter", "apollo", or "auto"
    enrichment_dry_run: bool = True  # Dry-run mode (default: True for safety)
    max_credits_per_run: int = 3  # Maximum Hunter credits per run (safety limit)
    max_apollo_credits_per_run: int = 10  # Maximum Apollo credits per run (free tier: 110/month)
    enrichment_cache_enabled: bool = True  # Enable geocoding/company caching
    enrichment_persist_cache: bool = True  # Persist enrichment cache across runs
    enrichment_cache_path: str = "data/enrichment_cache.json"  # Cache file path
    enrichment_blocked_email_domains: str = ""  # Comma-separated domains to reject
    enrichment_blocked_email_tlds: str = "edu,gov,org"  # Comma-separated TLDs to reject
    enrichment_allowed_email_tlds_no_domain: str = "com,net,biz"  # Allowed TLDs when domain unknown

    # Phase 2: Agentic Workflow settings
    email_provider: str = "smtp"  # "sendgrid", "ses", or "smtp"
    sendgrid_api_key: str | None = None  # SendGrid API key
    aws_ses_region: str | None = None  # AWS SES region (e.g., "us-east-1")
    smtp_host: str = "localhost"  # SMTP server host
    smtp_port: int = 587  # SMTP server port
    smtp_user: str | None = None  # SMTP username
    smtp_password: str | None = None  # SMTP password
    email_from_address: str = "noreply@aoro.ai"  # Default sender email
    email_from_name: str = "AORO"  # Default sender name
    email_send_dry_run: bool = True  # Do not send real emails when True
    workflow_persistence_enabled: bool = True  # Enable workflow state persistence

    # Phase 2.3: Free CRM export (CSV)
    crm_export_enabled: bool = True  # Enable CSV export for booking payloads
    crm_export_csv_path: str = "data/booking_exports.csv"  # CSV output path
    crm_export_dedupe_enabled: bool = True  # Skip duplicate booking export rows
    crm_provider: str = "csv"  # "csv" (default) or "airtable"
    airtable_api_key: str | None = None
    airtable_base_id: str | None = None
    airtable_table_name: str = "Bookings"
    
    # Phase 2.2: Response Handling settings
    response_timeout_days: int = 7  # Days to wait for response before follow-up
    
    # Phase 2.3: Follow-ups & Objection Management settings
    max_followup_attempts: int = 2  # Maximum number of follow-up attempts
    max_objection_handling_cycles: int = 3  # Maximum objection handling cycles before giving up
    
    # Phase 1.4: Permit Discovery Expansion settings
    google_custom_search_api_key: str | None = None  # Google Custom Search API key
    google_custom_search_engine_id: str | None = None  # Google Custom Search Engine ID

    def tenant_list(self) -> list[str]:
        return [t.strip() for t in self.tenants.split(",") if t.strip()]

    def regulatory_feed_list(self) -> list[str]:
        """Parse comma-separated RSS feed URLs."""
        return [f.strip() for f in self.regulatory_rss_feeds.split(",") if f.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


