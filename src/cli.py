"""AI Code Reviewer - CLI entry point.

Commands:
  review     Full review (static + AI)
  security   Security-focused review only
  bugs       Bug detection only
  performance Performance review only
  style      Code quality/style review only
  learn      View learning insights
  stats      Show statistics
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import json

console = Console()


@click.group()
@click.version_option(version='2.0.0')
def cli():
    """🤖 AI Code Reviewer — Multi-agent code review powered by AI."""
    pass


def _get_analyzer(stages=None):
    """Create an analyzer with optional pipeline and learning."""
    from src.config import Config
    from src.ai_client import get_ai_client
    from src.analyzer import CodeAnalyzer
    from src.pipeline import ReviewPipeline
    from src.learning import ReviewLearner

    config = Config()
    ai_client = get_ai_client(config)
    learner = ReviewLearner()

    pipeline = None
    if stages:
        pipeline = ReviewPipeline(ai_client)

    return CodeAnalyzer(ai_client, pipeline=pipeline, learner=learner), learner


def _print_issues(issues, title="Issues Found"):
    """Pretty-print issues as a table."""
    if not issues:
        console.print(f"[green]✓ {title}: None[/green]")
        return

    table = Table(title=title)
    table.add_column("Severity", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right")
    table.add_column("Message")
    table.add_column("Suggestion", style="yellow")

    severity_colors = {
        "critical": "[red]CRITICAL[/red]",
        "high": "[orange3]HIGH[/orange3]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "low": "[dim]LOW[/dim]",
    }

    for issue in issues:
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        sev = severity_colors.get(d.get("severity", "medium"), d.get("severity", ""))
        table.add_row(
            sev,
            d.get("type", ""),
            Path(d.get("file", "")).name if d.get("file") else "",
            str(d.get("line_number", "")),
            d.get("message", "")[:80],
            (d.get("suggestion") or "")[:60],
        )

    console.print(table)


def _print_summary(result):
    """Print a summary panel."""
    issues = result.get("issues", [])
    severity_counts = {}
    type_counts = {}
    for issue in issues:
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        sev = d.get("severity", "unknown")
        typ = d.get("type", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        type_counts[typ] = type_counts.get(typ, 0) + 1

    lines = []
    lines.append(f"[bold]Files reviewed:[/bold] {result.get('files_reviewed', result.get('files_analyzed', 1))}")
    lines.append(f"[bold]Total issues:[/bold] {len(issues)}")
    lines.append("")

    if severity_counts:
        lines.append("[bold]By severity:[/bold]")
        for sev in ["critical", "high", "medium", "low"]:
            if sev in severity_counts:
                color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "dim"}.get(sev, "white")
                lines.append(f"  [{color}]{sev.upper()}[/{color}]: {severity_counts[sev]}")

    if type_counts:
        lines.append("")
        lines.append("[bold]By type:[/bold]")
        for typ, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {typ}: {count}")

    stages = result.get("stages_used", result.get("stages_run", []))
    if stages:
        lines.append(f"\n[bold]Stages:[/bold] {', '.join(stages)}")

    console.print(Panel("\n".join(lines), title="📊 Review Summary", border_style="blue"))


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for report')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), default='text')
@click.option('--severity', '-s', type=click.Choice(['critical', 'high', 'medium', 'low']), help='Min severity filter')
@click.option('--stages', '-S', help='Comma-separated stages: security,bugs,performance,style')
@click.option('--sequential', is_flag=True, help='Run stages sequentially (default: parallel)')
@click.option('--no-learn', is_flag=True, help='Skip recording to learning database')
def review(path, output, format, severity, stages, sequential, no_learn):
    """🔍 Full code review (static + AI, all stages)."""
    if format != 'json':
        console.print(f"[bold blue]🔍 Starting full review:[/bold blue] {path}")

    stage_list = [s.strip() for s in stages.split(",")] if stages else None

    analyzer, learner = _get_analyzer(stages=stage_list)
    if no_learn:
        analyzer.learner = None

    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.analyze_file(path_obj, stages=stage_list)
        issues = result.get("issues", [])
    else:
        result = analyzer.analyze_directory(path_obj, stages=stage_list)
        issues = result.get("issues", [])

    # Filter by severity
    if severity:
        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        min_sev = sev_order.get(severity, 0)
        issues = [i for i in issues if sev_order.get(
            i.to_dict().get("severity", "low") if hasattr(i, 'to_dict') else i.get("severity", "low"), 0
        ) >= min_sev]
        result["issues"] = issues

    # Output
    if format == 'json':
        output_data = {
            "path": path,
            "issues": [i.to_dict() if hasattr(i, 'to_dict') else i for i in issues],
            "total": len(issues),
        }
        if output:
            Path(output).write_text(json.dumps(output_data, indent=2))
            console.print(f"[green]✓ JSON saved to {output}[/green]")
        else:
            console.print_json(data=output_data)
    elif format == 'markdown':
        lines = [f"# Code Review: `{path}`\n"]
        lines.append(f"**Total issues:** {len(issues)}\n")
        for i in issues:
            d = i.to_dict() if hasattr(i, 'to_dict') else i
            lines.append(f"### {'🔴' if d['severity']=='critical' else '🟡' if d['severity']=='high' else '🔵'} {d['severity'].upper()}: {d['message']}")
            lines.append(f"- **File:** `{d.get('file', '')}` (line {d.get('line_number', '?')})")
            lines.append(f"- **Type:** {d.get('type', '')}")
            if d.get('suggestion'):
                lines.append(f"- **Fix:** {d['suggestion']}")
            if d.get('stage'):
                lines.append(f"- **Stage:** {d['stage']}")
            lines.append("")
        md = "\n".join(lines)
        if output:
            Path(output).write_text(md)
            console.print(f"[green]✓ Markdown saved to {output}[/green]")
        else:
            console.print(md)
    else:
        _print_issues(issues)
        _print_summary(result)

    # Learning consolidation (background step)
    if not no_learn and analyzer.learner:
        analyzer.learner.consolidate()

    # Exit code
    critical_count = sum(1 for i in issues if (i.to_dict() if hasattr(i, 'to_dict') else i).get("severity") == "critical")
    if critical_count > 0:
        console.print(f"[red]✗ Found {critical_count} critical issues![/red]")
        raise click.Exit(code=1)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
def security(path, output, format):
    """🛡️ Security-focused review only."""
    if format != 'json':
        console.print(f"[bold red]🛡️ Security review:[/bold red] {path}")

    analyzer, _ = _get_analyzer(stages=["security"])
    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.analyze_file(path_obj, stages=["security"])
    else:
        result = analyzer.analyze_directory(path_obj, stages=["security"])

    issues = result.get("issues", [])

    if format == 'json':
        data = {"issues": [i.to_dict() if hasattr(i, 'to_dict') else i for i in issues]}
        if output:
            Path(output).write_text(json.dumps(data, indent=2))
        else:
            console.print_json(data=data)
    else:
        _print_issues(issues, "Security Issues")
        _print_summary(result)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
def bugs(path, output):
    """🐛 Bug detection review only."""
    console.print(f"[bold yellow]🐛 Bug detection:[/bold yellow] {path}")

    analyzer, _ = _get_analyzer(stages=["bugs"])
    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.analyze_file(path_obj, stages=["bugs"])
    else:
        result = analyzer.analyze_directory(path_obj, stages=["bugs"])

    issues = result.get("issues", [])
    _print_issues(issues, "Bug Issues")
    _print_summary(result)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
def performance(path, output):
    """⚡ Performance review only."""
    console.print(f"[bold magenta]⚡ Performance review:[/bold magenta] {path}")

    analyzer, _ = _get_analyzer(stages=["performance"])
    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.analyze_file(path_obj, stages=["performance"])
    else:
        result = analyzer.analyze_directory(path_obj, stages=["performance"])

    issues = result.get("issues", [])
    _print_issues(issues, "Performance Issues")
    _print_summary(result)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def style(path):
    """✨ Code quality & style review only."""
    console.print(f"[bold cyan]✨ Style review:[/bold cyan] {path}")

    analyzer, _ = _get_analyzer(stages=["style"])
    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.analyze_file(path_obj, stages=["style"])
    else:
        result = analyzer.analyze_directory(path_obj, stages=["style"])

    issues = result.get("issues", [])
    _print_issues(issues, "Style Issues")
    _print_summary(result)


@cli.command()
@click.option('--clear', is_flag=True, help='Clear all learning data')
@click.option('--language', '-l', help='Filter patterns by language')
def learn(clear, language):
    """🧠 View learning insights from past reviews."""
    from src.learning import ReviewLearner

    learner = ReviewLearner()

    if clear:
        learner.clear()
        console.print("[green]✓ Learning data cleared[/green]")
        return

    summary = learner.get_project_summary()

    if summary["total_observations"] == 0:
        console.print("[dim]No learning data yet. Run some reviews first![/dim]")
        return

    # Print summary
    lines = [
        f"[bold]Total observations:[/bold] {summary['total_observations']}",
        f"[bold]Unique patterns:[/bold] {summary['unique_patterns']}",
        "",
        "[bold]Top patterns:[/bold]",
    ]
    for p in summary["top_patterns"]:
        lines.append(f"  • {p['pattern']} ({p['count']}x)")

    lines.append("\n[bold]Languages:[/bold]")
    for lang, count in summary["languages"].items():
        lines.append(f"  • {lang}: {count}")

    console.print(Panel("\n".join(lines), title="🧠 Learning Summary", border_style="magenta"))

    # Hot patterns
    hot = learner.get_hot_patterns(language=language)
    if hot:
        table = Table(title="🔥 Hot Patterns (most frequent)")
        table.add_column("Pattern", style="cyan")
        table.add_column("Language")
        table.add_column("Count", justify="right")
        table.add_column("Severity")
        table.add_column("Example")
        for p in hot:
            table.add_row(
                p.pattern_key,
                p.language,
                str(p.count),
                p.typical_severity,
                p.example_messages[0][:60] if p.example_messages else "",
            )
        console.print(table)


@cli.command()
def stats():
    """📊 Show statistics and configuration."""
    console.print("[bold]📊 AI Code Reviewer v2.0.0[/bold]")
    console.print("")
    console.print("[bold]Architecture:[/bold]")
    console.print("  • Multi-agent pipeline (parallel staged reviews)")
    console.print("  • Cache-aware prompt engineering")
    console.print("  • Background learning (KAIROS-inspired)")
    console.print("")
    console.print("[bold]Available stages:[/bold]")
    console.print("  🛡️  security  — OWASP, secrets, injection")
    console.print("  🐛  bugs      — logic errors, edge cases")
    console.print("  ⚡  performance — complexity, allocations, I/O")
    console.print("  ✨  style     — naming, duplication, docs")
    console.print("")
    console.print("[bold]Commands:[/bold]")
    console.print("  review <path>      Full review (all stages)")
    console.print("  security <path>    Security-only review")
    console.print("  bugs <path>        Bug detection only")
    console.print("  performance <path> Performance review only")
    console.print("  style <path>       Style review only")
    console.print("  learn              View learning insights")
    console.print("")
    console.print("[dim]Inspired by Claude Code's production architecture patterns.[/dim]")


if __name__ == '__main__':
    cli()
