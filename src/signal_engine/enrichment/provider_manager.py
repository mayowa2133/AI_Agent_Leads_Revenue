"""Provider manager that abstracts between Hunter.io and Apollo with credit safety."""

from __future__ import annotations

import logging
from enum import Enum

from src.signal_engine.models import DecisionMaker

logger = logging.getLogger(__name__)


class EnrichmentProvider(str, Enum):
    """Available enrichment providers."""

    HUNTER = "hunter"
    APOLLO = "apollo"
    AUTO = "auto"  # Try Hunter first, then Apollo


class CreditGuard:
    """
    Credit guard to prevent runaway API calls.
    
    Enforces hard limit on credits per run to protect free tier accounts.
    Supports separate tracking for different providers.
    """

    def __init__(self, max_credits: int = 3, provider_name: str = "API"):
        """
        Initialize credit guard.
        
        Args:
            max_credits: Maximum credits allowed per run
            provider_name: Name of provider (for error messages)
        """
        self.max_credits = max_credits
        self.credits_used = 0
        self.provider_name = provider_name
        logger.info(f"Credit guard initialized ({provider_name}): max {max_credits} credits per run")

    def check_and_increment(self) -> None:
        """
        Check if credit limit reached and increment counter.
        
        Raises:
            RuntimeError: If credit limit exceeded
        """
        if self.credits_used >= self.max_credits:
            raise RuntimeError(
                f"{self.provider_name} credit safety brake triggered! "
                f"Used {self.credits_used}/{self.max_credits} credits. "
                f"Stopping enrichment to protect your account."
            )
        self.credits_used += 1
        logger.debug(f"{self.provider_name} credit used: {self.credits_used}/{self.max_credits}")

    def reset(self) -> None:
        """Reset credit counter (for testing)."""
        self.credits_used = 0


