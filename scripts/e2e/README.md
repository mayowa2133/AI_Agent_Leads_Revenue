# End-to-End Tests

Complete flow tests that verify multiple phases working together.

## Test Scripts

- `test_complete_phase1_flow.py` - **Complete Phase 1 flow (1.1 → 1.2 → 1.3)**
- `test_e2e_simplified.py` - Simplified end-to-end test (1.1 → 1.3)
- `test_e2e_phase1_1_to_1_3.py` - Full end-to-end with real scraping

## Usage

```bash
# Test complete Phase 1 flow (recommended)
poetry run python scripts/e2e/test_complete_phase1_flow.py

# Simplified end-to-end test
poetry run python scripts/e2e/test_e2e_simplified.py

# Full end-to-end with real scraping
poetry run python scripts/e2e/test_e2e_phase1_1_to_1_3.py
```

## What's Tested

- Phase 1.1 → Phase 1.3: Permit scraping → Enrichment
- Phase 1.2 → Phase 1.3: Regulatory updates → Matching
- Complete flow: Phase 1.1 → Phase 1.2 → Phase 1.3

