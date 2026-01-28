"""Check prerequisites for Phase 2.1 testing."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from src.core.config import get_settings


def check_openai_key():
    """Check if OpenAI API key is configured."""
    settings = get_settings()
    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
        return True
    else:
        print("❌ OpenAI API key not found in .env")
        print("   Add: OPENAI_API_KEY=sk-your-key-here")
        return False


def check_enriched_leads():
    """Check if enriched leads exist."""
    leads_file = Path("data/enriched_leads.json")
    if leads_file.exists():
        # Check if file has content
        content = leads_file.read_text().strip()
        if content and content != "[]" and content != "{}":
            print("✅ Enriched leads file exists and has data")
            return True
        else:
            print("⚠️  Enriched leads file exists but is empty")
            print("   Run: poetry run python scripts/phase1_3/test_enrichment_pipeline.py")
            return False
    else:
        print("❌ No enriched leads file found")
        print("   Run: poetry run python scripts/phase1_3/test_enrichment_pipeline.py")
        return False


def check_neo4j():
    """Check if Neo4j is accessible."""
    try:
        from neo4j import GraphDatabase
        
        settings = get_settings()
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        driver.verify_connectivity()
        driver.close()
        print("✅ Neo4j is accessible")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        print("   Start Neo4j: docker compose up -d neo4j")
        return False


def check_pinecone():
    """Check if Pinecone is configured."""
    settings = get_settings()
    if settings.pinecone_api_key:
        print("✅ Pinecone API key configured")
        try:
            from src.knowledge.vectors.pinecone_client import get_index
            index = get_index()
            if index:
                print("✅ Pinecone index accessible")
                return True
            else:
                print("⚠️  Pinecone index not found")
                return False
        except Exception as e:
            print(f"⚠️  Pinecone connection issue: {e}")
            print("   This is optional - case study search will be skipped")
            return False
    else:
        print("⚠️  Pinecone API key not configured")
        print("   Add: PINECONE_API_KEY=your-key")
        print("   This is optional - case study search will be skipped")
        return False


def check_email_provider():
    """Check if email provider is configured."""
    settings = get_settings()
    provider = settings.email_provider or "smtp"
    
    if provider == "sendgrid":
        if settings.sendgrid_api_key:
            print("✅ SendGrid configured")
            return True
        else:
            print("⚠️  SendGrid selected but API key not configured")
            print("   Add: SENDGRID_API_KEY=your-key")
            return False
    elif provider == "ses":
        if settings.aws_ses_region:
            print("✅ AWS SES configured")
            return True
        else:
            print("⚠️  AWS SES selected but region not configured")
            print("   Add: AWS_SES_REGION=us-east-1")
            return False
    else:
        print(f"⚠️  Using SMTP (provider: {provider})")
        print("   Email sending may fail if SMTP server not running")
        print("   This is optional - workflow will still run")
        return False


def main():
    """Run all prerequisite checks."""
    print("=" * 70)
    print("Phase 2.1 Prerequisites Check")
    print("=" * 70)
    print()
    
    checks = [
        ("OpenAI API Key", check_openai_key, True),
        ("Enriched Leads", check_enriched_leads, True),
        ("Neo4j Connection", check_neo4j, True),
        ("Pinecone", check_pinecone, False),  # Optional
        ("Email Provider", check_email_provider, False),  # Optional
    ]
    
    results = []
    for name, check_func, required in checks:
        print(f"Checking {name}...")
        try:
            result = check_func()
            results.append((name, result, required))
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            results.append((name, False, required))
        print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    required_passed = sum(1 for name, result, required in results if result and required)
    required_total = sum(1 for _, _, required in results if required)
    optional_passed = sum(1 for name, result, required in results if result and not required)
    
    for name, result, required in results:
        status = "✅" if result else "❌"
        req_text = "(Required)" if required else "(Optional)"
        print(f"{status} {name} {req_text}")
    
    print()
    print(f"Required: {required_passed}/{required_total} passed")
    print(f"Optional: {optional_passed} configured")
    print()
    
    if required_passed == required_total:
        print("✅ All required prerequisites met!")
        print("   You can run: poetry run python scripts/phase2/test_phase2_1_workflow.py")
        return 0
    else:
        print("❌ Some required prerequisites are missing")
        print("   Please fix the issues above before testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
