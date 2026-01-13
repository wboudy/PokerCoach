"""PokerCoach CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="pokercoach",
    help="AI-powered poker coaching system",
)
console = Console()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question for the poker coach"),
    hand: Optional[str] = typer.Option(None, "--hand", "-h", help="Your hand (e.g., 'AsKs')"),
    board: Optional[str] = typer.Option(None, "--board", "-b", help="Board cards"),
    position: Optional[str] = typer.Option(None, "--position", "-p", help="Your position"),
):
    """Ask the poker coach a question."""
    console.print(f"[bold]Question:[/bold] {question}")

    if hand:
        console.print(f"[dim]Hand: {hand}[/dim]")
    if board:
        console.print(f"[dim]Board: {board}[/dim]")
    if position:
        console.print(f"[dim]Position: {position}[/dim]")

    console.print("\n[yellow]Coach integration not yet implemented.[/yellow]")
    console.print("Run 'pokercoach serve' to start the web interface.")


@app.command()
def analyze(
    file: Path = typer.Argument(..., help="Hand history file to analyze"),
    format: str = typer.Option("pokerstars", "--format", "-f", help="File format"),
):
    """Analyze a hand history file."""
    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Analyzing:[/bold] {file}")
    console.print(f"[dim]Format: {format}[/dim]")
    console.print("\n[yellow]Analysis not yet implemented.[/yellow]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the web server."""
    import uvicorn

    console.print(f"[bold]Starting PokerCoach server...[/bold]")
    console.print(f"[dim]URL: http://{host}:{port}[/dim]")

    uvicorn.run(
        "pokercoach.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def capture(
    site: str = typer.Option("pokerstars", "--site", "-s", help="Poker site"),
    calibrate: bool = typer.Option(False, "--calibrate", "-c", help="Run calibration wizard"),
):
    """Start screen capture for live coaching."""
    console.print(f"[bold]Screen capture for {site}[/bold]")

    if calibrate:
        console.print("[yellow]Calibration wizard not yet implemented.[/yellow]")
    else:
        console.print("[yellow]Live capture not yet implemented.[/yellow]")


@app.command()
def players(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search for player"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
):
    """View tracked players."""
    console.print("[bold]Tracked Players[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Player ID")
    table.add_column("Hands")
    table.add_column("VPIP")
    table.add_column("PFR")
    table.add_column("Type")

    # TODO: Query database for players
    console.print("[yellow]Player database not yet populated.[/yellow]")


@app.command()
def version():
    """Show version information."""
    from pokercoach import __version__

    console.print(f"PokerCoach v{__version__}")


if __name__ == "__main__":
    app()
