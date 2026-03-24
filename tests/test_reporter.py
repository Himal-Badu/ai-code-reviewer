"""Tests for the reporter module."""

import pytest
from pathlib import Path

from src.reporter import ReportGenerator
from src.models import CodeIssue


class TestReportGenerator:
    """Test cases for ReportGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a report generator instance."""
        return ReportGenerator()
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results for testing."""
        return {
            "file": "test.py",
            "issues": [
                CodeIssue(
                    severity="high",
                    type="security",
                    message="Hardcoded secret detected",
                    file="test.py",
                    line_number=5,
                    suggestion="Use environment variables",
                ),
                CodeIssue(
                    severity="medium",
                    type="style",
                    message="Variable naming",
                    file="test.py",
                    line_number=10,
                ),
                CodeIssue(
                    severity="low",
                    type="style",
                    message="Code style suggestion",
                    file="test.py",
                    line_number=15,
                ),
            ],
            "stats": {
                "files_analyzed": 1,
                "lines_of_code": 50,
            },
        }
    
    def test_generator_initializes(self, generator):
        """Test that generator initializes correctly."""
        assert generator is not None
    
    def test_generate_html_report(self, generator, sample_results):
        """Test HTML report generation."""
        html = generator.generate_html_report(sample_results)
        
        assert "<html>" in html
        assert "AI Code Review Report" in html
        assert "high" in html.lower()
        assert "Files Analyzed: 1" in html
    
    def test_generate_csv_report(self, generator, sample_results):
        """Test CSV report generation."""
        csv = generator.generate_csv_report(sample_results)
        
        assert "Severity,Type,File,Line,Message,Suggestion" in csv
        assert "high,security,test.py,5" in csv
    
    def test_generate_junit_report(self, generator, sample_results):
        """Test JUnit report generation."""
        junit = generator.generate_junit_report(sample_results)
        
        assert '<?xml version="1.0"' in junit
        assert "<testsuite" in junit
        assert 'failure message="Hardcoded secret detected"' in junit
    
    def test_generate_summary_report(self, generator, sample_results):
        """Test summary report generation."""
        summary = generator.generate_summary_report(sample_results)
        
        assert "AI CODE REVIEW SUMMARY REPORT" in summary
        assert "Files Analyzed:     1" in summary
        assert "Total Issues:       3" in summary
    
    def test_save_report_json(self, generator, sample_results, tmp_path):
        """Test saving JSON report."""
        output_path = tmp_path / "report.json"
        
        generator.save_report(sample_results, output_path, "json")
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "file" in content
    
    def test_save_report_html(self, generator, sample_results, tmp_path):
        """Test saving HTML report."""
        output_path = tmp_path / "report.html"
        
        generator.save_report(sample_results, output_path, "html")
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "<html>" in content
    
    def test_save_report_creates_parent_dirs(self, generator, sample_results, tmp_path):
        """Test that save_report creates parent directories."""
        output_path = tmp_path / "subdir" / "report.json"
        
        generator.save_report(sample_results, output_path, "json")
        
        assert output_path.exists()
    
    def test_summary_with_no_issues(self, generator):
        """Test summary with no issues."""
        results = {
            "issues": [],
            "stats": {"files_analyzed": 0, "lines_of_code": 0},
        }
        
        summary = generator.generate_summary_report(results)
        
        assert "Total Issues:       0" in summary
        assert "Critical:          0" in summary