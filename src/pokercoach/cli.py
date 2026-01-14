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


# Create cache subcommand group
cache_app = typer.Typer(help="Cache management commands")
app.add_typer(cache_app, name="cache")


@cache_app.command()
def warm(
    spots: str = typer.Option(
        "preflop,postflop",
        "--spots",
        "-s",
        help="Comma-separated spot types to warm (preflop, postflop, all)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be generated without actually generating",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Regenerate even if cache files exist",
    ),
):
    """Warm the solver cache by precomputing common spots.

    Examples:
        pokercoach cache warm --spots=preflop
        pokercoach cache warm --spots=all --dry-run
        pokercoach cache warm --force
    """
    from pathlib import Path
    from rich.progress import Progress, SpinnerColumn, TextColumn

    # Determine cache directory
    cache_base = Path(__file__).parent.parent.parent / "cache"
    preflop_dir = cache_base / "preflop"
    postflop_dir = cache_base / "postflop"

    # Parse spots
    spot_list = [s.strip().lower() for s in spots.split(",")]
    if "all" in spot_list:
        spot_list = ["preflop", "postflop"]

    # Define spots to generate
    preflop_spots = [
        ("rfi_utg", "RFI from UTG"),
        ("rfi_hj", "RFI from HJ"),
        ("rfi_co", "RFI from CO"),
        ("rfi_btn", "RFI from BTN"),
        ("rfi_sb", "RFI from SB"),
        ("3bet_bb_vs_btn", "3-bet BB vs BTN"),
        ("squeeze_bb", "Squeeze from BB"),
    ]

    postflop_textures = [
        "dry_high", "dry_mid", "dry_low",
        "wet_connected", "wet_two_tone", "wet_broadway",
        "mono_high", "mono_mid",
        "paired_high", "paired_low",
    ]
    postflop_spots = [
        (f"{texture}_{pos}_{pot}", f"{texture} {pos.upper()} {pot.upper()}")
        for texture in postflop_textures
        for pos in ["ip", "oop"]
        for pot in ["srp", "3bet"]
    ]

    # Calculate totals
    total_preflop = len(preflop_spots) if "preflop" in spot_list else 0
    total_postflop = len(postflop_spots) if "postflop" in spot_list else 0
    total_spots = total_preflop + total_postflop

    if dry_run:
        console.print("[bold]Cache Warming - Dry Run[/bold]\n")
        console.print(f"Cache directory: {cache_base}")
        console.print(f"Selected spots: {', '.join(spot_list)}")
        console.print()

        if "preflop" in spot_list:
            console.print(f"[cyan]Preflop spots ({len(preflop_spots)}):[/cyan]")
            for filename, desc in preflop_spots:
                filepath = preflop_dir / f"{filename}.json"
                status = "[green]exists[/green]" if filepath.exists() else "[yellow]will create[/yellow]"
                console.print(f"  {desc}: {status}")

        if "postflop" in spot_list:
            console.print(f"\n[cyan]Postflop spots ({len(postflop_spots)}):[/cyan]")
            existing = sum(1 for f, _ in postflop_spots if (postflop_dir / f"{f}.json").exists())
            console.print(f"  {existing} existing, {len(postflop_spots) - existing} will create")

        console.print(f"\n[bold]Total spots: {total_spots}[/bold]")
        console.print("\nRun without --dry-run to generate cache files.")
        return

    # Actual cache generation
    console.print("[bold]Warming Solver Cache[/bold]\n")

    generated = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating cache...", total=total_spots)

        if "preflop" in spot_list:
            preflop_dir.mkdir(parents=True, exist_ok=True)

            # Import preflop generator
            import sys
            scripts_dir = Path(__file__).parent.parent.parent / "scripts"
            sys.path.insert(0, str(scripts_dir))

            try:
                from precompute_preflop import (
                    generate_rfi_range,
                    generate_3bet_range,
                    generate_squeeze_range,
                    create_preflop_solution,
                )
                import json
                from pokercoach.core.game_state import Position

                for filename, desc in preflop_spots:
                    progress.update(task, description=f"Generating {desc}...")
                    filepath = preflop_dir / f"{filename}.json"

                    if filepath.exists() and not force:
                        skipped += 1
                    else:
                        # Generate based on spot type
                        if filename.startswith("rfi_"):
                            pos_name = filename.replace("rfi_", "").upper()
                            try:
                                position = Position(pos_name)
                                strategies = generate_rfi_range(position)
                                solution = create_preflop_solution(
                                    filename, strategies, pot=1.5, effective_stack=100.0
                                )
                                with open(filepath, "w") as f:
                                    json.dump(solution, f, indent=2)
                                generated += 1
                            except (ValueError, KeyError):
                                skipped += 1
                        elif filename == "3bet_bb_vs_btn":
                            strategies = generate_3bet_range(Position.BB, Position.BTN)
                            solution = create_preflop_solution(
                                filename, strategies, pot=5.5, effective_stack=97.5
                            )
                            with open(filepath, "w") as f:
                                json.dump(solution, f, indent=2)
                            generated += 1
                        elif filename == "squeeze_bb":
                            strategies = generate_squeeze_range()
                            solution = create_preflop_solution(
                                filename, strategies, pot=8.0, effective_stack=97.5
                            )
                            with open(filepath, "w") as f:
                                json.dump(solution, f, indent=2)
                            generated += 1

                    progress.advance(task)

            except ImportError as e:
                console.print(f"[red]Error importing preflop generator: {e}[/red]")
                console.print("Run 'uv run python scripts/precompute_preflop.py' directly instead.")

        if "postflop" in spot_list:
            postflop_dir.mkdir(parents=True, exist_ok=True)

            try:
                from precompute_postflop import (
                    generate_cbet_strategy,
                    create_postflop_solution,
                )
                import json

                board_configs = {
                    "dry_high": (["As", "7d", "2c"], "dry"),
                    "dry_mid": (["Ks", "8d", "3c"], "dry"),
                    "dry_low": (["9s", "5d", "2c"], "dry"),
                    "wet_connected": (["Js", "Td", "9c"], "wet"),
                    "wet_two_tone": (["Qh", "Jh", "7c"], "wet"),
                    "wet_broadway": (["Ks", "Qd", "Jc"], "wet"),
                    "mono_high": (["Ah", "Kh", "5h"], "monotone"),
                    "mono_mid": (["Jh", "8h", "3h"], "monotone"),
                    "paired_high": (["Ks", "Kd", "7c"], "paired"),
                    "paired_low": (["7s", "7d", "2c"], "paired"),
                }

                for filename, desc in postflop_spots:
                    progress.update(task, description=f"Generating {desc}...")
                    filepath = postflop_dir / f"{filename}.json"

                    if filepath.exists() and not force:
                        skipped += 1
                    else:
                        # Parse filename to get texture, position, pot type
                        parts = filename.rsplit("_", 2)
                        if len(parts) >= 3:
                            texture_name = "_".join(parts[:-2])
                            position = parts[-2]
                            pot_type = parts[-1]

                            if texture_name in board_configs:
                                board_cards, texture = board_configs[texture_name]
                                pot = 6.0 if pot_type == "srp" else 18.0
                                stack = 94.0 if pot_type == "srp" else 82.0

                                strategies = generate_cbet_strategy(texture, position, pot_type)
                                solution = create_postflop_solution(
                                    filename, board_cards, strategies, pot, stack, position
                                )
                                with open(filepath, "w") as f:
                                    json.dump(solution, f, indent=2)
                                generated += 1
                            else:
                                skipped += 1
                        else:
                            skipped += 1

                    progress.advance(task)

            except ImportError as e:
                console.print(f"[red]Error importing postflop generator: {e}[/red]")
                console.print("Run 'uv run python scripts/precompute_postflop.py' directly instead.")

    # Summary
    console.print()
    console.print(f"[green]Generated:[/green] {generated} files")
    console.print(f"[yellow]Skipped:[/yellow] {skipped} files (already exist)")

    # Disk usage
    total_size = 0
    for cache_dir in [preflop_dir, postflop_dir]:
        if cache_dir.exists():
            for f in cache_dir.glob("*.json"):
                total_size += f.stat().st_size

    console.print(f"[dim]Total cache size: {total_size / 1024:.1f} KB[/dim]")


