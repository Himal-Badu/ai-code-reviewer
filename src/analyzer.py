"""Core code analysis logic.

This module provides the main CodeAnalyzer class that performs both
static analysis and AI-powered code review.
"""

import ast
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, TYPE_CHECKING

from src.models import CodeIssue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Type aliases for better readability
FilePath = Path
IssueList = List[CodeIssue]

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

    # Common patterns for detecting sensitive data
    SENSITIVE_PATTERNS = {
        "password": re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        "api_key": re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        "secret": re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        "token": re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        "private_key": re.compile(r'private[_-]?key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        "aws_key": re.compile(r'aws[_-]?(access[_-]?key|secret)[_-]?id\s*=', re.IGNORECASE),
    }

    # Dangerous function patterns
    DANGEROUS_FUNCTIONS = {
        "eval", "exec", "compile", "__import__",
        "pickle.load", "yaml.load", "marshall.loads",
    }

    def __init__(self, ai_client: "AIClient", language: str = "auto", 
                 enable_security: bool = True, enable_performance: bool = True):
        self.ai_client = ai_client
        self.language = language
        self.enable_security = enable_security
        self.enable_performance = enable_performance

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
            except Exception as e:
                # Skip files that can't be analyzed
                logger.warning(f"Could not analyze {file_path}: {e}")
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
                                            suggestion="Use environment variables or a secrets manager instead",
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

                # Check for inefficient string concatenation in loops
                if isinstance(node, (ast.For, ast.While)):
                    issues.extend(self._check_string_concatenation(node, file_path))

                # Check for unused imports
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module != "typing":
                        for alias in node.names:
                            if not self._is_import_used(tree, alias.name):
                                issues.append(CodeIssue(
                                    severity="low",
                                    type="code_smell",
                                    message=f"Unused import: {alias.name}",
                                    file=str(file_path),
                                    line_number=node.lineno,
                                    suggestion=f"Remove unused import '{alias.name}'",
                                ))

                # Check for TODO/FIXME comments
                issues.extend(self._check_comments(source, file_path))

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

    def _check_string_concatenation(self, loop_node: ast.AST, file_path: Path) -> List[CodeIssue]:
        """Check for inefficient string concatenation in loops."""
        issues = []
        for node in ast.walk(loop_node):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.target, ast.Subscript) or isinstance(node.target, ast.Attribute):
                    issues.append(CodeIssue(
                        severity="medium",
                        type="performance",
                        message="String concatenation in loop may be inefficient",
                        file=str(file_path),
                        line_number=node.lineno,
                        suggestion="Use list append and join() instead",
                    ))
        return issues

    def _is_import_used(self, tree: ast.AST, import_name: str) -> bool:
        """Check if an imported name is used in the AST."""
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)
        return import_name in used_names

    def _check_comments(self, source: str, file_path: Path) -> List[CodeIssue]:
        """Check for TODO/FIXME/HACK comments."""
        issues = []
        lines = source.split('\n')
        for i, line in enumerate(lines, 1):
            if '#' in line:
                comment = line.split('#', 1)[1]
                if 'TODO' in comment.upper() or 'FIXME' in comment.upper() or 'HACK' in comment.upper():
                    issues.append(CodeIssue(
                        severity="low",
                        type="best_practice",
                        message=f"Found comment: {comment.strip()}",
                        file=str(file_path),
                        line_number=i,
                        suggestion="Address the TODO/FIXME comment",
                    ))
        return issues

    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0