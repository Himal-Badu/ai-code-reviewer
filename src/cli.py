"""CLI entry point for AI Code Reviewer.

This module provides the command-line interface for the AI Code Reviewer tool.
It supports various commands for reviewing code, running security scans,
configuring settings, and generating reports.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from src.analyzer import CodeAnalyzer
from src.ai_client import AIClient, AnalysisConfig
from src.formatter import OutputFormatter
from src.config import Config

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="ai-code-reviewer")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.pass_context
def main(ctx, verbose, quiet):
    """AI-powered code review tool for developers.
    
    Built by Himal Badu, AI Founder 🤖
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


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
    type=click.Choice(["text", "json", "markdown", "html", "sarif", "csv"]),
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
@click.option(
    "--profile",
    type=click.Choice(["fast", "thorough", "security"]),
    help="Use a predefined configuration profile",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable result caching",
)
@click.option(
    "--output-file",
    "-f",
    type=click.Path(),
    help="Write output to file instead of stdout",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Patterns to exclude from analysis",
)
@click.pass_context
def review(ctx, path: str, language: str, output: str, severity: str, 
           api_key: Optional[str], model: str, profile: Optional[str],
           no_cache: bool, output_file: Optional[str], exclude: tuple):
    """Review code in a file or directory."""
    try:
        verbose = ctx.obj.get("verbose", False)
        quiet = ctx.obj.get("quiet", False)
        
        if not quiet:
            console.print(f"[dim]Starting review of {path}...[/dim]")
        
        start_time = time.time()
        
        # Initialize components
        config = Config(api_key=api_key, model=model, profile=profile)
        
        if no_cache:
            config.set("enable_cache", False)
        
        # Add exclude patterns
        if exclude:
            current_excludes = config.get("exclude_patterns", [])
            config.set("exclude_patterns", current_excludes + list(exclude))
        
        analysis_config = AnalysisConfig(
            temperature=0.3,
            max_tokens=2000,
            max_retries=3,
        )
        
        ai_client = AIClient(config, analysis_config)
        analyzer = CodeAnalyzer(ai_client, language)

        # Analyze the code
        target_path = Path(path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Analyzing code...", total=100)
            
            if target_path.is_file():
                results = analyzer.analyze_file(target_path)
            else:
                results = analyzer.analyze_directory(target_path)
            
            progress.update(task, completed=100)

        # Filter by severity
        results = filter_by_severity(results, severity)

        # Output results
        formatter = OutputFormatter()
        
        if output == "json":
            output_content = formatter.to_json(results)
        elif output == "markdown":
            output_content = formatter.to_markdown(results, str(target_path))
        elif output == "html":
            output_content = formatter.to_html(results, str(target_path))
        elif output == "sarif":
            output_content = formatter.to_sarif(results)
        elif output == "csv":
            output_content = formatter.to_csv(results)
        else:
            output_content = None
            display_text_results(results, formatter)

        # Write to file or stdout
        if output_content:
            if output_file:
                Path(output_file).write_text(output_content)
                console.print(f"[green]✓[/green] Output written to {output_file}")
            else:
                console.print(output_content)

        # Show summary
        elapsed = time.time() - start_time
        if not quiet:
            issues = results.get("issues", [])
            high_issues = [i for i in issues if i.get("severity") in ["high", "critical"]]
            
            if high_issues:
                console.print(f"\n[red]Found {len(high_issues)} high/critical issues![/red]")
            
            console.print(f"[dim]Analysis completed in {elapsed:.2f}s[/dim]")

        # Exit with appropriate code
        issues = results.get("issues", [])
        if any(i.get("severity") == "critical" for i in issues):
            sys.exit(3)  # Critical issues found
        elif any(i.get("severity") == "high" for i in issues):
            sys.exit(2)  # High severity issues found
        elif issues:
            sys.exit(1)  # Any issues found

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
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


@main.command()
def status():
    """Show configuration and status information."""
    config = Config()
    
    # Mask API key for display
    masked_config = config.masked_config()
    
    table = Table(title="🤖 AI Code Reviewer Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    for key, value in masked_config.items():
        if key == "api_key":
            value = value if value else "[red]Not set[/red]"
        table.add_row(key, str(value))
    
    console.print(table)
    
    # Check if API key is configured
    if not config.get("api_key"):
        console.print("\n[yellow]Warning:[/yellow] No API key configured.")
        console.print("Set it with: ai-code-reviewer configure --api-key YOUR_KEY")
        console.print("Or set the OPENAI_API_KEY environment variable.")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--parallel", "-p", is_flag=True, help="Run analysis in parallel")
def batch(paths: tuple, parallel: bool):
    """Review multiple files or directories at once."""
    if not paths:
        console.print("[red]Error:[/red] No paths specified")
        sys.exit(1)
    
    all_results = []
    total_issues = 0
    
    config = Config()
    ai_client = AIClient(config)
    formatter = OutputFormatter()
    
    for path in paths:
        target_path = Path(path)
        analyzer = CodeAnalyzer(ai_client)
        
        if target_path.is_file():
            results = analyzer.analyze_file(target_path)
        else:
            results = analyzer.analyze_directory(target_path)
        
        issues = results.get("issues", [])
        total_issues += len(issues)
        all_results.append(results)
        
        console.print(f"[cyan]{path}:[/cyan] {len(issues)} issues found")
    
    console.print(f"\n[bold]Total:[/bold] {total_issues} issues across {len(paths)} paths")


@main.command()
@click.argument("rule_id")
def explain(rule_id: str):
    """Explain a specific rule or issue type."""
    explanations = {
        "hardcoded-secret": {
            "name": "Hardcoded Secret",
            "description": "Detects hardcoded passwords, API keys, tokens, or secrets in code.",
            "severity": "high",
            "fix": "Use environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).",
        },
        "empty-except": {
            "name": "Empty Except Block",
            "description": "An except block that catches exceptions but doesn't handle them.",
            "severity": "medium",
            "fix": "Add proper exception handling or at least log the error.",
        },
        "eval-exec": {
            "name": "Dangerous Function",
            "description": "Use of eval() or exec() can lead to code injection vulnerabilities.",
            "severity": "high",
            "fix": "Avoid eval/exec if possible. Use safer alternatives.",
        },
        "sql-injection": {
            "name": "SQL Injection Risk",
            "description": "Potential SQL injection vulnerability detected.",
            "severity": "critical",
            "fix": "Use parameterized queries or an ORM.",
        },
        "unused-import": {
            "name": "Unused Import",
            "description": "An imported module or function is not used in the code.",
            "severity": "low",
            "fix": "Remove the unused import to clean up the code.",
        },
    }
    
    if rule_id not in explanations:
        console.print(f"[red]Unknown rule:[/red] {rule_id}")
        console.print(f"Available rules: {', '.join(explanations.keys())}")
        sys.exit(1)
    
    rule = explanations[rule_id]
    
    panel = Panel(
        f"[bold]{rule['name']}[/bold]\n\n"
        f"[cyan]Description:[/cyan] {rule['description']}\n\n"
        f"[cyan]Severity:[/cyan] {rule['severity'].upper()}\n\n"
        f"[cyan]How to fix:[/cyan] {rule['fix']}",
        title=f"Rule: {rule_id}",
    )
    console.print(panel)


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