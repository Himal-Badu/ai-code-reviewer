"""Utilities for AI Code Reviewer."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import os


def get_file_language(file_path: str) -> Optional[str]:
    """Detect programming language from file extension."""
    ext_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React',
        '.tsx': 'React',
        '.java': 'Java',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.md': 'Markdown',
        '.sql': 'SQL',
        '.sh': 'Shell',
        '.bash': 'Bash'
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext)


def should_exclude(path: str, exclude_patterns: List[str]) -> bool:
    """Check if path should be excluded."""
    path_obj = Path(path)
    path_str = str(path_obj)
    
    for pattern in exclude_patterns:
        if pattern in path_str:
            return True
        if path_obj.match(pattern):
            return True
    
    return False


def count_lines_of_code(file_path: str) -> int:
    """Count lines of code in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def extract_code_snippet(content: str, line_number: int, context: int = 2) -> str:
    """Extract code snippet around a line."""
    lines = content.split('\n')
    start = max(0, line_number - context - 1)
    end = min(len(lines), line_number + context)
    return '\n'.join(lines[start:end])


def sanitize_path(path: str) -> str:
    """Sanitize file path for display."""
    return path.replace(os.getcwd(), '.').replace('\\', '/')


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_gitignore_patterns() -> List[str]:
    """Get patterns from .gitignore if available."""
    patterns = []
    gitignore_path = Path('.gitignore')
    
    if gitignore_path.exists():
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    
    return patterns


def detect_secrets(content: str) -> List[Dict[str, Any]]:
    """Detect potential secrets in code."""
    patterns = {
        'API Key': r'[a-zA-Z0-9]{32,}',
        'AWS Key': r'AKIA[0-9A-Z]{16}',
        'Private Key': r'-----BEGIN [A-Z ]+ PRIVATE KEY-----',
        'Password': r'password\s*=\s*["\'][^"\']+["\']',
        'Token': r'token\s*=\s*["\'][^"\']+["\']'
    }
    
    secrets = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, content, re.IGNORECASE):
            secrets.append({
                'type': name,
                'match': match.group()[:50] + '...' if len(match.group()) > 50 else match.group()
            })
    
    return secrets


def calculate_complexity(code: str) -> Dict[str, int]:
    """Calculate code complexity metrics."""
    lines = code.split('\n')
    
    # Count functions
    functions = len(re.findall(r'def\s+\w+\s*\(', code))
    
    # Count classes
    classes = len(re.findall(r'class\s+\w+', code))
    
    # Count conditionals
    conditionals = len(re.findall(r'\b(if|elif|while|for)\b', code))
    
    return {
        'functions': functions,
        'classes': classes,
        'conditionals': conditionals,
        'lines': len(lines)
    }