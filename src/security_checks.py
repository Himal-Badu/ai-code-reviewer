"""Advanced security checks for AI Code Reviewer."""

import re
from typing import List, Dict, Any


class SecurityChecks:
    """Advanced security vulnerability checks."""
    
    @staticmethod
    def check_sql_injection(code: str) -> List[Dict[str, Any]]:
        """Check for SQL injection vulnerabilities."""
        issues = []
        
        patterns = [
            (r'execute\s*\(\s*f["\'].*\{.*\}', 'f-string in execute'),
            (r'execute\s*\(\s*["\'].*%s.*["\'].*%', 'String formatting in execute'),
            (r'execute\s*\(\s*["\'].*\+.*["\'].*\)', 'String concatenation in execute'),
        ]
        
        for i, line in enumerate(code.split('\n'), 1):
            for pattern, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'type': 'security',
                        'severity': 'critical',
                        'message': f'Potential SQL injection: {desc}',
                        'line': i,
                        'code': line.strip()
                    })
        
        return issues
    
    @staticmethod
    def check_hardcoded_secrets(code: str) -> List[Dict[str, Any]]:
        """Check for hardcoded secrets."""
        issues = []
        
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'Hardcoded token'),
            (r'aws[_-]?access[_-]?key', 'AWS access key'),
            (r'private[_-]?key\s*=', 'Private key'),
        ]
        
        for i, line in enumerate(code.split('\n'), 1):
            for pattern, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'message': f'Security issue: {desc}',
                        'line': i,
                        'code': line.strip()[:50]
                    })
        
        return issues
    
    @staticmethod
    def check_command_injection(code: str) -> List[Dict[str, Any]]:
        """Check for command injection."""
        issues = []
        
        dangerous_funcs = ['system', 'exec', 'popen', 'subprocess']
        
        for i, line in enumerate(code.split('\n'), 1):
            for func in dangerous_funcs:
                if f'{func}(' in line and ('+' in line or 'f"' in line or '" +' in line):
                    issues.append({
                        'type': 'security',
                        'severity': 'critical',
                        'message': f'Potential command injection: {func}',
                        'line': i,
                        'code': line.strip()
                    })
        
        return issues
    
    @staticmethod
    def check_unsafe_imports(code: str) -> List[Dict[str, Any]]:
        """Check for unsafe imports."""
        issues = []
        
        unsafe = ['pickle', 'eval', 'exec', '__import__']
        
        for i, line in enumerate(code.split('\n'), 1):
            for imp in unsafe:
                if f'import {imp}' in line or f'from {imp} import' in line:
                    issues.append({
                        'type': 'security',
                        'severity': 'medium',
                        'message': f'Unsafe import: {imp}',
                        'line': i,
                        'code': line.strip()
                    })
        
        return issues
    
    @staticmethod
    def check_weak_crypto(code: str) -> List[Dict[str, Any]]:
        """Check for weak cryptography."""
        issues = []
        
        weak_algos = ['md5', 'sha1', 'des']
        
        for i, line in enumerate(code.split('\n'), 1):
            for algo in weak_algos:
                if f'"{algo}"' in line.lower() or f"'{algo}'" in line.lower():
                    issues.append({
                        'type': 'security',
                        'severity': 'medium',
                        'message': f'Weak cryptographic algorithm: {algo}',
                        'line': i,
                        'code': line.strip()
                    })
        
        return issues
    
    @staticmethod
    def check_insecure_deserialization(code: str) -> List[Dict[str, Any]]:
        """Check for insecure deserialization."""
        issues = []
        
        dangerous = ['yaml.load', 'pickle.load', 'marshal.load']
        
        for i, line in enumerate(code.split('\n'), 1):
            for func in dangerous:
                if func in line:
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'message': f'Insecure deserialization: {func}',
                        'line': i,
                        'code': line.strip()
                    })
        
        return issues
    
    @staticmethod
    def check_path_traversal(code: str) -> List[Dict[str, Any]]:
        """Check for path traversal vulnerabilities."""
        issues = []
        
        dangerous = ['../', '..\\', '/etc/passwd', 'C:\\']
        
        for i, line in enumerate(code.split('\n'), 1):
            for pattern in dangerous:
                if pattern in line:
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'message': 'Potential path traversal',
                        'line': i,
                        'code': line.strip()[:50]
                    })
        
        return issues
    
    @staticmethod
    def run_all_checks(code: str) -> List[Dict[str, Any]]:
        """Run all security checks."""
        all_issues = []
        
        all_issues.extend(SecurityChecks.check_sql_injection(code))
        all_issues.extend(SecurityChecks.check_hardcoded_secrets(code))
        all_issues.extend(SecurityChecks.check_command_injection(code))
        all_issues.extend(SecurityChecks.check_unsafe_imports(code))
        all_issues.extend(SecurityChecks.check_weak_crypto(code))
        all_issues.extend(SecurityChecks.check_insecure_deserialization(code))
        all_issues.extend(SecurityChecks.check_path_traversal(code))
        
        return all_issues