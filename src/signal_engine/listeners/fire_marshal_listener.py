"""State Fire Marshal bulletin listener."""

from __future__ import annotations

import logging
from datetime import datetime

from src.signal_engine.listeners.base_listener import BaseRegulatoryListener
from src.signal_engine.listeners.rss_parser import RSSFeedParser
from src.signal_engine.models import RegulatoryUpdate

logger = logging.getLogger(__name__)


class FireMarshalListener(BaseRegulatoryListener):
    """
    Listener for state fire marshal bulletins.
    
    Supports RSS feeds and can be extended for web scraping.
    Starts with 1-2 states (Texas, North Carolina) as MVP.
    """

    source = "state_fire_marshal"

    def __init__(
        self,
        *,
        feed_url: str | None = None,
        state: str = "Texas",
        max_retries: int = 3,
        base_delay_s: float = 1.0,
    ):
        """
        Initialize state fire marshal listener.
        
        Args:
            feed_url: RSS feed URL (if None, will use default for state)
            state: State name (e.g., "Texas", "North Carolina")
            max_retries: Maximum retry attempts
            base_delay_s: Base delay between retries
        """
        super().__init__(max_retries=max_retries, base_delay_s=base_delay_s)
        self.state = state
        self.feed_url = feed_url or self._get_default_feed_url(state)
        self.rss_parser = RSSFeedParser(max_retries=max_retries, base_delay_s=base_delay_s)

    def _get_default_feed_url(self, state: str) -> str:
        """
        Get default RSS feed URL for a state.
        
        Args:
            state: State name
            
        Returns:
            RSS feed URL (placeholder - actual URLs need to be configured)
        """
        # Common patterns for state fire marshal RSS feeds
        # These are placeholders - actual URLs should be configured per state
        state_lower = state.lower().replace(" ", "_")
        
        # Example patterns (actual URLs need to be discovered/configured):
        # - https://[state].gov/fire-marshal/rss
        # - https://[state]firemarshal.gov/news/rss
        # - https://[state].gov/dps/fire/rss.xml
        
        # For MVP, return a placeholder that will need configuration
        logger.warning(
            f"No feed URL configured for {state}. "
            "Please set REGULATORY_RSS_FEEDS environment variable or provide feed_url."
        )
        return f"https://example.com/{state_lower}-fire-marshal/rss"  # Placeholder

    async def check_for_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """
        Check for new fire marshal bulletins since last run.
        
        Args:
            last_run: Last run timestamp (None for first run)
            
        Returns:
            List of new RegulatoryUpdate objects
        """
        return await self._with_retries(self._fetch_updates, last_run)

    async def _fetch_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """Internal method to fetch updates from RSS feed."""
        # Parse RSS feed
        updates = self.rss_parser.parse_feed(
            feed_url=self.feed_url,
            source=self.source,
            source_name=f"{self.state} State Fire Marshal",
            jurisdiction=self.state,
            last_run=last_run,
        )

        logger.info(f"Found {len(updates)} new updates from {self.state} Fire Marshal")
        return updates


def texas_fire_marshal_listener(feed_url: str | None = None) -> FireMarshalListener:
    """
    Factory for Texas State Fire Marshal listener.
    
    Args:
        feed_url: Optional RSS feed URL (if None, uses default)
        
    Returns:
        FireMarshalListener configured for Texas
    """
    return FireMarshalListener(feed_url=feed_url, state="Texas")


def north_carolina_fire_marshal_listener(
    feed_url: str | None = None,
) -> FireMarshalListener:
    """
    Factory for North Carolina State Fire Marshal listener.
    
    Args:
        feed_url: Optional RSS feed URL (if None, uses default)
        
    Returns:
        FireMarshalListener configured for North Carolina
    """
    return FireMarshalListener(feed_url=feed_url, state="North Carolina")

