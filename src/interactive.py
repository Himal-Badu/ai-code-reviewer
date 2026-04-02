"""Interactive mode for AI Code Reviewer.

Provides a guided, user-friendly experience:
- Beautiful banner on launch
- API key setup wizard (asks which provider + key)
- Project directory selection
- Plain language commands ("review my code for security issues")
- Visual feedback during analysis
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from src.config import Config
from src.ai_client import get_ai_client, PROVIDER_ENV_KEYS, DEFAULT_MODELS, PROVIDER_CLIENTS
from src.analyzer import CodeAnalyzer
from src.pipeline import ReviewPipeline, ALL_STAGES
from src.learning import ReviewLearner

console = Console()

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = """
[bold blue]
   ___    ________  _________  _____________  ____  _   ____________
  /   |  /  _/ __ \/ ____/   |/_  __/  _/ __ \/ __ \/ | / / ____/ __ \\
 / /| |  / // /_/ / __/ / /| | / /  / // / / / / / /  |/ / __/ / /_/ /
/ ___ | _/ // _, _/ /___/ ___ |/ / _/ // /_/ / /_/ / /|  / /___/ _, _/
/_/  |_/___/_/ |_/_____/_/  |/_/  /___/\____/\____/_/ |_/_____/_/ |_|
[/bold blue]
[bold white on blue]  Universal AI Code Reviewer  v2.0.0  [/bold white on blue]
[dim]  Powered by Claude Code architecture patterns  [/dim]
"""


# ---------------------------------------------------------------------------
# API Key Setup
# ---------------------------------------------------------------------------

def setup_api_key() -> Config:
    """Interactive API key setup wizard."""
    console.print()
    console.print(Panel(
        "[bold]🔑 API Key Setup[/bold]\n\n"
        "Connect your AI provider to enable smart code reviews.\n"
        "You only need ONE of these — pick whichever you have access to.",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    # Check existing keys
    available = {}
    for provider, env_var in PROVIDER_ENV_KEYS.items():
        key = os.environ.get(env_var, "")
        if key:
            available[provider] = key[:8] + "..." + key[-4:]

    if available:
        console.print("[green]✓ Found existing API keys:[/green]")
        for provider, masked in available.items():
            model = DEFAULT_MODELS.get(provider, "?")
            console.print(f"  • {provider:12} {masked:20} → {model}")
        console.print()

        use_existing = Confirm.ask("Use existing key(s)?", default=True)
        if use_existing:
            config = Config()
            first_provider = list(available.keys())[0]
            config.set("provider", first_provider)
            config.save()
            console.print(f"[green]✓ Using {first_provider} ({DEFAULT_MODELS.get(first_provider, '')})[/green]")
            console.print()
            return config

    # Provider selection
    console.print("[bold]Choose your AI provider:[/bold]")
    console.print()
    console.print("  [cyan]1[/cyan] OpenAI     → GPT-4o, GPT-5        (openai.com)")
    console.print("  [cyan]2[/cyan] Anthropic  → Claude               (anthropic.com)")
    console.print("  [cyan]3[/cyan] Google     → Gemini               (ai.google.dev)")
    console.print("  [cyan]4[/cyan] Skip       → Static analysis only (no API key needed)")
    console.print()

    choice = Prompt.ask("Pick one", choices=["1", "2", "3", "4"], default="1")

    provider_map = {"1": "openai", "2": "anthropic", "3": "google"}
    if choice == "4":
        console.print("[dim]Running in static-only mode. You can add an API key later.[/dim]")
        console.print()
        return Config()

    provider = provider_map[choice]
    default_model = DEFAULT_MODELS[provider]
    env_var = PROVIDER_ENV_KEYS[provider]

    console.print()
    console.print(f"[bold]Provider:[/bold] {provider.title()}  |  [bold]Model:[/bold] {default_model}")
    console.print(f"[dim]Get your key at: {'openai.com/api' if provider == 'openai' else 'anthropic.com' if provider == 'anthropic' else 'ai.google.dev'}[/dim]")
    console.print()

    api_key = Prompt.ask(f"Enter your {provider.title()} API key", password=True)

    if not api_key or len(api_key) < 10:
        console.print("[red]✗ Invalid API key. Running in static-only mode.[/red]")
        console.print()
        return Config()

    # Set in environment for this session
    os.environ[env_var] = api_key

    # Save to config
    config = Config()
    config.set("provider", provider)
    config.set("api_key", api_key)
    config.save()

    console.print(f"[green]✓ {provider.title()} connected![/green] Using model: [bold]{default_model}[/bold]")
    console.print()
    return config


# ---------------------------------------------------------------------------
# Directory Selection
# ---------------------------------------------------------------------------

def select_directory() -> Path:
    """Interactive project directory selection."""
    console.print(Panel(
        "[bold]📁 Project Selection[/bold]\n\n"
        "Enter the path to your project or code directory.",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    # Show current directory suggestion
    cwd = Path.cwd()
    console.print(f"[dim]Current directory: {cwd}[/dim]")
    console.print()

    while True:
        path_str = Prompt.ask("Project path", default=".")

        if path_str.lower() in ("here", "this", "cwd", "."):
            path = cwd
        else:
            path = Path(os.path.expanduser(path_str)).resolve()

        if not path.exists():
            console.print(f"[red]✗ Path does not exist: {path}[/red]")
            continue

        if path.is_file():
            console.print(f"[yellow]⚠ That's a file. I'll review just this file.[/yellow]")
            return path

        # Show what's in the directory (exclude venv/node_modules/.git)
        exclude = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}
        def filter_files(patterns):
            files = []
            for p in patterns:
                for f in path.rglob(p):
                    if not any(ex in f.parts for ex in exclude):
                        files.append(f)
                    if len(files) >= 5:
                        return files
            return files

        py_files = filter_files(["*.py"])
        js_files = filter_files(["*.js", "*.jsx"])
        ts_files = filter_files(["*.ts", "*.tsx"])
        all_files = py_files + js_files + ts_files

        if not all_files:
            console.print("[yellow]⚠ No supported code files found (.py, .js, .ts, .go, .rs)[/yellow]")
            retry = Confirm.ask("Try a different path?", default=True)
            if not retry:
                return path
            continue

        console.print(f"[green]✓ Found code files in:[/green] {path}")
        for f in all_files[:8]:
            console.print(f"  📄 {f.relative_to(path)}")
        if len(all_files) > 8:
            console.print(f"  ... and more")
        console.print()

        confirm = Confirm.ask("Review this project?", default=True)
        if confirm:
            return path


# ---------------------------------------------------------------------------
# Plain Language Command Parser
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    # Security
    "security": "security",
    "secure": "security",
    "vulnerabilities": "security",
    "vuln": "security",
    "hack": "security",
    "injection": "security",
    "secrets": "security",
    "owasp": "security",

    # Bugs
    "bugs": "bugs",
    "bug": "bugs",
    "errors": "bugs",
    "broken": "bugs",
    "crash": "bugs",
    "fix": "bugs",
    "debug": "bugs",

    # Performance
    "performance": "performance",
    "slow": "performance",
    "fast": "performance",
    "optimize": "performance",
    "speed": "performance",
    "memory": "performance",

    # Style
    "style": "style",
    "clean": "style",
    "refactor": "style",
    "quality": "style",
    "messy": "style",
    "readable": "style",

    # All
    "all": "all",
    "everything": "all",
    "full": "all",
    "complete": "all",
    "review": "all",
    "check": "all",
    "analyze": "all",
    "scan": "all",
}


def parse_command(text: str) -> List[str]:
    """Parse plain language into review stages.

    Examples:
        "check for security issues" → ["security"]
        "find bugs and performance problems" → ["bugs", "performance"]
        "review everything" → ["security", "bugs", "performance", "style"]
        "make my code clean" → ["style"]
    """
    text = text.lower().strip()
    stages = set()
    has_all_trigger = False

    for keyword, stage in COMMAND_MAP.items():
        if keyword in text:
            if stage == "all":
                has_all_trigger = True
            else:
                stages.add(stage)

    # If specific stages were mentioned, use those (ignore generic "check"/"review")
    if stages:
        return list(stages)

    # If only a generic trigger like "check" or "review" was used, do all
    if has_all_trigger:
        return ALL_STAGES

    # Nothing matched, default to all
    return ALL_STAGES


# ---------------------------------------------------------------------------
# Review Execution
# ---------------------------------------------------------------------------

def run_review(project_path: Path, stages: List[str], config: Config):
    """Run the review with nice visual output."""
    console.print()

    # Show what we're doing
    stage_emoji = {"security": "🛡️", "bugs": "🐛", "performance": "⚡", "style": "✨"}
    stage_display = " + ".join(f"{stage_emoji.get(s, '🔍')} {s}" for s in stages)

    console.print(Panel(
        f"[bold]🔍 Running Review[/bold]\n\n"
        f"[bold]Project:[/bold] {project_path}\n"
        f"[bold]Stages:[/bold] {stage_display}\n"
        f"[bold]Mode:[/bold] {'AI-powered' if config.get('api_key') or any(os.environ.get(v) for v in PROVIDER_ENV_KEYS.values()) else 'Static only'}",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print()

    # Build analyzer
    ai_client = get_ai_client(config)
    learner = ReviewLearner()
    pipeline = ReviewPipeline(ai_client) if stages else None
    analyzer = CodeAnalyzer(ai_client, pipeline=pipeline, learner=learner)

    # Run with spinner
    with console.status("[bold green]Analyzing code...", spinner="dots"):
        if project_path.is_file():
            result = analyzer.analyze_file(project_path, stages=stages if stages != ALL_STAGES else None)
            issues = result.get("issues", [])
            files_reviewed = 1
        else:
            result = analyzer.analyze_directory(project_path, stages=stages if stages != ALL_STAGES else None)
            issues = result.get("issues", [])
            files_reviewed = result.get("files_reviewed", result.get("files_analyzed", 0))

    # Show results
    if not issues:
        console.print(Panel(
            "[bold green]✅ No issues found![/bold green]\n\n"
            "Your code looks clean. Nice work! 🎉",
            border_style="green",
            padding=(1, 2),
        ))
        return

    # Issues table
    table = Table(title=f"🔍 Found {len(issues)} issue(s) across {files_reviewed} file(s)")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Type", style="cyan", width=14)
    table.add_column("File", style="dim", width=20)
    table.add_column("Line", justify="right", width=5)
    table.add_column("Issue", width=45)
    table.add_column("Fix", style="yellow", width=40)

    severity_colors = {
        "critical": "[bold red]CRITICAL[/bold red]",
        "high": "[bold orange3]HIGH[/bold orange3]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "low": "[dim]LOW[/dim]",
    }

    for issue in issues[:30]:  # Limit display to 30
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        sev = severity_colors.get(d.get("severity", ""), d.get("severity", ""))
        file_name = Path(d.get("file", "")).name if d.get("file") else ""

        table.add_row(
            sev,
            d.get("type", ""),
            file_name,
            str(d.get("line_number", "")),
            d.get("message", "")[:45],
            (d.get("suggestion") or "")[:40],
        )

    console.print()
    console.print(table)

    if len(issues) > 30:
        console.print(f"[dim]... and {len(issues) - 30} more issues[/dim]")

    # Summary
    severity_counts = {}
    for issue in issues:
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        sev = d.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    summary_lines = []
    for sev in ["critical", "high", "medium", "low"]:
        if sev in severity_counts:
            color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "dim"}.get(sev, "white")
            summary_lines.append(f"  [{color}]{sev.upper()}[/{color}]: {severity_counts[sev]}")

    console.print(Panel(
        f"[bold]📊 Summary[/bold]\n\n" + "\n".join(summary_lines) +
        f"\n\n[bold]Files reviewed:[/bold] {files_reviewed}",
        border_style="blue",
        padding=(1, 2),
    ))

    # Learning consolidation
    if learner:
        learner.consolidate()


# ---------------------------------------------------------------------------
# Main Interactive Loop
# ---------------------------------------------------------------------------

def run_interactive():
    """Main interactive mode — the full guided experience."""
    console.clear()
    console.print(BANNER)
    console.print()

    # Step 1: API Key Setup
    config = setup_api_key()

    # Step 2: Project Selection
    project_path = select_directory()

    # Step 3: Review Loop
    while True:
        console.print()
        console.print(Panel(
            "[bold]💬 What do you want to check?[/bold]\n\n"
            "Talk to me in plain language. Examples:\n"
            '  • "check for security issues"\n'
            '  • "find bugs"\n'
            '  • "review everything"\n'
            '  • "make my code clean"\n'
            '  • "is my code slow?"\n'
            '  • "scan for vulnerabilities"',
            border_style="magenta",
            padding=(1, 2),
        ))
        console.print()

        command = Prompt.ask("[bold magenta]You[/bold magenta]")

        if command.lower() in ("quit", "exit", "q", "bye", "done"):
            console.print()
            console.print("[bold]👋 Happy coding! See you next time.[/bold]")
            break

        if command.lower() in ("help", "?"):
            console.print()
            console.print("[bold]Available commands:[/bold]")
            console.print("  • Any plain language description of what to check")
            console.print("  • 'change project' — pick a different directory")
            console.print("  • 'change key' — update API key")
            console.print("  • 'quit' — exit")
            console.print()
            continue

        if command.lower() in ("change project", "new project", "switch project"):
            project_path = select_directory()
            continue

        if command.lower() in ("change key", "new key", "switch key", "api key"):
            config = setup_api_key()
            continue

        # Parse and run
        stages = parse_command(command)
        run_review(project_path, stages, config)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Entry point for interactive mode."""
    try:
        run_interactive()
    except KeyboardInterrupt:
        console.print()
        console.print("[bold]👋 Interrupted. Bye![/bold]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
