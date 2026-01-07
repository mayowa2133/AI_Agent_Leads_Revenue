"""Entry point script for running scheduled permit scrapers."""

from __future__ import annotations

import asyncio
import logging
import sys

from src.signal_engine.jobs.scraper_scheduler import run_scheduled_scrapers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

if __name__ == "__main__":
    try:
        asyncio.run(run_scheduled_scrapers())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

