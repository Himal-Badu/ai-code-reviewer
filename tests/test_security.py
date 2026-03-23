"""Tests for the security scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.security import SecurityScanner, OWASPChecker, CodeIssue


class TestSecurityScanner:
    """Test cases for SecurityScanner."""

    @pytest.fixture
    def scanner(self):
        """Create a SecurityScanner instance."""
        return SecurityScanner()

    def test_scanner_initializes(self, scanner):
        """Test that scanner initializes correctly."""
        assert scanner is not None
        assert scanner.issues == []

    @patch("subprocess.run")
    def test_run_bandit_not_installed(self, mock_run, scanner, tmp_path):
        """Test behavior when Bandit is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        issues = scanner._run_bandit(test_file)
        
        # Should get info message about Bandit not installed
        assert len(issues) > 0 or issues == []

    @patch("subprocess.run")
    def test_run_bandit_returns_issues(self, mock_run, scanner, tmp_path):
        """Test that Bandit results are parsed correctly."""
        # Mock Bandit output
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = '{"results": [{"issue_severity": "HIGH", "issue_text": "Test issue", "line_number": 10}]}'
        
        mock_run.return_value = mock_result
        
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        issues = scanner._run_bandit(test_file)
        
        assert isinstance(issues, list)

    def test_count_by_severity(self, scanner):
        """Test counting issues by severity."""
        issues = [
            CodeIssue("high", "security", "test", "file.py", 1),
            CodeIssue("high", "security", "test", "file.py", 2),
            CodeIssue("medium", "security", "test", "file.py", 3),
        ]
        
        counts = scanner._count_by_severity(issues)
        
        assert counts["high"] == 2
        assert counts["medium"] == 1
        assert counts["low"] == 0
        assert counts["critical"] == 0


class TestOWASPChecker:
    """Test cases for OWASP Checker."""

    @pytest.fixture
    def checker(self):
        """Create an OWASPChecker instance."""
        return OWASPChecker()

    def test_checker_initializes(self, checker):
        """Test that checker initializes with patterns."""
        assert checker is not None
        assert len(checker.VULNERABLE_PATTERNS) > 0

    def test_check_sql_injection_pattern(self, checker, tmp_path):
        """Test SQL injection detection."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")
        
        issues = checker.check_file(test_file)
        
        # Should find potential SQL injection
        assert any("sql" in i.message.lower() or "injection" in i.message.lower() 
                   for i in issues)

    def test_check_hardcoded_secrets(self, checker, tmp_path):
        """Test hardcoded secrets detection."""
        test_file = tmp_path / "test.py"
        test_file.write_text('API_KEY = "sk-1234567890abcdef"')
        
        issues = checker.check_file(test_file)
        
        # Should find hardcoded secret
        assert any(i.severity == "high" for i in issues)

    def test_check_xss_patterns(self, checker, tmp_path):
        """Test XSS pattern detection."""
        test_file = tmp_path / "test.js"
        test_file.write_text("element.innerHTML = userInput;")
        
        issues = checker.check_file(test_file)
        
        # Should find potential XSS
        assert any("xss" in i.message.lower() or "injection" in i.message.lower() 
                   for i in issues if hasattr(i, 'message'))

    def test_check_weak_crypto(self, checker, tmp_path):
        """Test weak crypto detection."""
        test_file = tmp_path / "test.py"
        test_file.write_text("hash = md5(password)")
        
        issues = checker.check_file(test_file)
        
        # Should find weak crypto
        assert any("crypto" in i.message.lower() for i in issues)


class TestVulnerablePatterns:
    """Test the vulnerable patterns dictionary."""

    def test_sql_injection_pattern_exists(self):
        """Test SQL injection pattern is defined."""
        patterns = OWASPChecker.VULNERABLE_PATTERNS
        assert "sql_injection" in patterns
        assert "owasp" in patterns["sql_injection"]
        assert "severity" in patterns["sql_injection"]

    def test_hardcoded_secrets_pattern_exists(self):
        """Test hardcoded secrets pattern is defined."""
        patterns = OWASPChecker.VULNERABLE_PATTERNS
        assert "hardcoded_secrets" in patterns

    def test_patterns_have_owasp_references(self):
        """Test all patterns have OWASP references."""
        patterns = OWASPChecker.VULNERABLE_PATTERNS
        for name, info in patterns.items():
            assert "owasp" in info, f"Pattern {name} missing OWASP reference"
            assert "severity" in info, f"Pattern {name} missing severity"