"""Exception classes for AI Code Reviewer."""


class AICodeReviewerError(Exception):
    """Base exception for AI Code Reviewer."""
    pass


class ConfigurationError(AICodeReviewerError):
    """Configuration related errors."""
    pass


class ScanError(AICodeReviewerError):
    """Scanning related errors."""
    pass


class AnalysisError(AICodeReviewerError):
    """Analysis related errors."""
    pass


class ReportError(AICodeReviewerError):
    """Report generation errors."""
    pass


class CacheError(AICodeReviewerError):
    """Cache related errors."""
    pass


class APIError(AICodeReviewerError):
    """API related errors."""
    pass


class ValidationError(AICodeReviewerError):
    """Validation errors."""
    pass


class TimeoutError(AICodeReviewerError):
    """Timeout errors."""
    pass


class AuthenticationError(AICodeReviewerError):
    """Authentication errors."""
    pass


class RateLimitError(AICodeReviewerError):
    """Rate limit errors."""
    pass