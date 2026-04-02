"""Universal AI client for code analysis.

Supports multiple AI providers — just add your API key and go:
- OpenAI (GPT-4, GPT-5) → OPENAI_API_KEY
- Anthropic (Claude) → ANTHROPIC_API_KEY
- Google (Gemini) → GOOGLE_API_KEY

Architecture inspired by Claude Code's cache-aware prompt system:
- STATIC layer: system identity, tool definitions, review rules (cached)
- DYNAMIC layer: file content, language context, project-specific config
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import hashlib

from src.models import CodeIssue

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt layers (shared across all providers)
# ---------------------------------------------------------------------------

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

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.0-flash",
}

# Environment variable names for each provider
PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


@dataclass
class AnalysisConfig:
    """Configuration for AI analysis."""
    temperature: float = 0.1
    max_tokens: int = 2000
    max_retries: int = 3
    timeout: int = 60


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

class OpenAIClient:
    """OpenAI (GPT-4, GPT-5) provider."""

    def __init__(self, api_key: str, model: str, config: AnalysisConfig):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, timeout=config.timeout, max_retries=config.max_retries)
        self.model = model
        self.config = config

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""


class AnthropicClient:
    """Anthropic (Claude) provider."""

    def __init__(self, api_key: str, model: str, config: AnalysisConfig):
        import httpx
        self.api_key = api_key
        self.model = model
        self.config = config
        self._http = httpx.Client(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=config.timeout,
        )

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        resp = self._http.post("/v1/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Extract text from content blocks
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""


class GoogleClient:
    """Google Gemini provider."""

    def __init__(self, api_key: str, model: str, config: AnalysisConfig):
        import httpx
        self.api_key = api_key
        self.model = model
        self.config = config
        self._http = httpx.Client(timeout=config.timeout)

    def complete(self, system: str, user: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        resp = self._http.post(url, json=payload, params={"key": self.api_key})
        resp.raise_for_status()
        data = resp.json()
        # Extract text from candidates
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return part["text"]
        return ""


# Map provider name to client class
PROVIDER_CLIENTS = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "google": GoogleClient,
}


# ---------------------------------------------------------------------------
# Main AI Client (universal, provider-agnostic)
# ---------------------------------------------------------------------------

class AIClient:
    """Universal AI code review client.

    Supports OpenAI, Anthropic, and Google — just set the right API key.
    Auto-detects provider from available environment variables or config.
    """

    def __init__(self, config: "Config", analysis_config: Optional[AnalysisConfig] = None):
        self.config = config
        self.analysis_config = analysis_config or AnalysisConfig()
        self._request_cache: Dict[str, List[CodeIssue]] = {}

        # Detect provider and API key
        self.provider = self._detect_provider()
        self.api_key = self._resolve_api_key()
        self.model = config.get("model") or DEFAULT_MODELS.get(self.provider, "gpt-4o")

        # Initialize provider client
        if self.provider in PROVIDER_CLIENTS:
            self._client = PROVIDER_CLIENTS[self.provider](
                api_key=self.api_key,
                model=self.model,
                config=self.analysis_config,
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use: openai, anthropic, google")

        logger.info(f"AI client initialized: provider={self.provider}, model={self.model}")

    def _detect_provider(self) -> str:
        """Detect which AI provider to use."""
        # Explicit config takes priority
        provider = self.config.get("provider")
        if provider:
            return provider.lower()

        # Auto-detect from available API keys
        for name, env_var in PROVIDER_ENV_KEYS.items():
            if os.environ.get(env_var):
                return name

        # Check config for any provider's api_key
        if self.config.get("api_key"):
            # Default to openai if just api_key is set
            return "openai"

        return "openai"  # fallback

    def _resolve_api_key(self) -> str:
        """Resolve the API key for the detected provider."""
        # Check config first
        key = self.config.get("api_key")
        if key:
            return key

        # Check config with provider prefix
        key = self.config.get(f"{self.provider}.api_key")
        if key:
            return key

        # Check environment variable
        env_var = PROVIDER_ENV_KEYS.get(self.provider, "")
        key = os.environ.get(env_var, "")
        if key:
            return key

        # Check all provider env vars
        for name, env_var in PROVIDER_ENV_KEYS.items():
            key = os.environ.get(env_var, "")
            if key:
                return key

        return ""

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        """Analyze a code file using AI.

        Args:
            file_path: Path to the file to analyze
            stage: Optional review stage ("security", "bugs", "performance", "style")
        """
        logger.debug(f"AI analyzing file: {file_path} (stage={stage}, provider={self.provider})")

        if not self.api_key:
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
        except Exception as e:
            logger.warning(f"AI analysis failed for {file_path}: {e}")
            return []

    def _get_cache_key(self, file_path: Path, code: str, stage: Optional[str]) -> str:
        content_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        stage_key = stage or "general"
        return f"{file_path}:{content_hash}:{stage_key}:{self.provider}"

    def _build_messages(self, file_path: Path, code: str, stage: Optional[str]) -> tuple:
        """Build system + user prompts."""
        lang = self._detect_language_hint(file_path)

        if stage and stage in STAGE_PROMPTS:
            system = SYSTEM_PROMPT_STATIC + "\n\n## Specialization\n" + STAGE_PROMPTS[stage]
        else:
            system = SYSTEM_PROMPT_STATIC

        user = f"""## File to Review
**Path**: `{file_path.name}`
**Language**: {lang}
**Size**: {len(code.splitlines())} lines

## Source Code
```{lang}
{code}
```

Analyze this file and return a JSON array of issues found. Return [] if clean."""

        return system, user

    def _perform_analysis(self, file_path: Path, code: str, stage: Optional[str]) -> List[CodeIssue]:
        """Send to AI provider and parse response."""
        system, user = self._build_messages(file_path, code, stage)

        content = self._client.complete(system, user)
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
        if not content:
            return []
        content = content.strip()

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
        self._request_cache.clear()
        logger.debug("AI analysis cache cleared")


class LocalAIClient:
    """Fallback: static analysis only, no AI calls."""

    def __init__(self, config: "Config"):
        self.config = config

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        return []


def get_ai_client(config: "Config") -> Any:
    """Factory: returns AIClient if any API key is found, LocalAIClient otherwise."""
    # Check all possible key sources
    has_key = bool(config.get("api_key"))
    if not has_key:
        for env_var in PROVIDER_ENV_KEYS.values():
            if os.environ.get(env_var):
                has_key = True
                break

    if has_key:
        return AIClient(config)
    return LocalAIClient(config)
