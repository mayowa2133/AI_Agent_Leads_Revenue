# Scripts Directory Organization

**Date:** 2026-01-06  
**Status:** ✅ Organized by phase and purpose

---

## New Structure

```
scripts/
├── README.md                    # Main scripts directory documentation
├── phase1_1/                    # Phase 1.1: Permit Scraping Tests
│   ├── README.md
│   ├── test_phase1_1_complete.py
│   ├── test_mecklenburg.py
│   ├── test_san_antonio.py
│   └── ... (13 files)
├── phase1_2/                    # Phase 1.2: Regulatory Listener Tests
│   ├── README.md
│   ├── test_regulatory_listeners.py
│   └── verify_regulatory_setup.py
├── phase1_3/                    # Phase 1.3: Enrichment Pipeline Tests
│   ├── README.md
│   ├── test_enrichment_pipeline.py
│   ├── test_hybrid_enrichment.py
│   └── ... (9 files)
├── e2e/                         # End-to-End Tests
│   ├── README.md
│   ├── test_complete_phase1_flow.py
│   ├── test_e2e_simplified.py
│   └── test_e2e_phase1_1_to_1_3.py
├── utils/                       # Utility Scripts (Production)
│   ├── README.md
│   ├── run_scheduled_scrapers.py
│   ├── run_scraper_job.py
│   ├── run_scraper_fixture.py
│   ├── seed_knowledge_graph.py
│   └── docs_gate.py
└── debug/                       # Debug Scripts (Development)
    ├── README.md
    ├── debug_mecklenburg.py
    └── ... (7 files)
```

---

## Organization Rationale

### By Phase
- **phase1_1/**: All Phase 1.1 (scraping) tests
- **phase1_2/**: All Phase 1.2 (regulatory) tests
- **phase1_3/**: All Phase 1.3 (enrichment) tests

### By Purpose
- **e2e/**: End-to-end tests that verify multiple phases
- **utils/**: Production utility scripts
- **debug/**: Development/debugging scripts

---

## Quick Reference

### Phase 1.1 Tests
```bash
poetry run python scripts/phase1_1/test_phase1_1_complete.py
poetry run python scripts/phase1_1/test_mecklenburg.py
poetry run python scripts/phase1_1/test_san_antonio.py
```

### Phase 1.2 Tests
```bash
poetry run python scripts/phase1_2/test_regulatory_listeners.py
poetry run python scripts/phase1_2/verify_regulatory_setup.py
```

### Phase 1.3 Tests
```bash
poetry run python scripts/phase1_3/test_enrichment_pipeline.py
poetry run python scripts/phase1_3/test_hybrid_enrichment.py
```

### End-to-End Tests
```bash
poetry run python scripts/e2e/test_complete_phase1_flow.py
poetry run python scripts/e2e/test_e2e_simplified.py
```

### Production Utilities
```bash
poetry run python scripts/utils/run_scheduled_scrapers.py
poetry run python scripts/utils/run_scraper_job.py
```

---

## Migration Notes

All scripts have been moved from the root `scripts/` directory to organized subdirectories:

- ✅ Phase 1.1 tests → `scripts/phase1_1/`
- ✅ Phase 1.2 tests → `scripts/phase1_2/`
- ✅ Phase 1.3 tests → `scripts/phase1_3/`
- ✅ E2E tests → `scripts/e2e/`
- ✅ Utility scripts → `scripts/utils/`
- ✅ Debug scripts → `scripts/debug/`

**No code changes required** - all imports and functionality remain the same, only file locations changed.

---

## Benefits

1. **Clear Organization**: Easy to find tests for specific phases
2. **Better Navigation**: Logical grouping by functionality
3. **Documentation**: Each directory has its own README
4. **Scalability**: Easy to add new tests to appropriate directories
5. **Maintainability**: Clear separation between production and debug scripts

---

**Organization Date:** 2026-01-06  
**Status:** ✅ Complete

