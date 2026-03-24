"""Report generation for analysis results."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from src.models import CodeIssue

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate various report formats from analysis results."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.timestamp = datetime.now().isoformat()
        logger.debug("Report generator initialized")
    
    def generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate an HTML report.
        
        Args:
            results: Analysis results
            
        Returns:
            HTML report as string
        """
        issues = results.get("issues", [])
        stats = results.get("stats", {})
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>AI Code Review Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #ecf0f1; padding: 15px; border-radius: 5px; }}
        .issue {{ border-left: 4px solid; padding: 10px; margin: 10px 0; }}
        .critical {{ border-color: #e74c3c; background: #fadbd8; }}
        .high {{ border-color: #e67e22; background: #fdebd0; }}
        .medium {{ border-color: #f1c40f; background: #fcf3cf; }}
        .low {{ border-color: #95a5a6; background: #f4f6f6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Code Review Report</h1>
        <p>Generated: {self.timestamp}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <h3>Files</h3>
            <p>{stats.get('files_analyzed', 0)}</p>
        </div>
        <div class="stat-box">
            <h3>Lines</h3>
            <p>{stats.get('lines_of_code', 0)}</p>
        </div>
        <div class="stat-box">
            <h3>Issues</h3>
            <p>{len(issues)}</p>
        </div>
    </div>
    
    <h2>Issues Found</h2>
"""
        
        # Group issues by severity
        severity_order = ["critical", "high", "medium", "low"]
        for severity in severity_order:
            severity_issues = [i for i in issues if i.severity == severity]
            if not severity_issues:
                continue
            
            html += f"<h3>{severity.upper()}</h3>\n"
            
            for issue in severity_issues:
                html += f"""
    <div class="issue {severity}">
        <strong>{issue.file}:{issue.line_number}</strong>
        <p>{issue.message}</p>
        {f'<p><em>Suggestion: {issue.suggestion}</em></p>' if issue.suggestion else ''}
    </div>
"""
        
        html += """
</body>
</html>"""
        
        return html
    
    def generate_csv_report(self, results: Dict[str, Any]) -> str:
        """Generate a CSV report.
        
        Args:
            results: Analysis results
            
        Returns:
            CSV report as string
        """
        issues = results.get("issues", [])
        
        csv = "Severity,Type,File,Line,Message,Suggestion\n"
        
        for issue in issues:
            message = issue.message.replace(",", ";").replace("\n", " ")
            suggestion = (issue.suggestion or "").replace(",", ";").replace("\n", " ")
            csv += f"{issue.severity},{issue.type},{issue.file},{issue.line_number},{message},{suggestion}\n"
        
        return csv
    
    def generate_junit_report(self, results: Dict[str, Any]) -> str:
        """Generate a JUnit XML report.
        
        Args:
            results: Analysis results
            
        Returns:
            JUnit XML report as string
        """
        issues = results.get("issues", [])
        
        junit = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="AI Code Review" tests="{len(issues)}" failures="{sum(1 for i in issues if i.severity in ['critical', 'high'])}">
"""
        
        for i, issue in enumerate(issues):
            failure = "failure" if issue.severity in ["critical", "high"] else ""
            junit += f"""    <testcase name="{issue.file}:{issue.line_number}" classname="code_review">
        <{failure} message="{issue.message}" type="{issue.type}"/>
    </testcase>
"""
        
        junit += "</testsuite>"
        
        return junit
    
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """Generate a summary report.
        
        Args:
            results: Analysis results
            
        Returns:
            Summary report as string
        """
        issues = results.get("issues", [])
        stats = results.get("stats", {})
        
        # Count by severity
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_type = {}
        
        for issue in issues:
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
            by_type[issue.type] = by_type.get(issue.type, 0) + 1
        
        summary = f"""
╔══════════════════════════════════════════════════════════╗
║           AI CODE REVIEW SUMMARY REPORT                  ║
╠══════════════════════════════════════════════════════════╣
║  Timestamp: {self.timestamp:<39} ║
╠══════════════════════════════════════════════════════════╣
║  STATISTICS                                              ║
║  Files Analyzed:     {stats.get('files_analyzed', 0):<30} ║
║  Lines of Code:      {stats.get('lines_of_code', 0):<30} ║
║  Total Issues:       {len(issues):<30} ║
╠══════════════════════════════════════════════════════════╣
║  BY SEVERITY                                             ║
║  Critical:          {by_severity.get('critical', 0):<30} ║
║  High:              {by_severity.get('high', 0):<30} ║
║  Medium:            {by_severity.get('medium', 0):<30} ║
║  Low:               {by_severity.get('low', 0):<30} ║
╠══════════════════════════════════════════════════════════╣
║  BY TYPE                                                 ║
"""
        
        for issue_type, count in sorted(by_type.items()):
            summary += f"║  {issue_type:<18} {count:<30} ║\n"
        
        summary += "╚══════════════════════════════════════════════════════════╝"
        
        return summary
    
    def save_report(self, results: Dict[str, Any], output_path: Path, format: str = "json"):
        """Save a report to a file.
        
        Args:
            results: Analysis results
            output_path: Path to save the report
            format: Report format (json, html, csv, junit, summary)
        """
        logger.info(f"Saving {format} report to {output_path}")
        
        if format == "html":
            content = self.generate_html_report(results)
        elif format == "csv":
            content = self.generate_csv_report(results)
        elif format == "junit":
            content = self.generate_junit_report(results)
        elif format == "summary":
            content = self.generate_summary_report(results)
        else:
            content = json.dumps(results, indent=2, default=lambda x: x.__dict__)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        
        logger.info(f"Report saved successfully to {output_path}")