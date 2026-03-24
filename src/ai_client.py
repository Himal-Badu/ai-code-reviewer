"""AI client for code analysis using OpenAI."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from openai import OpenAI
from src.models import CodeIssue

# Configure logging
logger = logging.getLogger(__name__)


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

    def __init__(self, config: "Config"):
        self.config = config
        self.client = OpenAI(api_key=config.get("api_key"))
        self.model = config.get("model", "gpt-4")

    def analyze_code(self, file_path: Path) -> List[CodeIssue]:
        """Analyze a code file using AI."""
        logger.debug(f"AI analyzing file: {file_path}")
        
        if not self.config.get("api_key"):
            # Return empty if no API key (for testing or local rules only)
            logger.debug("No API key configured, skipping AI analysis")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Skip files that are too large
            if len(code) > 50000:
                return []

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
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                issues_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                issues_data = json.loads(content)

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
                ))

            return issues

        except Exception as e:
            # Return empty list on error, don't break the review
            logger.warning(f"AI analysis failed for {file_path}: {e}")
            return []


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