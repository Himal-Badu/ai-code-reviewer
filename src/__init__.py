"""AI Code Reviewer - Automated code analysis with AI."""

__version__ = "1.0.0"
__author__ = "Himal Badu, AI Founder"

from src.analyzer import CodeAnalyzer
from src.ai_client import AIClient
from src.models import CodeIssue

__all__ = ["CodeAnalyzer", "AIClient", "CodeIssue"]