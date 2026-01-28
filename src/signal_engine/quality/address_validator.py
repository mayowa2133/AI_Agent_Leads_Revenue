"""Address validation and normalization."""

from __future__ import annotations

from dataclasses import dataclass

from src.signal_engine.enrichment.geocoder import GeocodeResult, geocode_address


@dataclass
class AddressValidationResult:
    """Result of address validation."""

    is_valid: bool
    normalized_address: str | None = None
    geocode_result: GeocodeResult | None = None
    error: str | None = None


class AddressValidator:
    """
    Validate and normalize addresses before enrichment.
    
    This helps filter out invalid addresses early and ensures
    we have geocodable addresses for location-based matching.
    """

    async def validate(self, address: str) -> AddressValidationResult:
        """
        Validate address and return normalized version.
        
        Args:
            address: Address string to validate
        
        Returns:
            AddressValidationResult with validation status and normalized address
        """
        if not address or len(address.strip()) < 5:
            return AddressValidationResult(
                is_valid=False,
                error="Address too short",
            )

        # Try geocoding to validate
        try:
            geocode_result = await geocode_address(address)
            
            if geocode_result and geocode_result.city:
                return AddressValidationResult(
                    is_valid=True,
                    normalized_address=geocode_result.formatted_address,
                    geocode_result=geocode_result,
                )
            else:
                return AddressValidationResult(
                    is_valid=False,
                    error="Address could not be geocoded",
                )
        except Exception as e:
            return AddressValidationResult(
                is_valid=False,
                error=f"Geocoding error: {str(e)}",
            )

    def is_valid_format(self, address: str) -> bool:
        """
        Quick format check without API call.
        
        Args:
            address: Address to check
        
        Returns:
            True if address format looks valid
        """
        if not address or len(address.strip()) < 10:
            return False
        
        # Should have numbers (street number)
        has_number = any(c.isdigit() for c in address)
        
        # Should have letters (street name)
        has_letters = any(c.isalpha() for c in address)
        
        # Should not be just a description
        is_description = any(
            word in address.lower()
            for word in ["ft", "feet", "tunnel", "area", "zone", "section", "description"]
        )
        
        return has_number and has_letters and not is_description
