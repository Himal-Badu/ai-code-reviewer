"""Tests for the security scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from src.security import SecurityScanner, OWASPChecker


class TestSecurityScanner:
    """Test cases for SecurityScanner."""

    @pytest.fixture
    def scanner(self):
        """Create a SecurityScanner instance."""
        return SecurityScanner(enable_bandit=False, enable_owasp=True)

    def test_scanner_initialization(self):
        """Test scanner can be initialized."""
        scanner = SecurityScanner()
        assert scanner is not None
        assert scanner.enable_bandit is True
        assert scanner.enable_owasp is True

    def test_scan_file(self, scanner, tmp_path):
        """Test scanning a single file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("password = 'hardcoded'")
        
        result = scanner.scan(test_file)
        
        assert "issues" in result
        assert "stats" in result

    def test_scan_directory(self, scanner, tmp_path):
        """Test scanning a directory."""
        # Create test files
        (tmp_path / "test1.py").write_text("password = 'secret'")
        (tmp_path / "test2.py").write_text("eval('1+1')")
        
        result = scanner.scan(tmp_path)
        
        assert "issues" in result
        assert result["stats"]["total_issues"] >= 0

    def test_deduplicate_issues(self, scanner):
        """Test issue deduplication."""
        from src.models import CodeIssue
        
        issues = [
            CodeIssue(
                severity="high",
                type="security",
                message="Test issue",
                file="test.py",
                line_number=10,
            ),
            CodeIssue(
                severity="high",
                type="security",
                message="Test issue",
                file="test.py",
                line_number=10,
            ),
        ]
        
        unique = scanner._deduplicate_issues(issues)
        
        assert len(unique) == 1

    def test_count_by_severity(self, scanner):
        """Test counting issues by severity."""
        from src.models import CodeIssue
        
        issues = [
            CodeIssue(severity="critical", type="security", message="", file="", line_number=0),
            CodeIssue(severity="high", type="security", message="", file="", line_number=0),
            CodeIssue(severity="high", type="security", message="", file="", line_number=0),
            CodeIssue(severity="medium", type="security", message="", file="", line_number=0),
        ]
        
        counts = scanner._count_by_severity(issues)
        
        assert counts["critical"] == 1
        assert counts["high"] == 2
        assert counts["medium"] == 1
        assert counts["low"] == 0


class TestOWASPChecker:
    """Test cases for OWASPChecker."""

    @pytest.fixture
    def checker(self):
        """Create an OWASPChecker instance."""
        return OWASPChecker()

    def test_checker_initialization(self, checker):
        """Test checker can be initialized."""
        assert checker is not None

    def test_detect_hardcoded_password(self, checker, tmp_path):
        """Test detection of hardcoded passwords."""
        test_file = tmp_path / "test.py"
        test_file.write_text("password = 'mysecretpassword'")
        
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0
        assert any(i.cwe_id == "CWE-798" for i in issues)

    def test_detect_sql_injection(self, checker, tmp_path):
        """Test detection of SQL injection patterns."""
        test_file = tmp_path / "test.py"
        test_file.write_text("cursor.execute('SELECT * FROM users WHERE id = ' + user_id)")
        
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0

    def test_detect_dangerous_functions(self, checker, tmp_path):
        """Test detection of dangerous functions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("eval('1+1')")
        
        issues = checker.check_file(test_file)
        
        # Should find eval usage
        assert len(issues) > 0

    def test_detect_weak_crypto(self, checker, tmp_path):
        """Test detection of weak cryptography."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import hashlib\nhashlib.md5(b'test')")
        
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0

    def test_get_supported_checks(self, checker):
        """Test getting supported checks list."""
        checks = checker.get_supported_checks()
        
        assert isinstance(checks, list)
        assert len(checks) > 0
        assert "sql_injection" in checks
        assert "hardcoded_secrets" in checks

    def test_no_issues_in_clean_code(self, checker, tmp_path):
        """Test that clean code has no issues."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def greet(name):
    return f'Hello, {name}!'

def add(a, b):
    return a + b
""")
        
        issues = checker.check_file(test_file)
        
        # Should not find any security issues
        assert len(issues) == 0

    def test_line_number_accuracy(self, checker, tmp_path):
        """Test that line numbers are accurate."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\npassword = 'secret'\nline4\n")
        
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0
        # Line number should be 3 (0-indexed: 0,1,2,3)
        assert any(i.line_number == 3 for i in issues)


class TestSecurityPatterns:
    """Test specific security patterns."""

    def test_command_injection_patterns(self, tmp_path):
        """Test command injection detection."""
        checker = OWASPChecker()
        
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nos.system('rm -rf ' + user_input)")
        
        issues = checker.check_file(test_file)
        
        assert any("command_injection" in i.rule_id.lower() for i in issues if i.rule_id)

    def test_xss_patterns(self, tmp_path):
        """Test XSS detection."""
        checker = OWASPChecker()
        
        test_file = tmp_path / "test.py"
        test_file.write_text("element.innerHTML = user_input")
        
        issues = checker.check_file(test_file)
        
        assert any("xss" in i.rule_id.lower() for i in issues if i.rule_id)

    def test_deserialization_patterns(self, tmp_path):
        """Test deserialization vulnerability detection."""
        checker = OWASPChecker()
        
        test_file = tmp_path / "test.py"
        test_file.write_text("import pickle\ndata = pickle.load(file)")
        
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0
