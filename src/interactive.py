"""Interactive mode for AI Code Reviewer.

Claude Code / Codex inspired interface:
- Clean minimal banner
- Chat-style prompt (You: / AI Reviewer:)
- Guided setup on first run
- Plain language commands
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

from src.config import Config
from src.ai_client import get_ai_client, PROVIDERS, ALL_ENV_VARS
from src.analyzer import CodeAnalyzer
from src.pipeline import ReviewPipeline, ALL_STAGES
from src.learning import ReviewLearner

console = Console(highlight=False)

# ---------------------------------------------------------------------------
# Banner — clean, Claude Code style
# ---------------------------------------------------------------------------

def show_banner():
    """Show a clean, minimal banner."""
    console.print()
    console.print("[bold white]  AI Code Reviewer[/bold white] [dim]v2.0.0[/dim]")
    console.print("  [dim]Universal · Multi-Agent · Learns from your code[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Prompt style
# ---------------------------------------------------------------------------

def user_prompt(prompt_text: str = "") -> str:
    """Claude Code style prompt."""
    return Prompt.ask(f"[bold cyan]❯[/bold cyan] {prompt_text}" if prompt_text else "[bold cyan]❯[/bold cyan]")


def ai_say(text: str, style: str = ""):
    """AI responds with a prefix."""
    for line in text.split("\n"):
        console.print(f"  [dim]│[/dim] {line}" if not style else f"  [dim]│[/dim] [{style}]{line}[/{style}]")


def ai_panel(title: str, body: str, border: str = "cyan"):
    """AI responds in a panel."""
    console.print()
    console.print(Panel(
        body,
        title=f"[bold]{title}[/bold]",
        border_style=border,
        box=box.ROUNDED,
        padding=(0, 2),
    ))


def divider():
    """Clean divider line."""
    console.print(f"  [dim]{'─' * 60}[/dim]")


# ---------------------------------------------------------------------------
# API Key Setup
# ---------------------------------------------------------------------------

def setup_api_key() -> Config:
    """Guided API key setup — Claude Code style."""
    console.print()
    ai_say("First, let's connect your AI provider.")
    ai_say("You need [bold]one[/bold] API key. Any LLM works.")
    console.print()

    # Check existing
    available = {}
    for env_var in ALL_ENV_VARS:
        key = os.environ.get(env_var, "")
        if key:
            # Find provider name
            prov_name = env_var.replace("_API_KEY", "").title()
            for pid, p in PROVIDERS.items():
                if p.env_var == env_var:
                    prov_name = p.name
                    break
            available[prov_name] = key[:8] + "..." + key[-4:]

    if available:
        ai_say("[green]Found existing keys:[/green]")
        for p, masked in available.items():
            ai_say(f"  ✓ {p} — {masked}")
        console.print()
        use = Confirm.ask(f"  [cyan]❯[/cyan] Use existing?", default=True)
        if use:
            config = Config()
            # Find which provider
            for env_var in ALL_ENV_VARS:
                if os.environ.get(env_var):
                    for pid, p in PROVIDERS.items():
                        if p.env_var == env_var:
                            config.set("provider", pid)
                            break
                    break
            config.save()
            ai_say(f"[green]✓ Connected.[/green]")
            return config

    # Provider menu — all providers
    ai_say("[bold]Choose your AI provider:[/bold]")
    console.print()

    provider_list = list(PROVIDERS.items())
    for i, (pid, prov) in enumerate(provider_list, 1):
        tag = " [dim](free)[/dim]" if pid in ("groq", "ollama") else ""
        console.print(f"  [cyan]{i:2}[/cyan]  {prov.name:14} {prov.default_model:30}{tag}")

    skip_num = len(provider_list) + 1
    console.print(f"  [cyan]{skip_num:2}[/cyan]  Skip              static analysis only")
    console.print()

    choices = [str(i) for i in range(1, skip_num + 1)]
    choice = Prompt.ask("  [cyan]❯[/cyan] Pick", choices=choices, default="1")

    if int(choice) == skip_num:
        ai_say("[dim]No AI key. Running static analysis only.[/dim]")
        return Config()

    prov_id, prov = provider_list[int(choice) - 1]
    model = prov.default_model

    ai_say(f"[bold]{prov.name}[/bold] → {model}")

    # Show where to get key
    urls = {
        "openai": "platform.openai.com/api-keys",
        "anthropic": "console.anthropic.com",
        "google": "aistudio.google.com/apikey",
        "groq": "console.groq.com/keys",
        "deepseek": "platform.deepseek.com",
        "mistral": "console.mistral.ai",
        "openrouter": "openrouter.ai/keys",
        "together": "api.together.xyz",
        "ollama": "ollama.com (no key needed for local)",
    }
    if prov_id in urls:
        ai_say(f"[dim]Get your key at: {urls[prov_id]}[/dim]")
    console.print()

    if prov_id == "ollama":
        ai_say("[dim]Ollama detected — no key needed if running locally.[/dim]")
        config = Config()
        config.set("provider", "ollama")
        config.save()
        return config

    api_key = Prompt.ask(f"  [cyan]❯[/cyan] Paste your {prov.name} key", password=True)

    if not api_key or len(api_key) < 8:
        ai_say("[red]✗ Invalid key. Switching to static mode.[/red]")
        return Config()

    os.environ[prov.env_var] = api_key
    config = Config()
    config.set("provider", prov_id)
    config.set("api_key", api_key)
    config.save()

    ai_say(f"[green]✓ Connected to {prov.name} ({model})[/green]")
    return config


# ---------------------------------------------------------------------------
# Directory Selection
# ---------------------------------------------------------------------------

def select_directory() -> Path:
    """Guided directory selection."""
    console.print()
    ai_say("Which project should I review?")
    console.print()
    ai_say(f"[dim]Current: {Path.cwd()}[/dim]")
    console.print()

    exclude = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}

    while True:
        path_str = Prompt.ask("  [cyan]❯[/cyan] Path", default=".")

        if path_str.lower() in ("here", "this", "."):
            path = Path.cwd()
        else:
            path = Path(os.path.expanduser(path_str)).resolve()

        if not path.exists():
            ai_say(f"[red]Path not found: {path}[/red]")
            continue

        if path.is_file():
            ai_say(f"[dim]Reviewing single file: {path.name}[/dim]")
            return path

        # Scan for code files
        code_files = []
        for ext in ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.jsx", "*.tsx"]:
            for f in path.rglob(ext):
                if not any(ex in f.parts for ex in exclude):
                    code_files.append(f)

        if not code_files:
            ai_say("[yellow]No code files found here.[/yellow]")
            retry = Confirm.ask("  [cyan]❯[/cyan] Try again?", default=True)
            if not retry:
                return path
            continue

        ai_say(f"[green]Found {len(code_files)} code files[/green]")
        for f in code_files[:6]:
            ai_say(f"  [dim]📄 {f.relative_to(path)}[/dim]")
        if len(code_files) > 6:
            ai_say(f"  [dim]  ... +{len(code_files) - 6} more[/dim]")
        console.print()

        ok = Confirm.ask("  [cyan]❯[/cyan] Review this?", default=True)
        if ok:
            return path


# ---------------------------------------------------------------------------
# Command Parser
# ---------------------------------------------------------------------------

KEYWORD_MAP = {
    "security": "security", "secure": "security", "vulnerabilit": "security",
    "vuln": "security", "hack": "security", "inject": "security",
    "secret": "security", "owasp": "security", "exploit": "security",
    "auth": "security", "xss": "security", "csrf": "security",

    "bug": "bugs", "error": "bugs", "broken": "bugs", "crash": "bugs",
    "fix": "bugs", "debug": "bugs", "exception": "bugs", "fault": "bugs",
    "null": "bugs", "none": "bugs", "logic": "bugs",

    "performance": "performance", "slow": "performance", "fast": "performance",
    "optimi": "performance", "speed": "performance", "memory": "performance",
    "complexit": "performance", "efficient": "performance", "bottleneck": "performance",

    "style": "style", "clean": "style", "refactor": "style", "quality": "style",
    "messy": "style", "readable": "style", "naming": "style", "duplication": "style",
    "unused": "style", "import": "style", "document": "style", "lint": "style",

    "everything": "all", "all": "all", "full": "all", "complete": "all",
    "review": "all", "check": "all", "analyze": "all", "scan": "all",
}

STAGE_EMOJI = {"security": "🛡️", "bugs": "🐛", "performance": "⚡", "style": "✨"}


def parse_command(text: str) -> List[str]:
    """Parse plain language → review stages."""
    text = text.lower().strip()
    stages = set()
    has_all = False

    for keyword, stage in KEYWORD_MAP.items():
        if keyword in text:
            if stage == "all":
                has_all = True
            else:
                stages.add(stage)

    if stages:
        return list(stages)
    if has_all:
        return ALL_STAGES
    return ALL_STAGES


# ---------------------------------------------------------------------------
# Review Runner
# ---------------------------------------------------------------------------

def run_review(project_path: Path, stages: List[str], config: Config):
    """Run review with clean output."""
    console.print()
    divider()

    stage_str = " + ".join(f"{STAGE_EMOJI.get(s, '🔍')} {s}" for s in stages)
    has_ai = bool(config.get("api_key") or any(os.environ.get(v) for v in PROVIDER_ENV_KEYS.values()))
    mode = f"[green]AI ({config.get('provider', 'auto')})[/green]" if has_ai else "[dim]static[/dim]"

    ai_say(f"Reviewing [bold]{project_path}[/bold]")
    ai_say(f"Stages: {stage_str}  |  Mode: {mode}")
    console.print()

    # Build
    ai_client = get_ai_client(config)
    learner = ReviewLearner()
    pipeline = ReviewPipeline(ai_client)
    analyzer = CodeAnalyzer(ai_client, pipeline=pipeline, learner=learner)

    # Run
    with console.status("[bold cyan]  Analyzing...", spinner="dots"):
        if project_path.is_file():
            result = analyzer.analyze_file(project_path, stages=stages if stages != ALL_STAGES else None)
        else:
            result = analyzer.analyze_directory(project_path, stages=stages if stages != ALL_STAGES else None)

    issues = result.get("issues", [])
    files = result.get("files_reviewed", result.get("files_analyzed", 1))

    # Results
    console.print()

    if not issues:
        ai_panel("✅ All Clear", "No issues found. Your code looks clean.", "green")
        return

    # Issues table
    table = Table(
        title=f"  {len(issues)} issues in {files} file(s)",
        box=box.SIMPLE_HEAVY,
        show_edge=True,
        border_style="dim",
        title_style="bold",
    )
    table.add_column("Sev", width=4, justify="center")
    table.add_column("Type", width=12)
    table.add_column("File", width=18, style="dim")
    table.add_column("Line", width=4, justify="right")
    table.add_column("Message", width=42)
    table.add_column("Fix", style="yellow", width=36)

    sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}

    for issue in issues[:25]:
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        table.add_row(
            sev_icon.get(d.get("severity", ""), "⚪"),
            d.get("type", ""),
            Path(d.get("file", "")).name if d.get("file") else "",
            str(d.get("line_number", "")),
            d.get("message", "")[:42],
            (d.get("suggestion") or "")[:36],
        )

    console.print(table)

    if len(issues) > 25:
        ai_say(f"[dim]... +{len(issues) - 25} more issues[/dim]")

    # Summary
    sev_count = {}
    for i in issues:
        d = i.to_dict() if hasattr(i, 'to_dict') else i
        s = d.get("severity", "?")
        sev_count[s] = sev_count.get(s, 0) + 1

    summary = "  ".join(
        f"[{'red' if s=='critical' else 'orange3' if s=='high' else 'yellow' if s=='medium' else 'dim'}]{s.upper()}:{c}[/]"
        for s, c in sorted(sev_count.items(), key=lambda x: ["critical","high","medium","low"].index(x[0]) if x[0] in ["critical","high","medium","low"] else 99)
    )
    ai_say(summary)
    console.print()

    # Learning
    if learner:
        learner.consolidate()


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

HELP_TEXT = """[bold]Commands:[/bold]

  [cyan]review my code[/cyan]              Run full review
  [cyan]check for security issues[/cyan]   Security scan
  [cyan]find bugs[/cyan]                   Bug detection
  [cyan]is my code slow?[/cyan]            Performance check
  [cyan]make my code clean[/cyan]          Style & quality
  [cyan]review everything[/cyan]           All stages

