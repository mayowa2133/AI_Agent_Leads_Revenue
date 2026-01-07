#!/bin/bash
# Quick verification script for Phase 1.1 components

set -e

echo "=========================================="
echo "Phase 1.1 Verification Script"
echo "=========================================="
echo ""

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first."
    exit 1
fi

echo "✅ Poetry found"

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if poetry check &> /dev/null; then
    echo "✅ Poetry project is valid"
else
    echo "⚠️  Poetry project check failed (may still work)"
fi

# Check if required files exist
echo ""
echo "Checking required files..."
REQUIRED_FILES=(
    "src/signal_engine/jobs/scraper_scheduler.py"
    "src/signal_engine/jobs/__init__.py"
    "scripts/run_scheduled_scrapers.py"
    "src/signal_engine/scrapers/permit_scraper.py"
)

ALL_FILES_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (missing)"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = false ]; then
    echo ""
    echo "❌ Some required files are missing!"
    exit 1
fi

# Check if APScheduler is in dependencies
echo ""
echo "Checking dependencies..."
if grep -q "apscheduler" pyproject.toml; then
    echo "✅ APScheduler found in pyproject.toml"
else
    echo "❌ APScheduler not found in pyproject.toml"
    exit 1
fi

# Run basic import test
echo ""
echo "Testing imports..."
if poetry run python -c "
from src.signal_engine.jobs.scraper_scheduler import ScraperScheduler
from src.signal_engine.scrapers.permit_scraper import MecklenburgPermitScraper, SanAntonioFireScraper
print('✅ All imports successful')
" 2>&1; then
    echo "✅ All imports successful"
else
    echo "❌ Import test failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Basic verification passed!"
echo "=========================================="
echo ""
echo "To run comprehensive tests:"
echo "  poetry run python scripts/test_phase1_1_complete.py"
echo ""
echo "To test applicant extraction (slower):"
echo "  TEST_APPLICANT_EXTRACTION=true poetry run python scripts/test_phase1_1_complete.py"
echo ""