@cache_app.command()
def stats():
    """Show cache statistics."""
    from pathlib import Path

    cache_base = Path(__file__).parent.parent.parent / "cache"
    preflop_dir = cache_base / "preflop"
    postflop_dir = cache_base / "postflop"

    console.print("[bold]Cache Statistics[/bold]\n")

    total_files = 0
    total_size = 0

    for name, cache_dir in [("Preflop", preflop_dir), ("Postflop", postflop_dir)]:
        if cache_dir.exists():
            files = list(cache_dir.glob("*.json"))
            size = sum(f.stat().st_size for f in files)
            total_files += len(files)
            total_size += size
            console.print(f"[cyan]{name}:[/cyan] {len(files)} files, {size / 1024:.1f} KB")
        else:
            console.print(f"[cyan]{name}:[/cyan] [dim]not initialized[/dim]")

    console.print()
    console.print(f"[bold]Total:[/bold] {total_files} files, {total_size / 1024:.1f} KB")


@cache_app.command()
def clear(
    spots: str = typer.Option(
        "all",
        "--spots",
        "-s",
        help="Spot types to clear (preflop, postflop, all)",
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation",
    ),
):
    """Clear cached solver solutions."""
    from pathlib import Path

    cache_base = Path(__file__).parent.parent.parent / "cache"
    preflop_dir = cache_base / "preflop"
    postflop_dir = cache_base / "postflop"

    spot_list = [s.strip().lower() for s in spots.split(",")]
    if "all" in spot_list:
        spot_list = ["preflop", "postflop"]

    dirs_to_clear = []
    if "preflop" in spot_list and preflop_dir.exists():
        dirs_to_clear.append(preflop_dir)
    if "postflop" in spot_list and postflop_dir.exists():
        dirs_to_clear.append(postflop_dir)

    if not dirs_to_clear:
        console.print("[yellow]No cache to clear.[/yellow]")
        return

    total_files = sum(len(list(d.glob("*.json"))) for d in dirs_to_clear)

    if not confirm:
        console.print(f"This will delete {total_files} cache files.")
        if not typer.confirm("Continue?"):
            raise typer.Abort()

    deleted = 0
    for cache_dir in dirs_to_clear:
        for f in cache_dir.glob("*.json"):
            f.unlink()
            deleted += 1

    console.print(f"[green]Deleted {deleted} cache files.[/green]")


@app.command()
def version():
    """Show version information."""
    from pokercoach import __version__

    console.print(f"PokerCoach v{__version__}")


if __name__ == "__main__":
    app()
