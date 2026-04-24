"""AI Code Reviewer - CLI v2.1 with integrated CodexBugFinder."""

import sys
import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import json

console = Console()

# Import CodexBugFinder (copied to src as codex_*)
try:
    from codex_bug_finder import BugDetector as CodexBugFinder
    from codex_research import ResearchReporter
    CODEX_AVAILABLE = True
except ImportError as e:
    CODEX_AVAILABLE = False


def _get_analyzer(stages=None, provider=None):
    """Create analyzer pipeline with integrated CodexBugFinder."""
    from src.config import Config
    from src.ai_client import get_ai_client
    from src.analyzer import CodeAnalyzer
    from src.pipeline import ReviewPipeline
    from src.learning import ReviewLearner

    config = Config()
    if provider:
        config.set("provider", provider)

    ai_client = get_ai_client(config)
    learner = ReviewLearner()

    codex_finder = None
    if CODEX_AVAILABLE:
        try:
            codex_finder = CodexBugFinder(mode='research')
        except Exception as e:
            console.print(f"[yellow]Note: CodexBugFinder not initialized: {e}[/yellow]")

    pipeline = ReviewPipeline(ai_client, static_analyzer=None, codex_bugfinder=codex_finder)
    return CodeAnalyzer(ai_client, pipeline=pipeline, learner=learner), learner, codex_finder