class ProviderManager:
    """
    Manages multiple enrichment providers with fallback logic and credit safety.
    
    Priority order (when AUTO):
    1. Hunter.io (free, always try first)
    2. Apollo (premium, if API key available)
    
    Safety features:
    - Credit guard to prevent runaway loops
    - Dry-run mode for testing
    - Automatic test key detection
    """

    def __init__(
        self,
        *,
        hunter_api_key: str | None = None,
        apollo_api_key: str | None = None,
        provider_priority: EnrichmentProvider = EnrichmentProvider.AUTO,
        dry_run: bool = True,
        max_credits_per_run: int = 3,
        max_apollo_credits_per_run: int = 10,
    ):
        """
        Initialize provider manager.
        
        Args:
            hunter_api_key: Hunter.io API key
            apollo_api_key: Apollo API key
            provider_priority: Which provider to prefer
            dry_run: If True, don't make real API calls
            max_credits_per_run: Maximum Hunter credits per run
            max_apollo_credits_per_run: Maximum Apollo credits per run
        """
        self.hunter_api_key = hunter_api_key
        self.apollo_api_key = apollo_api_key
        self.provider_priority = provider_priority
        self.dry_run = dry_run
        self.hunter_credit_guard = CreditGuard(max_credits=max_credits_per_run, provider_name="Hunter.io")
        self.apollo_credit_guard = CreditGuard(max_credits=max_apollo_credits_per_run, provider_name="Apollo")

        # Auto-detect test key
        if hunter_api_key == "test-api-key":
            logger.info("Test API key detected - enabling dry-run mode")
            self.dry_run = True

    async def find_decision_maker_email(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        company_domain: str | None = None,
        company_name: str | None = None,
        title: str | None = None,
    ) -> DecisionMaker | None:
        """
        Find decision maker using available providers with credit safety.
        
        Strategy:
        - If we have name + domain → Use Hunter (email finder)
        - If we have company + title → Use Apollo (person search)
        - Falls back through providers based on priority
        - Respects credit limits and dry-run mode
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (if first/last not available)
            company_domain: Company domain (e.g., "example.com")
            company_name: Company name
            title: Job title
        
        Returns:
            DecisionMaker or None if not found
        """
        # Strategy 1: Hunter email finder (if we have name + domain)
        if (first_name or full_name) and company_domain and self.hunter_api_key:
            if self.provider_priority in [EnrichmentProvider.HUNTER, EnrichmentProvider.AUTO]:
                try:
                    # Check credit limit before making call
                    if not self.dry_run:
                        self.hunter_credit_guard.check_and_increment()

                    from src.signal_engine.enrichment.hunter_client import HunterClient

                    client = HunterClient(api_key=self.hunter_api_key, dry_run=self.dry_run)
                    try:
                        email_result = await client.find_email(
                            first_name=first_name,
                            last_name=last_name,
                            full_name=full_name,
                            domain=company_domain,
                        )

                        if email_result and email_result.email:
                            logger.info(
                                f"Found email via Hunter: {email_result.email} "
                                f"(confidence: {email_result.score}%)"
                            )
                            return DecisionMaker(
                                full_name=full_name or f"{first_name} {last_name}".strip(),
                                email=email_result.email,
                                title=title,
                            )
                    finally:
                        await client.aclose()
                except RuntimeError:
                    # Credit limit reached - re-raise to stop processing
                    raise
                except Exception as e:
                    logger.debug(f"Hunter email finder failed: {e}")

        # Strategy 2: Apollo person search (if we have company + title)
        if company_name and title and self.apollo_api_key:
            if self.provider_priority in [EnrichmentProvider.APOLLO, EnrichmentProvider.AUTO]:
                try:
                    # Check credit limit (Apollo also uses credits)
                    if not self.dry_run:
                        self.apollo_credit_guard.check_and_increment()

                    from src.signal_engine.enrichment.apollo_client import ApolloClient

                    client = ApolloClient(api_key=self.apollo_api_key)
                    try:
                        people = await client.find_decision_makers_enhanced(
                            company_name=company_name,
                            company_domain=company_domain,
                            titles=[title] if title else None,
                            limit=1,
                        )

                        if people:
                            person = people[0]
                            logger.info(f"Found decision maker via Apollo: {person.full_name}")
                            return DecisionMaker(
                                full_name=person.full_name,
                                title=person.title,
                                email=person.email,
                                phone=person.phone,
                                linkedin_url=person.linkedin_url,
                            )
                    finally:
                        await client.aclose()
                except RuntimeError:
                    # Credit limit reached - re-raise to stop processing
                    raise
                except Exception as e:
                    logger.debug(f"Apollo person search failed: {e}")

        return None

    def get_credits_used(self) -> int:
        """Get number of Hunter credits used in this run."""
        return self.hunter_credit_guard.credits_used

    def get_apollo_credits_used(self) -> int:
        """Get number of Apollo credits used in this run."""
        return self.apollo_credit_guard.credits_used

    def reset_credits(self) -> None:
        """Reset credit counters (for testing)."""
        self.hunter_credit_guard.reset()
        self.apollo_credit_guard.reset()

    async def find_company_domain(
        self,
        *,
        company_name: str,
        location: str | None = None,
    ) -> str | None:
        """
        Find company domain using Apollo's organizations/search endpoint (FREE TIER).
        
        This is the "bridge" that converts company name to domain for Hunter.io.
        Uses Apollo free tier (organizations/search endpoint).
        
        Args:
            company_name: Company name to search
            location: Optional location string
        
        Returns:
            Company domain (e.g., "example.com") or None if not found
        """
        if not self.apollo_api_key or not company_name:
            return None

        try:
            # Check Apollo credit limit
            if not self.dry_run:
                self.apollo_credit_guard.check_and_increment()

            from src.signal_engine.enrichment.apollo_client import ApolloClient

            client = ApolloClient(api_key=self.apollo_api_key)
            try:
                company = await client.search_organization(
                    company_name=company_name,
                    location=location,
                )

                if company and company.domain:
                    logger.info(
                        f"Found domain via Apollo: {company_name} -> {company.domain}"
                    )
                    return company.domain
                else:
                    logger.debug(f"Apollo found company but no domain: {company_name}")
                    return None

            finally:
                await client.aclose()

        except RuntimeError:
            # Credit limit reached - re-raise to stop processing
            raise
        except Exception as e:
            logger.debug(f"Apollo domain search failed: {e}")
            return None

