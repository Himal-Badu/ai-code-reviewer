"""AI client for code analysis using OpenAI.

This module provides AI-powered code analysis using OpenAI's GPT models.
Inspired by Claude Code's cache-aware prompt architecture — stable system
instructions are separated from dynamic context to maximize prompt caching
and reduce latency + cost.

Architecture (from Claude Code leak):
- STATIC layer: system identity, tool definitions, review rules (cached)
- DYNAMIC layer: file content, language context, project-specific config
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import hashlib

from openai import OpenAI
from openai import RateLimitError, APIError, Timeout
from src.models import CodeIssue

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache-aware prompt layers (inspired by Claude Code's prompt architecture)
# ---------------------------------------------------------------------------

# STATIC: Never changes between requests — goes FIRST for API prompt caching
SYSTEM_PROMPT_STATIC = """You are an expert code reviewer. You analyze source code for defects, security vulnerabilities, performance problems, and code quality issues.

## Core Rules
1. Be precise — cite exact line numbers when possible
2. Be actionable — every issue must have a concrete fix suggestion
3. Be honest about confidence — say "likely" vs "definitely"
4. Prefer fewer, high-quality findings over many trivial ones
5. Never invent issues that don't exist in the code

## Severity Scale
- **critical**: Will cause crashes, data loss, or security breaches in production
- **high**: Likely bugs, security holes, or serious performance problems
- **medium**: Code smells, missing error handling, potential edge cases
- **low**: Style issues, minor improvements, documentation gaps

## Response Format
Always respond with a valid JSON array. Each element must have:
{
  "severity": "critical|high|medium|low",
  "type": "bug|security|performance|style|best_practice",
  "message": "Brief description of the issue",
  "line_number": 0,
  "suggestion": "How to fix it",
  "confidence": "high|medium|low"
}

Return [] if no issues found. Do not wrap in markdown."""

# STATIC: Review stage personas (each gets a focused subset of the rules)
STAGE_PROMPTS: Dict[str, str] = {
    "security": """You are a SECURITY specialist code reviewer. Focus ONLY on:
- OWASP Top 10 vulnerabilities (injection, broken auth, XSS, etc.)
- Hardcoded secrets, API keys, tokens
- Unsafe deserialization (eval, exec, pickle)
- SQL injection, command injection, path traversal
- Missing input validation and sanitization
- Insecure cryptographic practices

Ignore style, performance, and documentation issues. Only report security findings.""",

    "bugs": """You are a BUG DETECTION specialist. Focus ONLY on:
- Logic errors and off-by-one mistakes
- Null/None dereference risks
- Unhandled exceptions and missing error handling
- Race conditions and concurrency issues
- Edge cases (empty inputs, overflow, type mismatches)
- Unreachable code and dead logic

Ignore security, style, and performance. Only report potential bugs.""",

    "performance": """You are a PERFORMANCE specialist. Focus ONLY on:
- O(n²) or worse algorithmic complexity where O(n) or O(n log n) is possible
- Unnecessary memory allocations in hot paths
- String concatenation in loops (use join/builder instead)
- Missing caching opportunities
- Blocking I/O in async contexts
- N+1 query patterns
- Unbounded data structure growth

Ignore security and style. Only report performance issues.""",

    "style": """You are a CODE QUALITY specialist. Focus ONLY on:
- Naming conventions and clarity
- Function/method length (over 50 lines = too long)
- Class cohesion and single responsibility
- Code duplication (DRY violations)
- Missing or misleading documentation
- Unused imports, variables, dead code
- Complex nested logic that should be refactored

