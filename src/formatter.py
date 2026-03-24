"""Output formatting for different formats.

This module provides various output formatters for code review results
including JSON, Markdown, Text, HTML, and SARIF formats.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.models import CodeIssue


class OutputFormatter:
    """Format review results in different output formats."""

    # Severity styling
    SEVERITY_COLORS = {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "dim",
        "unknown": "white",
    }

    SEVERITY_EMOJI = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "unknown": "⚪",
    }

    def __init__(self, include_metadata: bool = True):
        self.include_metadata = include_metadata

    def to_json(self, results: Dict[str, Any], pretty: bool = True) -> str:
        """Convert results to JSON format.
        
        Args:
            results: Analysis results dictionary
            pretty: Whether to pretty-print the JSON
            
        Returns:
            JSON string representation of results
        """
        output = results.copy()
        
        # Add metadata
        if self.include_metadata:
            output["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "formatter_version": "1.0.0",
            }
        
        # Convert CodeIssue objects to dicts
        if "issues" in output:
            output["issues"] = self._serialize_issues(output["issues"])
        
        indent = 2 if pretty else None
        return json.dumps(output, indent=indent)

    def _serialize_issues(self, issues: List[Any]) -> List[Dict[str, Any]]:
        """Serialize issues to dictionaries."""
        serialized = []
        for issue in issues:
            if isinstance(issue, CodeIssue):
                serialized.append(issue.to_dict())
            elif isinstance(issue, dict):
                serialized.append(issue)
            else:
                serialized.append({"message": str(issue)})
        return serialized

    def to_html(self, results: Dict[str, Any], path: str, theme: str = "light") -> str:
        """Convert results to HTML format.
        
        Args:
            results: Analysis results dictionary
            path: Path being analyzed
            theme: Color theme (light or dark)
            
        Returns:
            HTML string representation
        """
        is_dark = theme == "dark"
        
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#e0e0e0" if is_dark else "#333333"
        accent_color = "#007acc"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Code Review: {path}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: {bg_color}; color: {text_color}; padding: 20px; margin: 0; }}
        .header {{ border-bottom: 2px solid {accent_color}; padding-bottom: 10px; margin-bottom: 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .stat {{ background: {accent_color}20; padding: 15px 25px; border-radius: 8px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: {accent_color}; }}
        .stat-label {{ font-size: 12px; opacity: 0.7; }}
        .severity-group {{ margin-bottom: 25px; }}
        .severity-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
        .severity-badge {{ padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; }}
        .critical {{ background: #ff4444; color: white; }}
        .high {{ background: #ff8800; color: white; }}
        .medium {{ background: #ffcc00; color: black; }}
        .low {{ background: #44bb44; color: white; }}
        .issue {{ background: {accent_color}10; padding: 12px; margin-bottom: 8px; 
                  border-left: 4px solid {accent_color}; border-radius: 4px; }}
        .issue-file {{ font-family: monospace; font-size: 13px; opacity: 0.7; }}
        .issue-message {{ margin: 5px 0; }}
        .issue-suggestion {{ font-size: 13px; opacity: 0.8; font-style: italic; }}
        .no-issues {{ text-align: center; padding: 40px; color: #44bb44; font-size: 18px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Code Review</h1>
        <p>{path}</p>
    </div>
"""
        
        stats = results.get("stats", {})
        issues = results.get("issues", [])
        
        html += f"""
    <div class="summary">
        <div class="stat">
            <div class="stat-value">{stats.get('files_analyzed', 0)}</div>
            <div class="stat-label">Files Analyzed</div>
        </div>
        <div class="stat">
            <div class="stat-value">{stats.get('lines_of_code', 0)}</div>
            <div class="stat-label">Lines of Code</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(issues)}</div>
            <div class="stat-label">Issues Found</div>
        </div>
    </div>
"""
        
        if not issues:
            html += '<div class="no-issues">✅ No issues found!</div>'
        else:
            by_severity = self._group_by_severity(issues)
            
            for severity in ["critical", "high", "medium", "low"]:
                severity_issues = by_severity.get(severity, [])
                if not severity_issues:
                    continue
                
                html += f'<div class="severity-group">'
                html += f'<div class="severity-header">'
                html += f'<span class="severity-badge {severity}">{severity.upper()}</span>'
                html += f'<span>{len(severity_issues)} issues</span>'
                html += f'</div>'
                
                for issue in severity_issues:
                    file = issue.file if isinstance(issue, CodeIssue) else issue.get("file", "unknown")
                    line = issue.line_number if isinstance(issue, CodeIssue) else issue.get("line_number", 0)
                    msg = issue.message if isinstance(issue, CodeIssue) else issue.get("message", "")
                    suggestion = issue.suggestion if isinstance(issue, CodeIssue) else issue.get("suggestion", "")
                    
                    html += f'<div class="issue">'
                    html += f'<div class="issue-file">{file}:{line}</div>'
                    html += f'<div class="issue-message">{msg}</div>'
                    if suggestion:
                        html += f'<div class="issue-suggestion">💡 {suggestion}</div>'
                    html += f'</div>'
                
                html += '</div>'
        
        html += """
</body>
</html>"""
        return html

    def to_sarif(self, results: Dict[str, Any]) -> str:
        """Convert results to SARIF (Static Analysis Results Interchange Format).
        
        SARIF is a standard format for static analysis tools.
        
        Args:
            results: Analysis results dictionary
            
        Returns:
            SARIF JSON string
        """
        issues = results.get("issues", [])
        
        sarif = {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "AI Code Reviewer",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/Himal-Badu/ai-code-reviewer",
                    }
                },
                "results": self._convert_to_sarif_results(issues),
            }]
        }
        
        return json.dumps(sarif, indent=2)

    def _convert_to_sarif_results(self, issues: List[Any]) -> List[Dict[str, Any]]:
        """Convert issues to SARIF result format."""
        sarif_results = []
        
        for issue in issues:
            if isinstance(issue, CodeIssue):
                severity_map = {
                    "critical": "error",
                    "high": "error", 
                    "medium": "warning",
                    "low": "note",
                }
                
                result = {
                    "level": severity_map.get(issue.severity, "note"),
                    "message": {
                        "text": issue.message,
                    },
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": issue.file,
                            },
                            "region": {
                                "startLine": issue.line_number,
                            }
                        }
                    }],
                }
                
                if issue.suggestion:
                    result["message"]["markdown"] = f"**Suggestion:** {issue.suggestion}"
                
                sarif_results.append(result)
        
        return sarif_results

    def _group_by_severity(self, issues: List[Any]) -> Dict[str, List[Any]]:
        """Group issues by severity level."""
        grouped = {"critical": [], "high": [], "medium": [], "low": []}
        
        for issue in issues:
            severity = "low"
            if isinstance(issue, CodeIssue):
                severity = issue.severity
            elif isinstance(issue, dict):
                severity = issue.get("severity", "low")
            
            if severity in grouped:
                grouped[severity].append(issue)
            else:
                grouped["low"].append(issue)
        
        return grouped

    def to_markdown(self, results: Dict[str, Any], path: str) -> str:
        """Convert results to Markdown format."""
        lines = []
        
        # Header
        lines.append(f"# AI Code Review: {path}")
        lines.append("")
        
        # Summary
        stats = results.get("stats", {})
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Files Analyzed:** {stats.get('files_analyzed', 0)}")
        lines.append(f"- **Lines of Code:** {stats.get('lines_of_code', 0)}")
        lines.append(f"- **Issues Found:** {len(results.get('issues', []))}")
        lines.append("")
        
        # Issues
        issues = results.get("issues", [])
        if issues:
            lines.append("## Issues")
            lines.append("")
            
            # Group by severity
            by_severity = {"critical": [], "high": [], "medium": [], "low": []}
            for issue in issues:
                severity = issue.severity if isinstance(issue, CodeIssue) else issue.get("severity", "low")
                if severity in by_severity:
                    by_severity[severity].append(issue)
            
            # Output by severity
            for severity in ["critical", "high", "medium", "low"]:
                severity_issues = by_severity[severity]
                if not severity_issues:
                    continue
                
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                lines.append(f"### {emoji} {severity.upper()}")
                lines.append("")
                
                for issue in severity_issues:
                    if isinstance(issue, CodeIssue):
                        file = issue.file
                        line = issue.line_number
                        msg = issue.message
                        suggestion = issue.suggestion
                    else:
                        file = issue.get("file", "unknown")
                        line = issue.get("line_number", 0)
                        msg = issue.get("message", "No description")
                        suggestion = issue.get("suggestion")
                    
                    lines.append(f"- **{file}:{line}** - {msg}")
                    if suggestion:
                        lines.append(f"  - 💡 {suggestion}")
                    lines.append("")
        else:
            lines.append("## ✅ No Issues Found")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("*Generated by AI Code Reviewer*")
        
        return "\n".join(lines)

    def to_text(self, results: Dict[str, Any]) -> str:
        """Convert results to plain text format."""
        lines = []
        
        stats = results.get("stats", {})
        lines.append("=" * 60)
        lines.append("AI CODE REVIEW RESULTS")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Files Analyzed: {stats.get('files_analyzed', 0)}")
        lines.append(f"Lines of Code: {stats.get('lines_of_code', 0)}")
        lines.append(f"Issues Found: {len(results.get('issues', []))}")
        lines.append("")
        
        issues = results.get("issues", [])
        if issues:
            by_severity = self._group_by_severity(issues)
            
            for severity in ["critical", "high", "medium", "low"]:
                severity_issues = by_severity.get(severity, [])
                if not severity_issues:
                    continue
                
                emoji = self.SEVERITY_EMOJI.get(severity, "")
                lines.append(f"\n{emoji} {severity.upper()} ({len(severity_issues)} issues)")
                lines.append("-" * 40)
                
                for issue in severity_issues:
                    if isinstance(issue, CodeIssue):
                        file = issue.file
                        line = issue.line_number
                        msg = issue.message
                        suggestion = issue.suggestion
                    else:
                        file = issue.get("file", "unknown")
                        line = issue.get("line_number", 0)
                        msg = issue.get("message", "No description")
                        suggestion = issue.get("suggestion")
                    
                    lines.append(f"  [{file}:{line}] {msg}")
                    if suggestion:
                        lines.append(f"    → {suggestion}")
                    lines.append("")
        
        return "\n".join(lines)

    def to_csv(self, results: Dict[str, Any]) -> str:
        """Convert results to CSV format."""
        import csv
        import io
        
        issues = results.get("issues", [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["severity", "type", "file", "line_number", "message", "suggestion"])
        
        # Data rows
        for issue in issues:
            if isinstance(issue, CodeIssue):
                writer.writerow([
                    issue.severity,
                    issue.type,
                    issue.file,
                    issue.line_number,
                    issue.message,
                    issue.suggestion or "",
                ])
            elif isinstance(issue, dict):
                writer.writerow([
                    issue.get("severity", ""),
                    issue.get("type", ""),
                    issue.get("file", ""),
                    issue.get("line_number", 0),
                    issue.get("message", ""),
                    issue.get("suggestion", ""),
                ])
        
        return output.getvalue()