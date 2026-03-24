"""Security scanning using Bandit and custom rules.

This module provides comprehensive security scanning capabilities including:
- Bandit integration for Python security checks
- OWASP Top 10 vulnerability detection
- Custom security pattern matching
- CWE (Common Weakness Enumeration) tracking
"""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple

from src.models import CodeIssue

logger = logging.getLogger(__name__)


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    # CWE to OWASP mapping
    CWE_TO_OWASP = {
        "CWE-89": "A03:2021 - Injection",
        "CWE-78": "A03:2021 - Injection",
        "CWE-79": "A03:2021 - Injection",
        "CWE-94": "A03:2021 - Injection",
        "CWE-20": "A03:2021 - Injection",
        "CWE-502": "A08:2021 - Software and Data Integrity Failures",
        "CWE-434": "A04:2021 - Insecure Design",
        "CWE-611": "A04:2021 - Insecure Design",
        "CWE-798": "A02:2021 - Cryptographic Failures",
        "CWE-295": "A02:2021 - Cryptographic Failures",
        "CWE-327": "A02:2021 - Cryptographic Failures",
        "CWE-352": "A01:2021 - Broken Access Control",
        "CWE-22": "A01:2021 - Broken Access Control",
        "CWE-862": "A01:2021 - Broken Access Control",
    }

    def __init__(self, enable_bandit: bool = True, enable_owasp: bool = True):
        self.issues: List[CodeIssue] = []
        self.enable_bandit = enable_bandit
        self.enable_owasp = enable_owasp
        self.owasp_checker = OWASPChecker() if enable_owasp else None

    def scan(self, path: Path) -> Dict[str, Any]:
        """Run security scan on a file or directory."""
        issues: List[CodeIssue] = []

        # Run Bandit for Python files
        if self.enable_bandit:
            if path.is_file() and path.suffix == ".py":
                issues.extend(self._run_bandit(path))
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    issues.extend(self._run_bandit(py_file))

        # Run OWASP checks
        if self.owasp_checker:
            if path.is_file():
                issues.extend(self.owasp_checker.check_file(path))
            elif path.is_dir():
                for file_path in path.rglob("*.py"):
                    issues.extend(self.owasp_checker.check_file(file_path))

        # Remove duplicates based on file and line number
        issues = self._deduplicate_issues(issues)

        return {
            "issues": issues,
            "stats": {
                "total_issues": len(issues),
                "by_severity": self._count_by_severity(issues),
                "by_owasp": self._count_by_owasp(issues),
            }
        }

    def _deduplicate_issues(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """Remove duplicate issues based on file, line, and message."""
        seen: Set[Tuple[str, int, str]] = set()
        unique_issues = []
        
        for issue in issues:
            key = (issue.file, issue.line_number, issue.message)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        return unique_issues

    def _run_bandit(self, file_path: Path) -> List[CodeIssue]:
        """Run Bandit security scanner on a Python file."""
        issues = []

        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-r", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                try:
                    data = json.loads(result.stdout)
                    for finding in data.get("results", []):
                        # Extract CWE if available
                        cwe_id = None
                        cwe_link = finding.get("issue_cwe", {}).get("url", "")
                        if cwe_link:
                            cwe_id = cwe_link.split("/")[-1] if "/" in cwe_link else None
                        
                        issues.append(CodeIssue(
                            severity=self._map_bandit_severity(finding.get("issue_severity")),
                            type="security",
                            message=finding.get("issue_text", "Security issue"),
                            file=str(file_path),
                            line_number=finding.get("line_number", 0),
                            suggestion=finding.get("issue_cwe", {}).get("description", ""),
                            cwe_id=cwe_id,
                            rule_id=finding.get("test_id", ""),
                        ))
                except json.JSONDecodeError:
                    # Bandit output might be plain text
                    logger.debug(f"Could not parse Bandit JSON output for {file_path}")

        except FileNotFoundError:
            # Bandit not installed
            issues.append(CodeIssue(
                severity="low",
                type="info",
                message="Bandit not installed. Install with: pip install bandit",
                file=str(file_path),
                line_number=0,
                suggestion="pip install bandit",
            ))
        except subprocess.TimeoutExpired:
            issues.append(CodeIssue(
                severity="low",
                type="info",
                message="Security scan timed out",
                file=str(file_path),
                line_number=0,
            ))
        except Exception as e:
            logger.warning(f"Error running Bandit on {file_path}: {e}")
            issues.append(CodeIssue(
                severity="low",
                type="info",
                message=f"Could not run security scan: {str(e)}",
                file=str(file_path),
                line_number=0,
            ))

        return issues

    def _map_bandit_severity(self, severity: str) -> str:
        """Map Bandit severity to our severity levels."""
        mapping = {
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
        }
        return mapping.get(severity.upper(), "medium")

    def _count_by_severity(self, issues: List[CodeIssue]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.severity.lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def _count_by_owasp(self, issues: List[CodeIssue]) -> Dict[str, int]:
        """Count issues by OWASP category."""
        counts: Dict[str, int] = {}
        
        for issue in issues:
            if issue.cwe_id and issue.cwe_id in self.CWE_TO_OWASP:
                category = self.CWE_TO_OWASP[issue.cwe_id]
                counts[category] = counts.get(category, 0) + 1
        
        return counts


class OWASPChecker:
    """Check for OWASP Top 10 vulnerabilities."""

    # Extended patterns with CWE mapping
    VULNERABLE_PATTERNS = {
        "sql_injection": {
            "patterns": [
                r'execute\s*\(\s*f["\'].*\{.*\}',  # f-string in execute
                r'execute\s*\(\s*["\'].*%s',  # % formatting in SQL
                r'execute\s*\(\s*["\'].*\+',  # String concatenation in SQL
                r'cursor\.execute\s*\([^,)]*\%',
                r'\.format\s*\([^)]*\+[^)]*\)',  # String formatting with concatenation
            ],
            "cwe": "CWE-89",
            "owasp": "A03:2021 - Injection",
            "severity": "critical",
            "suggestion": "Use parameterized queries or an ORM",
        },
        "hardcoded_secrets": {
            "patterns": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'private[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\'][^"\']+["\']',
                r'aws[_-]?secret[_-]?access[_-]?key\s*=\s*["\'][^"\']+["\']',
            ],
            "cwe": "CWE-798",
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "high",
            "suggestion": "Use environment variables or a secrets manager",
        },
        "weak_crypto": {
            "patterns": [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'hashlib\.new\s*\(\s*["\']md5',
                r'hashlib\.new\s*\(\s*["\']sha1',
                r'DES\s*\.new\s*\(',
                r'RC4\s*\(',
            ],
            "cwe": "CWE-327",
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "medium",
            "suggestion": "Use strong cryptographic algorithms (AES, SHA-256+)",
        },
        "xss": {
            "patterns": [
                r'innerHTML\s*=',
                r'dangerouslySetInnerHTML',
                r'document\.write\s*\(',
                r'\.html\s*\([^)]*\)',
            ],
            "cwe": "CWE-79",
            "owasp": "A03:2021 - Injection",
            "severity": "high",
            "suggestion": "Use proper output encoding or sanitization",
        },
        "path_traversal": {
            "patterns": [
                r'open\s*\([^,)]*\+[^,)]*\)',  # Open with string concatenation
                r'os\.path\.join\s*\([^,)]*\+',
                r'Path\s*\([^)]*\+[^)]*\)',
            ],
            "cwe": "CWE-22",
            "owasp": "A01:2021 - Broken Access Control",
            "severity": "high",
            "suggestion": "Validate and sanitize user input for file paths",
        },
        "deserialization": {
            "patterns": [
                r'pickle\.load\s*\(',
                r'yaml\.load\s*\(',
                r'marshal\.load\s*\(',
                r'yaml\.unsafe_load\s*\(',
            ],
            "cwe": "CWE-502",
            "owasp": "A08:2021 - Software and Data Integrity Failures",
            "severity": "critical",
            "suggestion": "Use safe serialization formats (JSON) or validate input",
        },
        "command_injection": {
            "patterns": [
                r'os\.system\s*\(',
                r'subprocess\.call\s*\([^,)]*\+[^,)]*\)',
                r'os\.popen\s*\(',
                r'subprocess\.run\s*\([^,)]*shell\s*=\s*True',
                r'os\.spawn',
            ],
            "cwe": "CWE-78",
            "owasp": "A03:2021 - Injection",
            "severity": "critical",
            "suggestion": "Avoid shell=True, use list arguments, sanitize inputs",
        },
        "hardcoded_ip": {
            "patterns": [
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP address pattern
            ],
            "cwe": "CWE-798",
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "medium",
            "suggestion": "Use configuration files or environment variables for IPs",
        },
        "insecure_random": {
            "patterns": [
                r'random\.random\s*\(\s*\)',  # Using random for security
                r'random\.choice\s*\(',
                r'random\.randint\s*\(',
            ],
            "cwe": "CWE-338",
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "medium",
            "suggestion": "Use secrets module for cryptographic randomness",
        },
        "debug_mode": {
            "patterns": [
                r'DEBUG\s*=\s*True',
                r'debug\s*=\s*True',
                r'app\.run\s*\(\s*debug\s*=\s*True',
            ],
            "cwe": "CWE-11",
            "owasp": "A05:2021 - Security Misconfiguration",
            "severity": "medium",
            "suggestion": "Disable debug mode in production",
        },
        "bypass_auth": {
            "patterns": [
                r'@app\.route.*methods.*POST.*if.*True',  # Suspicious auth bypass
                r'if.*admin.*return',  # Simple admin check
            ],
            "cwe": "CWE-287",
            "owasp": "A01:2021 - Broken Access Control",
            "severity": "high",
            "suggestion": "Implement proper authentication and authorization",
        },
        "logger_exposure": {
            "patterns": [
                r'logger\.(debug|info)\([^)]*password',
                r'logger\.(debug|info)\([^)]*secret',
                r'logger\.(debug|info)\([^)]*token',
            ],
            "cwe": "CWE-532",
            "owasp": "A01:2021 - Broken Access Control",
            "severity": "medium",
            "suggestion": "Avoid logging sensitive information",
        },
    }

    def __init__(self):
        # Pre-compile regex patterns for performance
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for vuln_type, info in self.VULNERABLE_PATTERNS.items():
            self._compiled_patterns[vuln_type] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in info["patterns"]
            ]

    def check_file(self, file_path: Path) -> List[CodeIssue]:
        """Check a file for OWASP vulnerabilities."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            for vuln_type, info in self.VULNERABLE_PATTERNS.items():
                patterns = self._compiled_patterns.get(vuln_type, [])
                
                for pattern in patterns:
                    for match in pattern.finditer(content):
                        line_num = content[:match.start()].count("\n") + 1
                        
                        # Get the line of code for context
                        code_snippet = ""
                        if line_num <= len(lines):
                            code_snippet = lines[line_num - 1].strip()
                        
                        issues.append(CodeIssue(
                            severity=info["severity"],
                            type="security",
                            message=f"Potential {info['owasp']}: {vuln_type.replace('_', ' ').title()}",
                            file=str(file_path),
                            line_number=line_num,
                            code_snippet=code_snippet,
                            suggestion=info["suggestion"],
                            cwe_id=info.get("cwe"),
                            rule_id=f"OWASP-{vuln_type}",
                        ))

        except Exception as e:
            logger.warning(f"Error checking {file_path} for OWASP vulnerabilities: {e}")

        return issues

    def get_supported_checks(self) -> List[str]:
        """Get list of supported vulnerability checks."""
        return list(self.VULNERABLE_PATTERNS.keys())