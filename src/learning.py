"""Background learning and pattern consolidation.

Inspired by Claude Code's KAIROS autoDream feature:
- Records findings from past reviews
- Learns recurring patterns per project/language
- Consolidates observations during idle time
- Converts vague trends into actionable scan rules

The idea: your code reviewer should get SMARTER over time, not just
re-run the same checks. Every review teaches it something about YOUR codebase.

Usage:
    learner = ReviewLearner()
    learner.record_review(file_path, issues)
    patterns = learner.get_hot_patterns(language="python")
    learner.consolidate()  # run periodically / during idle
"""

import json
import hashlib
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict

from src.models import CodeIssue

logger = logging.getLogger(__name__)

# Default storage location
DEFAULT_DB_PATH = Path.home() / ".ai-code-reviewer" / "learning.json"


@dataclass
class PatternObservation:
    """A single observed pattern from a review."""
    pattern_key: str          # e.g. "security:hardcoded_secret"
    language: str             # e.g. "python"
    file_path: str            # where it was found
    severity: str
    message: str
    timestamp: float = field(default_factory=time.time)
    stage: Optional[str] = None  # which review stage found it


@dataclass
class ConsolidatedPattern:
    """A pattern that has been observed multiple times — now a known issue."""
    pattern_key: str
    language: str
    count: int
    first_seen: float
    last_seen: float
    typical_severity: str
    example_messages: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None
    # After consolidation, we can generate a custom rule
    custom_rule_generated: bool = False


