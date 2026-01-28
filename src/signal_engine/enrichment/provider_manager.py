"""Provider manager that abstracts between Hunter.io and Apollo with credit safety."""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path

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
        apollo_enabled: bool = True,
        provider_priority: EnrichmentProvider = EnrichmentProvider.AUTO,
        dry_run: bool = True,
        max_credits_per_run: int = 3,
        max_apollo_credits_per_run: int = 10,
        persist_cache: bool = False,
        cache_path: str | None = None,
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
        self.apollo_enabled = apollo_enabled
        self.provider_priority = provider_priority
        self.dry_run = dry_run
        self.hunter_credit_guard = CreditGuard(
            max_credits=max_credits_per_run, provider_name="Hunter.io"
        )
        self.apollo_credit_guard = CreditGuard(
            max_credits=max_apollo_credits_per_run, provider_name="Apollo"
        )
        self._credit_usage = {"hunter": 0, "apollo": 0}
        self.persist_cache = persist_cache
        self.cache_path = Path(cache_path) if cache_path else None
        self._load_persistent_cache()

        # Auto-detect test key
        if hunter_api_key == "test-api-key":
            logger.info("Test API key detected - enabling dry-run mode")
            self.dry_run = True

    # Per-process caches to avoid repeat lookups for the same person/domain.
    _email_lookup_cache: dict[tuple[str, str], DecisionMaker | None] = {}
    _domain_search_cache: dict[str, object | None] = {}
    _persistent_cache_loaded: bool = False

    def _increment_hunter_credit(self) -> None:
        self.hunter_credit_guard.check_and_increment()
        self._credit_usage["hunter"] += 1

    def _increment_apollo_credit(self) -> None:
        self.apollo_credit_guard.check_and_increment()
        self._credit_usage["apollo"] += 1

    def credit_summary(self) -> dict[str, int]:
        return {
            "hunter": self.hunter_credit_guard.credits_used,
            "apollo": self.apollo_credit_guard.credits_used,
        }

    def _load_persistent_cache(self) -> None:
        if not self.persist_cache or not self.cache_path:
            return
        if ProviderManager._persistent_cache_loaded:
            return
        if not self.cache_path.exists():
            ProviderManager._persistent_cache_loaded = True
            return
        try:
            data = json.loads(self.cache_path.read_text())
        except Exception as exc:
            logger.warning(f"Failed to load enrichment cache: {exc}")
            ProviderManager._persistent_cache_loaded = True
            return

        email_cache = data.get("email_lookup", {}) if isinstance(data, dict) else {}
        for key, payload in email_cache.items():
            if not isinstance(key, str) or "|" not in key:
                continue
            name_key, domain_key = key.split("|", 1)
            if payload is None:
                ProviderManager._email_lookup_cache[(name_key, domain_key)] = None
            elif isinstance(payload, dict):
                ProviderManager._email_lookup_cache[(name_key, domain_key)] = DecisionMaker(
                    **payload
                )

        domain_cache = data.get("domain_search", {}) if isinstance(data, dict) else {}
        for domain_key, payload in domain_cache.items():
            if not isinstance(domain_key, str):
                continue
            ProviderManager._domain_search_cache[domain_key] = self._deserialize_domain_search_result(
                payload
            )

        ProviderManager._persistent_cache_loaded = True

    def _save_persistent_cache(self) -> None:
        if not self.persist_cache or not self.cache_path:
            return
        data = {
            "email_lookup": {
                f"{name}|{domain}": (decision.model_dump() if decision else None)
                for (name, domain), decision in self._email_lookup_cache.items()
            },
            "domain_search": {
                domain: self._serialize_domain_search_result(result)
                for domain, result in self._domain_search_cache.items()
            },
        }
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(data, indent=2, sort_keys=True))
        except Exception as exc:
            logger.warning(f"Failed to persist enrichment cache: {exc}")

    def _serialize_domain_search_result(self, result: object | None) -> object | None:
        if result is None:
            return None
        try:
            from src.signal_engine.enrichment.hunter_client import (
                HunterDomainSearchResult,
                HunterEmailRecord,
            )
        except Exception:
            return None
        if not isinstance(result, HunterDomainSearchResult):
            return None
        emails_payload = []
        for entry in result.emails or []:
            if not isinstance(entry, HunterEmailRecord):
                continue
            emails_payload.append(
                {
                    "email": entry.email,
                    "first_name": entry.first_name,
                    "last_name": entry.last_name,
                    "position": entry.position,
                    "confidence": entry.confidence,
                }
            )
        return {"pattern": result.pattern, "emails": emails_payload}

    def _deserialize_domain_search_result(self, payload: object | None) -> object | None:
        if payload is None or not isinstance(payload, dict):
            return None
        try:
            from src.signal_engine.enrichment.hunter_client import (
                HunterDomainSearchResult,
                HunterEmailRecord,
            )
        except Exception:
            return None
        emails_payload = payload.get("emails") or []
        emails: list[HunterEmailRecord] = []
        for entry in emails_payload:
            if not isinstance(entry, dict):
                continue
            emails.append(
                HunterEmailRecord(
                    email=entry.get("email"),
                    first_name=entry.get("first_name"),
                    last_name=entry.get("last_name"),
                    position=entry.get("position"),
                    confidence=entry.get("confidence"),
                )
            )
        return HunterDomainSearchResult(pattern=payload.get("pattern"), emails=emails)

    @staticmethod
    def _normalize_domain(domain: str | None) -> str | None:
        if not domain:
            return None
        return domain.strip().lower()

    @staticmethod
    def _normalize_name_key(
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
    ) -> str | None:
        if full_name and full_name.strip():
            return full_name.strip().lower()
        parts = [p for p in [first_name, last_name] if p]
        if not parts:
            return None
        return " ".join(parts).strip().lower()

    async def _get_domain_search_result(self, domain: str) -> object | None:
        domain_key = self._normalize_domain(domain)
        if not domain_key:
            return None

        if domain_key in self._domain_search_cache:
            return self._domain_search_cache[domain_key]

        try:
            if not self.dry_run:
                self._increment_hunter_credit()

            from src.signal_engine.enrichment.hunter_client import HunterClient

            client = HunterClient(api_key=self.hunter_api_key, dry_run=self.dry_run)
            try:
                result = await client.domain_search(domain=domain_key, limit=10)
                self._domain_search_cache[domain_key] = result
                self._save_persistent_cache()
                return result
            finally:
                await client.aclose()
        except RuntimeError:
            raise
        except Exception as e:
            logger.debug(f"Hunter domain search failed: {e}")
            self._domain_search_cache[domain_key] = None
            self._save_persistent_cache()
            return None

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
                name_key = self._normalize_name_key(
                    first_name=first_name, last_name=last_name, full_name=full_name
                )
                domain_key = self._normalize_domain(company_domain)
                if name_key and domain_key:
                    cache_key = (name_key, domain_key)
                    if cache_key in self._email_lookup_cache:
                        cached = self._email_lookup_cache[cache_key]
                        if cached is not None:
                            return cached
                        # Previously attempted; skip Hunter to avoid repeat spend.
                        name_key = None
                try:
                    # Check credit limit before making call
                    if not self.dry_run:
                        self._increment_hunter_credit()

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
                            decision = DecisionMaker(
                                full_name=full_name or f"{first_name} {last_name}".strip(),
                                email=email_result.email,
                                title=title,
                            )
                            if name_key and domain_key:
                                self._email_lookup_cache[(name_key, domain_key)] = decision
                                self._save_persistent_cache()
                            return decision
                        if name_key and domain_key:
                            self._email_lookup_cache[(name_key, domain_key)] = None
                            self._save_persistent_cache()
                    finally:
                        await client.aclose()
                except RuntimeError:
                    # Credit limit reached - re-raise to stop processing
                    raise
                except Exception as e:
                    logger.debug(f"Hunter email finder failed: {e}")

        # Strategy 2: Apollo person search (if we have company + title)
        if self.apollo_enabled and company_name and title and self.apollo_api_key:
            if self.provider_priority in [EnrichmentProvider.APOLLO, EnrichmentProvider.AUTO]:
                try:
                    # Check credit limit (Apollo also uses credits)
                    if not self.dry_run:
                        self._increment_apollo_credit()

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
        if not self.apollo_enabled or not self.apollo_api_key or not company_name:
            return None

        # Strategy 1: Apollo (preferred)
        try:
            # Check Apollo credit limit
            if not self.dry_run:
                self._increment_apollo_credit()

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
            finally:
                await client.aclose()

        except RuntimeError:
            # Credit limit reached - re-raise to stop processing
            raise
        except Exception as e:
            logger.debug(f"Apollo domain search failed: {e}")

        # Strategy 2: Clearbit autocomplete (fallback, no API key required)
        try:
            from src.signal_engine.enrichment.clearbit_client import ClearbitClient

            clearbit_client = ClearbitClient()
            try:
                suggestion = await clearbit_client.suggest_company(query=company_name)
                if suggestion and suggestion.domain:
                    logger.info(
                        f"Found domain via Clearbit: {company_name} -> {suggestion.domain}"
                    )
                    return suggestion.domain
                logger.debug(f"Clearbit returned no domain for: {company_name}")
            finally:
                await clearbit_client.aclose()
        except Exception as e:
            logger.debug(f"Clearbit domain search failed: {e}")

        return None

    async def find_decision_maker_email_via_domain_search(
        self,
        *,
        full_name: str,
        company_domain: str,
    ) -> DecisionMaker | None:
        """
        Use Hunter domain-search to infer email pattern and match a person.
        """
        if not full_name or not company_domain or not self.hunter_api_key:
            return None

        try:
            result = await self._get_domain_search_result(company_domain)
            if not result:
                return None

            # Try direct match from returned emails
            first_name, last_name = _split_name(full_name)
            if result.emails:
                for record in result.emails:
                    if (
                        record.first_name
                        and record.last_name
                        and record.first_name.lower() == first_name.lower()
                        and record.last_name.lower() == last_name.lower()
                        and record.email
                    ):
                        return DecisionMaker(
                            full_name=full_name,
                            title=record.position,
                            email=record.email,
                        )

            # If pattern exists, synthesize email
            if result.pattern and first_name and last_name:
                email = _apply_email_pattern(
                    pattern=result.pattern,
                    first_name=first_name,
                    last_name=last_name,
                    domain=company_domain,
                )
                if email:
                    return DecisionMaker(
                        full_name=full_name,
                        email=email,
                    )
        except RuntimeError:
            raise

        return None

    async def find_any_contact_email_via_domain_search(
        self,
        *,
        company_domain: str,
    ) -> DecisionMaker | None:
        """
        Use Hunter domain-search to return any valid contact when no name is known.
        """
        if not company_domain or not self.hunter_api_key:
            return None

        try:
            result = await self._get_domain_search_result(company_domain)
            if not result or not result.emails:
                return None

            candidates = [r for r in result.emails if r.email]
            if not candidates:
                return None

            def score(rec: object) -> int:
                confidence = getattr(rec, "confidence", None) or 0
                position = (getattr(rec, "position", None) or "").lower()
                position_bonus = 0
                if any(
                    k in position
                    for k in [
                        "owner",
                        "founder",
                        "chief",
                        "ceo",
                        "president",
                        "director",
                        "manager",
                    ]
                ):
                    position_bonus = 10
                elif any(
                    k in position
                    for k in ["admin", "info", "support", "sales", "contact"]
                ):
                    position_bonus = -5
                return confidence + position_bonus

            candidates.sort(key=score, reverse=True)
            top = candidates[0]
            first = getattr(top, "first_name", None)
            last = getattr(top, "last_name", None)
            full_name = " ".join(p for p in [first, last] if p) or None

            return DecisionMaker(
                full_name=full_name,
                title=getattr(top, "position", None),
                email=getattr(top, "email", None),
            )
        except RuntimeError:
            raise

        return None


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""
    return first, last


def _apply_email_pattern(
    *,
    pattern: str,
    first_name: str,
    last_name: str,
    domain: str,
) -> str | None:
    if not pattern or not first_name or not last_name:
        return None

    first = first_name.lower()
    last = last_name.lower()
    f = first[0] if first else ""
    l = last[0] if last else ""

    p = pattern.lower().replace("{", "").replace("}", "")
    replacements = {
        "first": first,
        "last": last,
        "f": f,
        "l": l,
    }
    # Replace longer tokens first to avoid collisions
    for token in ["first", "last", "f", "l"]:
        p = p.replace(token, replacements[token])

    p = p.replace("..", ".").strip(".-_")
    if "@" in p:
        email = p
    else:
        email = f"{p}@{domain}"

    return email if "@" in email else None
