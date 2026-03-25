"""
Benchmarks for AI Code Reviewer performance testing.
"""

import time
import tempfile
from pathlib import Path
import pytest
from src.scanner import CodeScanner


class Benchmark:
    """Benchmark runner."""
    
    def __init__(self):
        self.results = {}
    
    def run(self, name: str, func: callable) -> float:
        """Run benchmark and return duration."""
        start = time.time()
        func()
        duration = time.time() - start
        self.results[name] = duration
        return duration
    
    def get_results(self) -> dict:
        """Get benchmark results."""
        return self.results


def benchmark_scanner_empty_dir():
    """Benchmark scanner with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scanner = CodeScanner()
        scanner.scan(tmpdir)


def benchmark_scanner_single_file():
    """Benchmark scanner with single file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("print('hello')\n" * 100)
        
        scanner = CodeScanner()
        scanner.scan(str(test_file))


def benchmark_scanner_large_file():
    """Benchmark scanner with large file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("print('hello')\n" * 10000)
        
        scanner = CodeScanner()
        scanner.scan(str(test_file))


def benchmark_multiple_files():
    """Benchmark scanner with multiple files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(10):
            test_file = Path(tmpdir) / f"test{i}.py"
            test_file.write_text(f"print('test{i}')\n" * 100)
        
        scanner = CodeScanner()
        scanner.scan(tmpdir)


if __name__ == "__main__":
    b = Benchmark()
    
    print("Running benchmarks...")
    b.run("empty_dir", benchmark_scanner_empty_dir)
    b.run("single_file", benchmark_scanner_single_file)
    b.run("large_file", benchmark_scanner_large_file)
    b.run("multiple_files", benchmark_multiple_files)
    
    print("\nResults:")
    for name, duration in b.get_results().items():
        print(f"  {name}: {duration:.4f}s")