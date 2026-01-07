# Utility Scripts

Production scripts for running scrapers, schedulers, and other utilities.

## Scripts

- `run_scheduled_scrapers.py` - Run scheduled scraper jobs (APScheduler)
- `run_scraper_job.py` - Run a single scraper job
- `run_scraper_fixture.py` - Run scraper with offline fixture
- `seed_knowledge_graph.py` - Seed Neo4j knowledge graph

## Usage

```bash
# Run scheduled scrapers
poetry run python scripts/utils/run_scheduled_scrapers.py

# Run a single scraper job
poetry run python scripts/utils/run_scraper_job.py

# Run with offline fixture
poetry run python scripts/utils/run_scraper_fixture.py
```

## Production Use

These scripts are intended for production use. They integrate with:
- APScheduler for scheduled jobs
- Auto-enrichment pipeline
- Lead storage
- Credit safety mechanisms

