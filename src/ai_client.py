"""Universal AI client for code analysis.

Works with ANY LLM provider that has an API key. Built-in support for:
- OpenAI (GPT-4o, GPT-5)
- Anthropic (Claude)
- Google (Gemini)
- Groq (free, fast — Llama, Mixtral)
- Mistral AI
- DeepSeek
- OpenRouter (access 200+ models)
- Together AI
- Any OpenAI-compatible endpoint (custom base_url)

Just add your API key and the tool auto-detects the provider.
Or manually specify provider + model.

Architecture inspired by Claude Code's cache-aware prompt system.
"""

import os
import logging
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


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    base_url: str
    default_model: str
    env_var: str
    api_style: str  # "openai" or "anthropic" or "google"


# All supported providers
PROVIDERS: Dict[str, ProviderConfig] = {
    # Major providers
    "openai": ProviderConfig(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        env_var="OPENAI_API_KEY",
        api_style="openai",
    ),
    "anthropic": ProviderConfig(
        name="Anthropic",
        base_url="https://api.anthropic.com",
        default_model="claude-sonnet-4-20250514",
        env_var="ANTHROPIC_API_KEY",
        api_style="anthropic",
    ),
    "google": ProviderConfig(
        name="Google",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-2.0-flash",
        env_var="GOOGLE_API_KEY",
        api_style="google",
    ),
    # Free / cheap providers (OpenAI-compatible)
    "groq": ProviderConfig(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        env_var="GROQ_API_KEY",
        api_style="openai",
    ),
    "deepseek": ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        env_var="DEEPSEEK_API_KEY",
        api_style="openai",
    ),
    "mistral": ProviderConfig(
        name="Mistral",
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-large-latest",
        env_var="MISTRAL_API_KEY",
        api_style="openai",
    ),
    "openrouter": ProviderConfig(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct",
        env_var="OPENROUTER_API_KEY",
        api_style="openai",
    ),
    "together": ProviderConfig(
        name="Together AI",
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        env_var="TOGETHER_API_KEY",
        api_style="openai",
    ),
    "ollama": ProviderConfig(
        name="Ollama (local)",
        base_url="http://localhost:11434/v1",
        default_model="llama3.1",
        env_var="OLLAMA_API_KEY",
        api_style="openai",
    ),
}

# All known env vars (for auto-detection, in priority order)
ALL_ENV_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "TOGETHER_API_KEY",
    "OLLAMA_API_KEY",
    "AI_API_KEY",  # generic fallback
]


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

class OpenAICompatibleClient:
    """Generic OpenAI-compatible client (works with Groq, DeepSeek, Mistral, etc.)."""

    def __init__(self, api_key: str, model: str, base_url: str, config: AnalysisConfig):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
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
    """Anthropic (Claude) provider — uses native API."""

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
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""


class GoogleClient:
    """Google Gemini provider — uses native API."""

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
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return part["text"]
        return ""


# ---------------------------------------------------------------------------
# Provider detection and client creation
# ---------------------------------------------------------------------------

def _detect_provider_from_env() -> Optional[str]:
    """Detect provider from environment variables."""
    for env_var in ALL_ENV_VARS:
        if os.environ.get(env_var):
            # Match env var to provider
            for prov_id, prov in PROVIDERS.items():
                if prov.env_var == env_var:
                    return prov_id
            # Generic AI_API_KEY — default to openai-compatible
            if env_var == "AI_API_KEY":
                return "openai"
    return None


def _detect_provider_from_config(config: "Config") -> Optional[str]:
    """Detect provider from config."""
    # Explicit provider
    provider = config.get("provider")
    if provider:
        return provider

    # Check for provider-specific api key in config
    for prov_id in PROVIDERS:
        key = config.get(f"{prov_id}.api_key") or config.get("api_key")
        if key:
            return prov_id

    return None


