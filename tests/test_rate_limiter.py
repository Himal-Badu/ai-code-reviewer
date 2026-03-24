"""Tests for the rate limiter module."""

import pytest
import time
from src.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with low limits for testing."""
        return RateLimiter(max_calls=5, period_seconds=2)
    
    def test_limiter_initializes(self, limiter):
        """Test that limiter initializes correctly."""
        assert limiter is not None
        assert limiter.max_calls == 5
        assert limiter.period == 2
    
    def test_acquire_slot(self, limiter):
        """Test acquiring a slot."""
        result = limiter.acquire()
        assert result is True
    
    def test_rate_limit_reached(self, limiter):
        """Test that rate limit is enforced."""
        # Use up all slots
        for _ in range(5):
            assert limiter.acquire() is True
        
        # Next call should fail
        assert limiter.acquire() is False
    
    def test_wait_and_acquire(self):
        """Test wait and acquire functionality."""
        limiter = RateLimiter(max_calls=2, period_seconds=1)
        
        # Use up slots
        limiter.acquire()
        limiter.acquire()
        
        # Should wait and then acquire when period expires
        result = limiter.wait_and_acquire(max_wait=3)
        assert result is True
    
    def test_get_remaining(self, limiter):
        """Test getting remaining slots."""
        limiter.acquire()
        remaining = limiter.get_remaining()
        assert remaining == 4
    
    def test_reset(self, limiter):
        """Test resetting the limiter."""
        # Use up some slots
        limiter.acquire()
        limiter.acquire()
        
        # Reset
        limiter.reset()
        
        # Should have full capacity again
        assert limiter.get_remaining() == 5
    
    def test_stats(self, limiter):
        """Test getting limiter statistics."""
        limiter.acquire()
        
        stats = limiter.get_stats()
        
        assert stats["max_calls"] == 5
        assert stats["period_seconds"] == 2
        assert stats["current_calls"] == 1
        assert stats["remaining"] == 4
    
    def test_window_expiration(self):
        """Test that calls expire after the window."""
        limiter = RateLimiter(max_calls=2, period_seconds=1)
        
        limiter.acquire()
        limiter.acquire()
        
        # Wait for window to expire
        time.sleep(1.5)
        
        # Should be able to acquire again
        assert limiter.acquire() is True
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        import threading
        
        limiter = RateLimiter(max_calls=10, period_seconds=1)
        results = []
        
        def make_call():
            result = limiter.acquire()
            results.append(result)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_call) for _ in range(20)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have exactly 10 successful calls
        assert sum(results) == 10