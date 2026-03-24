"""Caching mechanism for AI code analysis results."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from src.models import CodeIssue

logger = logging.getLogger(__name__)


class AnalysisCache:
    """Cache for storing and retrieving analysis results."""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        """Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "ai-code-reviewer"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
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
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Could not read file for cache key: {e}")
            return file_path.name
    
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
    
    def clear(self):
        """Clear all cached entries."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear cache: {e}")
    
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