Ignore security and performance. Only report code quality issues.""",
}


@dataclass
class AnalysisConfig:
    """Configuration for AI analysis."""
    temperature: float = 0.1  # Low temp for consistent, factual reviews
    max_tokens: int = 2000
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 60


class AIClient:
    """Handles AI-powered code analysis using OpenAI.

    Uses cache-aware prompt architecture:
    - Static system prompt is sent FIRST (API can cache this)
    - Dynamic file content comes AFTER
    - Each review stage gets a focused specialist persona
    """

    def __init__(self, config: "Config", analysis_config: Optional[AnalysisConfig] = None):
        self.config = config
        self.analysis_config = analysis_config or AnalysisConfig()
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(
            api_key=api_key,
            timeout=self.analysis_config.timeout,
            max_retries=self.analysis_config.max_retries,
        )
        self.model = config.get("model", "gpt-4")
        self._request_cache: Dict[str, List[CodeIssue]] = {}

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        """Analyze a code file using AI.

        Args:
            file_path: Path to the file to analyze
            stage: Optional review stage ("security", "bugs", "performance", "style")
                   If None, runs a general review covering all categories.
        """
        logger.debug(f"AI analyzing file: {file_path} (stage={stage})")

        if not self.config.get("api_key") and not os.environ.get("OPENAI_API_KEY"):
            logger.debug("No API key configured, skipping AI analysis")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return []

        # Check cache
        cache_key = self._get_cache_key(file_path, code, stage)
        if cache_key in self._request_cache:
            logger.debug(f"Using cached analysis for {file_path} (stage={stage})")
            return self._request_cache[cache_key]

        # Skip huge files
        if len(code) > 50000:
            logger.warning(f"File {file_path} exceeds size limit, skipping")
            return []

        try:
            issues = self._perform_analysis(file_path, code, stage)
            for issue in issues:
                if stage:
                    issue.stage = stage
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
            logger.warning(f"AI analysis failed for {file_path}: {e}")
            return []

    def _get_cache_key(self, file_path: Path, code: str, stage: Optional[str]) -> str:
        """Generate cache key from file, content hash, and stage."""
        content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        stage_key = stage or "general"
        return f"{file_path}:{content_hash}:{stage_key}"

    def _build_messages(self, file_path: Path, code: str, stage: Optional[str]) -> List[Dict[str, str]]:
        """Build cache-aware message list.

        Order matters for prompt caching:
        1. System message with STATIC rules (cacheable)
        2. User message with DYNAMIC file content (changes per request)
        """
        lang = self._detect_language_hint(file_path)

        # Choose system prompt based on stage
        if stage and stage in STAGE_PROMPTS:
            system_content = SYSTEM_PROMPT_STATIC + "\n\n## Specialization\n" + STAGE_PROMPTS[stage]
        else:
            system_content = SYSTEM_PROMPT_STATIC

        # Dynamic user content — file-specific, changes every request
        user_content = f"""## File to Review
**Path**: `{file_path.name}`
**Language**: {lang}
**Size**: {len(code.splitlines())} lines

## Source Code
```{lang}
{code}
```

Analyze this file and return a JSON array of issues found. Return [] if clean."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _perform_analysis(self, file_path: Path, code: str, stage: Optional[str]) -> List[CodeIssue]:
        """Perform the actual AI analysis with cache-aware prompts."""
        messages = self._build_messages(file_path, code, stage)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.analysis_config.temperature,
            max_tokens=self.analysis_config.max_tokens,
        )

        content = response.choices[0].message.content
        issues_data = self._parse_json_response(content)

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
                stage=stage,
            ))

        return issues

    def _detect_language_hint(self, file_path: Path) -> str:
        """Detect language from file extension for syntax highlighting."""
        ext_map = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".go": "go",
            ".rs": "rust", ".java": "java", ".rb": "ruby",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp",
            ".php": "php", ".sh": "bash", ".yaml": "yaml",
            ".yml": "yaml", ".json": "json", ".md": "markdown",
        }
        return ext_map.get(file_path.suffix.lower(), "")

    def _parse_json_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON from AI response, handling markdown wrapping."""
        if not content:
            return []
        content = content.strip()

        # Try direct parse
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            pass

        # Extract from markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1]
            if "```" in content:
                content = content.split("```")[0]
        elif "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        try:
            result = json.loads(content.strip())
            return result if isinstance(result, list) else []
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

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        """Run local rule-based analysis only."""
        return []


def get_ai_client(config: "Config") -> AIClient:
    """Factory function to get the appropriate AI client."""
    if config.get("api_key") or os.environ.get("OPENAI_API_KEY"):
        return AIClient(config)
    return LocalAIClient(config)
