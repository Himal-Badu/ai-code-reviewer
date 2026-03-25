"""Filter module for filtering scan results."""

from typing import List, Dict, Any, Callable, Optional


class Filter:
    """Base filter class."""
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results."""
        return results


class SeverityFilter(Filter):
    """Filter by severity level."""
    
    def __init__(self, min_severity: str = "info"):
        self.min_severity = min_severity
        
        self.levels = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "info": 1
        }
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter by minimum severity."""
        min_level = self.levels.get(self.min_severity, 1)
        
        filtered = []
        for result in results:
            severity = result.get("severity", "info")
            level = self.levels.get(severity, 1)
            if level >= min_level:
                filtered.append(result)
        
        return filtered


class TypeFilter(Filter):
    """Filter by issue type."""
    
    def __init__(self, include_types: Optional[List[str]] = None, exclude_types: Optional[List[str]] = None):
        self.include_types = include_types
        self.exclude_types = exclude_types or []
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter by type."""
        filtered = []
        
        for result in results:
            issue_type = result.get("type", "")
            
            if self.include_types and issue_type not in self.include_types:
                continue
            
            if issue_type in self.exclude_types:
                continue
            
            filtered.append(result)
        
        return filtered


class PathFilter(Filter):
    """Filter by file path."""
    
    def __init__(self, include_patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None):
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns or []
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter by path."""
        filtered = []
        
        for result in results:
            path = result.get("file_path", "")
            
            if self.include_patterns:
                if not any(p in path for p in self.include_patterns):
                    continue
            
            if any(p in path for p in self.exclude_patterns):
                continue
            
            filtered.append(result)
        
        return filtered


class CustomFilter(Filter):
    """Custom filter with callable."""
    
    def __init__(self, filter_func: Callable[[Dict[str, Any]], bool]):
        self.filter_func = filter_func
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply custom filter."""
        return [r for r in results if self.filter_func(r)]


class FilterChain:
    """Chain multiple filters together."""
    
    def __init__(self):
        self.filters: List[Filter] = []
    
    def add_filter(self, filter: Filter) -> 'FilterChain':
        """Add a filter to the chain."""
        self.filters.append(filter)
        return self
    
    def apply(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all filters in chain."""
        filtered = results
        for f in self.filters:
            filtered = f.filter(filtered)
        return filtered