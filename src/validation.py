"""Validation module for AI Code Reviewer."""

from typing import Dict, Any, List, Optional
from pathlib import Path
import re


class Validator:
    """Base validator."""
    
    def validate(self, data: Any) -> bool:
        """Validate data."""
        return True
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return []


class ConfigValidator(Validator):
    """Validate configuration."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate configuration."""
        self.errors = []
        
        if 'version' not in config:
            self.errors.append("Missing 'version' field")
        
        if 'scanner' in config:
            scanner = config['scanner']
            if not isinstance(scanner.get('enabled'), bool):
                self.errors.append("scanner.enabled must be boolean")
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors


class PathValidator(Validator):
    """Validate file paths."""
    
    def __init__(self, allowed_extensions: Optional[List[str]] = None):
        self.allowed_extensions = allowed_extensions or ['.py', '.js', '.ts', '.java', '.go']
        self.errors: List[str] = []
    
    def validate(self, path: str) -> bool:
        """Validate file path."""
        self.errors = []
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            self.errors.append(f"Path does not exist: {path}")
            return False
        
        if path_obj.is_file():
            if path_obj.suffix not in self.allowed_extensions:
                self.errors.append(f"Extension {path_obj.suffix} not allowed")
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors


class CodeValidator(Validator):
    """Validate code content."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate(self, code: str) -> bool:
        """Validate code content."""
        self.errors = []
        
        if not code or not code.strip():
            self.errors.append("Code is empty")
            return False
        
        if len(code) > 1000000:
            self.errors.append("Code exceeds maximum size (1MB)")
            return False
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors


class ResultValidator(Validator):
    """Validate scan results."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate(self, results: Dict[str, Any]) -> bool:
        """Validate scan results."""
        self.errors = []
        
        required_fields = ['issues', 'file_results']
        for field in required_fields:
            if field not in results:
                self.errors.append(f"Missing required field: {field}")
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors


def validate_api_key(key: str) -> bool:
    """Validate API key format."""
    if not key:
        return False
    
    if len(key) < 20:
        return False
    
    return True


def validate_severity(severity: str) -> bool:
    """Validate severity level."""
    valid_severities = ['critical', 'high', 'medium', 'low', 'info']
    return severity.lower() in valid_severities


def validate_file_size(size_bytes: int, max_size: int = 10485760) -> bool:
    """Validate file size."""
    return 0 < size_bytes < max_size