"""Shared data structures for AI Code Reviewer."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SeverityLevel(Enum):
    """Severity levels for code issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """Types of code issues."""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_SMELL = "code_smell"
    BEST_PRACTICE = "best_practice"
    SYNTAX_ERROR = "syntax_error"
    STYLE = "style"


@dataclass
class CodeIssue:
    """Represents a code issue found during analysis."""
    severity: str
    type: str
    message: str
    file: str
    line_number: int
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration
    confidence: str = "high"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "severity": self.severity,
            "type": self.type,
            "message": self.message,
            "file": self.file,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
            "cwe_id": self.cwe_id,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisResult:
    """Result of a code analysis session."""
    file: str
    language: str
    issues: List[CodeIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "file": self.file,
            "language": self.language,
            "issues": [issue.to_dict() for issue in self.issues],
            "stats": self.stats,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


@dataclass
class ReviewSummary:
    """Summary of a complete code review."""
    total_files: int
    total_issues: int
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_type: Dict[str, int] = field(default_factory=dict)
    analysis_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total_files": self.total_files,
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_type": self.issues_by_type,
            "analysis_time": self.analysis_time,
        }