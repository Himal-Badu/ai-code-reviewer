"""Version information for AI Code Reviewer."""

__version__ = "2.0.0"
__author__ = "Himal Badu"
__email__ = "himalbaduhimalbadu@gmail.com"
__license__ = "MIT"
__description__ = "Multi-agent AI code review tool with cache-aware prompts and background learning"
__url__ = "https://github.com/Himal-Badu/ai-code-reviewer"

VERSION_INFO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

VERSIONS = {
    "1.0.0": {
        "release_date": "2026-03-25",
        "features": [
            "Bug detection",
            "Security scanning",
            "AI-powered analysis",
            "Multiple output formats"
        ]
    },
    "2.0.0": {
        "release_date": "2026-04-02",
        "features": [
            "Multi-agent review pipeline (4 specialized stages)",
            "Cache-aware prompt architecture (lower cost, faster)",
            "Background learning (KAIROS-inspired pattern consolidation)",
            "Parallel stage execution (ThreadPoolExecutor)",
            "Deduplication across review stages",
            "Severity-filtered output",
            "Markdown report generation",
            "Custom rule generation from learned patterns",
            "Learning insights dashboard",
        ]
    }
}


def get_version() -> str:
    """Get version string."""
    return __version__


def get_version_info() -> dict:
    """Get detailed version info."""
    return VERSIONS.get(__version__, {})


def is_compatible(version: str) -> bool:
    """Check if version is compatible."""
    current = tuple(map(int, __version__.split('.')))
    target = tuple(map(int, version.split('.')))
    return current[0] == target[0]
