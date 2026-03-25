"""
Test suite for AI Code Reviewer.

This module contains comprehensive tests for all components.
"""

import pytest
from pathlib import Path
import tempfile
import os
from src.scanner import CodeScanner
from src.reporter import ReportGenerator
from src.config import Config
from src.cache import Cache


class TestScanner:
    """Tests for CodeScanner."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_scanner_init(self):
        """Test scanner initialization."""
        scanner = CodeScanner()
        assert scanner is not None
    
    def test_scanner_scan_empty(self, temp_dir):
        """Test scanning empty directory."""
        scanner = CodeScanner()
        result = scanner.scan(str(temp_dir))
        assert 'issues' in result
    
    def test_scanner_with_file(self, temp_dir):
        """Test scanning directory with file."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')\n")
        
        scanner = CodeScanner()
        result = scanner.scan(str(temp_dir))
        assert result is not None


class TestReporter:
    """Tests for ReportGenerator."""
    
    @pytest.fixture
    def sample_results(self):
        """Sample results for testing."""
        return {
            'issues': {
                'critical': [],
                'warning': ['Use f-string instead of % formatting'],
                'info': ['Consider adding type hints']
            },
            'security': {
                'issues': []
            },
            'ai_analysis': {
                'summary': 'Code looks good'
            }
        }
    
    def test_reporter_text_format(self, sample_results):
        """Test text format output."""
        generator = ReportGenerator()
        report = generator.generate(sample_results, format='text')
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_reporter_json_format(self, sample_results):
        """Test JSON format output."""
        generator = ReportGenerator()
        report = generator.generate(sample_results, format='json')
        assert isinstance(report, str)
    
    def test_reporter_markdown_format(self, sample_results):
        """Test markdown format output."""
        generator = ReportGenerator()
        report = generator.generate(sample_results, format='markdown')
        assert isinstance(report, str)
        assert '#' in report


class TestConfig:
    """Tests for Config."""
    
    def test_config_init(self):
        """Test config initialization."""
        config = Config()
        assert config is not None
    
    def test_config_get(self):
        """Test config get method."""
        config = Config()
        version = config.get('version')
        assert version is not None
    
    def test_config_set(self):
        """Test config set method."""
        config = Config()
        config.set('test_key', 'test_value')
        assert config.get('test_key') == 'test_value'


class TestCache:
    """Tests for Cache."""
    
    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_cache_init(self, cache_dir):
        """Test cache initialization."""
        cache = Cache(cache_dir=str(cache_dir))
        assert cache is not None
    
    def test_cache_set_get(self, cache_dir):
        """Test cache set and get."""
        cache = Cache(cache_dir=str(cache_dir))
        cache.set('test_key', {'data': 'test_value'})
        result = cache.get('test_key')
        assert result is not None
    
    def test_cache_delete(self, cache_dir):
        """Test cache delete."""
        cache = Cache(cache_dir=str(cache_dir))
        cache.set('test_key', 'test_value')
        cache.delete('test_key')
        result = cache.get('test_key')
        assert result is None
    
    def test_cache_clear(self, cache_dir):
        """Test cache clear."""
        cache = Cache(cache_dir=str(cache_dir))
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.clear()
        assert cache.size() == 0


class TestCLI:
    """Tests for CLI commands."""
    
    def test_cli_help(self):
        """Test CLI help."""
        from src.cli import cli
        # This would need click testing framework
        assert cli is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])