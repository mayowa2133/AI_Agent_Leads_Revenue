"""RSS/Atom feed parser for regulatory updates."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import feedparser

from src.signal_engine.models import RegulatoryUpdate

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class RSSFeedParser:
    """
    Parser for RSS and Atom feeds.
    
    Handles parsing of feed entries and filtering by date to support
    incremental updates.
    """

    def __init__(self, *, max_retries: int = 3, base_delay_s: float = 1.0):
        """
        Initialize RSS feed parser.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay_s: Base delay between retries (exponential backoff)
        """
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s

    def parse_feed(
        self,
        feed_url: str,
        source: str,
        source_name: str,
        jurisdiction: str | None = None,
        *,
        last_run: datetime | None = None,
    ) -> list[RegulatoryUpdate]:
        """
        Parse RSS/Atom feed and extract regulatory updates.
        
        Args:
            feed_url: URL of the RSS/Atom feed
            source: Source identifier (e.g., "state_fire_marshal")
            source_name: Human-readable source name
            jurisdiction: Jurisdiction (state, federal, etc.)
            last_run: Only process entries published after this date
            
        Returns:
            List of RegulatoryUpdate objects
        """
        updates: list[RegulatoryUpdate] = []

        try:
            # Parse feed
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed parsing issues for {feed_url}: {feed.bozo_exception}")

            # Process entries
            for entry in feed.entries:
                try:
                    update = self._parse_entry(entry, source, source_name, jurisdiction, feed_url)
                    if update:
                        # Filter by date if last_run is provided
                        if last_run and update.published_date <= last_run:
                            continue
                        updates.append(update)
                except Exception as e:
                    logger.warning(f"Error parsing feed entry: {e}")
                    continue

            logger.info(f"Parsed {len(updates)} updates from {feed_url}")

        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}", exc_info=True)
            raise

        return updates

    def _parse_entry(
        self,
        entry: feedparser.FeedParserDict,
        source: str,
        source_name: str,
        jurisdiction: str | None,
        feed_url: str,
    ) -> RegulatoryUpdate | None:
        """
        Parse a single feed entry into a RegulatoryUpdate.
        
        Args:
            entry: Feed entry from feedparser
            source: Source identifier
            source_name: Human-readable source name
            jurisdiction: Jurisdiction
            feed_url: Original feed URL
            
        Returns:
            RegulatoryUpdate or None if parsing fails
        """
        # Extract title
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Extract content (prefer summary, fallback to description)
        content = entry.get("summary", "") or entry.get("description", "") or ""
        # Clean HTML tags if present
        if content:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text(separator=" ", strip=True)

        # Extract published date
        published_date = self._parse_date(entry.get("published_parsed") or entry.get("updated_parsed"))
        if not published_date:
            # If no date, skip entry (can't determine if it's new)
            logger.warning(f"Skipping entry '{title}' - no published date")
            return None

        # Extract URL (prefer link, fallback to id)
        url = entry.get("link", "") or entry.get("id", "")
        if not url:
            logger.warning(f"Skipping entry '{title}' - no URL")
            return None

        # Generate unique ID (hash of source + title + url)
        update_id = self._generate_update_id(source, title, url)

        # Extract effective date if available (some feeds include this)
        effective_date = None
        if "effective_date" in entry:
            effective_date = self._parse_date(entry.get("effective_date"))

        return RegulatoryUpdate(
            update_id=update_id,
            source=source,
            source_name=source_name,
            title=title,
            content=content,
            published_date=published_date,
            effective_date=effective_date,
            url=url,
            jurisdiction=jurisdiction,
            applicable_codes=[],  # Will be populated by content processor
            compliance_triggers=[],  # Will be populated by content processor
            building_types_affected=[],  # Will be populated by content processor
        )

    def _parse_date(self, date_tuple: tuple | None) -> datetime | None:
        """
        Parse date tuple from feedparser into datetime.
        
        Args:
            date_tuple: Time tuple from feedparser (9-tuple)
            
        Returns:
            datetime or None if parsing fails
        """
        if not date_tuple:
            return None

        try:
            # feedparser returns 9-tuple: (year, month, day, hour, minute, second, weekday, yearday, isdst)
            import time

            timestamp = time.mktime(date_tuple[:6] + (0, 0, 0))
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception as e:
            logger.warning(f"Error parsing date tuple: {e}")
            return None

    def _generate_update_id(self, source: str, title: str, url: str) -> str:
        """
        Generate unique ID for regulatory update.
        
        Args:
            source: Source identifier
            title: Update title
            url: Update URL
            
        Returns:
            Unique hash-based ID
        """
        # Create hash from source + title + url
        content = f"{source}:{title}:{url}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

