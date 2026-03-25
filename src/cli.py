"""AI Code Reviewer - Main CLI entry point."""

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import json
from .scanner import CodeScanner
from .reporter import ReportGenerator

console = Console()


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """AI Code Reviewer - Automated code review tool."""
    pass


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for report')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), default='text')
@click.option('--ai/--no-ai', default=True, help='Use AI for analysis')
@click.option('--security/ --no-security', default=True, help='Run security scans')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def review(path, output, format, ai, security, verbose):
    """Review code at the given path."""
    console.print(f"[bold blue]🔍 Starting code review:[/bold blue] {path}")
    
    scanner = CodeScanner()
    results = scanner.scan(path, security=security, ai=ai)
    
    generator = ReportGenerator()
    report = generator.generate(results, format=format)
    
    if output:
        Path(output).write_text(report)
        console.print(f"[green]✓ Report saved to:[/green] {output}")
    else:
        console.print(report)
    
    # Summary table
    table = Table(title="Review Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Issues", style="yellow")
    
    issues = results.get('issues', {})
    for category, items in issues.items():
        table.add_row(category, str(len(items)))
    
    console.print(table)
    
    # Exit with error code if critical issues found
    critical = len(issues.get('critical', []))
    if critical > 0:
        console.print(f"[red]✗ Found {critical} critical issues![/red]")
        raise click.Exit(code=1)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
def scan(path, output):
    """Run security scan only."""
    console.print(f"[bold red]🛡️ Running security scan:[/bold red] {path}")
    
    scanner = CodeScanner()
    results = scanner.security_scan(path)
    
    console.print(results)


@cli.command()
def stats():
    """Show statistics and configuration."""
    console.print("[bold]📊 AI Code Reviewer Statistics[/bold]")
    console.print(f"Version: 1.0.0")
    console.print(f"Scanner: Active")
    console.print(f"AI Integration: Enabled")


if __name__ == '__main__':
    cli()