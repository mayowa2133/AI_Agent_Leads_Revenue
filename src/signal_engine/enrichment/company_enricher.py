"""Enhanced company enrichment pipeline with geocoding, company matching, and decision maker identification."""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass

from src.core.config import get_settings
from src.signal_engine.enrichment.apollo_client import ApolloClient, ApolloCompany
from src.signal_engine.enrichment.geocoder import GeocodeResult, geocode_address
from src.signal_engine.enrichment.provider_manager import (
    EnrichmentProvider,
    ProviderManager,
)
from src.signal_engine.enrichment.regulatory_matcher import match_regulatory_updates
from src.signal_engine.models import (
    Company,
    ComplianceContext,
    DecisionMaker,
    EnrichedLead,
    PermitData,
    RegulatoryUpdate,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichmentInputs:
    tenant_id: str
    permit: PermitData


def _is_likely_person_name(name: str) -> bool:
    """
    Heuristic to determine if a name is likely a person vs company.

    Args:
        name: Name to check

    Returns:
        True if likely a person name
    """
    if not name:
        return False

    name_lower = name.lower().strip()

    # Common person name patterns
    person_indicators = [
        r"^(mr|mrs|ms|dr|prof)\.?\s+",  # Titles
        r"\s+(jr|sr|ii|iii|iv)\.?$",  # Suffixes
        r"^[a-z]\.\s+[a-z]",  # Initials (e.g., "J. Smith")
    ]

    for pattern in person_indicators:
        if re.search(pattern, name_lower):
            return True

    # If it's 2-3 words and doesn't contain common company words, likely person
    words = name.split()
    if 2 <= len(words) <= 3:
        company_words = [
            "inc",
            "llc",
            "corp",
            "ltd",
            "company",
            "co",
            "group",
            "associates",
            "services",
            "systems",
        ]
        if not any(word.lower() in name_lower for word in company_words):
            return True

    return False


async def match_company(permit: PermitData, geocode_result: GeocodeResult | None) -> Company:
    """
    Match company from permit data using enhanced logic with Apollo domain lookup.

    HYBRID STRATEGY:
    1. Extract company name from applicant_name (if not a person name)
    2. Use Apollo's organizations/search (FREE TIER) to find company domain
    3. Return Company object with website/domain for Hunter.io email finding

    Args:
        permit: Permit data
        geocode_result: Geocoding result with location info

    Returns:
        Company object with matched or inferred information (including website/domain)
    """
    settings = get_settings()
    apollo_key = settings.apollo_api_key or os.environ.get("APOLLO_API_KEY")

    # Strategy 1: Use applicant_name if it looks like a company name
    company_name = None
    if permit.applicant_name and not _is_likely_person_name(permit.applicant_name):
        company_name = permit.applicant_name.strip()
        logger.debug(f"Using applicant_name as company: {company_name}")

    # Strategy 2: Use Apollo's organizations/search (FREE TIER) to find domain
    # This is the "gold mine" endpoint - converts company name to website domain
    apollo_company: ApolloCompany | None = None
    if company_name and apollo_key:
        try:
            location_str = None
            if geocode_result:
                location_parts = []
                if geocode_result.city:
                    location_parts.append(geocode_result.city)
                if geocode_result.state:
                    location_parts.append(geocode_result.state)
                location_str = ", ".join(location_parts) if location_parts else None

            client = ApolloClient(api_key=apollo_key)
            try:
                # Use the new search_organization endpoint (free tier compatible)
                apollo_company = await client.search_organization(
                    company_name=company_name, location=location_str
                )
                if apollo_company:
                    logger.info(
                        f"Found company domain via Apollo: {company_name} -> {apollo_company.domain or 'no domain'}"
                    )
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Apollo company search failed: {e}")

    # Build Company object
    if apollo_company:
        return Company(
            name=apollo_company.name or company_name or "Unknown Company",
            website=apollo_company.website,
            employee_count=apollo_company.employee_count,
            revenue_estimate=apollo_company.revenue_estimate,
            industry=apollo_company.industry,
        )
    elif company_name:
        return Company(name=company_name)
    else:
        # Fallback: placeholder based on address
        address_snippet = permit.address[:32] if permit.address else "Unknown"
        return Company(name=f"Unknown Org ({address_snippet})")


async def find_decision_maker(
    company: Company,
    geocode_result: GeocodeResult | None,
    permit: PermitData | None = None,
) -> DecisionMaker | None:
    """
    Find decision maker using available providers (Hunter.io or Apollo) with credit safety.

    Args:
        company: Company object
        geocode_result: Geocoding result with location info
        permit: Optional permit data (to extract applicant name if it's a person)

    Returns:
        DecisionMaker or None if not found
    """
    settings = get_settings()

    if not company.name or company.name.startswith("Unknown"):
        return None

    # Initialize provider manager with safety settings
    provider_manager = ProviderManager(
        hunter_api_key=settings.hunter_api_key or os.environ.get("HUNTER_API_KEY"),
        apollo_api_key=settings.apollo_api_key or os.environ.get("APOLLO_API_KEY"),
        provider_priority=EnrichmentProvider(settings.enrichment_provider_priority),
        dry_run=settings.enrichment_dry_run,
        max_credits_per_run=settings.max_credits_per_run,
        max_apollo_credits_per_run=settings.max_apollo_credits_per_run,
    )

    # Extract company domain from website
    company_domain = None
    if company.website:
        # Simple domain extraction
        domain = (
            company.website.replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .split("/")[0]
        )
        company_domain = domain
    elif company.name and not company.name.startswith("Unknown"):
        # HYBRID STRATEGY: If we have company name but no domain, use Apollo to find it
        # This is the "bridge" that makes the free tier pipeline work
        try:
            location_str = None
            if geocode_result:
                location_parts = []
                if geocode_result.city:
                    location_parts.append(geocode_result.city)
                if geocode_result.state:
                    location_parts.append(geocode_result.state)
                location_str = ", ".join(location_parts) if location_parts else None

            found_domain = await provider_manager.find_company_domain(
                company_name=company.name,
                location=location_str,
            )
            if found_domain:
                company_domain = found_domain
                logger.info(f"Found domain via Apollo for {company.name}: {company_domain}")
        except RuntimeError as e:
            # Apollo credit limit reached
            logger.warning(f"Apollo credit limit reached: {e}")
        except Exception as e:
            logger.debug(f"Apollo domain lookup failed: {e}")

    # Strategy 1: If permit has applicant_name that looks like a person, use Hunter
    if permit and permit.applicant_name:
        if _is_likely_person_name(permit.applicant_name) and company_domain:
            # Parse name
            name_parts = permit.applicant_name.strip().split(maxsplit=1)
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None

            try:
                decision_maker = await provider_manager.find_decision_maker_email(
                    first_name=first_name,
                    last_name=last_name,
                    full_name=permit.applicant_name,
                    company_domain=company_domain,
                    title="Facility Manager",  # Default title
                )
                if decision_maker:
                    return decision_maker
            except RuntimeError as e:
                # Credit limit reached - log and stop
                logger.warning(f"Credit limit reached: {e}")
                raise

    # Strategy 2: Use provider manager for company-based search (Apollo fallback)
    if company_domain or company.name:
        try:
            decision_maker = await provider_manager.find_decision_maker_email(
                company_name=company.name,
                company_domain=company_domain,
                title="Facility Director",  # Default title to search for
            )
            if decision_maker:
                return decision_maker
        except RuntimeError as e:
            # Credit limit reached - log and stop
            logger.warning(f"Credit limit reached: {e}")
            raise

    return None


def build_compliance_context(
    regulatory_updates: list[RegulatoryUpdate], geocode_result: GeocodeResult | None
) -> ComplianceContext:
    """
    Build compliance context from matched regulatory updates.

    Args:
        regulatory_updates: List of matched regulatory updates
        geocode_result: Geocoding result with jurisdiction info

    Returns:
        ComplianceContext object
    """
    jurisdiction = None
    if geocode_result:
        jurisdiction = geocode_result.state or geocode_result.county

    # Extract applicable codes from updates
    applicable_codes = []
    for update in regulatory_updates:
        applicable_codes.extend(update.applicable_codes)

    # Extract compliance triggers
    triggers = []
    for update in regulatory_updates:
        triggers.extend(update.compliance_triggers)
        # Also add update title as a trigger if no specific triggers
        if not update.compliance_triggers:
            triggers.append(update.title)

    return ComplianceContext(
        jurisdiction=jurisdiction,
        applicable_codes=list(set(applicable_codes)),  # Deduplicate
        triggers=list(set(triggers)),  # Deduplicate
        inspection_history=[],  # Not available from permit data alone
    )


async def enrich_permit_to_lead(inputs: EnrichmentInputs) -> EnrichedLead:
    """
    Enhanced enrichment pipeline: geocode → company match → decision maker → regulatory match → build EnrichedLead.

    Args:
        inputs: Enrichment inputs (tenant_id, permit)

    Returns:
        EnrichedLead with all enriched information
    """
    settings = get_settings()

    # Step 1: Geocode address
    geocode_result: GeocodeResult | None = None
    try:
        geocode_result = await geocode_address(inputs.permit.address)
        logger.debug(
            f"Geocoded address: {inputs.permit.address} -> "
            f"{geocode_result.city}, {geocode_result.state}"
        )
    except Exception as e:
        logger.warning(f"Geocoding failed for {inputs.permit.address}: {e}")
        # Continue without geocoding - not critical

    # Step 2: Match company (enhanced logic)
    company = await match_company(inputs.permit, geocode_result)

    # Step 3: Find decision maker (using ProviderManager: Hunter.io → Apollo)
    decision_maker: DecisionMaker | None = None
    if settings.enable_enrichment:
        try:
            decision_maker = await find_decision_maker(company, geocode_result, inputs.permit)
        except RuntimeError as e:
            # Credit limit reached - log warning but continue with enrichment
            logger.warning(f"Decision maker search stopped: {e}")
            decision_maker = None

    # Step 4: Match regulatory updates
    regulatory_matches: list[RegulatoryUpdate] = []
    if settings.enable_enrichment:
        try:
            regulatory_matches = await match_regulatory_updates(inputs.permit, geocode_result)
            if regulatory_matches:
                logger.debug(
                    f"Matched {len(regulatory_matches)} regulatory updates to permit "
                    f"{inputs.permit.permit_id}"
                )
        except Exception as e:
            logger.warning(f"Regulatory matching failed: {e}")

    # Step 5: Build compliance context
    compliance_context = build_compliance_context(regulatory_matches, geocode_result)

    # Step 6: Build enriched lead
    lead_id = str(uuid.uuid4())
    return EnrichedLead(
        lead_id=lead_id,
        tenant_id=inputs.tenant_id,
        company=company,
        decision_maker=decision_maker,
        permit=inputs.permit,
        compliance=compliance_context,
    )


# Keep old function for backward compatibility (deprecated)
def naive_company_guess_from_permit(permit: PermitData) -> Company:
    """
    Legacy function - kept for backward compatibility.

    Use match_company() instead.
    """
    if permit.applicant_name:
        name = permit.applicant_name
    else:
        name = f"Unknown Org ({permit.address[:32]})"
    return Company(name=name)
