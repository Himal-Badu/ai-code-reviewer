"""Caching mechanism for AI code analysis results.

This module provides disk-based caching for code analysis results to improve
performance and reduce API calls. It supports TTL (time-to-live) expiration,
cache statistics, and selective clearing.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta

from src.models import CodeIssue

logger = logging.getLogger(__name__)


class AnalysisCache:
    """Cache for storing and retrieving analysis results."""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24, 
                 max_size_mb: int = 100):
        """Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "ai-code-reviewer"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._memory_cache: Dict[str, List[CodeIssue]] = {}
        logger.debug(f"Cache initialized at {self.cache_dir} with TTL: {ttl_hours}h")
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate a cache key from file path and content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cache key string
        """
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            # Include file path in hash to handle same content in different files
            path_bytes = str(file_path).encode()
            combined = content + path_bytes
            return hashlib.sha256(combined).hexdigest()
        except Exception as e:
            logger.warning(f"Could not read file for cache key: {e}")
            return file_path.name
    
    def get_or_compute(self, file_path: Path, 
                       compute_fn: callable) -> List[CodeIssue]:
        """Get cached result or compute and cache it.
        
        Args:
            file_path: Path to the file
            compute_fn: Function to compute results if not cached
            
        Returns:
            List of issues
        """
        # Check memory cache first
        cache_key = self._get_cache_key(file_path)
        if cache_key in self._memory_cache:
            logger.debug(f"Memory cache hit for {file_path}")
            return self._memory_cache[cache_key]
        
        # Check disk cache
        cached = self.get(file_path)
        if cached is not None:
            self._memory_cache[cache_key] = cached
            return cached
        
        # Compute fresh results
        logger.debug(f"Computing fresh results for {file_path}")
        issues = compute_fn()
        
        # Cache the results
        self.set(file_path, issues)
        self._memory_cache[cache_key] = issues
        
        return issues
    
    def invalidate(self, file_path: Path):
        """Invalidate cache for a specific file.
        
        Args:
            file_path: Path to the file
        """
        cache_key = self._get_cache_key(file_path)
        
        # Remove from memory cache
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
        
        # Remove from disk cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Invalidated cache for {file_path}")
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the path to a cache file.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, file_path: Path) -> Optional[List[CodeIssue]]:
        """Get cached analysis results for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached issues or None if not found/expired
        """
        cache_key = self._get_cache_key(file_path)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            logger.debug(f"Cache miss for {file_path}")
            return None
        
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_time > self.ttl:
                logger.debug(f"Cache expired for {file_path}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit for {file_path}")
            # Convert back to CodeIssue objects
            issues = []
            for item in data.get("issues", []):
                issues.append(CodeIssue(
                    severity=item.get("severity", "medium"),
                    type=item.get("type", "unknown"),
                    message=item.get("message", ""),
                    file=item.get("file", ""),
                    line_number=item.get("line_number", 0),
                    suggestion=item.get("suggestion"),
                ))
            return issues
            
        except Exception as e:
            logger.warning(f"Could not read cache: {e}")
            return None
    
    def set(self, file_path: Path, issues: List[CodeIssue]):
        """Store analysis results in cache.
        
        Args:
            file_path: Path to the file
            issues: List of issues to cache
        """
        cache_key = self._get_cache_key(file_path)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            data = {
                "cached_at": datetime.now().isoformat(),
                "file": str(file_path),
                "issues": [
                    {
                        "severity": issue.severity,
                        "type": issue.type,
                        "message": issue.message,
                        "file": issue.file,
                        "line_number": issue.line_number,
                        "suggestion": issue.suggestion,
                    }
                    for issue in issues
                ]
            }
            
            with open(cache_path, "w") as f:
                json.dump(data, f)
            
            logger.debug(f"Cached {len(issues)} issues for {file_path}")
            
        except Exception as e:
            logger.warning(f"Could not write cache: {e}")
    
    def clear(self, older_than_hours: Optional[int] = None):
        """Clear cached entries.
        
        Args:
            older_than_hours: If specified, only clear entries older than this many hours.
                            If None, clear all entries.
        """
        try:
            cutoff = None
            if older_than_hours:
                cutoff = datetime.now() - timedelta(hours=older_than_hours)
            
            cleared = 0
            for cache_file in self.cache_dir.glob("*.json"):
                if cutoff:
                    try:
                        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                        if mtime > cutoff:
                            continue
                    except Exception:
                        pass
                
                cache_file.unlink()
                cleared += 1
            
            # Clear memory cache
            self._memory_cache.clear()
            
            logger.info(f"Cache cleared: {cleared} entries")
            
        except Exception as e:
            logger.warning(f"Could not clear cache: {e}")
    
    def cleanup(self):
        """Clean up expired and excess cache entries."""
        try:
            # Remove expired entries
            expired = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    cached_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                    if datetime.now() - cached_time > self.ttl:
                        cache_file.unlink()
                        expired += 1
                except Exception:
                    pass
            
            # Check size and remove oldest if needed
            files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime
            )
            
            total_size = sum(f.stat().st_size for f in files)
            removed = 0
            
            while total_size > self.max_size_bytes and files:
                oldest = files.pop(0)
                total_size -= oldest.stat().st_size
                oldest.unlink()
                removed += 1
            
            if expired or removed:
                logger.info(f"Cache cleanup: {expired} expired, {removed} removed for size")
                
        except Exception as e:
            logger.warning(f"Could not cleanup cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            # Check for expired entries
            expired = 0
            for cache_file in files:
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    cached_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                    if datetime.now() - cached_time > self.ttl:
                        expired += 1
                except Exception:
                    pass
            
            return {
                "total_entries": len(files),
                "total_size_bytes": total_size,
                "expired_entries": expired,
                "cache_dir": str(self.cache_dir),
            }
        except Exception as e:
            logger.warning(f"Could not get cache stats: {e}")
            return {"error": str(e)}