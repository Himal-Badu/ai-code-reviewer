"""Test configuration for pytest."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_results():
    """Provide sample results for testing."""
    return {
        "file": "test.py",
        "language": "python",
        "issues": [
            {
                "severity": "high",
                "type": "security",
                "message": "Hardcoded secret detected",
                "file": "test.py",
                "line_number": 5,
                "suggestion": "Use environment variables",
            },
            {
                "severity": "medium",
                "type": "style",
                "message": "Variable name too short",
                "file": "test.py",
                "line_number": 10,
                "suggestion": "Use more descriptive name",
            },
        ],
        "stats": {
            "files_analyzed": 1,
            "lines_of_code": 50,
        },
    }