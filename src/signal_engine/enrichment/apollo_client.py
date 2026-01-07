from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class ApolloError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApolloPerson:
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None


@dataclass(frozen=True)
class ApolloCompany:
    name: str
    website: str | None = None
    employee_count: int | None = None
    revenue_estimate: str | None = None
    industry: str | None = None
    domain: str | None = None


class ApolloClient:
    """
    Minimal Apollo-style client wrapper.

    Note: Apollo endpoints/fields can change; this wrapper is intentionally small and
    isolates HTTP concerns so the rest of the system only consumes normalized objects.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.apollo.io/v1",
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        # Apollo requires API key in X-Api-Key header
        self._headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def find_decision_maker(
        self,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
        titles: list[str] | None = None,
        location: str | None = None,
        limit: int = 5,
    ) -> list[ApolloPerson]:
        """
        Find likely decision makers at a company.

        This uses a conservative, provider-agnostic request format; adapt the payload
        mapping to your Apollo plan once you have the exact endpoint/fields.
        """
        titles = titles or [
            "Facility Director",
            "Facilities Director",
            "Facilities Manager",
            "Director of Facilities",
            "Building Engineer",
            "Chief Engineer",
        ]

        # Provider-agnostic payload shape (adjust when wiring real Apollo endpoint)
        payload = {
            "q_organization_name": company_name,
            "q_organization_domains": [company_domain] if company_domain else None,
            "person_titles": titles,
            "q_location": location,
            "page": 1,
            "per_page": max(1, min(limit, 25)),
        }

        # Remove Nones for cleaner requests.
        payload = {k: v for k, v in payload.items() if v is not None}

        url = f"{self.base_url}/mixed_people/search"
        resp = await self._client.post(url, json=payload, headers=self._headers)
        if resp.status_code >= 400:
            raise ApolloError(f"Apollo error {resp.status_code}: {resp.text}")

        data = resp.json()
        people = data.get("people") or data.get("contacts") or []
        out: list[ApolloPerson] = []
        for p in people:
            out.append(
                ApolloPerson(
                    full_name=p.get("name") or p.get("full_name"),
                    title=p.get("title"),
                    email=p.get("email"),
                    phone=p.get("phone") or p.get("phone_numbers", [None])[0],
                    linkedin_url=p.get("linkedin_url"),
                )
            )
            return out

    async def search_organization(
        self,
        *,
        company_name: str,
        location: str | None = None,
    ) -> ApolloCompany | None:
        """
        Search for organization using Apollo's organizations/search endpoint (FREE TIER).
        
        This is the "gold mine" endpoint - converts company name to website domain.
        Works on Apollo free tier (110 credits/month).
        
        Args:
            company_name: Company name to search (e.g., "Mecklenburg Electric")
            location: Optional location string (city, state, etc.)
        
        Returns:
            ApolloCompany with website_url/domain, or None if not found
        """
        if not company_name:
            return None

        payload = {
            "q_organization_name": company_name,
            "page": 1,
            "per_page": 1,
        }

        if location:
            payload["q_location"] = location

        url = f"{self.base_url}/organizations/search"
        resp = await self._client.post(url, json=payload, headers=self._headers)

        if resp.status_code >= 400:
            # If search fails, return None (not an error)
            logger.debug(f"Organization search returned {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        organizations = data.get("organizations") or []

        if not organizations:
            return None

        org = organizations[0]

        # Extract domain - Apollo provides primary_domain directly, or extract from website_url
        primary_domain = org.get("primary_domain")
        website_url = org.get("website_url") or org.get("website")
        
        # Use primary_domain if available (cleanest), otherwise extract from website_url
        domain = None
        if primary_domain:
            domain = primary_domain
        elif website_url:
            # Extract domain from URL
            domain = (
                website_url.replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .split("/")[0]
            )

        return ApolloCompany(
            name=org.get("name") or company_name,
            website=website_url,
            employee_count=org.get("estimated_num_employees"),
            revenue_estimate=org.get("estimated_annual_revenue"),
            industry=org.get("industry") or org.get("industry_tag_id"),
            domain=domain,
        )

    async def get_organization_top_people(
        self,
        *,
        organization_id: str | None = None,
        organization_domain: str | None = None,
        limit: int = 5,
    ) -> list[ApolloPerson]:
        """
        Get top people at an organization using organization_top_people endpoint (FREE TIER).
        
        Works on Apollo free tier - returns names (but not emails on free plan).
        Use this to get owner/manager names, then pass to Hunter.io for email finding.
        
        Args:
            organization_id: Apollo organization ID
            organization_domain: Organization domain (alternative to ID)
            limit: Maximum number of people to return
        
        Returns:
            List of ApolloPerson objects (names and titles, but emails may be hidden)
        """
        if not organization_id and not organization_domain:
            return []

        payload = {
            "page": 1,
            "per_page": max(1, min(limit, 25)),
        }

        if organization_id:
            payload["organization_id"] = organization_id
        if organization_domain:
            payload["organization_domain"] = organization_domain

        url = f"{self.base_url}/mixed_people/organization_top_people"
        resp = await self._client.post(url, json=payload, headers=self._headers)

        if resp.status_code >= 400:
            logger.debug(f"Organization top people returned {resp.status_code}: {resp.text}")
            return []

        data = resp.json()
        people = data.get("people") or []

        out: list[ApolloPerson] = []
        for p in people:
            # Note: On free tier, emails may be hidden or return [email hidden]
            email = p.get("email")
            if email and "[email hidden]" in email.lower():
                email = None

            out.append(
                ApolloPerson(
                    full_name=p.get("name") or p.get("full_name"),
                    title=p.get("title"),
                    email=email,  # May be None on free tier
                    phone=p.get("phone") or (p.get("phone_numbers", [None])[0] if p.get("phone_numbers") else None),
                    linkedin_url=p.get("linkedin_url"),
                )
            )

        return out

    async def find_company(
        self,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
        location: str | None = None,
    ) -> ApolloCompany | None:
        """
        Find company information by name, domain, or location.
        
        DEPRECATED: Use search_organization() instead for free tier compatibility.
        This method is kept for backward compatibility.

        Args:
            company_name: Company name to search
            company_domain: Company domain (e.g., "example.com")
            location: Location string (city, state, etc.)

        Returns:
            ApolloCompany or None if not found
        """
        # Use the new search_organization endpoint for better free tier support
        if company_name:
            return await self.search_organization(company_name=company_name, location=location)

        # Fallback to old method if only domain provided
        if not company_domain:
            return None

        payload = {
            "q_organization_domains": [company_domain],
            "page": 1,
            "per_page": 1,
        }

        if location:
            payload["q_location"] = location

        url = f"{self.base_url}/mixed_people/search"
        resp = await self._client.post(url, json=payload, headers=self._headers)

        if resp.status_code >= 400:
            logger.debug(f"Company search returned {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        organizations = data.get("organizations") or data.get("companies") or []
        if not organizations:
            return None

        org = organizations[0]
        return ApolloCompany(
            name=org.get("name") or company_name or "",
            website=org.get("website_url") or org.get("website"),
            employee_count=org.get("estimated_num_employees"),
            revenue_estimate=org.get("estimated_annual_revenue"),
            industry=org.get("industry") or org.get("industry_tag_id"),
            domain=org.get("primary_domain") or company_domain,
        )

    async def find_decision_makers_enhanced(
        self,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
        location: str | None = None,
        titles: list[str] | None = None,
        limit: int = 5,
    ) -> list[ApolloPerson]:
        """
        Enhanced decision maker search with multiple strategies.

        Tries multiple search strategies and ranks results by relevance.

        Args:
            company_name: Company name
            company_domain: Company domain
            location: Location string
            titles: List of titles to search for
            limit: Maximum number of results

        Returns:
            List of ApolloPerson objects, ranked by relevance
        """
        titles = titles or [
            "Facility Director",
            "Facilities Director",
            "Facilities Manager",
            "Director of Facilities",
            "Building Manager",
            "Building Engineer",
            "Chief Engineer",
            "Property Manager",
        ]

        all_results: list[ApolloPerson] = []

        # Strategy 1: Search by company name + location + titles
        if company_name:
            try:
                results = await self.find_decision_maker(
                    company_name=company_name,
                    titles=titles,
                    location=location,
                    limit=limit * 2,  # Get more for ranking
                )
                all_results.extend(results)
            except Exception as e:
                logger.debug(f"Strategy 1 (company name) failed: {e}")

        # Strategy 2: Search by domain + titles (if domain available)
        if company_domain and company_domain not in [r.email.split("@")[-1] if r.email else None for r in all_results]:
            try:
                results = await self.find_decision_maker(
                    company_domain=company_domain,
                    titles=titles,
                    location=location,
                    limit=limit * 2,
                )
                all_results.extend(results)
            except Exception as e:
                logger.debug(f"Strategy 2 (domain) failed: {e}")

        # Deduplicate by email (if available) or name
        seen = set()
        unique_results = []
        for person in all_results:
            key = person.email or person.full_name
            if key and key not in seen:
                seen.add(key)
                unique_results.append(person)

        # Rank results by title relevance
        title_priority = {
            "facility director": 10,
            "facilities director": 10,
            "director of facilities": 10,
            "facilities manager": 8,
            "building manager": 8,
            "building engineer": 6,
            "chief engineer": 6,
            "property manager": 4,
        }

        def rank_person(person: ApolloPerson) -> float:
            score = 0.0
            if person.title:
                title_lower = person.title.lower()
                for keyword, priority in title_priority.items():
                    if keyword in title_lower:
                        score += priority
                        break

            # Bonus for verified email
            if person.email:
                score += 2.0

            # Bonus for location match (if location provided)
            if location and person.linkedin_url:  # LinkedIn often has location
                score += 1.0

            return score

        # Sort by rank (highest first)
        unique_results.sort(key=rank_person, reverse=True)

        # Return top N results
        return unique_results[:limit]


