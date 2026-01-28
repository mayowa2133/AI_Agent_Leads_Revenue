"""Enhanced company enrichment pipeline with geocoding, company matching, and decision maker identification."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.core.config import get_settings
from src.signal_engine.enrichment.apollo_client import (
    ApolloAuthError,
    ApolloClient,
    ApolloCompany,
    ApolloRateLimitError,
)
from src.signal_engine.enrichment.clearbit_client import ClearbitClient
from src.signal_engine.enrichment.opencorporates_client import OpenCorporatesClient
from src.signal_engine.enrichment.search_snippet_client import SearchSnippetClient
from src.signal_engine.enrichment.snippet_llm_parser import (
    extract_person_from_snippets,
    pick_domain_from_snippets,
)
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

# Per-process circuit breaker: if Apollo starts returning auth/credit/rate-limit errors,
# disable Apollo for the remainder of this run and fall back to Clearbit/Hunter only.
_APOLLO_RUNTIME_DISABLED: bool = False

# Lightweight enrichment metrics for observability (per process/run).
_ENRICHMENT_METRICS: dict[str, int] = {
    "emails_accepted": 0,
    "emails_rejected_domain": 0,
    "hunter_credits_used": 0,
    "apollo_credits_used": 0,
}


def get_enrichment_metrics(*, reset: bool = False) -> dict[str, int]:
    metrics = dict(_ENRICHMENT_METRICS)
    if reset:
        for key in _ENRICHMENT_METRICS:
            _ENRICHMENT_METRICS[key] = 0
    return metrics


def persist_enrichment_metrics(
    *,
    label: str,
    permits_tested: int,
    emails_found: int,
    metrics: dict[str, int],
    output_path: str = "data/workflow_metrics.json",
) -> None:
    """
    Append enrichment metrics to workflow_metrics.json for lightweight observability.
    """
    entry = {
        "label": label,
        "permits_tested": permits_tested,
        "emails_found": emails_found,
        "metrics": metrics,
    }
    path = Path(output_path)
    try:
        if path.exists():
            try:
                payload = json.loads(path.read_text())
            except Exception:
                payload = {}
        else:
            payload = {}
        runs = payload.get("enrichment_runs") or []
        runs.append(entry)
        payload["enrichment_runs"] = runs
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    except Exception as exc:
        logger.warning(f"Failed to persist enrichment metrics: {exc}")


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
            "architect",
            "architects",
            "engineering",
            "engineers",
            "construction",
            "builders",
            "plumbing",
            "electric",
            "electrical",
            "mechanical",
            "hvac",
            "roofing",
            "sprinkler",
            "alarm",
            "fire",
            "contractor",
            "contractors",
        ]
        tokens = re.findall(r"[a-z0-9]+", name_lower)
        if not any(word in tokens for word in company_words):
            return True

    return False


def _guess_company_domains(company_name: str) -> list[str]:
    """
    Generate simple domain guesses from company name.
    """
    if not company_name:
        return []

    suffixes = {
        "llc",
        "inc",
        "ltd",
        "llp",
        "pllc",
        "corp",
        "co",
        "company",
        "group",
        "partners",
        "associates",
        "architects",
        "architect",
        "engineering",
        "engineers",
        "construction",
        "builders",
        "contractors",
        "contractor",
        "services",
        "systems",
    }
    tokens = [
        t.strip(".,()")
        for t in company_name.lower().replace("&", "and").split()
        if t.strip(".,()")
    ]
    tokens = [t for t in tokens if t not in suffixes]
    if not tokens:
        return []

    joined = "".join(tokens)
    hyphenated = "-".join(tokens)
    guesses = []
    for base in [joined, hyphenated]:
        if base and base not in guesses:
            guesses.append(f"{base}.com")
    return guesses[:2]


def _extract_domain_from_url(url: str) -> str | None:
    if not url:
        return None
    try:
        # Strip scheme
        cleaned = url.replace("https://", "").replace("http://", "")
        cleaned = cleaned.split("/")[0].split("?")[0]
        cleaned = cleaned.replace("www.", "")
        if "." not in cleaned:
            return None
        return cleaned.lower()
    except Exception:
        return None


def _extract_email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.split("@")[-1].strip().lower()


def _tokenize_company_name(company_name: str | None) -> list[str]:
    if not company_name:
        return []
    suffixes = {
        "llc",
        "inc",
        "ltd",
        "llp",
        "pllc",
        "corp",
        "co",
        "company",
        "group",
        "partners",
        "associates",
        "architects",
        "architect",
        "engineering",
        "engineers",
        "construction",
        "builders",
        "contractors",
        "contractor",
        "services",
        "systems",
    }
    tokens = [
        t.strip(".,()")
        for t in company_name.lower().replace("&", "and").split()
        if t.strip(".,()")
    ]
    return [t for t in tokens if t not in suffixes]


def _is_email_domain_sane(
    *,
    email: str | None,
    company_domain: str | None,
    company_name: str | None,
    blocked_domains: set[str] | None = None,
    blocked_tlds: set[str] | None = None,
    allowed_tlds_no_domain: set[str] | None = None,
) -> bool:
    """
    Basic sanity checks to avoid mismatched domains (e.g., personal/school emails).
    """
    email_domain = _extract_email_domain(email)
    if not email_domain:
        return False

    public_domains = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "me.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "gmx.com",
        "yandex.com",
    }
    normalized_company_domain = (company_domain or "").strip().lower()

    blocked_domains = blocked_domains or set()
    blocked_tlds = blocked_tlds or set()
    allowed_tlds_no_domain = allowed_tlds_no_domain or set()

    if email_domain in blocked_domains:
        return False
    if blocked_tlds:
        tld = email_domain.rsplit(".", 1)[-1]
        if tld in blocked_tlds:
            return False

    if email_domain in public_domains and email_domain != normalized_company_domain:
        return False

    if normalized_company_domain:
        if (
            email_domain == normalized_company_domain
            or email_domain.endswith(f".{normalized_company_domain}")
            or normalized_company_domain.endswith(f".{email_domain}")
        ):
            return True
        return False

    if allowed_tlds_no_domain:
        tld = email_domain.rsplit(".", 1)[-1]
        if tld not in allowed_tlds_no_domain:
            return False

    tokens = _tokenize_company_name(company_name)
    if not tokens:
        return True
    return any(token in email_domain for token in tokens)


def _accept_decision_maker(
    decision_maker: DecisionMaker | None,
    *,
    company_domain: str | None,
    company_name: str | None,
    source: str,
) -> DecisionMaker | None:
    if not decision_maker:
        return None
    settings = get_settings()
    blocked_domains = {
        d.strip().lower()
        for d in (settings.enrichment_blocked_email_domains or "").split(",")
        if d.strip()
    }
    blocked_tlds = {
        t.strip().lower()
        for t in (settings.enrichment_blocked_email_tlds or "").split(",")
        if t.strip()
    }
    allowed_tlds_no_domain = {
        t.strip().lower()
        for t in (settings.enrichment_allowed_email_tlds_no_domain or "").split(",")
        if t.strip()
    }
    if decision_maker.email and not _is_email_domain_sane(
        email=decision_maker.email,
        company_domain=company_domain,
        company_name=company_name,
        blocked_domains=blocked_domains,
        blocked_tlds=blocked_tlds,
        allowed_tlds_no_domain=allowed_tlds_no_domain,
    ):
        _ENRICHMENT_METRICS["emails_rejected_domain"] += 1
        logger.info(
            "Rejected email due to domain sanity check "
            f"(source={source}, company={company_name}, email={decision_maker.email})"
        )
        return None
    if decision_maker.email:
        _ENRICHMENT_METRICS["emails_accepted"] += 1
    return decision_maker


def _candidate_domains_from_snippets(
    company_name: str, snippets: list[dict]
) -> list[str]:
    blocked = {
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "yelp.com",
        "bbb.org",
        "chamberofcommerce.com",
        "opencorporates.com",
        "mapquest.com",
        "youtube.com",
        "houzz.com",
        "angi.com",
        "angieslist.com",
        "yellowpages.com",
        "thebluebook.com",
        "dandb.com",
        "manta.com",
        "buildzoom.com",
        "homestars.com",
        "homeadvisor.com",
        "thumbtack.com",
    }
    tokens = [
        t.strip(".,()")
        for t in company_name.lower().replace("&", "and").split()
        if t.strip(".,()")
    ]
    token_set = {t for t in tokens if t}

    scored: list[tuple[int, str]] = []
    seen = set()
    for item in snippets:
        url = item.get("url") or ""
        domain = _extract_domain_from_url(url)
        if not domain or domain in seen:
            continue
        if any(domain.endswith(b) for b in blocked):
            continue

        score = 0
        for token in tokens:
            if token and token in domain:
                score += 2
        if token_set and score == 0:
            # Require at least one company token match to keep domain candidate.
            continue
        if domain.startswith("www."):
            score += 1
        if domain.count(".") == 1:
            score += 1

        scored.append((score, domain))
        seen.add(domain)

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:3]]


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
    global _APOLLO_RUNTIME_DISABLED

    if (
        settings.apollo_enabled
        and not _APOLLO_RUNTIME_DISABLED
        and company_name
        and apollo_key
    ):
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
        except (ApolloRateLimitError, ApolloAuthError) as e:
            _APOLLO_RUNTIME_DISABLED = True
            logger.warning(f"Apollo disabled for this run due to error: {e}")
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
        # If Apollo is disabled/unavailable, try Clearbit to get a domain anyway.
        try:
            clearbit_client = ClearbitClient()
            try:
                suggestion = await clearbit_client.suggest_company(query=company_name)
                if suggestion and suggestion.domain:
                    return Company(
                        name=company_name,
                        website=f"https://{suggestion.domain}",
                    )
            finally:
                await clearbit_client.aclose()
        except Exception as e:
            logger.debug(f"Clearbit domain lookup failed during company match: {e}")
        return Company(name=company_name)
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
        apollo_enabled=settings.apollo_enabled and (not _APOLLO_RUNTIME_DISABLED),
        provider_priority=EnrichmentProvider(settings.enrichment_provider_priority),
        dry_run=settings.enrichment_dry_run,
        max_credits_per_run=settings.max_credits_per_run,
        max_apollo_credits_per_run=settings.max_apollo_credits_per_run,
        persist_cache=settings.enrichment_persist_cache,
        cache_path=settings.enrichment_cache_path,
    )

    def _log_credit_usage() -> None:
        summary = provider_manager.credit_summary()
        if summary["hunter"] or summary["apollo"]:
            _ENRICHMENT_METRICS["hunter_credits_used"] += summary["hunter"]
            _ENRICHMENT_METRICS["apollo_credits_used"] += summary["apollo"]
            logger.info(
                "Enrichment credits used for %s: Hunter %s, Apollo %s",
                company.name,
                summary["hunter"],
                summary["apollo"],
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
    else:
        # Fallback Chain A: Clearbit domain suggestion (no Apollo)
        if company.name and not company.name.startswith("Unknown"):
            try:
                clearbit_client = ClearbitClient()
                try:
                    suggestion = await clearbit_client.suggest_company(query=company.name)
                    if suggestion and suggestion.domain:
                        company_domain = suggestion.domain
                        logger.info(
                            f"Found domain via Clearbit: {company.name} -> {company_domain}"
                        )
                finally:
                    await clearbit_client.aclose()
            except Exception as e:
                logger.debug(f"Clearbit domain lookup failed: {e}")

        # Fallback Chain B: OpenCorporates officers (only if key configured)
        officer_names: list[str] = []
        if (
            company.name
            and not company.name.startswith("Unknown")
            and settings.opencorporates_api_key
        ):
            try:
                oc_client = OpenCorporatesClient(api_key=settings.opencorporates_api_key)
                try:
                    officer_names = await oc_client.find_officer_names_by_company(
                        name=company.name
                    )
                    if officer_names:
                        logger.info(
                            f"OpenCorporates officers for {company.name}: {officer_names[:2]}"
                        )
                    else:
                        logger.debug(
                            f"OpenCorporates returned no officers for {company.name}"
                        )
                finally:
                    await oc_client.aclose()
            except Exception as e:
                logger.debug(f"OpenCorporates officer lookup failed: {e}")

        if officer_names and company_domain:
            for officer_name in officer_names[:2]:
                try:
                    decision_maker = await provider_manager.find_decision_maker_email(
                        full_name=officer_name,
                        company_domain=company_domain,
                        title="Owner",
                    )
                    decision_maker = _accept_decision_maker(
                        decision_maker,
                        company_domain=company_domain,
                        company_name=company.name,
                        source="opencorporates-prelookup",
                    )
                    if decision_maker:
                        _log_credit_usage()
                        return decision_maker
                except RuntimeError as e:
                    logger.warning(f"Credit limit reached: {e}")
                    raise
    if (
        settings.apollo_enabled
        and not company_domain
        and company.name
        and not company.name.startswith("Unknown")
    ):
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
                decision_maker = _accept_decision_maker(
                    decision_maker,
                    company_domain=company_domain,
                    company_name=company.name,
                    source="hunter-email",
                )
                if decision_maker:
                    _log_credit_usage()
                    return decision_maker
            except RuntimeError as e:
                # Credit limit reached - log and stop
                logger.warning(f"Credit limit reached: {e}")
                raise

    # Strategy 2: Hunter domain-search fallback (no person name required)
    if company_domain:
        try:
            decision_maker = await provider_manager.find_any_contact_email_via_domain_search(
                company_domain=company_domain
            )
            decision_maker = _accept_decision_maker(
                decision_maker,
                company_domain=company_domain,
                company_name=company.name,
                source="hunter-domain-search",
            )
            if decision_maker:
                _log_credit_usage()
                return decision_maker
        except RuntimeError as e:
            logger.warning(f"Credit limit reached: {e}")
            raise

    # Strategy 2.5: Use provider manager for company-based search (Apollo fallback)
    if company_domain or company.name:
        try:
            decision_maker = await provider_manager.find_decision_maker_email(
                company_name=company.name,
                company_domain=company_domain,
                title="Facility Director",  # Default title to search for
            )
            decision_maker = _accept_decision_maker(
                decision_maker,
                company_domain=company_domain,
                company_name=company.name,
                source="provider-fallback",
            )
            if decision_maker:
                _log_credit_usage()
                return decision_maker
        except RuntimeError as e:
            # Credit limit reached - log and stop
            logger.warning(f"Credit limit reached: {e}")
            raise

    # Strategy 3: OpenCorporates officer/agent fallback (when we have domain + company name)
    if (
        company_domain
        and company.name
        and not company.name.startswith("Unknown")
        and settings.opencorporates_api_key
    ):
        try:
            oc_client = OpenCorporatesClient(
                api_key=settings.opencorporates_api_key
            )
            try:
                officer_names = await oc_client.find_officer_names_by_company(
                    name=company.name
                )
                if officer_names:
                    logger.info(
                        f"OpenCorporates officers for {company.name}: {officer_names[:2]}"
                    )
                else:
                    logger.debug(f"OpenCorporates returned no officers for {company.name}")
                for officer_name in officer_names[:2]:
                    decision_maker = await provider_manager.find_decision_maker_email(
                        full_name=officer_name,
                        company_domain=company_domain,
                        title="Owner",
                    )
                    decision_maker = _accept_decision_maker(
                        decision_maker,
                        company_domain=company_domain,
                        company_name=company.name,
                        source="opencorporates-officer",
                    )
                    if decision_maker:
                        _log_credit_usage()
                        return decision_maker
            finally:
                await oc_client.aclose()
        except Exception as e:
            logger.debug(f"OpenCorporates officer lookup failed: {e}")

    # Strategy 4: Search snippets + LLM parsing (company name -> person) then Hunter
    if company.name and not company.name.startswith("Unknown"):
        try:
            location_str = None
            if geocode_result:
                location_parts = []
                if geocode_result.city:
                    location_parts.append(geocode_result.city)
                if geocode_result.state:
                    location_parts.append(geocode_result.state)
                location_str = ", ".join(location_parts) if location_parts else None

            queries = [
                f'"{company.name}" owner OR president OR director',
                f'"{company.name}" leadership',
            ]
            if location_str:
                queries.append(f'"{company.name}" "{location_str}" owner')

            snippet_client = SearchSnippetClient()
            try:
                snippets = []
                for query in queries:
                    results = await snippet_client.search(query=query, limit=5)
                    snippets.extend(
                        [
                            {"title": r.title, "snippet": r.snippet, "url": r.url}
                            for r in results
                        ]
                    )
            finally:
                await snippet_client.aclose()

            if snippets:
                # If we still don't have a domain, try to derive from snippet URLs
                if not company_domain:
                    snippet_domains = _candidate_domains_from_snippets(
                        company.name, snippets
                    )
                    if snippet_domains:
                        # Let LLM pick best domain if multiple options
                        llm_domain = await pick_domain_from_snippets(
                            company_name=company.name,
                            snippets=snippets,
                            candidate_domains=snippet_domains,
                        )
                        if llm_domain and llm_domain.domain and (llm_domain.confidence or 0) >= 0.6:
                            company_domain = llm_domain.domain
                        else:
                            company_domain = snippet_domains[0]

                        logger.info(
                            f"Domain from snippets for {company.name}: {company_domain}"
                        )

                extraction = await extract_person_from_snippets(
                    company_name=company.name,
                    snippets=snippets,
                )
                if extraction and extraction.person_name:
                    confidence = extraction.confidence or 0.0
                    if confidence >= 0.75:
                        logger.info(
                            f"LLM snippet person for {company.name}: "
                            f"{extraction.person_name} ({confidence:.2f})"
                        )
                        domains_to_try = (
                            [company_domain]
                            if company_domain
                            else _guess_company_domains(company.name)
                        )
                        for domain in domains_to_try:
                            if not domain:
                                continue
                            decision_maker = await provider_manager.find_decision_maker_email(
                                full_name=extraction.person_name,
                                company_domain=domain,
                                title=extraction.title or "Owner",
                            )
                            decision_maker = _accept_decision_maker(
                                decision_maker,
                                company_domain=domain,
                                company_name=company.name,
                                source="snippet-hunter-email",
                            )
                            if decision_maker:
                                _log_credit_usage()
                                return decision_maker
                            decision_maker = await provider_manager.find_decision_maker_email_via_domain_search(
                                full_name=extraction.person_name,
                                company_domain=domain,
                            )
                            decision_maker = _accept_decision_maker(
                                decision_maker,
                                company_domain=domain,
                                company_name=company.name,
                                source="snippet-hunter-pattern",
                            )
                            if decision_maker:
                                _log_credit_usage()
                                return decision_maker
                    else:
                        logger.debug(
                            f"LLM snippet extraction low confidence for {company.name}: "
                            f"{confidence:.2f}"
                        )
        except Exception as e:
            logger.debug(f"LLM snippet fallback failed: {e}")

    _log_credit_usage()
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
