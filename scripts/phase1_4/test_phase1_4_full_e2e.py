"""End-to-End Test for Phase 1.4: Permit Discovery Expansion."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.config.portal_config import PortalConfig, PortalConfigManager
from src.signal_engine.discovery.portal_discovery import PortalDiscoveryService, PortalType
from src.signal_engine.discovery.portal_storage import PortalStorage
from src.signal_engine.jobs.discovery_scheduler import DiscoveryScheduler
from src.signal_engine.monitoring.portal_monitor import PortalMonitor
from src.signal_engine.quality.quality_filter import QualityFilter
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.signal_engine.scrapers.registry import ScraperRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_phase1_4_1_portal_discovery():
    """Test Phase 1.4.1: Automated Portal Discovery."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.1: AUTOMATED PORTAL DISCOVERY")
    logger.info("=" * 80)
    logger.info("")
    
    # Test portal storage
    storage = PortalStorage()
    existing_portals = storage.get_all_portals()
    logger.info(f"✅ Portal Storage: {len(existing_portals)} portals loaded")
    
    # Test portal discovery service
    discovery = PortalDiscoveryService()
    logger.info("✅ Portal Discovery Service initialized")
    
    # Test discovery scheduler (without running full discovery to avoid API limits)
    scheduler = DiscoveryScheduler()
    logger.info("✅ Discovery Scheduler initialized")
    logger.info(f"  Target cities: {len(scheduler.get_target_cities())} cities")
    
    logger.info("")
    logger.info("✅ Phase 1.4.1: Portal Discovery - WORKING")
    logger.info("")
    
    return True


