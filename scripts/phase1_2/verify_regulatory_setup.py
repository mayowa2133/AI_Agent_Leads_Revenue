"""Quick verification script for regulatory listener setup."""

from __future__ import annotations

import sys

from src.core.config import get_settings
from src.signal_engine.jobs.scraper_scheduler import ScraperScheduler
from src.signal_engine.listeners.epa_listener import EPARegulatoryListener
from src.signal_engine.listeners.fire_marshal_listener import FireMarshalListener
from src.signal_engine.listeners.nfpa_listener import NFPAListener
from src.signal_engine.storage.regulatory_storage import RegulatoryStorage


def main():
    """Verify regulatory listener setup."""
    print("\n" + "=" * 60)
    print("REGULATORY LISTENER SETUP VERIFICATION")
    print("=" * 60)

    settings = get_settings()
    all_good = True

    # Check configuration
    print("\n📋 Configuration:")
    print(f"   Regulatory RSS Feeds: {settings.regulatory_rss_feeds or '(not configured)'}")
    print(f"   Update Frequency: {settings.regulatory_update_frequency_hours} hours")
    print(f"   LLM Processing: {'Enabled' if settings.regulatory_llm_enabled else 'Disabled'}")

    if settings.regulatory_rss_feeds:
        feeds = settings.regulatory_feed_list()
        print(f"   ✅ {len(feeds)} RSS feed(s) configured")
    else:
        print("   ⚠️  No RSS feeds configured (Fire Marshal listener will use placeholder)")

    # Check listeners can be instantiated
    print("\n🔧 Listeners:")
    try:
        epa_listener = EPARegulatoryListener()
        print("   ✅ EPA Listener: OK")
    except Exception as e:
        print(f"   ❌ EPA Listener: {e}")
        all_good = False

    try:
        nfpa_listener = NFPAListener()
        print("   ✅ NFPA Listener: OK")
    except Exception as e:
        print(f"   ❌ NFPA Listener: {e}")
        all_good = False

    try:
        fire_marshal_listener = FireMarshalListener(state="Texas")
        print("   ✅ Fire Marshal Listener: OK")
    except Exception as e:
        print(f"   ❌ Fire Marshal Listener: {e}")
        all_good = False

    # Check storage
    print("\n💾 Storage:")
    try:
        storage = RegulatoryStorage()
        updates = storage.load_all()
        print(f"   ✅ Storage: OK ({len(updates)} updates stored)")
    except Exception as e:
        print(f"   ❌ Storage: {e}")
        all_good = False

    # Check scheduler integration
    print("\n⏰ Scheduler Integration:")
    try:
        scheduler = ScraperScheduler()
        scheduler.add_regulatory_listener_job(
            "test_epa", EPARegulatoryListener(), "demo", schedule_type="interval", hours=168
        )
        jobs = scheduler.scheduler.get_jobs()
        print(f"   ✅ Scheduler: OK ({len(jobs)} jobs configured)")
    except Exception as e:
        print(f"   ❌ Scheduler: {e}")
        all_good = False

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All components verified successfully!")
        print("\nNext steps:")
        print("1. Configure RSS feeds in .env: REGULATORY_RSS_FEEDS='url1,url2'")
        print("2. Run scheduler: poetry run python scripts/run_scheduled_scrapers.py")
        print("3. Monitor updates in: data/regulatory_updates.json")
        return 0
    else:
        print("❌ Some components have issues - review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

