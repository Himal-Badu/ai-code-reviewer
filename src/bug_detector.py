"""Integrated CodexBugFinder - bug detection for AI Code Reviewer v2.1."""

import ast
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


CVE_DB = {
    "CWE-89": {"name": "SQL Injection", "cves": ["CVE-2021-34473", "CVE-2019-18348"]},
    "CWE-78": {"name": "OS Command Injection", "cves": ["CVE-2021-4034", "CVE-2014-6271"]},
    "CWE-79": {"name": "Cross-Site Scripting", "cves": ["CVE-2021-21373", "CVE-2019-11358"]},
    "CWE-94": {"name": "Code Injection", "cves": ["CVE-2019-18348", "CVE-2018-1000862"]},
    "CWE-502": {"name": "Insecure Deserialization", "cves": ["CVE-2019-12384", "CVE-2017-9805"]},
    "CWE-798": {"name": "Hardcoded Credentials", "cves": ["CVE-2020-5217", "CVE-2019-18874"]},
}


@dataclass
class CodeIssue:
    type: str
    severity: str
    message: str
    file: str
    line_number: int
    suggestion: str = ""
    details: str = ""
    stage: str = "static"
    confidence: float = 0.5


class BugDetector:
    """Codex-style bug detector integrated into AI Code Reviewer."""
    
    def __init__(self, mode="research"):
        self.mode = mode
        self.patterns = self._load_patterns()
    
    def scan_file(self, filepath: str) -> List[CodeIssue]:
        """Scan a file for bugs."""
        path = Path(filepath)
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        return self._analyze(source, str(path))
    
    def _load_patterns(self) -> List[Dict]:
        """Load bug patterns."""
        return [
            ("SQL Injection", r'(execute|executemany|query)\s*\([^)]*["\'].*%[^)]*\)|cursor\.execute\([^)]*\+',
             "CRITICAL", "SQL Injection", "CWE-89",
             "User input directly concatenated into SQL query",
             "Use parameterized queries with placeholders",
             ["cursor.execute(f\"SELECT * FROM users WHERE id={user_id}\")"]),
            
            ("Hardcoded Password", r'(password|passwd|pwd|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']',
             "CRITICAL", "Hardcoded Secret", "CWE-798",
             "Hardcoded password or secret in source code",
             "Use environment variables or secure vault",
             ["password = 'admin123'"]),
            
            ("Command Injection", r'os\.system\([^)]*\+|subprocess\.(call|run|Popen)\([^)]*\+|exec\([^)]*\+',
             "CRITICAL", "Command Injection", "CWE-78",
             "User input passed to system commands",
             "Use subprocess with shell=False and proper escaping",
             ["os.system('ls ' + user_input)"]),
            
            ("Path Traversal", r'(open|file|read)\([^)]*\+|Path\([^)]*\+',
             "HIGH", "Path Traversal", "CWE-22",
             "File path constructed with user input",
             "Validate and sanitize file paths, use allowlists",
             ["open('/var/www/' + filename)"]),
            
            ("eval() Usage", r'eval\s*\([^)]*\)',
             "CRITICAL", "Code Injection", "CWE-94",
             "Dynamic code execution with eval()",
             "Avoid eval(), use ast.literal_eval() or safer alternatives",
             ["eval(user_input)"]),
            
            ("exec() Usage", r'exec\s*\([^)]*\)',
             "CRITICAL", "Code Injection", "CWE-94",
             "Dynamic code execution with exec()",
             "Avoid exec(), use safer alternatives",
             ["exec(user_input)"]),
            
            ("Insecure Deserialization", r'pickle\.loads\s*\([^)]*\)',
             "HIGH", "Insecure Deserialization", "CWE-502",
             "Unpickling untrusted data",
             "Use JSON or validate data before unpickling",
             ["pickle.loads(user_data)"]),
            
            ("XSS", r'innerHTML\s*=|document\.write\(',
             "HIGH", "Cross-Site Scripting", "CWE-79",
             "User input written to DOM without sanitization",
             "Sanitize user input, use textContent instead of innerHTML",
             ["element.innerHTML = userComment"]),
            
            ("Bare Except", r'^\s*except\s*:',
             "MEDIUM", "Bare Except", "CWE-391",
             "Bare except catches all exceptions silently",
             "Catch specific exceptions or use 'except Exception:'",
             ["except:"]),
            
            ("Empty Except", r'^\s*except[^:]*:\s*\n\s*(pass|#)',
             "MEDIUM", "Empty Except Block", "CWE-391",
             "Exception is silently ignored",
             "Log or handle the exception properly",
             ["except: pass"]),
            
            ("Mutable Default", r'def\s+\w+\([^)]*=\s*\[\]',
             "MEDIUM", "Mutable Default Argument", "CWE-484",
             "Mutable default arguments are shared between calls",
             "Use None as default and initialize inside function",
             ["def f(items=[]):"]),
        ]
    
    def _analyze_patterns(self, source: str, filepath: str) -> List[CodeIssue]:
        """Pattern-based analysis."""
        findings = []
        lines = source.split('\n')
        
        for name, pattern, severity, bug_type, cwe_id, desc, fix, examples in self.patterns:
            for line_num, line in enumerate(lines, 1):
                try:
                    if re.search(pattern, line, re.IGNORECASE):
                        cwe_info = CVE_DB.get(cwe_id, {})
                        details = f"Analysis: {desc}\n\nCWE: {cwe_info.get('name', 'Unknown')}"
                        if cwe_info.get('cves'):
                            details += f"\nRelated: {', '.join(cwe_info['cves'][:2])}"
                        findings.append(CodeIssue(
                            type=bug_type, severity=severity, message=desc,
                            file=filepath, line_number=line_num,
                            suggestion=fix, details=details, stage="codex-bug",
                            confidence=0.85
                        ))
                except re.error:
                    pass
        return findings
    
    def _analyze_ast(self, source: str, filepath: str) -> List[CodeIssue]:
        """AST-based deep analysis."""
        findings = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id == 'eval':
                            findings.append(CodeIssue(
                                type="Code Injection (eval)", severity="CRITICAL",
                                message="eval() executes arbitrary code",
                                file=filepath, line_number=node.lineno,
                                suggestion="Use ast.literal_eval() or safer alternatives",
                                details="eval() allows arbitrary code execution - major security risk",
                                stage="codex-bug", confidence=0.95
                            ))
                        elif node.func.id == 'exec':
                            findings.append(CodeIssue(
                                type="Code Injection (exec)", severity="CRITICAL",
                                message="exec() executes arbitrary code",
                                file=filepath, line_number=node.lineno,
                                suggestion="Avoid exec(), use safer alternatives",
                                details="exec() allows arbitrary code execution",
                                stage="codex-bug", confidence=0.95
                            ))
                elif isinstance(node, ast.Assert):
                    findings.append(CodeIssue(
                        type="Assert Statement", severity="LOW",
                        message="Assert can be disabled with -O flag",
                        file=filepath, line_number=node.lineno,
                        suggestion="Use proper error handling (if/raise)",
                        details="Not for production validation",
                        stage="codex-bug", confidence=0.7
                    ))
                elif isinstance(node, ast.Global):
                    findings.append(CodeIssue(
                        type="Global Variable", severity="MEDIUM",
                        message="Global variables reduce testability",
                        file=filepath, line_number=node.lineno,
                        suggestion="Use function parameters and return values",
                        stage="codex-bug", confidence=0.6
                    ))
        except SyntaxError:
            pass
        return findings
    
    def _analyze(self, source: str, filepath: str) -> List[CodeIssue]:
        """Run all analyses."""
        findings = []
        findings.extend(self._analyze_patterns(source, filepath))
        findings.extend(self._analyze_ast(source, filepath))
        # Deduplicate
        seen = {}
        for f in findings:
            key = f"{f.file}:{f.line_number}:{f.message}"
            seen[key] = f
        return list(seen.values())
    
    def generate_report(self, issues: List[CodeIssue]) -> str:
        """Generate research-style report."""
        if not issues:
            return "\n✅ No bugs found!\n"
        
        sev_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        critical = sum(1 for i in issues if i.severity == "CRITICAL")
        high = sum(1 for i in issues if i.severity == "HIGH")
        medium = sum(1 for i in issues if i.severity == "MEDIUM")
        low = sum(1 for i in issues if i.severity == "LOW")
        
        lines = []
        lines.append("\n╔═══════════════════════════════════════════════════════════╗")
        lines.append("║              🔍 CODEX BUG DETECTION REPORT               ║")
        lines.append("╚═══════════════════════════════════════════════════════════╝")
        lines.append(f"\n📊 Total: {len(issues)} | 🔴 {critical} | 🟠 {high} | 🟡 {medium} | 🟢 {low}\n")
        lines.append("═" * 65 + "\n")
        
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            sev_issues = [i for i in issues if i.severity == sev]
            if not sev_issues:
                continue
            lines.append(f"\n{sev_emoji.get(sev, '⚪')} {sev} ({len(sev_issues)})\n")
            lines.append("─" * 65 + "\n")
            for i, issue in enumerate(sev_issues, 1):
                lines.append(f"\n  [{sev[0]}{i}] {issue.type}\n")
                lines.append(f"      📍 {issue.file}:{issue.line_number}\n")
                if issue.message:
                    lines.append(f"      💡 {issue.message}\n")
                if issue.details:
                    lines.append(f"      🔬 {issue.details}\n")
                if issue.suggestion:
                    lines.append(f"      ✅ {issue.suggestion}\n")
                lines.append(f"      Confidence: {issue.confidence * 100:.0f}%\n")
                lines.append("─" * 65 + "\n")
        
        lines.append("\nReport generated by CodexBugFinder 🐛🔬\n")
        return "".join(lines)
