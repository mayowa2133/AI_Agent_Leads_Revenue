"""Scheduled job runner for permit scrapers using APScheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.listeners.base_listener import BaseRegulatoryListener
from src.signal_engine.scrapers.base_scraper import BaseScraper
from src.signal_engine.scrapers.permit_scraper import (
    MecklenburgPermitScraper,
    SanAntonioFireScraper,
)
from src.signal_engine.storage.lead_storage import LeadStorage

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Manages scheduled execution of permit scrapers.
    
    Uses APScheduler to run scrapers on a configurable schedule.
    Stores last run timestamps in a simple JSON file for persistence.
    """

    def __init__(
        self,
        *,
        job_store: str = "memory",  # "memory" or "sqlite" for persistence
        timezone_str: str = "UTC",
    ):
        """
        Initialize the scheduler.
        
        Args:
            job_store: Storage backend ("memory" for MVP, "sqlite" for persistence)
            timezone_str: Timezone for scheduling (default UTC)
        """
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": {"type": "memory"}} if job_store == "memory" else None,
            timezone=timezone_str,
        )
        self.last_run_file = Path("data/scraper_last_runs.json")
        self.last_run_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = get_settings()
        self.lead_storage = LeadStorage()

    async def run_regulatory_listener_job(
        self,
        listener_name: str,
        listener: BaseRegulatoryListener,
        tenant_id: str,
    ) -> None:
        """
        Execute a single regulatory listener job.
        
        Args:
            listener_name: Human-readable name for logging
            listener: Listener instance to run
            tenant_id: Tenant identifier for multi-tenancy
        """
        logger.info(f"Starting regulatory listener job: {listener_name} (tenant: {tenant_id})")
        start_time = datetime.now(tz=timezone.utc)

        try:
            # Get last run time (if available)
            last_run = self._get_last_run(listener_name, tenant_id)
            
            # Run listener
            updates = await listener.check_for_updates(last_run)
            logger.info(
                f"Listener {listener_name} found {len(updates)} new regulatory updates since {last_run or 'beginning'}"
            )

            # TODO: Store updates in storage layer
            # For now, just log the results
            if updates:
                logger.info(f"Sample update titles: {[u.title[:50] for u in updates[:5]]}")

            # Update last run timestamp
            self._save_last_run(listener_name, tenant_id, start_time)

            logger.info(f"Completed listener job: {listener_name} in {datetime.now(tz=timezone.utc) - start_time}")

        except Exception as e:
            logger.error(f"Error running listener {listener_name}: {e}", exc_info=True)
            # Don't update last_run on error - will retry from same point

    async def run_scraper_job(
        self,
        scraper_name: str,
        scraper: BaseScraper,
        tenant_id: str,
    ) -> None:
        """
        Execute a single scraper job.
        
        Args:
            scraper_name: Human-readable name for logging
            scraper: Scraper instance to run
            tenant_id: Tenant identifier for multi-tenancy
        """
        logger.info(f"Starting scraper job: {scraper_name} (tenant: {tenant_id})")
        start_time = datetime.now(tz=timezone.utc)

        try:
            # Get last run time (if available)
            last_run = self._get_last_run(scraper_name, tenant_id)
            
            # Run scraper
            if last_run:
                permits = await scraper.check_for_updates(last_run)
                logger.info(
                    f"Scraper {scraper_name} found {len(permits)} new/updated permits since {last_run}"
                )
            else:
                permits = await scraper.scrape()
                logger.info(f"Scraper {scraper_name} extracted {len(permits)} permits (full scrape)")

            # Enrich permits if enabled (with quality filtering and credit safety)
            enriched_leads = []
            if permits and self.settings.enable_enrichment:
                # Step 1: Quality filtering (filter low-quality permits before enrichment)
                from src.signal_engine.quality.quality_filter import QualityFilter
                
                quality_filter = QualityFilter(
                    threshold=0.3,  # Lower threshold for real-world data (0.3 instead of 0.5)
                    validate_addresses=False,  # Fast sync filtering
                )
                
                quality_permits, filtered_permits, filter_stats = (
                    quality_filter.filter_permits_sync(permits)
                )
                
                logger.info(
                    f"Quality filter: {filter_stats['passed']}/{filter_stats['total']} permits passed "
                    f"({filter_stats['passed']/filter_stats['total']*100:.1f}%)"
                )
                logger.info(
                    f"Score distribution: {filter_stats['score_distribution']}"
                )
                
                if not quality_permits:
                    logger.warning(
                        "No permits passed quality filter - skipping enrichment"
                    )
                else:
                    # Step 2: Apply credit limit to quality permits
                    max_permits = self.settings.max_credits_per_run
                    permits_to_enrich = quality_permits[:max_permits]
                    
                    if len(quality_permits) > max_permits:
                        logger.warning(
                            f"Credit safety: Only enriching first {max_permits} of {len(quality_permits)} "
                            f"quality permits (max_credits_per_run={max_permits}). "
                            f"Remaining permits will be processed in subsequent runs."
                        )
                    else:
                        logger.info(
                            f"Enriching {len(permits_to_enrich)} quality permits "
                            f"(filtered from {len(permits)} total permits)..."
                        )
                    
                    enriched_leads = await self._enrich_permits(permits_to_enrich, tenant_id)
                
                # Store enriched leads
                if enriched_leads:
                    self.lead_storage.save_leads(enriched_leads)
                    logger.info(
                        f"Enriched and stored {len(enriched_leads)} leads from {len(permits)} permits"
                    )
                else:
                    logger.warning("No leads were enriched (enrichment may have failed)")
            elif permits:
                logger.info(f"Enrichment disabled - skipping enrichment for {len(permits)} permits")

            # Log results
            if permits:
                logger.info(f"Sample permit IDs: {[p.permit_id for p in permits[:5]]}")

            # Update last run timestamp
            self._save_last_run(scraper_name, tenant_id, start_time)

            logger.info(f"Completed scraper job: {scraper_name} in {datetime.now(tz=timezone.utc) - start_time}")

        except Exception as e:
            logger.error(f"Error running scraper {scraper_name}: {e}", exc_info=True)
            # Don't update last_run on error - will retry from same point

    async def run_api_job(
        self,
        source_name: str,
        source: PermitSource,
        tenant_id: str,
        *,
        days_back: int = 30,
        limit: int = 1000,
        enrich: bool = True,
    ) -> None:
        """
        Execute a single API ingestion job.

        Args:
            source_name: Human-readable name for logging
            source: PermitSource configuration
            tenant_id: Tenant identifier
            days_back: Number of days to look back
            limit: Maximum permits to fetch
        """
        logger.info(f"Starting API ingestion job: {source_name} (tenant: {tenant_id})")
        start_time = datetime.now(tz=timezone.utc)

        try:
            ingestion = UnifiedPermitIngestion()
            permits = await ingestion.ingest_permits(
                source, days_back=days_back, limit=limit
            )
            logger.info(
                f"API source {source_name} fetched {len(permits)} permits"
            )

            # Enrich permits if enabled (reuse same pipeline)
            enriched_leads = []
            if permits and self.settings.enable_enrichment and enrich:
                from src.signal_engine.quality.quality_filter import QualityFilter

                quality_filter = QualityFilter(
                    threshold=0.3,
                    validate_addresses=False,
                )

                quality_permits, _, filter_stats = (
                    quality_filter.filter_permits_sync(permits)
                )
                logger.info(
                    f"Quality filter: {filter_stats['passed']}/{filter_stats['total']} permits passed "
                    f"({filter_stats['passed']/filter_stats['total']*100:.1f}%)"
                )

                if quality_permits:
                    max_permits = self.settings.max_credits_per_run
                    permits_to_enrich = quality_permits[:max_permits]
                    enriched_leads = await self._enrich_permits(
                        permits_to_enrich, tenant_id
                    )

                if enriched_leads:
                    self.lead_storage.save_leads(enriched_leads)
                    logger.info(
                        f"Enriched and stored {len(enriched_leads)} leads from {len(permits)} permits"
                    )
                else:
                    logger.warning("No leads were enriched (enrichment may have failed)")
            elif permits and not enrich:
                logger.info(
                    f"Enrichment disabled for API job {source_name} - skipping enrichment for {len(permits)} permits"
                )

            if permits:
                logger.info(f"Sample permit IDs: {[p.permit_id for p in permits[:5]]}")

            self._save_last_run(source_name, tenant_id, start_time)
            logger.info(
                f"Completed API ingestion job: {source_name} in "
                f"{datetime.now(tz=timezone.utc) - start_time}"
            )
        except Exception as e:
            logger.error(f"Error running API ingestion {source_name}: {e}", exc_info=True)

    async def _enrich_permits(
        self, permits: list, tenant_id: str
    ) -> list:
        """
        Enrich a list of permits into leads.

        Args:
            permits: List of PermitData objects
            tenant_id: Tenant identifier

        Returns:
            List of EnrichedLead objects
        """
        from src.signal_engine.models import PermitData

        enriched_leads = []
        for permit in permits:
            try:
                if not isinstance(permit, PermitData):
                    logger.warning(f"Skipping invalid permit: {type(permit)}")
                    continue

                lead = await enrich_permit_to_lead(
                    EnrichmentInputs(tenant_id=tenant_id, permit=permit)
                )
                enriched_leads.append(lead)
            except Exception as e:
                logger.error(
                    f"Error enriching permit {permit.permit_id if hasattr(permit, 'permit_id') else 'unknown'}: {e}",
                    exc_info=True,
                )
                # Continue with other permits even if one fails

        return enriched_leads

    def _get_last_run(self, scraper_name: str, tenant_id: str) -> datetime | None:
        """Get the last run timestamp for a scraper."""
        import json

        if not self.last_run_file.exists():
            return None

        try:
            data = json.loads(self.last_run_file.read_text())
            key = f"{scraper_name}:{tenant_id}"
            if key in data:
                return datetime.fromisoformat(data[key])
        except Exception as e:
            logger.warning(f"Error reading last run file: {e}")
        
        return None

    def _save_last_run(self, scraper_name: str, tenant_id: str, timestamp: datetime) -> None:
        """Save the last run timestamp for a scraper."""
        import json

        try:
            if self.last_run_file.exists():
                data = json.loads(self.last_run_file.read_text())
            else:
                data = {}
            
            key = f"{scraper_name}:{tenant_id}"
            data[key] = timestamp.isoformat()
            
            self.last_run_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Error saving last run file: {e}")

    def add_regulatory_listener_job(
        self,
        listener_name: str,
        listener: BaseRegulatoryListener,
        tenant_id: str,
        *,
        schedule_type: str = "interval",  # "interval" or "cron"
        hours: int = 24,  # For interval: run every N hours
        cron_expr: str | None = None,  # For cron: e.g., "0 2 * * *" (daily at 2 AM)
    ) -> None:
        """
        Add a regulatory listener to the schedule.
        
        Args:
            listener_name: Human-readable name
            listener: Listener instance
            tenant_id: Tenant identifier
            schedule_type: "interval" or "cron"
            hours: Hours between runs (for interval)
            cron_expr: Cron expression (for cron schedule)
        """
        if schedule_type == "interval":
            trigger = IntervalTrigger(hours=hours)
        elif schedule_type == "cron":
            if cron_expr is None:
                raise ValueError("cron_expr required for cron schedule")
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            raise ValueError(f"Unknown schedule_type: {schedule_type}")

        self.scheduler.add_job(
            self.run_regulatory_listener_job,
            trigger=trigger,
            args=[listener_name, listener, tenant_id],
            id=f"regulatory_{listener_name}:{tenant_id}",
            replace_existing=True,
        )
        logger.info(
            f"Added regulatory listener job: {listener_name} (tenant: {tenant_id}, schedule: {schedule_type})"
        )

    def add_scraper_job(
        self,
        scraper_name: str,
        scraper: BaseScraper,
        tenant_id: str,
        *,
        schedule_type: str = "interval",  # "interval" or "cron"
        hours: int = 24,  # For interval: run every N hours
        cron_expr: str | None = None,  # For cron: e.g., "0 2 * * *" (daily at 2 AM)
    ) -> None:
        """
        Add a scraper to the schedule.
        
        Args:
            scraper_name: Human-readable name
            scraper: Scraper instance
            tenant_id: Tenant identifier
            schedule_type: "interval" or "cron"
            hours: Hours between runs (for interval)
            cron_expr: Cron expression (for cron schedule)
        """
        if schedule_type == "interval":
            trigger = IntervalTrigger(hours=hours)
        elif schedule_type == "cron":
            if cron_expr is None:
                raise ValueError("cron_expr required for cron schedule")
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            raise ValueError(f"Unknown schedule_type: {schedule_type}")

        self.scheduler.add_job(
            self.run_scraper_job,
            trigger=trigger,
            args=[scraper_name, scraper, tenant_id],
            id=f"{scraper_name}:{tenant_id}",
            replace_existing=True,
        )
        logger.info(
            f"Added scraper job: {scraper_name} (tenant: {tenant_id}, schedule: {schedule_type})"
        )

    def add_api_job(
        self,
        source_name: str,
        source: PermitSource,
        tenant_id: str,
        *,
        schedule_type: str = "interval",
        hours: int = 24,
        cron_expr: str | None = None,
        run_date: datetime | None = None,
        days_back: int = 30,
        limit: int = 1000,
        enrich: bool = True,
    ) -> None:
        """
        Add an API ingestion job to the schedule.
        """
        if schedule_type == "interval":
            trigger = IntervalTrigger(hours=hours)
        elif schedule_type == "cron":
            if cron_expr is None:
                raise ValueError("cron_expr required for cron schedule")
            trigger = CronTrigger.from_crontab(cron_expr)
        elif schedule_type == "date":
            if run_date is None:
                raise ValueError("run_date required for date schedule")
            trigger = DateTrigger(run_date=run_date)
        else:
            raise ValueError(f"Unknown schedule_type: {schedule_type}")

        self.scheduler.add_job(
            self.run_api_job,
            trigger=trigger,
            args=[source_name, source, tenant_id],
            kwargs={"days_back": days_back, "limit": limit, "enrich": enrich},
            id=f"{source_name}:{tenant_id}",
            replace_existing=True,
        )
        logger.info(
            f"Added API ingestion job: {source_name} (tenant: {tenant_id}, schedule: {schedule_type})"
        )

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scraper scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown()
        logger.info("Scraper scheduler shut down")


