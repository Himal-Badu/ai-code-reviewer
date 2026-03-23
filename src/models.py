"""Shared data structures for AI Code Reviewer."""

from dataclasses import dataclass
from typing import Optional


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