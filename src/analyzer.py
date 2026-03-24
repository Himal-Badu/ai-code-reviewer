"""Core code analysis logic."""

import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from src.models import CodeIssue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.ai_client import AIClient


class CodeAnalyzer:
    """Analyzes code files and directories for issues."""

    SUPPORTED_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
    }

    def __init__(self, ai_client: "AIClient", language: str = "auto"):
        self.ai_client = ai_client
        self.language = language

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file."""
        logger.info(f"Analyzing file: {file_path}")
        detected_language = self._detect_language(file_path)
        logger.debug(f"Detected language: {detected_language}")
        
        issues = []
        
        # Static analysis
        if detected_language == "python":
            issues.extend(self._analyze_python(file_path))
        
        # AI-powered analysis
        ai_issues = self.ai_client.analyze_code(file_path)
        issues.extend(ai_issues)

        return {
            "file": str(file_path),
            "language": detected_language,
            "issues": issues,
            "stats": {
                "lines_of_code": self._count_lines(file_path),
            }
        }

    def analyze_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Analyze all files in a directory."""
        logger.info(f"Analyzing directory: {dir_path}")
        all_issues = []
        total_files = 0
        total_lines = 0

        for file_path in self._get_files_to_analyze(dir_path):
            try:
                result = self.analyze_file(file_path)
                all_issues.extend(result.get("issues", []))
                total_files += 1
                total_lines += result.get("stats", {}).get("lines_of_code", 0)
            except Exception:
                # Skip files that can't be analyzed
                continue

        logger.info(f"Directory analysis complete: {total_files} files, {total_lines} lines, {len(all_issues)} issues")
        
        return {
            "directory": str(dir_path),
            "issues": all_issues,
            "stats": {
                "files_analyzed": total_files,
                "lines_of_code": total_lines,
            }
        }

    def _detect_language(self, file_path: Path) -> str:
        """Detect the programming language of a file."""
        if self.language != "auto":
            return self.language

        ext = file_path.suffix.lower()
        
        for lang, extensions in self.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return lang
        
        return "unknown"

    def _get_files_to_analyze(self, dir_path: Path) -> List[Path]:
        """Get all supported files in a directory."""
        files = []
        
        for ext_list in self.SUPPORTED_EXTENSIONS.values():
            for ext in ext_list:
                files.extend(dir_path.rglob(f"*{ext}"))
        
        # Filter out common non-code directories
        exclude_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}
        
        return [f for f in files if not any(ex in f.parts for ex in exclude_dirs)]

    def _analyze_python(self, file_path: Path) -> List[CodeIssue]:
        """Run Python-specific static analysis."""
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Check for hardcoded secrets
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id.lower()
                            if any(word in var_name for word in ["password", "secret", "token", "key"]):
                                if isinstance(node.value, ast.Constant):
                                    if isinstance(node.value.value, str) and node.value.value:
                                        issues.append(CodeIssue(
                                            severity="high",
                                            type="security",
                                            message="Potential hardcoded secret detected",
                                            file=str(file_path),
                                            line_number=node.lineno,
                                            suggestion="Use environment variables instead",
                                        ))

                # Check for empty except blocks
                if isinstance(node, ast.ExceptHandler):
                    if node.body is None or len(node.body) == 0:
                        issues.append(CodeIssue(
                            severity="medium",
                            type="code_smell",
                            message="Empty except block",
                            file=str(file_path),
                            line_number=node.lineno,
                            suggestion="Handle the exception or log it",
                        ))

                # Check for dangerous exec/eval usage
                if isinstance(node, (ast.Exec, ast.Eval)):
                    issues.append(CodeIssue(
                        severity="high",
                        type="security",
                        message="Use of eval/exec can be dangerous",
                        file=str(file_path),
                        line_number=node.lineno,
                        suggestion="Avoid eval/exec if possible",
                    ))

        except SyntaxError as e:
            issues.append(CodeIssue(
                severity="critical",
                type="syntax_error",
                message=f"Syntax error: {str(e)}",
                file=str(file_path),
                line_number=e.lineno or 0,
            ))
        except Exception as e:
            issues.append(CodeIssue(
                severity="medium",
                type="analysis_error",
                message=f"Could not analyze: {str(e)}",
                file=str(file_path),
                line_number=0,
            ))

        return issues

    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0