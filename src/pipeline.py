"""Multi-agent review pipeline.

Inspired by Claude Code's architecture: instead of one monolithic review call,
we split the review into specialized stages that run focused analyses.

Each stage is a "mini-agent" with its own prompt persona:
- security: OWASP, secrets, injection
- bugs: logic errors, edge cases, null derefs
- performance: complexity, allocations, I/O
- style: naming, duplication, documentation

Stages can run in parallel (threaded) for faster reviews.
Users can select which stages to run — skip what you don't need.

Architecture note (from Claude Code leak):
Claude Code's multi-agent orchestration fits "in a prompt, not a framework."
We follow the same principle: each stage is just a prompt variant + a function call.
No LangChain, no frameworks — just clean prompts and parallel execution.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from src.models import CodeIssue, ReviewStageResult

logger = logging.getLogger(__name__)

# All available review stages
ALL_STAGES = ["security", "bugs", "performance", "style"]

# Severity priority for deduplication (higher = more severe)
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


class ReviewPipeline:
    """Orchestrates multi-stage code review.

    Usage:
        pipeline = ReviewPipeline(ai_client)
        result = pipeline.review_file(pathlib.Path("app.py"))
        result = pipeline.review_file(pathlib.Path("app.py"), stages=["security", "bugs"])
    """

    def __init__(self, ai_client, static_analyzer=None):
        """
        Args:
            ai_client: AIClient instance for AI-powered analysis
            static_analyzer: Optional CodeAnalyzer for local rule-based analysis
        """
        self.ai_client = ai_client
        self.static_analyzer = static_analyzer

    def review_file(
        self,
        file_path: Path,
        stages: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """Run multi-stage review on a single file.

        Args:
            file_path: Path to the file
            stages: Which stages to run. None = all stages.
            parallel: Run stages in parallel using threads (default True)

        Returns:
            Dict with file info, merged issues, and per-stage results
        """
        stages = stages or ALL_STAGES
        # Validate stage names
        stages = [s for s in stages if s in ALL_STAGES]
        if not stages:
            logger.warning("No valid stages specified, running all")
            stages = ALL_STAGES

        start_time = time.time()
        stage_results: List[ReviewStageResult] = []
        all_issues: List[CodeIssue] = []

        # Step 1: Static analysis (always runs, instant, no API cost)
        static_issues: List[CodeIssue] = []
        if self.static_analyzer:
            try:
                result = self.static_analyzer.analyze_file(file_path)
                static_issues = result.get("issues", [])
                for issue in static_issues:
                    issue.stage = "static"
            except Exception as e:
                logger.warning(f"Static analysis failed for {file_path}: {e}")

        all_issues.extend(static_issues)

        # Step 2: AI-powered stages
        if parallel and len(stages) > 1:
            stage_results = self._run_stages_parallel(file_path, stages)
        else:
            stage_results = self._run_stages_sequential(file_path, stages)

        # Merge issues from all stages
        for sr in stage_results:
            all_issues.extend(sr.issues)

        # Deduplicate: same file + line + message = duplicate
        all_issues = self._deduplicate_issues(all_issues)

        duration_ms = (time.time() - start_time) * 1000

        return {
            "file": str(file_path),
            "issues": all_issues,
            "issues_count": len(all_issues),
            "stages_run": [sr.stage_name for sr in stage_results],
            "stage_results": stage_results,
            "duration_ms": duration_ms,
            "static_issues": len(static_issues),
            "ai_issues": len(all_issues) - len(static_issues),
        }

    def review_directory(
        self,
        dir_path: Path,
        stages: Optional[List[str]] = None,
        parallel: bool = True,
        file_limit: int = 50,
    ) -> Dict[str, Any]:
        """Review all supported files in a directory.

        Args:
            dir_path: Directory to review
            stages: Which review stages to run
            parallel: Run stages in parallel per file
            file_limit: Max files to review (prevents runaway API costs)
        """
        from src.analyzer import CodeAnalyzer

        supported_exts = set()
        for exts in CodeAnalyzer.SUPPORTED_EXTENSIONS.values():
            supported_exts.update(exts)

        exclude_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}

        files = []
        for ext in supported_exts:
            for f in dir_path.rglob(f"*{ext}"):
                if not any(ex in f.parts for ex in exclude_dirs):
                    files.append(f)

        files = files[:file_limit]

        all_results = []
        all_issues: List[CodeIssue] = []

        for file_path in files:
            try:
                result = self.review_file(file_path, stages=stages, parallel=parallel)
                all_results.append(result)
                all_issues.extend(result["issues"])
            except Exception as e:
                logger.warning(f"Failed to review {file_path}: {e}")

        # Summary stats
        severity_counts = {}
        type_counts = {}
        for issue in all_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            type_counts[issue.type] = type_counts.get(issue.type, 0) + 1

        return {
            "directory": str(dir_path),
            "files_reviewed": len(all_results),
            "total_issues": len(all_issues),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "file_results": all_results,
            "stages_used": stages or ALL_STAGES,
        }

    def _run_stages_parallel(self, file_path: Path, stages: List[str]) -> List[ReviewStageResult]:
        """Run review stages in parallel using ThreadPoolExecutor."""
        results: List[ReviewStageResult] = []

        with ThreadPoolExecutor(max_workers=len(stages)) as executor:
            future_to_stage = {
                executor.submit(self._run_single_stage, file_path, stage): stage
                for stage in stages
            }
            for future in as_completed(future_to_stage):
                stage = future_to_stage[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Stage '{stage}' failed for {file_path}: {e}")
                    results.append(ReviewStageResult(
                        stage_name=stage,
                        error=str(e),
                    ))

        # Sort by stage order for consistent output
        stage_order = {s: i for i, s in enumerate(ALL_STAGES)}
        results.sort(key=lambda r: stage_order.get(r.stage_name, 99))
        return results

    def _run_stages_sequential(self, file_path: Path, stages: List[str]) -> List[ReviewStageResult]:
        """Run review stages one after another."""
        results = []
        for stage in stages:
            try:
                result = self._run_single_stage(file_path, stage)
                results.append(result)
            except Exception as e:
                logger.error(f"Stage '{stage}' failed for {file_path}: {e}")
                results.append(ReviewStageResult(stage_name=stage, error=str(e)))
        return results

    def _run_single_stage(self, file_path: Path, stage: str) -> ReviewStageResult:
        """Run a single review stage."""
        start = time.time()
        issues = self.ai_client.analyze_code(file_path, stage=stage)
        duration_ms = (time.time() - start) * 1000

        return ReviewStageResult(
            stage_name=stage,
            issues=issues,
            duration_ms=duration_ms,
        )

    def _deduplicate_issues(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """Remove duplicate issues (same file + line + message).

        When duplicates exist across stages, keep the one with higher severity.
        """
        seen: Dict[str, CodeIssue] = {}

        for issue in issues:
            key = f"{issue.file}:{issue.line_number}:{issue.message}"
            if key in seen:
                existing = seen[key]
                if SEVERITY_ORDER.get(issue.severity, 0) > SEVERITY_ORDER.get(existing.severity, 0):
                    seen[key] = issue
            else:
                seen[key] = issue

        # Sort by severity (critical first) then by line number
        result = list(seen.values())
        result.sort(key=lambda i: (-SEVERITY_ORDER.get(i.severity, 0), i.line_number or 0))
        return result
