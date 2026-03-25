"""Statistics module for AI Code Reviewer."""

from typing import Dict, Any, List
from collections import defaultdict
import time


class Statistics:
    """Track and analyze review statistics."""
    
    def __init__(self):
        self.scans = []
        self.start_time = None
    
    def start_scan(self):
        """Start tracking a new scan."""
        self.start_time = time.time()
    
    def end_scan(self, results: Dict[str, Any]):
        """End scan and record results."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.scans.append({
                'duration': duration,
                'results': results,
                'timestamp': time.time()
            })
    
    def get_total_scans(self) -> int:
        """Get total number of scans."""
        return len(self.scans)
    
    def get_average_duration(self) -> float:
        """Get average scan duration."""
        if not self.scans:
            return 0.0
        return sum(s['duration'] for s in self.scans) / len(self.scans)
    
    def get_total_issues(self) -> int:
        """Get total issues found."""
        total = 0
        for scan in self.scans:
            results = scan.get('results', {})
            issues = results.get('issues', {})
            total += sum(len(items) for items in issues.values())
        return total
    
    def get_issues_by_type(self) -> Dict[str, int]:
        """Get issues grouped by type."""
        by_type = defaultdict(int)
        for scan in self.scans:
            results = scan.get('results', {})
            issues = results.get('issues', {})
            for category, items in issues.items():
                by_type[category] += len(items)
        return dict(by_type)
    
    def get_most_problematic_files(self, limit: int = 5) -> List[tuple]:
        """Get files with most issues."""
        file_issues = defaultdict(int)
        for scan in self.scans:
            results = scan.get('results', {})
            file_results = results.get('file_results', [])
            for file_result in file_results:
                path = file_result.get('file_path', 'unknown')
                issues = len(file_result.get('issues', []))
                file_issues[path] += issues
        
        sorted_files = sorted(file_issues.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_scans': self.get_total_scans(),
            'average_duration': self.get_average_duration(),
            'total_issues': self.get_total_issues(),
            'issues_by_type': self.get_issues_by_type(),
            'most_problematic_files': self.get_most_problematic_files()
        }


class Metrics:
    """Calculate code quality metrics."""
    
    @staticmethod
    def calculate_maintainability_index(issues: List[Dict]) -> float:
        """Calculate maintainability index (0-100)."""
        if not issues:
            return 100.0
        
        critical_weight = 10
        warning_weight = 5
        info_weight = 1
        
        score = 100.0
        for issue in issues:
            severity = issue.get('severity', 'info')
            if severity == 'critical':
                score -= critical_weight
            elif severity == 'warning':
                score -= warning_weight
            else:
                score -= info_weight
        
        return max(0.0, score)
    
    @staticmethod
    def calculate_security_score(issues: List[Dict]) -> float:
        """Calculate security score (0-100)."""
        security_issues = [i for i in issues if i.get('type') == 'security']
        
        if not security_issues:
            return 100.0
        
        score = 100.0 - (len(security_issues) * 15)
        return max(0.0, score)
    
    @staticmethod
    def calculate_quality_score(issues: List[Dict]) -> float:
        """Calculate overall quality score."""
        maintainability = Metrics.calculate_maintainability_index(issues)
        security = Metrics.calculate_security_score(issues)
        
        return (maintainability + security) / 2