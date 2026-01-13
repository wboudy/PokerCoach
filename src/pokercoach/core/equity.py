"""Hand equity calculations."""

from dataclasses import dataclass
from typing import Optional

from pokercoach.core.game_state import Board, Hand


@dataclass
class EquityResult:
    """Result of an equity calculation."""

    equity: float  # 0.0 to 1.0
    win_pct: float
    tie_pct: float
    samples: int


def calculate_equity(
    hand: Hand,
    board: Board,
    villain_range: Optional[str] = None,
    samples: int = 10000,
) -> EquityResult:
    """
    Calculate hand equity via Monte Carlo simulation.

    Args:
        hand: Hero's hole cards
        board: Current community cards
        villain_range: Villain's range in standard notation (e.g., "AA,KK,QQ,AKs")
        samples: Number of Monte Carlo iterations

    Returns:
        EquityResult with equity percentage
    """
    # TODO: Implement Monte Carlo equity calculation
    # Could use eval7 or treys library
    raise NotImplementedError("Equity calculation not yet implemented")


def range_vs_range_equity(
    hero_range: str,
    villain_range: str,
    board: Optional[Board] = None,
) -> float:
    """
    Calculate equity of one range vs another.

    Args:
        hero_range: Hero's range notation
        villain_range: Villain's range notation
        board: Optional board cards

    Returns:
        Hero's equity as float 0.0 to 1.0
    """
    raise NotImplementedError("Range vs range equity not yet implemented")