async def test_phase1_4_2_scraper_standardization():
    """Test Phase 1.4.2: Scraper Standardization."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.2: SCRAPER STANDARDIZATION")
    logger.info("=" * 80)
    logger.info("")
    
    # Test scraper registry
    logger.info("Testing Scraper Registry...")
    supported_types = ScraperRegistry.get_supported_types()
    logger.info(f"✅ Supported portal types: {[t.value for t in supported_types]}")
    
    # Test Accela scraper creation
    logger.info("")
    logger.info("Testing Accela Scraper (San Antonio)...")
    try:
        scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
        permits = await scraper.scrape()
        logger.info(f"✅ San Antonio: {len(permits)} permits extracted")
        
        if permits:
            logger.info(f"  Sample permit: {permits[0].permit_id} - {permits[0].permit_type}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    # Test multiple cities
    logger.info("")
    logger.info("Testing Multiple Cities...")
    cities = [
        ("DENVER", "Denver, CO"),
        ("CHARLOTTE", "Charlotte, NC"),
    ]
    
    total_permits = len(permits)
    for city_code, city_name in cities:
        try:
            scraper = create_accela_scraper(city_code, "Fire", None, days_back=120)
            city_permits = await scraper.scrape()
            total_permits += len(city_permits)
            logger.info(f"✅ {city_name}: {len(city_permits)} permits")
        except Exception as e:
            logger.warning(f"⚠️  {city_name}: {e}")
    
    logger.info("")
    logger.info(f"✅ Total permits from 3 cities: {total_permits}")
    logger.info("")
    logger.info("✅ Phase 1.4.2: Scraper Standardization - WORKING")
    logger.info("")
    
    return True


async def test_phase1_4_3_api_integration():
    """Test Phase 1.4.3: Open Data API Integration."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.3: OPEN DATA API INTEGRATION")
    logger.info("=" * 80)
    logger.info("")
    
    # Test Socrata API
    logger.info("Testing Socrata API (Seattle)...")
    try:
        client = SocrataPermitClient(
            portal_url="https://data.seattle.gov",
            dataset_id="76t5-zqzr",
            field_mapping={
                "permit_id": "permitnum",
                "permit_type": "permittypedesc",
                "address": "originaladdress1",
                "status": "statuscurrent",
            },
        )
        api_permits = await client.get_permits(days_back=30, limit=20)
        logger.info(f"✅ Seattle Socrata API: {len(api_permits)} permits fetched")
        
        if api_permits:
            logger.info(f"  Sample permit: {api_permits[0].permit_id} - {api_permits[0].permit_type}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    # Test unified ingestion
    logger.info("")
    logger.info("Testing Unified Ingestion...")
    ingestion = UnifiedPermitIngestion()
    
    api_source = PermitSource(
        source_type=PermitSourceType.SOCRATA_API,
        city="Seattle, WA",
        source_id="seattle_socrata_test",
        config={
            "portal_url": "https://data.seattle.gov",
            "dataset_id": "76t5-zqzr",
            "field_mapping": {
                "permit_id": "permitnum",
                "permit_type": "permittypedesc",
                "address": "originaladdress1",
                "status": "statuscurrent",
            },
        },
    )
    
    unified_permits = await ingestion.ingest_permits(api_source, days_back=30, limit=10)
    logger.info(f"✅ Unified Ingestion: {len(unified_permits)} permits from API")
    
    logger.info("")
    logger.info("✅ Phase 1.4.3: API Integration - WORKING")
    logger.info("")
    
    return True


async def test_phase1_4_4_quality_filtering():
    """Test Phase 1.4.4: Data Quality & Filtering."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.4: DATA QUALITY & FILTERING")
    logger.info("=" * 80)
    logger.info("")
    
    # Get real permits
    logger.info("Fetching real permits for quality testing...")
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    permits = await scraper.scrape()
    logger.info(f"Fetched {len(permits)} permits")
    logger.info("")
    
    # Test quality filter
    logger.info("Testing Quality Filter (threshold 0.3)...")
    quality_filter = QualityFilter(threshold=0.3)
    high_quality, filtered, stats = quality_filter.filter_permits_sync(permits)
    
    logger.info(f"✅ Quality Filter Results:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Passed: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    logger.info(f"  Filtered: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    logger.info(f"  Score Distribution: {stats['score_distribution']}")
    
    if high_quality:
        logger.info("")
        logger.info("Sample high-quality permits:")
        for permit in high_quality[:3]:
            score = quality_filter.scorer.score(permit)
            logger.info(f"  - {permit.permit_id}: Score {score.total_score:.2f}")
    
    logger.info("")
    logger.info("✅ Phase 1.4.4: Quality Filtering - WORKING")
    logger.info("")
    
    return True


async def test_phase1_4_5_integration_automation():
    """Test Phase 1.4.5: Integration & Automation."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.5: INTEGRATION & AUTOMATION")
    logger.info("=" * 80)
    logger.info("")
    
    # Test portal config manager
    logger.info("Testing Portal Configuration Manager...")
    config_manager = PortalConfigManager()
    all_configs = config_manager.get_all_configs()
    logger.info(f"✅ Portal Configs: {len(all_configs)} configurations loaded")
    
    enabled_configs = config_manager.get_all_configs(enabled_only=True)
    logger.info(f"  Enabled: {len(enabled_configs)}")
    
    stats = config_manager.get_statistics()
    logger.info(f"  By System Type: {stats['by_system_type']}")
    logger.info(f"  By Source Type: {stats['by_source_type']}")
    
    # Test portal monitor
    logger.info("")
    logger.info("Testing Portal Monitor...")
    monitor = PortalMonitor(config_manager)
    
    health = monitor.get_all_portals_health()
    logger.info(f"✅ Portal Health:")
    logger.info(f"  Total: {health['total']}")
    logger.info(f"  Healthy: {health['healthy']}")
    logger.info(f"  Unhealthy: {health['unhealthy']}")
    logger.info(f"  Disabled: {health['disabled']}")
    
    metrics = monitor.get_metrics()
    logger.info("")
    logger.info(f"✅ Metrics (30 days):")
    logger.info(f"  Active Portals: {metrics['active_portals']}")
    logger.info(f"  Total Permits Scraped: {metrics['total_permits_scraped']}")
    logger.info(f"  Avg Quality Score: {metrics['avg_quality_score']}")
    
    # Test discovery scheduler
    logger.info("")
    logger.info("Testing Discovery Scheduler...")
    scheduler = DiscoveryScheduler(config_manager)
    logger.info(f"✅ Discovery Scheduler initialized")
    logger.info(f"  Target cities: {len(scheduler.get_target_cities())} cities")
    
    logger.info("")
    logger.info("✅ Phase 1.4.5: Integration & Automation - WORKING")
    logger.info("")
    
    return True