[bold]Controls:[/bold]

  [cyan]change project[/cyan]              Switch directory
  [cyan]change key[/cyan]                  Update API key
  [cyan]help[/cyan]                        Show this help
  [cyan]quit[/cyan]                        Exit"""


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def run_interactive():
    """Claude Code style interactive mode."""
    console.clear()
    show_banner()

    # Setup
    config = setup_api_key()
    project_path = select_directory()

    # Ready
    console.print()
    ai_say(f"Ready. Reviewing [bold]{project_path.name}[/bold]")
    ai_say("Type what you want to check, or [cyan]help[/cyan] for options.")
    divider()

    # Loop
    while True:
        console.print()
        cmd = user_prompt()

        if not cmd:
            continue

        cmd_lower = cmd.lower().strip()

        if cmd_lower in ("quit", "exit", "q", "bye", "done", "q()"):
            console.print()
            ai_say("[dim]Goodbye.[/dim]")
            console.print()
            break

        if cmd_lower in ("help", "?", "h"):
            console.print()
            ai_panel("Help", HELP_TEXT, "cyan")
            continue

        if cmd_lower in ("change project", "new project", "switch project", "cd"):
            project_path = select_directory()
            console.print()
            ai_say(f"Now reviewing: [bold]{project_path.name}[/bold]")
            continue

        if cmd_lower in ("change key", "new key", "switch key", "api key", "key"):
            config = setup_api_key()
            console.print()
            ai_say("[green]Key updated.[/green]")
            continue

        # Parse and run
        stages = parse_command(cmd)
        run_review(project_path, stages, config)

        # Post-review prompt
        console.print()
        ai_say("What next? (or [cyan]quit[/cyan])")
        divider()


def main():
    """Entry point."""
    try:
        run_interactive()
    except KeyboardInterrupt:
        console.print()
        ai_say("[dim]Interrupted.[/dim]")
        console.print()
    except EOFError:
        console.print()
        ai_say("[dim]Goodbye.[/dim]")
        console.print()
    except Exception as e:
        console.print(f"\n  [red]Error: {e}[/red]\n")
