"""Geocoding service for converting addresses to coordinates and jurisdiction information."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeocodeResult:
    """Result of geocoding an address."""

    latitude: float
    longitude: float
    formatted_address: str
    city: str | None = None
    county: str | None = None
    state: str | None = None
    country: str | None = None
    raw_data: dict | None = None  # Store raw API response for debugging


class GeocodingError(RuntimeError):
    """Error during geocoding operation."""

    pass


class Geocoder:
    """
    Geocoding service using Nominatim (OpenStreetMap) API.

    Free, no API key required, but has rate limits (1 request/second recommended).
    Implements caching to reduce API calls.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://nominatim.openstreetmap.org",
        timeout_s: float = 10.0,
        cache_file: Path | str | None = None,
        cache_enabled: bool = True,
        user_agent: str = "AORO-Enrichment/1.0",
    ):
        """
        Initialize geocoder.

        Args:
            base_url: Nominatim API base URL
            timeout_s: Request timeout in seconds
            cache_file: Path to cache file (default: data/geocoding_cache.json)
            cache_enabled: Enable caching of results
            user_agent: User agent string (required by Nominatim)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.cache_enabled = cache_enabled

        if cache_file is None:
            cache_file = Path("data/geocoding_cache.json")
        elif isinstance(cache_file, str):
            cache_file = Path(cache_file)

        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        self._client = httpx.AsyncClient(
            timeout=timeout_s,
            headers={"User-Agent": user_agent},
        )
        self._cache: dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        if not self.cache_enabled or not self.cache_file.exists():
            return

        try:
            content = self.cache_file.read_text()
            self._cache = json.loads(content)
            logger.debug(f"Loaded {len(self._cache)} geocoding results from cache")
        except Exception as e:
            logger.warning(f"Failed to load geocoding cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        if not self.cache_enabled:
            return

        try:
            self.cache_file.write_text(json.dumps(self._cache, indent=2))
            logger.debug(f"Saved {len(self._cache)} geocoding results to cache")
        except Exception as e:
            logger.warning(f"Failed to save geocoding cache: {e}")

    async def aclose(self) -> None:
        """Close HTTP client and save cache."""
        await self._client.aclose()
        self._save_cache()

    async def geocode(self, address: str) -> GeocodeResult:
        """
        Geocode an address to coordinates and jurisdiction information.

        Args:
            address: Address string to geocode

        Returns:
            GeocodeResult with coordinates and jurisdiction info

        Raises:
            GeocodingError: If geocoding fails
        """
        # Normalize address (strip whitespace, etc.)
        address = address.strip()

        # Check cache first
        if self.cache_enabled and address in self._cache:
            cached = self._cache[address]
            logger.debug(f"Using cached geocoding result for: {address[:50]}")
            return GeocodeResult(**cached)

        try:
            # Call Nominatim API
            url = f"{self.base_url}/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,  # Include detailed address components
            }

            resp = await self._client.get(url, params=params)

            if resp.status_code >= 400:
                raise GeocodingError(f"Geocoding API error {resp.status_code}: {resp.text}")

            data = resp.json()

            if not data:
                raise GeocodingError(f"No results found for address: {address}")

            # Parse first result
            result = data[0]
            lat = float(result.get("lat", 0))
            lon = float(result.get("lon", 0))
            formatted = result.get("display_name", address)

            # Extract address components
            address_parts = result.get("address", {})
            city = (
                address_parts.get("city")
                or address_parts.get("town")
                or address_parts.get("village")
                or address_parts.get("municipality")
            )
            county = address_parts.get("county") or address_parts.get("state_district")
            state = address_parts.get("state") or address_parts.get("region")
            country = address_parts.get("country")

            geocode_result = GeocodeResult(
                latitude=lat,
                longitude=lon,
                formatted_address=formatted,
                city=city,
                county=county,
                state=state,
                country=country,
                raw_data=result,
            )

            # Cache result
            if self.cache_enabled:
                self._cache[address] = {
                    "latitude": lat,
                    "longitude": lon,
                    "formatted_address": formatted,
                    "city": city,
                    "county": county,
                    "state": state,
                    "country": country,
                }

            return geocode_result

        except httpx.HTTPError as e:
            raise GeocodingError(f"HTTP error during geocoding: {e}") from e
        except (KeyError, ValueError, TypeError) as e:
            raise GeocodingError(f"Failed to parse geocoding response: {e}") from e
        except Exception as e:
            raise GeocodingError(f"Unexpected error during geocoding: {e}") from e


# Global geocoder instance (lazy initialization)
_geocoder: Geocoder | None = None


async def geocode_address(address: str) -> GeocodeResult:
    """
    Convenience function to geocode an address using the global geocoder.

    Args:
        address: Address string to geocode

    Returns:
        GeocodeResult with coordinates and jurisdiction info
    """
    global _geocoder

    if _geocoder is None:
        from src.core.config import get_settings

        settings = get_settings()
        _geocoder = Geocoder(
            cache_enabled=settings.enrichment_cache_enabled,
        )

    return await _geocoder.geocode(address)


async def close_geocoder() -> None:
    """Close the global geocoder and save cache."""
    global _geocoder
    if _geocoder is not None:
        await _geocoder.aclose()
        _geocoder = None