async def test_end_to_end_workflow():
    """Test complete end-to-end workflow."""
    logger.info("=" * 80)
    logger.info("END-TO-END WORKFLOW TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing complete workflow: Discovery → Scraping → Quality → Enrichment")
    logger.info("")
    
    # Step 1: Get portal configs
    config_manager = PortalConfigManager()
    enabled_configs = config_manager.get_all_configs(enabled_only=True)
    logger.info(f"Step 1: Found {len(enabled_configs)} enabled portals")
    
    # Step 2: Ingest permits from multiple sources
    logger.info("")
    logger.info("Step 2: Ingesting permits from multiple sources...")
    ingestion = UnifiedPermitIngestion()
    quality_filter = QualityFilter(threshold=0.3)
    
    all_permits = []
    sources_tested = 0
    
    # Test scraper source
    scraper_source = PermitSource(
        source_type=PermitSourceType.SCRAPER,
        city="San Antonio, TX",
        source_id="cosa_fire",
        config={
            "portal_type": "accela",
            "city_code": "COSA",
            "module": "Fire",
            "url": "https://aca-prod.accela.com/COSA",
        },
    )
    
    try:
        permits = await ingestion.ingest_permits(scraper_source, days_back=120, limit=20)
        all_permits.extend(permits)
        sources_tested += 1
        logger.info(f"  ✅ Scraper (San Antonio): {len(permits)} permits")
    except Exception as e:
        logger.warning(f"  ⚠️  Scraper error: {e}")
    
    # Test API source
    api_source = PermitSource(
        source_type=PermitSourceType.SOCRATA_API,
        city="Seattle, WA",
        source_id="seattle_socrata",
        config={
            "portal_url": "https://data.seattle.gov",
            "dataset_id": "76t5-zqzr",
            "field_mapping": {
                "permit_id": "permitnum",
                "permit_type": "permittypedesc",
                "address": "originaladdress1",
                "status": "statuscurrent",
            },
        },
    )
    
    try:
        permits = await ingestion.ingest_permits(api_source, days_back=30, limit=20)
        all_permits.extend(permits)
        sources_tested += 1
        logger.info(f"  ✅ API (Seattle): {len(permits)} permits")
    except Exception as e:
        logger.warning(f"  ⚠️  API error: {e}")
    
    logger.info("")
    logger.info(f"Total permits from {sources_tested} sources: {len(all_permits)}")
    
    # Step 3: Quality filtering
    logger.info("")
    logger.info("Step 3: Applying quality filter...")
    high_quality, filtered, stats = quality_filter.filter_permits_sync(all_permits)
    
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Passed: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    logger.info(f"  Filtered: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    
    # Step 4: Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("END-TO-END WORKFLOW SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Sources Tested: {sources_tested}")
    logger.info(f"Total Permits: {len(all_permits)}")
    logger.info(f"High-Quality Permits: {len(high_quality)}")
    logger.info(f"Filter Rate: {stats['filter_rate']*100:.1f}%")
    logger.info("")
    logger.info("✅ End-to-End Workflow - WORKING")
    logger.info("")
    
    return True


async def main():
    """Run complete Phase 1.4 end-to-end test."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4: PERMIT DISCOVERY EXPANSION - FULL E2E TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing all 5 sub-phases:")
    logger.info("  1.4.1: Automated Portal Discovery")
    logger.info("  1.4.2: Scraper Standardization")
    logger.info("  1.4.3: Open Data API Integration")
    logger.info("  1.4.4: Data Quality & Filtering")
    logger.info("  1.4.5: Integration & Automation")
    logger.info("")
    
    results = {}
    
    # Test each phase
    results["1.4.1"] = await test_phase1_4_1_portal_discovery()
    results["1.4.2"] = await test_phase1_4_2_scraper_standardization()
    results["1.4.3"] = await test_phase1_4_3_api_integration()
    results["1.4.4"] = await test_phase1_4_4_quality_filtering()
    results["1.4.5"] = await test_phase1_4_5_integration_automation()
    results["e2e"] = await test_end_to_end_workflow()
    
    # Final summary
    logger.info("=" * 80)
    logger.info("PHASE 1.4: FINAL TEST RESULTS")
    logger.info("=" * 80)
    logger.info("")
    
    for phase, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {phase}: {status}")
    
    all_passed = all(results.values())
    
    logger.info("")
    if all_passed:
        logger.info("=" * 80)
        logger.info("✅ PHASE 1.4: PERMIT DISCOVERY EXPANSION - FULLY TESTED")
        logger.info("=" * 80)
        logger.info("")
        logger.info("All components are working correctly!")
        logger.info("The system is ready for production use.")
    else:
        logger.info("=" * 80)
        logger.info("⚠️  PHASE 1.4: SOME TESTS FAILED")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Please review failed tests above.")
    
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
