"""Test CKAN permit ingestion + enrichment pipeline to verify email extraction from PRIMARY CONTACT names."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.core.config import get_settings
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.enrichment.apollo_client import ApolloAuthError, ApolloClient, ApolloRateLimitError
from src.signal_engine.enrichment.company_enricher import (
    EnrichmentInputs,
    enrich_permit_to_lead,
    get_enrichment_metrics,
    persist_enrichment_metrics,
)
from src.signal_engine.enrichment.hunter_client import HunterClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def should_stop_for_email_target(
    enriched_results: list[dict], target_unique_emails: int
) -> bool:
    return (
        target_unique_emails > 0
        and sum(1 for r in enriched_results if r.get("email")) >= target_unique_emails
    )


async def test_ckan_enrichment() -> None:
    """Test CKAN permit ingestion and enrichment to find emails from PRIMARY CONTACT names."""
    settings = get_settings()
    logger.info("=" * 80)
    logger.info("Testing CKAN Permit Enrichment Pipeline")
    logger.info("=" * 80)
    logger.info(f"Dry Run Mode: {settings.enrichment_dry_run}")
    logger.info(f"Enrichment Enabled: {settings.enable_enrichment}")
    logger.info(f"Apollo Enabled: {settings.apollo_enabled}")
    logger.info("")

    # Step 0: Known company test (verify Apollo domain + Hunter email path)
    # Default to skipping (can hang when Apollo is rate-limiting or out of credits).
    import os

    logger.info("Step 0: Known company enrichment test (Apollo → Hunter)...")
    run_known_company_test = os.environ.get("SKIP_KNOWN_COMPANY_TEST", "true").lower() in [
        "0",
        "false",
        "no",
    ]
    if not run_known_company_test:
        logger.info(
            "  ⚠ Skipping known company test (default). "
            "Set SKIP_KNOWN_COMPANY_TEST=false to enable."
        )
    else:
        known_companies = [
            {"name": "Home Depot", "location": "United States"},
            {"name": "Starbucks", "location": "United States"},
            {"name": "Hilton", "location": "United States"},
        ]

        apollo_key = settings.apollo_api_key
        hunter_key = settings.hunter_api_key

        if not settings.apollo_enabled:
            logger.info("  ⚠ Skipping known company test: Apollo disabled (APOLLO_ENABLED=false)")
        elif not apollo_key:
            logger.info("  ⚠ Skipping known company test: APOLLO_API_KEY not set")
        elif not hunter_key:
            logger.info("  ⚠ Skipping known company test: HUNTER_API_KEY not set")
        else:
            apollo_client = ApolloClient(api_key=apollo_key)
            hunter_client = HunterClient(api_key=hunter_key, dry_run=settings.enrichment_dry_run)
            try:
                for company in known_companies:
                    name = company["name"]
                    location = company.get("location")
                    logger.info(f"  → Testing company: {name}")

                    try:
                        org = await asyncio.wait_for(
                            apollo_client.search_organization(
                                company_name=name, location=location
                            ),
                            timeout=10,
                        )
                    except asyncio.TimeoutError:
                        logger.info("    ✗ Apollo organization search timed out")
                        continue
                    except (ApolloRateLimitError, ApolloAuthError) as e:
                        logger.info(f"    ✗ Apollo error: {e}")
                        continue
                    if not org or not org.domain:
                        logger.info("    ✗ Apollo did not return a domain")
                        continue

                    domain = org.domain
                    logger.info(f"    ✓ Domain: {domain}")

                    # Use Apollo top people to get a real person name
                    top_people = await apollo_client.get_organization_top_people(
                        organization_id=org.apollo_id,
                        organization_domain=domain,
                        limit=1,
                    )
                    if not top_people or not top_people[0].full_name:
                        logger.info("    ✗ Apollo did not return a top person name")
                        continue

                    person_name = top_people[0].full_name
                    logger.info(f"    ✓ Top person: {person_name}")

                    email_result = await hunter_client.find_email(
                        full_name=person_name,
                        domain=domain,
                    )
                    if email_result and email_result.email:
                        logger.info(f"    ✓ Email: {email_result.email}")
                    else:
                        logger.info("    ✗ Hunter did not return an email")
            finally:
                await apollo_client.aclose()
                await hunter_client.aclose()

    logger.info("")

    sources_to_test = [
        {
            "label": "CKAN Current (last 365 days)",
            "resource_id": "c21106f9-3ef5-4f3a-8604-f992b4db7512",
            "days_back": 365,
            "limit": 1000,
        },
        {
            "label": "CKAN Historical (2020-2024)",
            "resource_id": "c22b1ef2-dcf8-4d77-be1a-ee3638092aab",
            "days_back": 3650,
            "limit": 2000,
        },
    ]

    ingestion = UnifiedPermitIngestion()

    for source_cfg in sources_to_test:
        get_enrichment_metrics(reset=True)
        logger.info(f"Step 1: Fetching permits from {source_cfg['label']}...")
        source = PermitSource(
            source_type=PermitSourceType.CKAN_API,
            city="San Antonio",
            source_id=f"san_antonio_ckan_{source_cfg['resource_id']}",
            config={
                "portal_url": "https://data.sanantonio.gov",
                "resource_id": source_cfg["resource_id"],
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

        permits = await ingestion.ingest_permits(
            source,
            days_back=source_cfg["days_back"],
            limit=source_cfg["limit"],
        )

        logger.info(f"✓ Fetched {len(permits)} permits from CKAN")
        logger.info("")

        # Step 2: Filter for quality permits and deduplicate
        logger.info("Step 2: Filtering for quality permits (with PRIMARY CONTACT and address)...")
        quality_permits = []
        seen_permit_ids = set()
        company_keywords = [
            "llc",
            "inc",
            "ltd",
            "corp",
            "company",
            "co",
            "group",
            "associates",
            "services",
            "systems",
            "construction",
            "builders",
            "contractor",
            "contractors",
            "architect",
            "architects",
            "engineering",
            "engineers",
            "plumbing",
            "electric",
            "electrical",
            "mechanical",
            "roofing",
            "hvac",
        ]

        for p in permits:
            if not p.applicant_name or len(p.applicant_name.strip()) <= 2:
                continue
            if not p.address or len(p.address.strip()) <= 5:
                continue
            # Skip obvious residential/garage sale permits
            if p.permit_type and "garage" in p.permit_type.lower():
                continue
            # Prefer business-looking applicant names
            applicant_lower = p.applicant_name.lower()
            if not any(keyword in applicant_lower for keyword in company_keywords):
                continue
            if p.permit_id in seen_permit_ids:
                continue
            seen_permit_ids.add(p.permit_id)
            quality_permits.append(p)

        logger.info(f"✓ Found {len(quality_permits)} quality permits with PRIMARY CONTACT + address")
        logger.info("")

        # Show sample permits
        logger.info("Sample permits:")
        for i, permit in enumerate(quality_permits[:5], 1):
            logger.info(
                f"  {i}. Permit {permit.permit_id} | "
                f"Type: {permit.permit_type} | "
                f"Contact: {permit.applicant_name} | "
                f"Address: {permit.address[:50]}..."
            )
        logger.info("")

        # Step 3: Run enrichment (limit to avoid API rate limits)
        test_limit = 100
        test_permits = quality_permits[:test_limit]
        logger.info(f"Step 3: Enriching first {len(test_permits)} permits...")
        logger.info("")

        enriched_results = []
        seen_company_names = set()
        seen_email_domains = set()
        target_unique_emails = 5
        for i, permit in enumerate(test_permits, 1):
            logger.info(f"[{i}/{len(test_permits)}] Processing Permit {permit.permit_id}")
            logger.info(f"  → PRIMARY CONTACT: {permit.applicant_name}")
            logger.info(f"  → Address: {permit.address}")

            try:
                lead = await enrich_permit_to_lead(
                    EnrichmentInputs(tenant_id="ckan_test", permit=permit)
                )

                # Extract results
                company_name = lead.company.name if lead.company else None
                company_website = lead.company.website if lead.company else None
                decision_maker_name = lead.decision_maker.full_name if lead.decision_maker else None
                email = lead.decision_maker.email if lead.decision_maker else None

                # Deduplicate by company name and email domain if email found
                if company_name:
                    if company_name.lower() in seen_company_names:
                        continue
                if email and "@" in email:
                    domain = email.split("@")[-1].lower()
                    if domain in seen_email_domains:
                        continue

                result = {
                    "permit_id": permit.permit_id,
                    "primary_contact": permit.applicant_name,
                    "address": permit.address,
                    "company_name": company_name,
                    "company_website": company_website,
                    "decision_maker_name": decision_maker_name,
                    "email": email,
                    "success": email is not None,
                }
                enriched_results.append(result)

                if company_name:
                    seen_company_names.add(company_name.lower())
                if email and "@" in email:
                    seen_email_domains.add(email.split("@")[-1].lower())

                logger.info(f"  ✓ Company: {company_name or 'Not found'}")
                logger.info(f"  ✓ Website: {company_website or 'Not found'}")
                logger.info(f"  ✓ Decision Maker: {decision_maker_name or 'Not found'}")
                logger.info(f"  {'✓' if email else '✗'} Email: {email or 'Not found'}")
                logger.info("")

                if email and should_stop_for_email_target(
                    enriched_results, target_unique_emails
                ):
                    logger.info(
                        f"Reached target of {target_unique_emails} unique emails. Stopping early."
                    )
                    break

            except Exception as exc:
                logger.error(f"  ✗ Enrichment failed: {exc}", exc_info=True)
                enriched_results.append(
                    {
                        "permit_id": permit.permit_id,
                        "primary_contact": permit.applicant_name,
                        "address": permit.address,
                        "company_name": None,
                        "company_website": None,
                        "decision_maker_name": None,
                        "email": None,
                        "success": False,
                        "error": str(exc),
                    }
                )
                logger.info("")

        # Step 4: Summary report
        logger.info("=" * 80)
        logger.info(f"ENRICHMENT RESULTS SUMMARY: {source_cfg['label']}")
        logger.info("=" * 80)
        logger.info(f"Total permits tested: {len(enriched_results)}")
        logger.info(f"Permits with company found: {sum(1 for r in enriched_results if r['company_name'])}")
        logger.info(f"Permits with website found: {sum(1 for r in enriched_results if r['company_website'])}")
        logger.info(f"Permits with decision maker: {sum(1 for r in enriched_results if r['decision_maker_name'])}")
        logger.info(f"Permits with EMAIL FOUND: {sum(1 for r in enriched_results if r['email'])}")
        logger.info("")

        # Detailed breakdown
        emails_found = [r for r in enriched_results if r["email"]]
        if emails_found:
            logger.info("✓ SUCCESS: Found emails for the following permits:")
            for r in emails_found:
                logger.info(
                    f"  • Permit {r['permit_id']}: {r['primary_contact']} → "
                    f"{r['company_name']} ({r['company_website']}) → "
                    f"{r['decision_maker_name']} <{r['email']}>"
                )
        else:
            logger.info("✗ No emails found. Possible reasons:")
            logger.info("  - Dry run mode is enabled (check ENRICHMENT_DRY_RUN)")
            logger.info("  - API keys not configured (check HUNTER_API_KEY, APOLLO_API_KEY)")
            logger.info("  - Companies don't have websites (Apollo can't find domain)")
            logger.info("  - PRIMARY CONTACT names don't match company employees (Hunter.io can't find email)")

        logger.info("")
        logger.info("=" * 80)
        metrics = get_enrichment_metrics(reset=True)
        logger.info(
            "ENRICHMENT METRICS SUMMARY: emails_accepted=%s emails_rejected_domain=%s "
            "hunter_credits_used=%s apollo_credits_used=%s",
            metrics["emails_accepted"],
            metrics["emails_rejected_domain"],
            metrics["hunter_credits_used"],
            metrics["apollo_credits_used"],
        )
        persist_enrichment_metrics(
            label=source_cfg["label"],
            permits_tested=len(enriched_results),
            emails_found=sum(1 for r in enriched_results if r["email"]),
            metrics=metrics,
        )
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ckan_enrichment())