def create_client(config: "Config", analysis_config: Optional[AnalysisConfig] = None) -> tuple:
    """Create an AI client based on available config/env.

    Returns:
        (client_instance, provider_name, model_name) or (None, None, None)
    """
    ac = analysis_config or AnalysisConfig()

    # 1. Try config
    provider_id = _detect_provider_from_config(config)
    if not provider_id:
        # 2. Try environment
        provider_id = _detect_provider_from_env()

    if not provider_id:
        return None, None, None

    prov = PROVIDERS.get(provider_id)
    if not prov:
        # Unknown provider — treat as openai-compatible with custom base_url
        api_key = config.get("api_key") or os.environ.get("AI_API_KEY", "")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model", "gpt-4o")
        if api_key:
            client = OpenAICompatibleClient(api_key, model, base_url, ac)
            return client, provider_id, model
        return None, None, None

    # Get API key
    api_key = config.get("api_key") or config.get(f"{provider_id}.api_key") or os.environ.get(prov.env_var, "")
    if not api_key:
        # For Ollama, no key is fine
        if provider_id == "ollama":
            api_key = "ollama"
        else:
            return None, None, None

    model = config.get("model") or prov.default_model
    base_url = config.get("base_url") or prov.base_url

    # Create appropriate client
    if prov.api_style == "anthropic":
        client = AnthropicClient(api_key, model, ac)
    elif prov.api_style == "google":
        client = GoogleClient(api_key, model, ac)
    else:
        # OpenAI-compatible (covers OpenAI, Groq, DeepSeek, Mistral, etc.)
        client = OpenAICompatibleClient(api_key, model, base_url, ac)

    return client, provider_id, model


# ---------------------------------------------------------------------------
# Main AI Client
# ---------------------------------------------------------------------------

class AIClient:
    """Universal AI code review client.

    Works with ANY LLM provider. Auto-detects from environment or config.
    Supports: OpenAI, Anthropic, Google, Groq, DeepSeek, Mistral,
    OpenRouter, Together AI, Ollama, and any OpenAI-compatible endpoint.
    """

    def __init__(self, config: "Config", analysis_config: Optional[AnalysisConfig] = None):
        self.config = config
        self.analysis_config = analysis_config or AnalysisConfig()
        self._request_cache: Dict[str, List[CodeIssue]] = {}

        self._client, self.provider, self.model = create_client(config, self.analysis_config)

        if self._client is None:
            raise ValueError(
                "No AI provider configured. Set an API key:\n"
                "  export OPENAI_API_KEY=sk-...\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "  export GROQ_API_KEY=gsk_...\n"
                "  Or any provider — see 'python -m src.cli stats'"
            )

        prov_name = PROVIDERS.get(self.provider, None)
        display_name = prov_name.name if prov_name else self.provider
        logger.info(f"AI client: {display_name} / {self.model}")

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        """Analyze a code file using AI."""
        logger.debug(f"AI analyzing: {file_path} (stage={stage}, provider={self.provider})")

        if not self._client:
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return []

        cache_key = self._get_cache_key(file_path, code, stage)
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]

        if len(code) > 50000:
            logger.warning(f"File {file_path} too large, skipping")
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
            ".php": "php", ".sh": "bash",
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
        except json.JSONDecodeError:
            pass
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


class LocalAIClient:
    """Fallback: static analysis only."""

    def __init__(self, config: "Config"):
        self.config = config

    def analyze_code(self, file_path: Path, stage: Optional[str] = None) -> List[CodeIssue]:
        return []


def get_ai_client(config: "Config"):
    """Factory: returns AIClient if any API key found, LocalAIClient otherwise."""
    # Check all known env vars
    has_key = bool(config.get("api_key"))
    if not has_key:
        for env_var in ALL_ENV_VARS:
            if os.environ.get(env_var):
                has_key = True
                break

    if has_key:
        try:
            return AIClient(config)
        except ValueError:
            pass

    return LocalAIClient(config)
