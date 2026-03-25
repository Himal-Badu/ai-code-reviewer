"""Demo scripts for AI Code Reviewer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scanner import CodeScanner
from reporter import ReportGenerator


def demo_basic_scan():
    """Demo: Basic code scanning."""
    print("=" * 50)
    print("DEMO: Basic Code Scan")
    print("=" * 50)
    
    scanner = CodeScanner()
    
    # Create temp code
    code = """
def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    return a * b

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        self.result += value
        return self.result
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        results = scanner.scan(temp_path)
        print(f"Found {len(results.get('issues', {}))} issues")
        
        generator = ReportGenerator()
        report = generator.generate(results)
        print(report)
    finally:
        Path(temp_path).unlink()


def demo_security_scan():
    """Demo: Security scanning."""
    print("\n" + "=" * 50)
    print("DEMO: Security Scan")
    print("=" * 50)
    
    scanner = CodeScanner()
    
    code = """
import os
import sys

# Hardcoded password - security issue
PASSWORD = "admin123"

# SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        results = scanner.security_scan(temp_path)
        print(f"Security issues found: {len(results.get('issues', []))}")
    finally:
        Path(temp_path).unlink()


def demo_report_formats():
    """Demo: Different report formats."""
    print("\n" + "=" * 50)
    print("DEMO: Report Formats")
    print("=" * 50)
    
    sample_data = {
        'issues': {
            'critical': [{'message': 'SQL injection', 'severity': 'critical'}],
            'warning': [{'message': 'Use f-string', 'severity': 'warning'}],
            'info': [{'message': 'Add type hints', 'severity': 'info'}]
        }
    }
    
    generator = ReportGenerator()
    
    print("\n--- TEXT FORMAT ---")
    print(generator.generate(sample_data, format='text'))
    
    print("\n--- JSON FORMAT ---")
    print(generator.generate(sample_data, format='json'))
    
    print("\n--- MARKDOWN FORMAT ---")
    print(generator.generate(sample_data, format='markdown'))


if __name__ == "__main__":
    import tempfile
    demo_basic_scan()
    demo_security_scan()
    demo_report_formats()