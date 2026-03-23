"""Security scanning using Bandit and custom rules."""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

from src.models import CodeIssue


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    def __init__(self):
        self.issues = []

    def scan(self, path: Path) -> Dict[str, Any]:
        """Run security scan on a file or directory."""
        issues = []

        # Run Bandit for Python files
        if path.is_file() and path.suffix == ".py":
            issues.extend(self._run_bandit(path))
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                issues.extend(self._run_bandit(py_file))

        return {
            "issues": issues,
            "stats": {
                "total_issues": len(issues),
                "by_severity": self._count_by_severity(issues),
            }
        }

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
                        issues.append(CodeIssue(
                            severity=self._map_bandit_severity(finding.get("issue_severity")),
                            type="security",
                            message=finding.get("issue_text", "Security issue"),
                            file=str(file_path),
                            line_number=finding.get("line_number", 0),
                            suggestion=finding.get("issue_cwe", {}).get("url", ""),
                        ))
                except json.JSONDecodeError:
                    # Bandit output might be plain text
                    pass

        except FileNotFoundError:
            # Bandit not installed
            issues.append(CodeIssue(
                severity="low",
                type="info",
                message="Bandit not installed. Install with: pip install bandit",
                file=str(file_path),
                line_number=0,
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


class OWASPChecker:
    """Check for OWASP Top 10 vulnerabilities."""

    # Patterns that might indicate vulnerabilities
    VULNERABLE_PATTERNS = {
        "sql_injection": {
            "patterns": [
                r'execute\s*\(\s*f["\'].*\{.*\}',  # f-string in execute
                r'execute\s*\(\s*["\'].*%s',  # % formatting in SQL
            ],
            "owasp": "A03:2021 - Injection",
            "severity": "critical",
        },
        "hardcoded_secrets": {
            "patterns": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            ],
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "high",
        },
        "weak_crypto": {
            "patterns": [
                r'md5\s*\(',
                r'sha1\s*\(',
            ],
            "owasp": "A02:2021 - Cryptographic Failures",
            "severity": "medium",
        },
        "xss": {
            "patterns": [
                r'innerHTML\s*=',
                r'dangerouslySetInnerHTML',
            ],
            "owasp": "A03:2021 - Injection",
            "severity": "high",
        },
    }

    def check_file(self, file_path: Path) -> List[CodeIssue]:
        """Check a file for OWASP vulnerabilities."""
        import re

        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for vuln_type, info in self.VULNERABLE_PATTERNS.items():
                for pattern in info["patterns"]:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line_num = content[:match.start()].count("\n") + 1
                        issues.append(CodeIssue(
                            severity=info["severity"],
                            type="security",
                            message=f"Potential {info['owasp']}",
                            file=str(file_path),
                            line_number=line_num,
                            suggestion=f"Review for {vuln_type}",
                        ))

        except Exception:
            pass

        return issues