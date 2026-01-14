"""PokerCoach CLI."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
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
    pot: Optional[float] = typer.Option(None, "--pot", help="Current pot size in BBs"),
    stack: Optional[float] = typer.Option(None, "--stack", "-s", help="Effective stack in BBs"),
):
    """Ask the poker coach a question."""
    from pokercoach.core.game_state import Board, Card, GameState, Hand as PokerHand, Player
    from pokercoach.core.game_state import Position as GamePosition
    from pokercoach.llm.coach import CoachConfig, PokerCoach
    from pokercoach.solver.texas_solver import PrecomputedSolver, TexasSolverBridge, TexasSolverConfig

    # Read API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]")
        console.print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        raise typer.Exit(1)

    # Read solver path from environment (optional)
    solver_path_str = os.environ.get("TEXASSOLVER_PATH")
    fallback_solver: Optional[TexasSolverBridge] = None
    if solver_path_str:
        solver_path = Path(solver_path_str)
        if solver_path.exists():
            solver_config = TexasSolverConfig(binary_path=solver_path)
            fallback_solver = TexasSolverBridge(solver_config)

    # Create PrecomputedSolver with cache fallback
    cache_dir = Path(__file__).parent.parent.parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    solver = PrecomputedSolver(
        cache_dir=cache_dir,
        fallback_solver=fallback_solver,
    )

    # Create coach instance
    config = CoachConfig(api_key=api_key)
    coach = PokerCoach(config=config, solver=solver)

    # Build GameState from options
    game_state: Optional[GameState] = None
    if hand or board or position or pot or stack:
        game_state = GameState(
            pot=pot if pot else 3.0,
            effective_stack=stack if stack else 100.0,
        )

        # Parse position
        if position:
            try:
                game_state.hero_position = GamePosition(position.upper())
            except (ValueError, KeyError):
                console.print(f"[yellow]Warning: Unknown position '{position}', using BTN[/yellow]")
                game_state.hero_position = GamePosition.BTN

        # Parse board cards
        if board:
            board_cards = board.replace(",", " ").split()
            for card_str in board_cards:
                card_str = card_str.strip()
                if len(card_str) >= 2:
                    try:
                        card = Card.from_string(card_str)
                        game_state.board.add_card(card)
                    except (ValueError, KeyError):
                        console.print(f"[yellow]Warning: Invalid board card '{card_str}'[/yellow]")

        # Parse hero's hand and create hero player
        if hand:
            try:
                hero_hand = PokerHand.from_string(hand)
                hero_player = Player(
                    position=game_state.hero_position or GamePosition.BTN,
                    stack=game_state.effective_stack,
                    hand=hero_hand,
                    is_hero=True,
                )
                game_state.players.append(hero_player)
            except (ValueError, KeyError):
                console.print(f"[yellow]Warning: Invalid hand format '{hand}'[/yellow]")

    # Display context
    console.print(f"[bold]Question:[/bold] {question}")
    if hand:
        console.print(f"[dim]Hand: {hand}[/dim]")
    if board:
        console.print(f"[dim]Board: {board}[/dim]")
    if position:
        console.print(f"[dim]Position: {position}[/dim]")
    if pot:
        console.print(f"[dim]Pot: {pot} BB[/dim]")
    if stack:
        console.print(f"[dim]Stack: {stack} BB[/dim]")

    console.print()

    # Call coach and print response
    with console.status("[bold green]Thinking...[/bold green]"):
        try:
            response = coach.ask(question, game_state)
            console.print(Panel(response, title="[bold]Coach Response[/bold]", border_style="green"))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def analyze(
    file: Path = typer.Argument(..., help="Hand history file to analyze"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="File format (auto-detected if not specified)"),
    hero: str = typer.Option("Hero", "--hero", help="Hero's screen name"),
):
    """Analyze a hand history file."""
    from pokercoach.storage.database import Database
    from pokercoach.storage.hand_repository import HandRepository
    from pokercoach.storage.importer import HandHistoryImporter, PokerStarsParser

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Analyzing:[/bold] {file}")

    # Detect format from flag or filename
    detected_format = format
    if detected_format is None:
        # Try to auto-detect from filename
        filename_lower = file.name.lower()
        if "pokerstars" in filename_lower or "ps_" in filename_lower:
            detected_format = "pokerstars"
        elif "ggpoker" in filename_lower or "gg_" in filename_lower:
            detected_format = "ggpoker"
        elif "partypoker" in filename_lower:
            detected_format = "partypoker"
        else:
            # Default to pokerstars, will try to detect from content
            detected_format = None

    console.print(f"[dim]Format: {detected_format or 'auto-detect'}[/dim]")
    console.print(f"[dim]Hero: {hero}[/dim]")
    console.print()

    # Create database and repository
    db_path = Path(__file__).parent.parent.parent / "data" / "pokercoach.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(db_path=db_path)
    db_session = database.get_session()
    repository = HandRepository(session=db_session)

    # Create importer with appropriate parser
    importer = HandHistoryImporter(repository=repository, hero_name=hero)

    # Import hands from file
    with console.status("[bold green]Importing hands...[/bold green]"):
        try:
            result = importer.import_from_file(file, site=detected_format)
        except Exception as e:
            console.print(f"[red]Import error: {e}[/red]")
            db_session.close()
            raise typer.Exit(1)

    # Print summary
    console.print("[bold]Import Summary[/bold]")
    console.print()

    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Hands imported", str(result.hands_imported))
    summary_table.add_row("Hands failed", str(result.hands_failed))

    console.print(summary_table)

    # Print errors if any
    if result.errors:
        console.print()
        console.print(f"[yellow]Errors ({len(result.errors)}):[/yellow]")
        for error in result.errors[:5]:  # Show first 5 errors
            console.print(f"  [dim]- {error}[/dim]")
        if len(result.errors) > 5:
            console.print(f"  [dim]... and {len(result.errors) - 5} more[/dim]")

    # Print stats
    if result.hands_imported > 0:
        console.print()
        console.print("[bold]Statistics[/bold]")

        # Query some basic stats from imported hands
        total_hands = repository.count_hands()
        console.print(f"[dim]Total hands in database: {total_hands}[/dim]")

    db_session.close()

    if result.hands_imported == 0 and result.hands_failed > 0:
        console.print()
        console.print("[yellow]No hands imported. Check the file format and hero name.[/yellow]")
        raise typer.Exit(1)


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