@click.group(invoke_without_command=True)
@click.version_option(version='2.1.0')
@click.pass_context
def cli(ctx):
    """🤖 AI Code Reviewer v2.1 — Multi-agent + Codex bug detection."""
    if ctx.invoked_subcommand is None:
        from src.interactive import run_interactive
        run_interactive()
        ctx.exit()


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), default='text')
@click.option('--severity', '-s', type=click.Choice(['critical', 'high', 'medium', 'low']), help='Filter by severity')
@click.option('--stages', type=str, help='Comma-separated stages (e.g. security,bugs)')
@click.option('--codex/--no-codex', default=True, help='Enable CodexBugFinder (v2.1+)')
@click.option('--sequential/--parallel', default=False, help='Run stages sequentially')
@click.option('--no-learn', is_flag=True, help='Disable learning')
@click.option('--provider', '-p', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
def review(path, output, format, severity, stages, codex, sequential, no_learn, provider):
    """🔍 Full code review (static + AI + Codex bug detection)."""
    if format != 'json':
        if codex and CODEX_AVAILABLE:
            console.print(f"[bold blue]🔍 Starting review with CodexBugFinder (v2.1):[/bold blue] {path}")
        else:
            console.print(f"[bold blue]🔍 Starting full review:[/bold blue] {path}")

    stage_list = [s.strip() for s in stages.split(",")] if stages else None

    analyzer, learner, codex_finder = _get_analyzer(stages=stage_list, provider=provider)
    if no_learn:
        analyzer.learner = None

    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.pipeline.review_file(
            path_obj, stages=stage_list, parallel=not sequential, enable_codex=codex
        )
        issues = result["issues"]
    else:
        result = analyzer.pipeline.review_directory(
            path_obj, stages=stage_list, parallel=not sequential, enable_codex=codex
        )
        issues = result["issues"]

    # Filter by severity
    if severity:
        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        min_sev = sev_order.get(severity, 0)
        issues = [i for i in issues if sev_order.get(i.severity, 0) >= min_sev]
        result["issues"] = issues

    # JSON output
    if format == 'json':
        output_data = {
            "version": result.get("version", "2.1"),
            "path": str(path),
            "issues": [{
                "type": i.type,
                "severity": i.severity,
                "message": i.message,
                "file": i.file,
                "line_number": i.line_number,
                "suggestion": i.suggestion,
                "stage": i.stage,
            } for i in issues],
            "total": len(issues),
            "codex_bugs": result.get("codex_bugs", 0),
            "stages_run": result.get("stages_run", []),
        }
        if output:
            Path(output).write_text(json.dumps(output_data, indent=2))
            console.print(f"[green]✓ JSON saved to {output}[/green]")
        else:
            console.print_json(data=output_data)
        
    # MarkDown output
    elif format == 'markdown':
        lines = [f"# AI Code Review (v2.1)\n"]
        lines.append(f"**Path:** `{path}`\n")
        lines.append(f"**Total:** {len(issues)} issues\n")
        lines.append(f"**Codex bugs:** {result.get('codex_bugs', 0)}\n")
        for i in issues:
            emoji = "🔴" if i.severity == "critical" else "🟠" if i.severity == "high" else "🟡" if i.severity == "medium" else "🟢"
            lines.append(f"### {emoji} {i.severity.upper()}: {i.type}\n")
            lines.append(f"- **File:** `{i.file}` (line {i.line_number})\n")
            lines.append(f"- **Message:** {i.message}\n")
            if i.suggestion:
                lines.append(f"- **Fix:** {i.suggestion}\n")
            if i.stage:
                lines.append(f"- **Stage:** {i.stage}\n")
            lines.append("")
        md = "".join(lines)
        if output:
            Path(output).write_text(md)
            console.print(f"[green]✓ Markdown saved to {output}[/green]")
        else:
            console.print(md)

    # Text output
    else:
        sev_colors = {
            "critical": "[red]🔴 CRITICAL[/red]",
            "high": "[orange3]🟠 HIGH[/orange3]",
            "medium": "[yellow]🟡 MEDIUM[/yellow]",
            "low": "[dim]🟢 LOW[/dim]",
        }
        for i in issues:
            console.print(f"{sev_colors.get(i.severity, i.severity)} [{i.type}] {i.message}")
            console.print(f"  📍 {i.file}:{i.line_number}", style="dim")
            if i.suggestion:
                console.print(f"  ✅ {i.suggestion}", style="yellow")
            console.print()

        if result.get("codex_bugs", 0) > 0:
            console.print(f"[bold green]🐛 CodexBugFinder: {result['codex_bugs']} bugs found![/bold green]")
        console.print(f"\n{'─' * 60}")
        console.print(f"Total: {len(issues)} | Stages: {', '.join(result.get('stages_run', []))}")

    # Learning
    if not no_learn and analyzer.learner:
        analyzer.learner.consolidate()

    critical_count = sum(1 for i in issues if i.severity == "critical")
    if critical_count > 0:
        console.print(f"[red]✗ {critical_count} critical issues found![/red]")
        raise click.Exit(code=1)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
@click.option('--provider', '-p', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
def security(path, output, format, provider):
    """🛡️ Security-focused review only."""
    if format != 'json':
        console.print(f"[bold red]🛡️ Security review:[/bold red] {path}")

    analyzer, _, _ = _get_analyzer(stages=["security"], provider=provider)
    path_obj = Path(path)
    if path_obj.is_file():
        result = analyzer.pipeline.review_file(path_obj, stages=["security"])
    else:
        result = analyzer.pipeline.review_directory(path_obj, stages=["security"])

    issues = result["issues"]

    if format == 'json':
        data = {"issues": [{
            "type": i.type, "severity": i.severity,
            "message": i.message, "file": i.file,
            "line_number": i.line_number
        } for i in issues]}
        if output:
            Path(output).write_text(json.dumps(data, indent=2))
        else:
            console.print_json(data=data)
    else:
        for i in issues:
            sev = "🔴" if i.severity == "critical" else "🟠"
            console.print(f"{sev} [{i.severity}] {i.type}: {i.message}")
            console.print(f"  📍 {i.file}:{i.line_number}", style="dim")


@cli.command()
def codex():
    """🐛 CodexBugFinder standalone scan."""
    if not CODEX_AVAILABLE:
        console.print("[red]CodexBugFinder not available[/red]")
        return
    finder = CodexBugFinder(mode='research')
    findings = finder.scan_directory('.')
    print(finder.reporter.generate_report(findings))
    print(f"\nTotal: {finder.summary()['total_findings']} bugs")


if __name__ == '__main__':
    cli()
