"""Tests for the output formatter."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.formatter import OutputFormatter
from src.models import CodeIssue, AnalysisResult


class TestOutputFormatter:
    """Test cases for OutputFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create an OutputFormatter instance."""
        return OutputFormatter()

    @pytest.fixture
    def sample_issues(self):
        """Create sample issues for testing."""
        return [
            CodeIssue(
                severity="critical",
                type="security",
                message="Hardcoded password detected",
                file="test.py",
                line_number=10,
                suggestion="Use environment variables",
                cwe_id="CWE-798",
            ),
            CodeIssue(
                severity="high",
                type="security",
                message="SQL injection vulnerability",
                file="app.py",
                line_number=25,
                suggestion="Use parameterized queries",
                cwe_id="CWE-89",
            ),
            CodeIssue(
                severity="medium",
                type="code_smell",
                message="Empty except block",
                file="utils.py",
                line_number=50,
                suggestion="Add error handling",
            ),
            CodeIssue(
                severity="low",
                type="style",
                message="Unused import",
                file="main.py",
                line_number=5,
                suggestion="Remove unused import",
            ),
        ]

    @pytest.fixture
    def sample_results(self, sample_issues):
        """Create sample results for testing."""
        return {
            "issues": sample_issues,
            "stats": {
                "files_analyzed": 5,
                "lines_of_code": 1500,
            },
            "path": "/test/project",
        }

    def test_formatter_initialization(self, formatter):
        """Test formatter can be initialized."""
        assert formatter is not None

    def test_to_json(self, formatter, sample_results):
        """Test JSON output format."""
        json_output = formatter.to_json(sample_results)
        
        assert isinstance(json_output, str)
        
        # Should be valid JSON
        data = json.loads(json_output)
        assert "issues" in data
        assert "stats" in data

    def test_to_json_includes_metadata(self, formatter, sample_results):
        """Test that JSON includes metadata."""
        json_output = formatter.to_json(sample_results)
        
        data = json.loads(json_output)
        assert "metadata" in data
        assert "generated_at" in data["metadata"]
        assert "formatter_version" in data["metadata"]

    def test_to_json_without_metadata(self):
        """Test JSON output without metadata."""
        formatter = OutputFormatter(include_metadata=False)
        results = {"issues": [], "stats": {}}
        
        json_output = formatter.to_json(results)
        
        data = json.loads(json_output)
        assert "metadata" not in data

    def test_to_text(self, formatter, sample_results):
        """Test text output format."""
        text_output = formatter.to_text(sample_results)
        
        assert isinstance(text_output, str)
        assert "AI CODE REVIEW RESULTS" in text_output
        assert "Files Analyzed: 5" in text_output

    def test_to_text_groups_by_severity(self, formatter, sample_results):
        """Test that text output groups issues by severity."""
        text_output = formatter.to_text(sample_results)
        
        assert "CRITICAL" in text_output
        assert "HIGH" in text_output
        assert "MEDIUM" in text_output
        assert "LOW" in text_output

    def test_to_markdown(self, formatter, sample_results):
        """Test markdown output format."""
        md_output = formatter.to_markdown(sample_results, "/test/project")
        
        assert isinstance(md_output, str)
        assert "# AI Code Review" in md_output
        assert "## Summary" in md_output

    def test_to_markdown_includes_issues(self, formatter, sample_results):
        """Test markdown includes issue details."""
        md_output = formatter.to_markdown(sample_results, "/test/project")
        
        assert "Hardcoded password detected" in md_output
        assert "SQL injection vulnerability" in md_output

    def test_to_markdown_empty_issues(self, formatter):
        """Test markdown output with no issues."""
        results = {
            "issues": [],
            "stats": {"files_analyzed": 3, "lines_of_code": 100},
        }
        
        md_output = formatter.to_markdown(results, "/test")
        
        assert "No Issues Found" in md_output or "No issues" in md_output

    def test_to_html(self, formatter, sample_results):
        """Test HTML output format."""
        html_output = formatter.to_html(sample_results, "/test/project")
        
        assert isinstance(html_output, str)
        assert "<!DOCTYPE html>" in html_output
        assert "<html>" in html_output

    def test_to_html_with_theme(self, formatter, sample_results):
        """Test HTML output with different themes."""
        html_light = formatter.to_html(sample_results, "/test", theme="light")
        html_dark = formatter.to_html(sample_results, "/test", theme="dark")
        
        # Dark theme should have dark background
        assert "#1e1e1e" in html_dark
        assert "#ffffff" in html_light

    def test_to_csv(self, formatter, sample_results):
        """Test CSV output format."""
        csv_output = formatter.to_csv(sample_results)
        
        assert isinstance(csv_output, str)
        lines = csv_output.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one data row
        assert "severity,type,file,line_number,message,suggestion" in lines[0]

    def test_to_sarif(self, formatter, sample_results):
        """Test SARIF output format."""
        sarif_output = formatter.to_sarif(sample_results)
        
        assert isinstance(sarif_output, str)
        
        data = json.loads(sarif_output)
        assert "version" in data
        assert "runs" in data

    def test_severity_colors(self, formatter):
        """Test severity color mapping."""
        assert formatter.SEVERITY_COLORS["critical"] == "red bold"
        assert formatter.SEVERITY_COLORS["high"] == "red"
        assert formatter.SEVERITY_COLORS["medium"] == "yellow"
        assert formatter.SEVERITY_COLORS["low"] == "dim"

    def test_severity_emoji(self, formatter):
        """Test severity emoji mapping."""
        assert formatter.SEVERITY_EMOJI["critical"] == "🔴"
        assert formatter.SEVERITY_EMOJI["high"] == "🟠"
        assert formatter.SEVERITY_EMOJI["medium"] == "🟡"
        assert formatter.SEVERITY_EMOJI["low"] == "🟢"


class TestGroupBySeverity:
    """Test severity grouping functionality."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return OutputFormatter()

    def test_group_by_severity(self, formatter):
        """Test grouping issues by severity."""
        issues = [
            CodeIssue(severity="high", type="bug", message="", file="", line_number=0),
            CodeIssue(severity="high", type="bug", message="", file="", line_number=0),
            CodeIssue(severity="medium", type="bug", message="", file="", line_number=0),
            CodeIssue(severity="low", type="bug", message="", file="", line_number=0),
        ]
        
        grouped = formatter._group_by_severity(issues)
        
        assert len(grouped["high"]) == 2
        assert len(grouped["medium"]) == 1
        assert len(grouped["low"]) == 1

    def test_group_by_severity_with_dict(self, formatter):
        """Test grouping with dict issues."""
        issues = [
            {"severity": "high", "message": "test1"},
            {"severity": "low", "message": "test2"},
        ]
        
        grouped = formatter._group_by_severity(issues)
        
        assert len(grouped["high"]) == 1
        assert len(grouped["low"]) == 1


class TestSerialization:
    """Test issue serialization."""

    def test_serialize_issues_with_code_issue_objects(self):
        """Test serializing CodeIssue objects."""
        formatter = OutputFormatter()
        
        issues = [
            CodeIssue(
                severity="high",
                type="security",
                message="Test",
                file="test.py",
                line_number=1,
            )
        ]
        
        serialized = formatter._serialize_issues(issues)
        
        assert len(serialized) == 1
        assert serialized[0]["severity"] == "high"

    def test_serialize_issues_with_dicts(self):
        """Test serializing dict issues."""
        formatter = OutputFormatter()
        
        issues = [
            {"severity": "high", "message": "Test", "file": "test.py", "line_number": 1}
        ]
        
        serialized = formatter._serialize_issues(issues)
        
        assert len(serialized) == 1

    def test_serialize_mixed_issues(self):
        """Test serializing mixed issue types."""
        formatter = OutputFormatter()
        
        issues = [
            CodeIssue(
                severity="high",
                type="security",
                message="Test",
                file="test.py",
                line_number=1,
            ),
            {"severity": "low", "message": "Test2", "file": "test.py", "line_number": 2},
        ]
        
        serialized = formatter._serialize_issues(issues)
        
        assert len(serialized) == 2
