"""AI client for code analysis using OpenAI.

This module provides AI-powered code analysis using OpenAI's GPT models.
It can detect bugs, security issues, code smells, and best practice violations.
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import hashlib

from openai import OpenAI
from openai import RateLimitError, APIError, Timeout
from src.models import CodeIssue

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for AI analysis."""
    temperature: float = 0.3
    max_tokens: int = 2000
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 60


class AIClient:
    """Handles AI-powered code analysis using OpenAI."""

    SYSTEM_PROMPT = """You are an expert code reviewer analyzing code for:
1. Bugs and logical errors
2. Security vulnerabilities (OWASP Top 10)
3. Code smells and anti-patterns
4. Performance issues
5. Best practices violations
6. Maintainability concerns

For each issue found, provide:
- severity: critical, high, medium, or low
- type: bug, security, performance, style, or best_practice
- message: brief description of the issue
- suggestion: how to fix it

Respond in JSON format with an array of issues."""

    def __init__(self, config: "Config", analysis_config: Optional[AnalysisConfig] = None):
        self.config = config
        self.analysis_config = analysis_config or AnalysisConfig()
        self.client = OpenAI(
            api_key=config.get("api_key"),
            timeout=self.analysis_config.timeout,
            max_retries=self.analysis_config.max_retries,
        )
        self.model = config.get("model", "gpt-4")
        self._request_cache: Dict[str, List[CodeIssue]] = {}

    def analyze_code(self, file_path: Path) -> List[CodeIssue]:
        """Analyze a code file using AI.
        
        Implements caching to avoid redundant API calls for the same file content.
        """
        logger.debug(f"AI analyzing file: {file_path}")
        
        if not self.config.get("api_key"):
            # Return empty if no API key (for testing or local rules only)
            logger.debug("No API key configured, skipping AI analysis")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return []

        # Check cache using file content hash
        cache_key = self._get_cache_key(file_path, code)
        if cache_key in self._request_cache:
            logger.debug(f"Using cached analysis for {file_path}")
            return self._request_cache[cache_key]

        # Skip files that are too large
        if len(code) > 50000:
            logger.warning(f"File {file_path} exceeds size limit, skipping")
            return []

        try:
            issues = self._perform_analysis(file_path, code)
            
            # Cache successful results
            if issues:
                self._request_cache[cache_key] = issues
            
            return issues

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for {file_path}: {e}")
            return []
        except Timeout as e:
            logger.warning(f"Request timeout for {file_path}: {e}")
            return []
        except APIError as e:
            logger.warning(f"API error for {file_path}: {e}")
            return []
        except Exception as e:
            # Return empty list on error, don't break the review
            logger.warning(f"AI analysis failed for {file_path}: {e}")
            return []

    def _get_cache_key(self, file_path: Path, code: str) -> str:
        """Generate cache key from file path and content."""
        content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        return f"{file_path}:{content_hash}"

    def _perform_analysis(self, file_path: Path, code: str) -> List[CodeIssue]:
        """Perform the actual AI analysis."""
        prompt = f"""Analyze this code file: {file_path.name}

```
{code}
```

{SYSTEM_PROMPT}

Respond with a JSON array of issues found. If no issues, return an empty array []."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.analysis_config.temperature,
            max_tokens=self.analysis_config.max_tokens,
        )

        content = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            issues_data = self._parse_json_response(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return []

        # Convert to CodeIssue objects
        issues = []
        for item in issues_data:
            issues.append(CodeIssue(
                severity=item.get("severity", "medium"),
                type=item.get("type", "best_practice"),
                message=item.get("message", "Issue found"),
                file=str(file_path),
                line_number=item.get("line_number", 0),
                suggestion=item.get("suggestion"),
                confidence=item.get("confidence", "high"),
            ))

        return issues

    def _parse_json_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON from AI response, handling various formats."""
        content = content.strip()
        
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1]
            if "```" in content:
                content = content.split("```")[0]
        elif "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        # Try parsing again
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.warning("Could not parse AI response as JSON")
            return []

    def clear_cache(self):
        """Clear the analysis cache."""
        self._request_cache.clear()
        logger.debug("AI analysis cache cleared")


class LocalAIClient:
    """Fallback client for when no API key is available."""

    def __init__(self, config: "Config"):
        self.config = config

    def analyze_code(self, file_path: Path) -> List[CodeIssue]:
        """Run local rule-based analysis only."""
        return []


def get_ai_client(config: "Config") -> AIClient:
    """Factory function to get the appropriate AI client."""
    if config.get("api_key"):
        return AIClient(config)
    return LocalAIClient(config)