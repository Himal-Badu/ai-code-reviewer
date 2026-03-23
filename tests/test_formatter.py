"""Tests for the output formatter."""

import pytest
import json

from src.formatter import OutputFormatter
from src.analyzer import CodeIssue


class TestOutputFormatter:
    """Test cases for OutputFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create an OutputFormatter instance."""
        return OutputFormatter()

    def test_formatter_initializes(self, formatter):
        """Test that formatter initializes correctly."""
        assert formatter is not None

    def test_to_json_with_empty_issues(self, formatter):
        """Test JSON output with no issues."""
        results = {
            "file": "test.py",
            "issues": [],
            "stats": {"files_analyzed": 1},
        }
        
        output = formatter.to_json(results)
        
        # Should be valid JSON
        parsed = json.loads(output)
        assert "file" in parsed
        assert "issues" in parsed

    def test_to_json_with_issues(self, formatter):
        """Test JSON output with issues."""
        results = {
            "file": "test.py",
            "issues": [
                CodeIssue(
                    severity="high",
                    type="security",
                    message="Test issue",
                    file="test.py",
                    line_number=5,
                )
            ],
            "stats": {"files_analyzed": 1},
        }
        
        output = formatter.to_json(results)
        
        parsed = json.loads(output)
        assert len(parsed["issues"]) == 1
        assert parsed["issues"][0]["severity"] == "high"

    def test_to_markdown_creates_header(self, formatter):
        """Test that markdown output creates a header."""
        results = {
            "file": "test.py",
            "issues": [],
            "stats": {"files_analyzed": 1, "lines_of_code": 10},
        }
        
        output = formatter.to_markdown(results, "test.py")
        
        assert "# AI Code Review" in output
        assert "test.py" in output

    def test_to_markdown_creates_summary(self, formatter):
        """Test that markdown has summary section."""
        results = {
            "file": "test.py",
            "issues": [],
            "stats": {"files_analyzed": 2, "lines_of_code": 100},
        }
        
        output = formatter.to_markdown(results, "test.py")
        
        assert "## Summary" in output
        assert "Files Analyzed:" in output
        assert "100" in output  # lines of code

    def test_to_markdown_no_issues(self, formatter):
        """Test markdown with no issues."""
        results = {
            "file": "test.py",
            "issues": [],
            "stats": {"files_analyzed": 1},
        }
        
        output = formatter.to_markdown(results, "test.py")
        
        assert "No Issues Found" in output or "✅" in output

    def test_to_markdown_with_issues(self, formatter):
        """Test markdown with issues."""
        results = {
            "file": "test.py",
            "issues": [
                CodeIssue(
                    severity="high",
                    type="security",
                    message="Hardcoded secret",
                    file="test.py",
                    line_number=5,
                    suggestion="Use env vars",
                )
            ],
            "stats": {"files_analyzed": 1},
        }
        
        output = formatter.to_markdown(results, "test.py")
        
        assert "## Issues" in output
        assert "HIGH" in output
        assert "Hardcoded secret" in output or "security" in output.lower()

    def test_to_text_format(self, formatter):
        """Test text output format."""
        results = {
            "file": "test.py",
            "issues": [
                CodeIssue(
                    severity="high",
                    type="bug",
                    message="Test issue",
                    file="test.py",
                    line_number=5,
                )
            ],
            "stats": {"files_analyzed": 1},
        }
        
        output = formatter.to_text(results)
        
        assert "AI CODE REVIEW RESULTS" in output
        assert "test.py:5" in output
        assert "HIGH" in output

    def test_to_text_summary(self, formatter):
        """Test that text output has summary."""
        results = {
            "file": "test.py",
            "issues": [],
            "stats": {"files_analyzed": 3, "lines_of_code": 150},
        }
        
        output = formatter.to_text(results)
        
        assert "Files Analyzed: 3" in output
        assert "Lines of Code: 150" in output