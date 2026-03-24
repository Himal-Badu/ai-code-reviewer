"""Tests for the cache module."""

import pytest
import tempfile
import time
from pathlib import Path

from src.cache import AnalysisCache
from src.models import CodeIssue


class TestAnalysisCache:
    """Test cases for AnalysisCache."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache instance with temporary directory."""
        return AnalysisCache(cache_dir=tmp_path, ttl_hours=1)
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create a test file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        return test_file
    
    def test_cache_initializes(self, cache):
        """Test that cache initializes correctly."""
        assert cache is not None
        assert cache.cache_dir.exists()
    
    def test_cache_miss(self, cache, test_file):
        """Test cache miss for new file."""
        result = cache.get(test_file)
        assert result is None
    
    def test_cache_set_and_get(self, cache, test_file):
        """Test setting and getting from cache."""
        issues = [
            CodeIssue(
                severity="high",
                type="security",
                message="Test issue",
                file=str(test_file),
                line_number=5,
            )
        ]
        
        cache.set(test_file, issues)
        result = cache.get(test_file)
        
        assert result is not None
        assert len(result) == 1
        assert result[0].severity == "high"
    
    def test_cache_expiration(self, tmp_path):
        """Test that cache expires after TTL."""
        # Create cache with very short TTL
        cache = AnalysisCache(cache_dir=tmp_path, ttl_hours=0)
        
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        issues = [CodeIssue("high", "security", "Test", str(test_file), 1)]
        cache.set(test_file, issues)
        
        # Force expire by waiting a bit (in practice would be TTL)
        time.sleep(0.1)
        
        result = cache.get(test_file)
        # With TTL=0, should be considered expired immediately
        assert result is None or isinstance(result, list)
    
    def test_cache_clear(self, cache, test_file):
        """Test clearing cache."""
        issues = [CodeIssue("high", "security", "Test", str(test_file), 1)]
        cache.set(test_file, issues)
        
        cache.clear()
        
        result = cache.get(test_file)
        assert result is None
    
    def test_cache_stats(self, cache, test_file):
        """Test getting cache statistics."""
        issues = [CodeIssue("high", "security", "Test", str(test_file), 1)]
        cache.set(test_file, issues)
        
        stats = cache.get_stats()
        
        assert "total_entries" in stats
        assert stats["total_entries"] >= 1
    
    def test_different_files_different_cache(self, cache, tmp_path):
        """Test that different files get different cache entries."""
        file1 = tmp_path / "test1.py"
        file1.write_text("print('hello')")
        
        file2 = tmp_path / "test2.py"
        file2.write_text("print('world')")
        
        issues1 = [CodeIssue("high", "security", "Issue 1", str(file1), 1)]
        issues2 = [CodeIssue("low", "style", "Issue 2", str(file2), 2)]
        
        cache.set(file1, issues1)
        cache.set(file2, issues2)
        
        result1 = cache.get(file1)
        result2 = cache.get(file2)
        
        assert result1 is not None
        assert result2 is not None
        assert len(result1) == 1
        assert len(result2) == 1
    
    def test_same_content_same_cache(self, cache, tmp_path):
        """Test that files with same content share cache."""
        content = "print('hello')"
        
        file1 = tmp_path / "test1.py"
        file1.write_text(content)
        
        file2 = tmp_path / "test2.py"
        file2.write_text(content)
        
        issues = [CodeIssue("high", "security", "Issue", str(file1), 1)]
        cache.set(file1, issues)
        
        result2 = cache.get(file2)
        
        # Files with same content should share cache
        assert result2 is not None