class ReviewLearner:
    """Learns from past reviews to improve future ones.

    Storage: simple JSON file at ~/.ai-code-reviewer/learning.json
    No database needed — this is lightweight by design.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._observations: List[PatternObservation] = []
        self._consolidated: Dict[str, ConsolidatedPattern] = {}
        self._load()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_review(self, file_path: str, issues: List[CodeIssue], language: str = "unknown"):
        """Record issues from a review for learning.

        Call this after every review. It's cheap — just appends to memory.
        """
        for issue in issues:
            key = self._make_pattern_key(issue)
            obs = PatternObservation(
                pattern_key=key,
                language=language,
                file_path=file_path,
                severity=issue.severity,
                message=issue.message,
                stage=issue.stage,
            )
            self._observations.append(obs)

        logger.debug(f"Recorded {len(issues)} observations from {file_path}")

    def _make_pattern_key(self, issue: CodeIssue) -> str:
        """Create a normalized pattern key from an issue.

        Groups similar issues together:
        - "Potential hardcoded secret detected" → "security:hardcoded_secret"
        - "Unused import: json" → "style:unused_import"
        """
        issue_type = issue.type or "unknown"
        msg_lower = issue.message.lower()

        # Normalize common patterns
        if "hardcoded" in msg_lower or "secret" in msg_lower or "password" in msg_lower:
            return f"{issue_type}:hardcoded_secret"
        if "unused import" in msg_lower:
            return f"{issue_type}:unused_import"
        if "eval" in msg_lower or "exec" in msg_lower:
            return f"{issue_type}:dangerous_exec"
        if "empty except" in msg_lower:
            return f"{issue_type}:empty_except"
        if "sql" in msg_lower and "inject" in msg_lower:
            return f"{issue_type}:sql_injection"
        if "string concatenation" in msg_lower and "loop" in msg_lower:
            return f"{issue_type}:string_concat_in_loop"
        if "todo" in msg_lower or "fixme" in msg_lower:
            return f"{issue_type}:todo_comment"

        # Fallback: hash the message for grouping
        msg_hash = hashlib.md5(issue.message.encode()).hexdigest()[:8]
        return f"{issue_type}:{msg_hash}"

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_hot_patterns(self, language: Optional[str] = None, limit: int = 10) -> List[ConsolidatedPattern]:
        """Get the most frequently seen patterns.

        Args:
            language: Filter by language (None = all)
            limit: Max patterns to return

        Returns:
            List of consolidated patterns, sorted by frequency (highest first)
        """
        patterns = list(self._consolidated.values())

        if language:
            patterns = [p for p in patterns if p.language == language]

        patterns.sort(key=lambda p: p.count, reverse=True)
        return patterns[:limit]

    def get_project_summary(self) -> Dict[str, Any]:
        """Get a summary of what the learner knows about this project."""
        total_obs = len(self._observations)
        total_patterns = len(self._consolidated)

        # Top issues by severity
        severity_counts = Counter(obs.severity for obs in self._observations)

        # Top languages
        lang_counts = Counter(obs.language for obs in self._observations)

        # Most common pattern keys
        pattern_counts = Counter(obs.pattern_key for obs in self._observations)

        return {
            "total_observations": total_obs,
            "unique_patterns": total_patterns,
            "severity_distribution": dict(severity_counts),
            "languages": dict(lang_counts.most_common(10)),
            "top_patterns": [
                {"pattern": k, "count": v}
                for k, v in pattern_counts.most_common(10)
            ],
        }

    def should_prioritize_stage(self, stage: str, language: str) -> bool:
        """Check if a review stage is historically important for this codebase.

        E.g., if 80% of findings are security issues → always run security stage first.
        """
        stage_patterns = [
            p for p in self._consolidated.values()
            if p.pattern_key.startswith(f"{stage}:") and p.language == language
        ]
        total = sum(p.count for p in self._consolidated.values() if p.language == language)
        if total == 0:
            return False

        stage_total = sum(p.count for p in stage_patterns)
        return (stage_total / total) > 0.3  # >30% of findings = prioritize

    # ------------------------------------------------------------------
    # Consolidation (the "autoDream" step)
    # ------------------------------------------------------------------

    def consolidate(self) -> Dict[str, Any]:
        """Consolidate raw observations into patterns.

        This is the "autoDream" step — runs during idle time:
        1. Groups observations by pattern key
        2. Merges similar patterns, removes contradictions
        3. Updates frequency counts
        4. Marks patterns as "known issues" if they appear enough

        Returns:
            Summary of what was consolidated
        """
        logger.info(f"Consolidating {len(self._observations)} observations...")

        # Group observations by pattern key
        grouped: Dict[str, List[PatternObservation]] = defaultdict(list)
        for obs in self._observations:
            grouped[obs.pattern_key].append(obs)

        new_consolidated = 0
        updated = 0

        for key, obs_list in grouped.items():
            # Determine the most common language and severity
            lang_counts = Counter(o.language for o in obs_list)
            sev_counts = Counter(o.severity for o in obs_list)
            top_lang = lang_counts.most_common(1)[0][0]
            top_severity = sev_counts.most_common(1)[0][0]

            # Collect unique example messages (max 3)
            seen_msgs = set()
            examples = []
            for o in obs_list:
                if o.message not in seen_msgs:
                    seen_msgs.add(o.message)
                    examples.append(o.message)
                if len(examples) >= 3:
                    break

            timestamps = [o.timestamp for o in obs_list]

            if key in self._consolidated:
                # Update existing pattern
                cp = self._consolidated[key]
                cp.count = len(obs_list)
                cp.last_seen = max(timestamps)
                cp.typical_severity = top_severity
                cp.example_messages = examples
                updated += 1
            else:
                # New pattern
                self._consolidated[key] = ConsolidatedPattern(
                    pattern_key=key,
                    language=top_lang,
                    count=len(obs_list),
                    first_seen=min(timestamps),
                    last_seen=max(timestamps),
                    typical_severity=top_severity,
                    example_messages=examples,
                )
                new_consolidated += 1

        # Remove observations older than 30 days from raw storage
        cutoff = time.time() - (30 * 24 * 3600)
        old_count = len(self._observations)
        self._observations = [o for o in self._observations if o.timestamp > cutoff]
        pruned = old_count - len(self._observations)

        self._save()

        summary = {
            "new_patterns": new_consolidated,
            "updated_patterns": updated,
            "total_consolidated": len(self._consolidated),
            "observations_pruned": pruned,
            "observations_remaining": len(self._observations),
        }

        logger.info(f"Consolidation complete: {summary}")
        return summary

    # ------------------------------------------------------------------
    # Custom rule generation
    # ------------------------------------------------------------------

    def generate_custom_rules(self, min_count: int = 3) -> List[Dict[str, Any]]:
        """Generate custom scan rules from consolidated patterns.

        If a pattern appears >= min_count times, we can generate a
        regex-based or AST-based rule to catch it without AI.

        Args:
            min_count: Minimum occurrences before generating a rule
        """
        rules = []
        for key, pattern in self._consolidated.items():
            if pattern.count >= min_count and not pattern.custom_rule_generated:
                rule = self._pattern_to_rule(pattern)
                if rule:
                    rules.append(rule)
                    pattern.custom_rule_generated = True

        if rules:
            self._save()

        return rules

    def _pattern_to_rule(self, pattern: ConsolidatedPattern) -> Optional[Dict[str, Any]]:
        """Convert a consolidated pattern into a custom scan rule."""
        # Simple rule generation based on pattern type
        if "hardcoded_secret" in pattern.pattern_key:
            return {
                "id": f"learned_{pattern.pattern_key}",
                "type": "regex",
                "severity": pattern.typical_severity,
                "message": f"Learned pattern: hardcoded secret (seen {pattern.count}x in {pattern.language})",
                "suggestion": "Use environment variables or a secrets manager",
                "pattern": r'(?:password|secret|api_key|token)\s*=\s*["\'][^"\']{4,}["\']',
                "languages": [pattern.language],
            }
        if "unused_import" in pattern.pattern_key:
            return {
                "id": f"learned_{pattern.pattern_key}",
                "type": "ast",
                "severity": pattern.typical_severity,
                "message": f"Learned pattern: unused import (seen {pattern.count}x in {pattern.language})",
                "suggestion": "Remove unused imports to keep code clean",
                "languages": [pattern.language],
            }
        if "empty_except" in pattern.pattern_key:
            return {
                "id": f"learned_{pattern.pattern_key}",
                "type": "regex",
                "severity": pattern.typical_severity,
                "message": f"Learned pattern: empty except block (seen {pattern.count}x)",
                "suggestion": "Handle the exception or at minimum log it",
                "pattern": r"except\s+\w+\s*:\s*\n\s*pass",
                "languages": [pattern.language],
            }
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        """Load learning data from disk."""
        if not self.db_path.exists():
            return
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f)

            self._observations = [
                PatternObservation(**obs) for obs in data.get("observations", [])
            ]
            self._consolidated = {
                k: ConsolidatedPattern(**v) for k, v in data.get("consolidated", {}).items()
            }
            logger.debug(f"Loaded {len(self._observations)} observations, {len(self._consolidated)} patterns")
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")

    def _save(self):
        """Save learning data to disk."""
        try:
            data = {
                "observations": [asdict(o) for o in self._observations],
                "consolidated": {k: asdict(v) for k, v in self._consolidated.items()},
                "updated_at": time.time(),
            }
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save learning data: {e}")

    def clear(self):
        """Clear all learning data."""
        self._observations.clear()
        self._consolidated.clear()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("Learning data cleared")
