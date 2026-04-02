"""AI Code Reviewer - Automated code analysis with AI.

Architecture inspired by Claude Code's production patterns:
- Multi-agent pipeline with focused review stages
- Cache-aware prompt engineering for lower cost + latency
- Background learning that gets smarter over time

Author: Himal Badu
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Himal Badu"

from src.analyzer import CodeAnalyzer
from src.ai_client import AIClient, get_ai_client
from src.models import CodeIssue, ReviewStageResult
from src.pipeline import ReviewPipeline
from src.learning import ReviewLearner

__all__ = [
    "CodeAnalyzer",
    "AIClient",
    "get_ai_client",
    "CodeIssue",
    "ReviewStageResult",
    "ReviewPipeline",
    "ReviewLearner",
]