async def run_scheduled_scrapers() -> None:
    """
    Main entry point for running scheduled scrapers.
    
    Configures and starts scrapers based on environment settings.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings = get_settings()
    scheduler = ScraperScheduler()

    # Configure scrapers for each tenant
    for tenant_id in settings.tenant_list():
        # Mecklenburg County scraper
        # Use address search to avoid database overload
        mecklenburg_scraper = MecklenburgPermitScraper(
            search_type="address",
            search_value="Tryon",  # Default search - can be overridden via env
            street_number="600",
        )
        scheduler.add_scraper_job(
            "mecklenburg_county",
            mecklenburg_scraper,
            tenant_id,
            schedule_type="interval",
            hours=24,  # Daily
        )

        # San Antonio Fire scraper
        san_antonio_scraper = SanAntonioFireScraper(
            record_type="Fire Alarm",
            days_back=30,
        )
        scheduler.add_scraper_job(
            "san_antonio_fire",
            san_antonio_scraper,
            tenant_id,
            schedule_type="interval",
            hours=12,  # Twice daily
        )

        # San Antonio Building Permits (CKAN Open Data)
        san_antonio_ckan_source = PermitSource(
            source_type=PermitSourceType.CKAN_API,
            city="San Antonio",
            source_id="san_antonio_building_permits_ckan",
            config={
                "portal_url": "https://data.sanantonio.gov",
                # Current, actively updated dataset
                "resource_id": "c21106f9-3ef5-4f3a-8604-f992b4db7512",
                "field_mapping": {
                    "permit_id": "PERMIT #",
                    "permit_type": "PERMIT TYPE",
                    "address": "ADDRESS",
                    "status": "PERMIT TYPE",
                    "applicant_name": "PRIMARY CONTACT",
                    "issued_date": "DATE ISSUED",
                },
            },
        )
        scheduler.add_api_job(
            "san_antonio_building_ckan_daily",
            san_antonio_ckan_source,
            tenant_id,
            schedule_type="interval",
            hours=24,
            days_back=30,  # Current daily permits
            limit=1000,
            enrich=True,
        )

        # San Antonio Building Permits backfill (2020-2024) - one-time job
        san_antonio_ckan_backfill_source = PermitSource(
            source_type=PermitSourceType.CKAN_API,
            city="San Antonio",
            source_id="san_antonio_building_permits_ckan_backfill",
            config={
                "portal_url": "https://data.sanantonio.gov",
                "resource_id": "c22b1ef2-dcf8-4d77-be1a-ee3638092aab",
                "field_mapping": {
                    "permit_id": "PERMIT #",
                    "permit_type": "PERMIT TYPE",
                    "address": "ADDRESS",
                    "status": "PERMIT TYPE",
                    "applicant_name": "PRIMARY CONTACT",
                    "issued_date": "DATE ISSUED",
                },
            },
        )
        scheduler.add_api_job(
            "san_antonio_building_ckan_backfill",
            san_antonio_ckan_backfill_source,
            tenant_id,
            schedule_type="date",
            run_date=datetime.now(tz=timezone.utc) + timedelta(seconds=10),
            days_back=3650,  # Historical range
            limit=5000,
            enrich=True,
        )

        # Regulatory listeners
        from src.signal_engine.listeners.epa_listener import EPARegulatoryListener
        from src.signal_engine.listeners.fire_marshal_listener import FireMarshalListener
        from src.signal_engine.listeners.nfpa_listener import NFPAListener

        # EPA listener (weekly - Federal Register updates less frequently)
        epa_listener = EPARegulatoryListener()
        scheduler.add_regulatory_listener_job(
            "epa_regulatory",
            epa_listener,
            tenant_id,
            schedule_type="interval",
            hours=168,  # Weekly
        )

        # NFPA listener (weekly - code amendments are infrequent)
        nfpa_listener = NFPAListener()
        scheduler.add_regulatory_listener_job(
            "nfpa",
            nfpa_listener,
            tenant_id,
            schedule_type="interval",
            hours=168,  # Weekly
        )

        # State fire marshal listeners (daily for RSS feeds)
        # Configure from environment if RSS feeds are provided
        for feed_url in settings.regulatory_feed_list():
            # Extract state name from URL or use generic name
            state_name = feed_url.split("/")[-2] if "/" in feed_url else "Unknown"
            fire_marshal_listener = FireMarshalListener(feed_url=feed_url, state=state_name)
            scheduler.add_regulatory_listener_job(
                f"fire_marshal_{state_name.lower().replace(' ', '_')}",
                fire_marshal_listener,
                tenant_id,
                schedule_type="interval",
                hours=24,  # Daily
            )

    # Start scheduler
    scheduler.start()

    # Keep running until interrupted
    try:
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(run_scheduled_scrapers())

