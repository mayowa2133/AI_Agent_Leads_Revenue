"""Base class for regulatory listeners."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime

from src.signal_engine.models import RegulatoryUpdate


class BaseRegulatoryListener(ABC):
    """
    Base class for all regulatory listeners.
    
    Similar to BaseScraper, provides retry logic and common functionality
    for monitoring regulatory updates from various sources.
    """

    source: str

    def __init__(self, *, max_retries: int = 3, base_delay_s: float = 1.0):
        """
        Initialize regulatory listener.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay_s: Base delay between retries (exponential backoff)
        """
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s

    @abstractmethod
    async def check_for_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """
        Check for new regulatory updates since last run.
        
        Args:
            last_run: Last run timestamp (None for first run)
            
        Returns:
            List of new RegulatoryUpdate objects
        """

    async def _with_retries(self, coro_fn, *args, **kwargs):
        """
        Execute coroutine with retry logic and exponential backoff.
        
        Args:
            coro_fn: Coroutine function to execute
            *args: Positional arguments for coro_fn
            **kwargs: Keyword arguments for coro_fn
            
        Returns:
            Result of coro_fn
            
        Raises:
            Exception: If all retries fail
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == self.max_retries:
                    break
                delay = self.base_delay_s * (2 ** (attempt - 1))
                logger.warning(
                    f"{self.source}: Attempt {attempt} failed, retrying in {delay}s: {exc}"
                )
                await asyncio.sleep(delay)

        raise RuntimeError(f"{self.source}: failed after {self.max_retries} retries") from last_exc


# Import logger at module level
import logging

logger = logging.getLogger(__name__)

