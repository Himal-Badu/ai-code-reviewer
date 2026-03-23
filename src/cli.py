"""CLI entry point for AI Code Reviewer."""

import sys
import os
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from src.analyzer import CodeAnalyzer
from src.ai_client import AIClient
from src.formatter import OutputFormatter
from src.config import Config

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """AI-powered code review tool for developers."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--language",
    "-l",
    type=click.Choice(["python", "javascript", "typescript", "go", "rust", "auto"]),
    default="auto",
    help="Programming language",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    help="Output format",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["all", "high", "medium", "low"]),
    default="all",
    help="Minimum severity level to report",
)
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    help="OpenAI API key (or set OPENAI_API_KEY env var)",
)
@click.option(
    "--model",
    default="gpt-4",
    help="AI model to use for review",
)
def review(path: str, language: str, output: str, severity: str, api_key: Optional[str], model: str):
    """Review code in a file or directory."""
    try:
        # Initialize components
        config = Config(api_key=api_key, model=model)
        ai_client = AIClient(config)
        analyzer = CodeAnalyzer(ai_client, language)

        # Analyze the code
        target_path = Path(path)
        if target_path.is_file():
            results = analyzer.analyze_file(target_path)
        else:
            results = analyzer.analyze_directory(target_path)

        # Filter by severity
        results = filter_by_severity(results, severity)

        # Output results
        formatter = OutputFormatter()
        if output == "json":
            console.print(formatter.to_json(results))
        elif output == "markdown":
            console.print(formatter.to_markdown(results, str(target_path)))
        else:
            display_text_results(results, formatter)

        # Exit with appropriate code
        issues = results.get("issues", [])
        if any(i.get("severity") == "high" for i in issues):
            sys.exit(2)  # High severity issues found

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True))
def security(path: str):
    """Run security-focused analysis."""
    from src.security import SecurityScanner

    console.print("[yellow]Running security scan...[/yellow]")
    scanner = SecurityScanner()
    results = scanner.scan(Path(path))

    table = Table(title="Security Issues Found")
    table.add_column("Severity", style="red")
    table.add_column("Issue", style="white")
    table.add_column("Line", justify="right")
    table.add_column("Description")

    for issue in results.get("issues", []):
        table.add_row(
            issue.get("severity", "unknown"),
            issue.get("issue_id", "N/A"),
            str(issue.get("line_number", "-")),
            issue.get("message", "No description"),
        )

    console.print(table)


@main.command()
def setup():
    """Generate GitHub Action workflow file."""
    workflow_content = """name: AI Code Review

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install AI Code Reviewer
        run: pip install ai-code-reviewer
      
      - name: Run AI Code Review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          ai-code-reviewer review . --output=markdown >> $GITHUB_STEP_SUMMARY
      
      - name: Post Review Comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const summary = fs.readFileSync(process.env.GITHUB_STEP_SUMMARY, 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## AI Code Review\\n' + summary
            });
"""

    workflow_path = Path(".github/workflows/ai-review.yml")
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(workflow_content)

    console.print(f"[green]✓[/green] Created GitHub Action workflow at {workflow_path}")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Add OPENAI_API_KEY to your GitHub secrets")
    console.print("  2. Push .github/workflows/ai-review.yml to your repo")


@main.command()
@click.option("--api-key", help="OpenAI API key")
@click.option("--model", default="gpt-4", help="AI model")
def configure(api_key: Optional[str], model: str):
    """Configure AI Code Reviewer settings."""
    config = Config()
    if api_key:
        config.set("api_key", api_key)
    if model:
        config.set("model", model)

    config.save()
    console.print("[green]✓[/green] Configuration saved")


def filter_by_severity(results: dict, level: str) -> dict:
    """Filter results by severity level."""
    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_level = severity_order.get(level, 0)

    filtered_issues = []
    for issue in results.get("issues", []):
        issue_level = severity_order.get(issue.get("severity", "low"), 0)
        if issue_level >= min_level:
            filtered_issues.append(issue)

    results["issues"] = filtered_issues
    return results


def display_text_results(results: dict, formatter: OutputFormatter):
    """Display results in text format with rich formatting."""
    stats = results.get("stats", {})
    issues = results.get("issues", [])

    # Summary panel
    summary = f"""[bold]Files Analyzed:[/bold] {stats.get('files_analyzed', 0)}
[bold]Lines of Code:[/bold] {stats.get('lines_of_code', 0)}
[bold]Issues Found:[/bold] {len(issues)}"""
    console.print(Panel(summary, title="📊 Review Summary"))

    if not issues:
        console.print("\n[green]✓ No issues found![/green]")
        return

    # Issues table
    table = Table(title="🚨 Issues Found")
    table.add_column("Severity", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Line", justify="right")
    table.add_column("Description")

    severity_styles = {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "dim",
    }

    for issue in issues:
        severity = issue.get("severity", "low")
        style = severity_styles.get(severity, "white")
        table.add_row(
            f"[{style}]{severity.upper()}[/{style}]",
            issue.get("type", "unknown"),
            issue.get("file", "unknown"),
            str(issue.get("line_number", "-")),
            issue.get("message", "No description")[:60],
        )

    console.print("\n")
    console.print(table)


if __name__ == "__main__":
    main()