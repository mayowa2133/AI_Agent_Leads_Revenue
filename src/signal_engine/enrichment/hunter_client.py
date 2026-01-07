"""Hunter.io API client for email finding with credit-safe testing."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class HunterError(RuntimeError):
    """Error during Hunter.io API call."""
    pass


@dataclass(frozen=True)
class HunterEmailResult:
    """Result from Hunter.io email finder."""

    email: str | None = None
    score: int | None = None  # Confidence score 0-100
    sources: list[dict] | None = None
    first_name: str | None = None
    last_name: str | None = None
    domain: str | None = None


class MockHunterClient:
    """
    Mock Hunter.io client for zero-cost testing.
    
    Simulates API responses without making network calls.
    Use this during development to test logic without spending credits.
    """

    def __init__(self, *, api_key: str | None = None):
        """
        Initialize mock client.
        
        Args:
            api_key: API key (ignored in mock mode)
        """
        self.api_key = api_key
        logger.debug("MockHunterClient initialized - no real API calls will be made")

    async def aclose(self) -> None:
        """Mock close - no-op."""
        pass

    async def find_email(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        domain: str,
    ) -> HunterEmailResult | None:
        """
        Mock email finder - returns simulated response.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (if first/last not available)
            domain: Company domain
        
        Returns:
            Mock HunterEmailResult with test data
        """
        if not domain:
            return None

        # Parse full_name if provided
        if full_name and not (first_name and last_name):
            parts = full_name.strip().split(maxsplit=1)
            if len(parts) == 2:
                first_name = parts[0]
                last_name = parts[1]
            elif len(parts) == 1:
                first_name = parts[0]

        if not first_name:
            return None

        # Return mock response
        email = f"{first_name.lower()}.{last_name.lower() if last_name else 'test'}@{domain}"
        logger.debug(f"[MOCK] Would return email: {email}")

        return HunterEmailResult(
            email=email,
            score=95,  # High confidence for mock
            sources=[{"domain": domain, "uri": f"https://{domain}/team"}],
            first_name=first_name,
            last_name=last_name,
            domain=domain,
        )


class HunterClient:
    """
    Hunter.io API client for email finding.
    
    Free tier: 50 email searches/month
    API docs: https://hunter.io/api-documentation
    
    Important: Only charges credits when email is found (404 = no charge).
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.hunter.io/v2",
        timeout_s: float = 30.0,
        dry_run: bool = False,
    ):
        """
        Initialize Hunter client.
        
        Args:
            api_key: Hunter.io API key
            base_url: API base URL
            timeout_s: Request timeout
            dry_run: If True, only log what would be sent (no real API calls)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self._client = httpx.AsyncClient(timeout=timeout_s)

        # Detect test key
        if api_key == "test-api-key":
            logger.info("Test API key detected - using mock mode")
            self.dry_run = True

    async def aclose(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    async def find_email(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        domain: str,
    ) -> HunterEmailResult | None:
        """
        Find email address for a person at a domain.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (if first/last not available)
            domain: Company domain (e.g., "example.com")
        
        Returns:
            HunterEmailResult or None if not found
        
        Note: Only charges credit if email is found. 404 responses don't cost credits.
        """
        if not domain:
            return None

        # Parse full_name if provided
        if full_name and not (first_name and last_name):
            parts = full_name.strip().split(maxsplit=1)
            if len(parts) == 2:
                first_name = parts[0]
                last_name = parts[1]
            elif len(parts) == 1:
                first_name = parts[0]

        if not first_name:
            return None

        url = f"{self.base_url}/email-finder"
        params = {
            "api_key": self.api_key,
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Dry-run mode: just log what would be sent
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would call Hunter.io email-finder: "
                f"{first_name} {last_name or ''} @ {domain}"
            )
            logger.debug(f"[DRY RUN] URL: {url}, Params: {params}")
            return None

        try:
            resp = await self._client.get(url, params=params)

            # 404 = no email found, doesn't cost a credit
            if resp.status_code == 404:
                logger.debug(f"No email found for {first_name} @ {domain} (no credit charged)")
                return None

            if resp.status_code >= 400:
                raise HunterError(f"Hunter.io error {resp.status_code}: {resp.text}")

            data = resp.json().get("data", {})

            if not data.get("email"):
                return None

            # Extract confidence score
            score = data.get("score")
            if score and score < 80:
                logger.debug(
                    f"Email found but low confidence ({score}%): {data.get('email')} - skipping"
                )
                return None

            return HunterEmailResult(
                email=data.get("email"),
                score=score,
                sources=data.get("sources", []),
                first_name=data.get("first_name") or first_name,
                last_name=data.get("last_name") or last_name,
                domain=domain,
            )

        except httpx.HTTPError as e:
            raise HunterError(f"HTTP error during Hunter.io call: {e}") from e

