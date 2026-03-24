"""Rate limiting for AI API calls."""

import time
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int = 100, period_seconds: int = 60):
        """Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period_seconds: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = []
        self.lock = Lock()
        logger.debug(f"Rate limiter initialized: {max_calls} calls per {period_seconds}s")
    
    def acquire(self) -> bool:
        """Try to acquire a rate limit slot.
        
        Returns:
            True if slot acquired, False if rate limited
        """
        with self.lock:
            now = time.time()
            
            # Remove old calls outside the window
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) >= self.max_calls:
                logger.warning(f"Rate limit reached: {len(self.calls)} calls in {self.period}s")
                return False
            
            self.calls.append(now)
            return True
    
    def wait_and_acquire(self, max_wait: float = 60.0) -> bool:
        """Wait for a rate limit slot if necessary.
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if slot acquired, False if max wait exceeded
        """
        start = time.time()
        
        while True:
            if self.acquire():
                return True
            
            if time.time() - start > max_wait:
                logger.error(f"Rate limit wait exceeded: {max_wait}s")
                return False
            
            # Wait a bit before retrying
            time.sleep(0.5)
    
    def get_remaining(self) -> int:
        """Get the number of remaining calls in current window.
        
        Returns:
            Number of remaining calls
        """
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            return max(0, self.max_calls - len(self.calls))
    
    def get_reset_time(self) -> Optional[float]:
        """Get time until rate limit resets.
        
        Returns:
            Seconds until reset, or None if not rate limited
        """
        with self.lock:
            if not self.calls:
                return None
            
            now = time.time()
            oldest = min(self.calls)
            return max(0, self.period - (now - oldest))
    
    def reset(self):
        """Reset the rate limiter."""
        with self.lock:
            self.calls = []
            logger.info("Rate limiter reset")
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            now = time.time()
            active_calls = [t for t in self.calls if now - t < self.period]
            
            return {
                "max_calls": self.max_calls,
                "period_seconds": self.period,
                "current_calls": len(active_calls),
                "remaining": self.get_remaining(),
            }