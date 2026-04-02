"""Models and data structures for AI Code Reviewer."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueType(Enum):
    """Types of issues that can be detected."""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"
    CODE_SMELL = "code_smell"


@dataclass
class Issue:
    """Represents a code issue."""
    severity: Severity
    issue_type: IssueType
    message: str
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    cwe_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            'severity': self.severity.value,
            'type': self.issue_type.value,
            'message': self.message,
            'line_number': self.line_number,
            'file_path': self.file_path,
            'code_snippet': self.code_snippet,
            'suggestion': self.suggestion,
            'cwe_id': self.cwe_id
        }


@dataclass
class CodeIssue:
    """Unified code issue used across the analyzer and AI pipeline."""
    severity: str = "medium"
    type: str = "best_practice"
    message: str = ""
    file: str = ""
    line_number: int = 0
    suggestion: Optional[str] = None
    confidence: str = "high"
    stage: Optional[str] = None  # Which review stage found this

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'severity': self.severity,
            'type': self.type,
            'message': self.message,
            'file': self.file,
            'line_number': self.line_number,
            'suggestion': self.suggestion,
            'confidence': self.confidence,
            'stage': self.stage,
        }


@dataclass
class ReviewStageResult:
    """Result from a single review stage in the multi-agent pipeline."""
    stage_name: str
    issues: List[CodeIssue] = field(default_factory=list)
    duration_ms: float = 0.0
    tokens_used: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'stage_name': self.stage_name,
            'issues': [i.to_dict() for i in self.issues],
            'duration_ms': self.duration_ms,
            'tokens_used': self.tokens_used,
            'error': self.error,
        }


@dataclass
class FileResult:
    """Result of scanning a single file."""
    file_path: str
    issues: List[Issue] = field(default_factory=list)
    lines_of_code: int = 0
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'issues': [i.to_dict() for i in self.issues],
            'lines_of_code': self.lines_of_code,
            'scan_time': self.scan_time,
            'errors': self.errors
        }


@dataclass
class ScanResult:
    """Complete scan result."""
    total_files: int = 0
    files_scanned: int = 0
    files_with_issues: int = 0
    total_issues: int = 0
    issues_by_severity: Dict[Severity, int] = field(default_factory=dict)
    issues_by_type: Dict[IssueType, int] = field(default_factory=dict)
    file_results: List[FileResult] = field(default_factory=list)
    scan_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    ai_summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_files': self.total_files,
            'files_scanned': self.files_scanned,
            'files_with_issues': self.files_with_issues,
            'total_issues': self.total_issues,
            'issues_by_severity': {k.value: v for k, v in self.issues_by_severity.items()},
            'issues_by_type': {k.value: v for k, v in self.issues_by_type.items()},
            'file_results': [f.to_dict() for f in self.file_results],
            'scan_time': self.scan_time,
            'timestamp': self.timestamp.isoformat(),
            'ai_summary': self.ai_summary
        }


@dataclass
class ProjectStats:
    """Statistics about a project."""
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    largest_file: Optional[str] = None
    newest_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_files': self.total_files,
            'total_lines': self.total_lines,
            'languages': self.languages,
            'largest_file': self.largest_file,
            'newest_file': self.newest_file
        }
