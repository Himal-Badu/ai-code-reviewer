"""Caching module for AI Code Reviewer."""

import hashlib
import json
from pathlib import Path
from typing import Any, Optional
import time


class Cache:
    """Simple file-based cache for code review results."""
    
    def __init__(self, cache_dir: str = None, ttl: int = 3600):
        self.cache_dir = cache_dir or Path.home() / ".ai-code-reviewer" / "cache"
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, data: str) -> str:
        """Generate cache key from data."""
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path) as f:
                cached = json.load(f)
            
            # Check TTL
            if time.time() - cached.get('timestamp', 0) > self.ttl:
                cache_path.unlink()
                return None
            
            return cached.get('data')
        except Exception:
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        cache_path = self._get_cache_path(key)
        cached = {
            'timestamp': time.time(),
            'data': value
        }
        with open(cache_path, 'w') as f:
            json.dump(cached, f)
    
    def delete(self, key: str) -> None:
        """Delete cached value."""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
    
    def clear(self) -> None:
        """Clear all cache."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def size(self) -> int:
        """Get cache size in bytes."""
        return sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
    
    def cleanup(self) -> int:
        """Remove expired cache entries."""
        count = 0
        current_time = time.time()
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    cached = json.load(f)
                if current_time - cached.get('timestamp', 0) > self.ttl:
                    cache_file.unlink()
                    count += 1
            except Exception:
                pass
        return count


# Global cache instance
_cache = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache