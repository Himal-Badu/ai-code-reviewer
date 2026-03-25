"""Async support for AI Code Reviewer."""

import asyncio
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import aiofiles


class AsyncScanner:
    """Async version of code scanner."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def scan_file(self, file_path: str) -> Dict[str, Any]:
        """Scan a single file asynchronously."""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            # Run sync scanner in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._scan_content,
                file_path,
                content
            )
            return result
        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'issues': []
            }
    
    def _scan_content(self, file_path: str, content: str) -> Dict[str, Any]:
        """Sync scan content."""
        return {
            'file_path': file_path,
            'content_length': len(content),
            'issues': []
        }
    
    async def scan_directory(self, directory: str, extensions: List[str]) -> List[Dict[str, Any]]:
        """Scan directory asynchronously."""
        import os
        from pathlib import Path
        
        files = []
        for ext in extensions:
            files.extend(Path(directory).rglob(f"*{ext}"))
        
        tasks = [self.scan_file(str(f)) for f in files]
        results = await asyncio.gather(*tasks)
        
        return results
    
    def close(self):
        """Close executor."""
        self.executor.shutdown(wait=True)


class AsyncReporter:
    """Async version of report generator."""
    
    def __init__(self):
        pass
    
    async def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate report asynchronously."""
        # Simulate async work
        await asyncio.sleep(0.1)
        
        report = "Async Report\n"
        report += "=" * 40 + "\n"
        report += f"Total files: {len(results)}\n"
        
        return report
    
    async def save_report(self, report: str, output_path: str):
        """Save report to file asynchronously."""
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(report)


async def run_async_scan(directory: str, extensions: List[str]) -> List[Dict[str, Any]]:
    """Run async scan on directory."""
    scanner = AsyncScanner()
    try:
        results = await scanner.scan_directory(directory, extensions)
        return results
    finally:
        scanner.close()