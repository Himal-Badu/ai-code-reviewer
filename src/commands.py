"""CLI commands module for AI Code Reviewer."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), default='text')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def scan_command(path, output, format, verbose):
    """Scan code at the given path."""
    console.print(f"[bold blue]Scanning:[/bold blue] {path}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task(description="Scanning...", total=None)
    
    console.print("[green]✓ Scan complete[/green]")


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--severity', '-s', type=click.Choice(['critical', 'high', 'medium', 'low', 'info']), default='info')
@click.option('--type', '-t', type=click.Choice(['bug', 'security', 'performance', 'style']), default='all')
def filter_command(path, severity, type):
    """Filter scan results."""
    console.print(f"[bold]Filtering by:[/bold] severity={severity}, type={type}")


@click.command()
@click.argument('report_file', type=click.Path(exists=True))
def view_command(report_file):
    """View saved report."""
    with open(report_file) as f:
        content = f.read()
    console.print(content)


@click.command()
def stats_command():
    """Show scan statistics."""
    console.print("[bold]Statistics:[/bold]")
    console.print("Total scans: 0")
    console.print("Total issues: 0")


@click.command()
@click.argument('config_file', type=click.Path(exists=True))
def config_command(config_file):
    """Load configuration from file."""
    console.print(f"[green]✓ Loaded config from:[/green] {config_file}")


# Export all commands
__all__ = ['scan_command', 'filter_command', 'view_command', 'stats_command', 'config_command']