#!/usr/bin/env python3
"""Precompute common preflop solver solutions.

Generates JSON cache files for common preflop spots:
- RFI (Raise First In) ranges by position
- 3-bet spots
- 4-bet spots
- Squeeze spots
"""

import json
from pathlib import Path
from typing import Any

from pokercoach.core.game_state import Position

# Output directory
CACHE_DIR = Path(__file__).parent.parent / "cache" / "preflop"


def generate_rfi_range(position: Position) -> dict[str, dict[str, float]]:
    """Generate RFI (Raise First In) range for a position.

    Returns a dict mapping hand strings to action frequencies.
    """
    # Standard RFI ranges by position (simplified GTO)
    # Values are raise frequencies, rest is fold
    rfi_ranges: dict[Position, dict[str, float]] = {
        Position.UTG: {
            # Tight UTG range (~15%)
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
            "99": 0.5, "88": 0.25,
            "AKs": 1.0, "AKo": 1.0, "AQs": 1.0, "AQo": 0.75,
            "AJs": 1.0, "ATs": 0.75, "A5s": 0.5,
            "KQs": 1.0, "KQo": 0.5, "KJs": 0.75,
            "QJs": 0.5, "JTs": 0.5,
        },
        Position.HJ: {
            # HJ range (~20%)
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
            "99": 1.0, "88": 0.75, "77": 0.5,
            "AKs": 1.0, "AKo": 1.0, "AQs": 1.0, "AQo": 1.0,
            "AJs": 1.0, "AJo": 0.5, "ATs": 1.0, "A9s": 0.5,
            "A5s": 1.0, "A4s": 0.75, "A3s": 0.5,
            "KQs": 1.0, "KQo": 1.0, "KJs": 1.0, "KTs": 0.75,
            "QJs": 1.0, "QTs": 0.75, "JTs": 1.0, "T9s": 0.5,
        },
        Position.CO: {
            # CO range (~27%)
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
            "99": 1.0, "88": 1.0, "77": 1.0, "66": 0.75, "55": 0.5,
            "AKs": 1.0, "AKo": 1.0, "AQs": 1.0, "AQo": 1.0,
            "AJs": 1.0, "AJo": 1.0, "ATs": 1.0, "ATo": 0.5,
            "A9s": 1.0, "A8s": 0.75, "A7s": 0.5, "A6s": 0.5,
            "A5s": 1.0, "A4s": 1.0, "A3s": 0.75, "A2s": 0.5,
            "KQs": 1.0, "KQo": 1.0, "KJs": 1.0, "KJo": 0.5,
            "KTs": 1.0, "K9s": 0.75, "K8s": 0.25,
            "QJs": 1.0, "QJo": 0.5, "QTs": 1.0, "Q9s": 0.75,
            "JTs": 1.0, "J9s": 1.0, "J8s": 0.5,
            "T9s": 1.0, "T8s": 0.75, "98s": 1.0, "97s": 0.5,
            "87s": 1.0, "76s": 0.75, "65s": 0.75, "54s": 0.5,
        },
        Position.BTN: {
            # BTN range (~45%)
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
            "99": 1.0, "88": 1.0, "77": 1.0, "66": 1.0, "55": 1.0,
            "44": 0.75, "33": 0.5, "22": 0.5,
            "AKs": 1.0, "AKo": 1.0, "AQs": 1.0, "AQo": 1.0,
            "AJs": 1.0, "AJo": 1.0, "ATs": 1.0, "ATo": 1.0,
            "A9s": 1.0, "A9o": 0.5, "A8s": 1.0, "A7s": 1.0,
            "A6s": 1.0, "A5s": 1.0, "A4s": 1.0, "A3s": 1.0, "A2s": 1.0,
            "KQs": 1.0, "KQo": 1.0, "KJs": 1.0, "KJo": 1.0,
            "KTs": 1.0, "KTo": 0.75, "K9s": 1.0, "K8s": 0.75,
            "K7s": 0.5, "K6s": 0.5, "K5s": 0.5, "K4s": 0.25,
            "QJs": 1.0, "QJo": 1.0, "QTs": 1.0, "QTo": 0.75,
            "Q9s": 1.0, "Q8s": 0.75, "Q7s": 0.25,
            "JTs": 1.0, "JTo": 0.75, "J9s": 1.0, "J8s": 1.0, "J7s": 0.5,
            "T9s": 1.0, "T9o": 0.5, "T8s": 1.0, "T7s": 0.75,
            "98s": 1.0, "98o": 0.25, "97s": 1.0, "96s": 0.75,
            "87s": 1.0, "86s": 1.0, "85s": 0.5,
            "76s": 1.0, "75s": 0.75, "65s": 1.0, "64s": 0.5,
            "54s": 1.0, "53s": 0.5, "43s": 0.5,
        },
        Position.SB: {
            # SB range vs BB (~50% - wider due to pot odds)
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 1.0, "TT": 1.0,
            "99": 1.0, "88": 1.0, "77": 1.0, "66": 1.0, "55": 1.0,
            "44": 1.0, "33": 0.75, "22": 0.75,
            "AKs": 1.0, "AKo": 1.0, "AQs": 1.0, "AQo": 1.0,
            "AJs": 1.0, "AJo": 1.0, "ATs": 1.0, "ATo": 1.0,
            "A9s": 1.0, "A9o": 0.75, "A8s": 1.0, "A8o": 0.5,
            "A7s": 1.0, "A6s": 1.0, "A5s": 1.0, "A4s": 1.0,
            "A3s": 1.0, "A2s": 1.0, "A2o": 0.25,
            "KQs": 1.0, "KQo": 1.0, "KJs": 1.0, "KJo": 1.0,
            "KTs": 1.0, "KTo": 1.0, "K9s": 1.0, "K9o": 0.5,
            "K8s": 1.0, "K7s": 0.75, "K6s": 0.75, "K5s": 0.5,
            "K4s": 0.5, "K3s": 0.5, "K2s": 0.5,
            "QJs": 1.0, "QJo": 1.0, "QTs": 1.0, "QTo": 1.0,
            "Q9s": 1.0, "Q9o": 0.5, "Q8s": 1.0, "Q7s": 0.5, "Q6s": 0.5,
            "JTs": 1.0, "JTo": 1.0, "J9s": 1.0, "J9o": 0.5,
            "J8s": 1.0, "J7s": 0.75, "J6s": 0.5,
            "T9s": 1.0, "T9o": 0.75, "T8s": 1.0, "T7s": 1.0, "T6s": 0.5,
            "98s": 1.0, "98o": 0.5, "97s": 1.0, "96s": 1.0,
            "87s": 1.0, "87o": 0.25, "86s": 1.0, "85s": 0.75,
            "76s": 1.0, "75s": 1.0, "74s": 0.5,
            "65s": 1.0, "64s": 0.75, "54s": 1.0, "53s": 0.75,
            "43s": 0.75, "32s": 0.5,
        },
    }

    # Get range for this position
    range_dict = rfi_ranges.get(position, {})

    # Convert to full action dict format
    result: dict[str, dict[str, float]] = {}
    for hand_str, raise_freq in range_dict.items():
        result[hand_str] = {
            "raise": raise_freq,
            "fold": 1.0 - raise_freq,
            "call": 0.0,  # No limping in GTO
        }

    return result


def generate_3bet_range(
    position: Position, raiser_position: Position
) -> dict[str, dict[str, float]]:
    """Generate 3-bet range for position vs raiser.

    Args:
        position: Hero's position
        raiser_position: Position of the original raiser

    Returns:
        Dict mapping hands to action frequencies
    """
    # 3-bet value + bluff ranges (simplified)
    # BB vs BTN (common spot)
    if position == Position.BB and raiser_position == Position.BTN:
        return {
            # Value 3-bets
            "AA": {"raise": 1.0, "call": 0.0, "fold": 0.0},
            "KK": {"raise": 1.0, "call": 0.0, "fold": 0.0},
            "QQ": {"raise": 1.0, "call": 0.0, "fold": 0.0},
            "JJ": {"raise": 0.75, "call": 0.25, "fold": 0.0},
            "TT": {"raise": 0.5, "call": 0.5, "fold": 0.0},
            "AKs": {"raise": 1.0, "call": 0.0, "fold": 0.0},
            "AKo": {"raise": 0.75, "call": 0.25, "fold": 0.0},
            "AQs": {"raise": 0.75, "call": 0.25, "fold": 0.0},
            # Bluff 3-bets
            "A5s": {"raise": 0.75, "call": 0.0, "fold": 0.25},
            "A4s": {"raise": 0.5, "call": 0.0, "fold": 0.5},
            "K9s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "Q9s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "J9s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "T8s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "97s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "86s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "75s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
            "64s": {"raise": 0.25, "call": 0.5, "fold": 0.25},
        }

    # Default minimal 3-bet range
    return {
        "AA": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "KK": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "QQ": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "AKs": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "AKo": {"raise": 0.75, "call": 0.25, "fold": 0.0},
    }


def generate_squeeze_range() -> dict[str, dict[str, float]]:
    """Generate squeeze range (3-bet with caller behind)."""
    return {
        # Tighter than standard 3-bet due to multiple opponents
        "AA": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "KK": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "QQ": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "JJ": {"raise": 0.75, "call": 0.25, "fold": 0.0},
        "TT": {"raise": 0.25, "call": 0.75, "fold": 0.0},
        "AKs": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "AKo": {"raise": 1.0, "call": 0.0, "fold": 0.0},
        "AQs": {"raise": 0.75, "call": 0.25, "fold": 0.0},
        # Bluffs
        "A5s": {"raise": 0.5, "call": 0.0, "fold": 0.5},
        "A4s": {"raise": 0.25, "call": 0.0, "fold": 0.75},
    }


def create_preflop_solution(
    spot_name: str,
    strategies: dict[str, dict[str, float]],
    pot: float = 3.0,
    effective_stack: float = 100.0,
) -> dict[str, Any]:
    """Create a preflop solution JSON structure.

    Args:
        spot_name: Name of the spot (for metadata)
        strategies: Dict of hand -> action frequencies
        pot: Pot size in BB
        effective_stack: Effective stack in BB

    Returns:
        Solution dict ready for JSON serialization
    """
    return {
        "spot_name": spot_name,
        "pot": pot,
        "effective_stack": effective_stack,
        "street": "preflop",
        "strategies": strategies,
        "metadata": {
            "generated_by": "precompute_preflop.py",
            "source": "approximated_gto",
        },
    }


def main():
    """Generate all preflop cache files."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate RFI ranges for each position
    for position in [Position.UTG, Position.HJ, Position.CO, Position.BTN, Position.SB]:
        spot_name = f"rfi_{position.value.lower()}"
        strategies = generate_rfi_range(position)
        solution = create_preflop_solution(
            spot_name=spot_name,
            strategies=strategies,
            pot=1.5,  # SB posted
            effective_stack=100.0,
        )

        output_file = CACHE_DIR / f"{spot_name}.json"
        with open(output_file, "w") as f:
            json.dump(solution, f, indent=2)
        print(f"Generated: {output_file}")

    # Generate 3-bet ranges
    # BB vs BTN
    spot_name = "3bet_bb_vs_btn"
    strategies = generate_3bet_range(Position.BB, Position.BTN)
    solution = create_preflop_solution(
        spot_name=spot_name,
        strategies=strategies,
        pot=5.5,  # BTN raise to 2.5x + SB 0.5 + BB 1
        effective_stack=97.5,
    )
    with open(CACHE_DIR / f"{spot_name}.json", "w") as f:
        json.dump(solution, f, indent=2)
    print(f"Generated: {CACHE_DIR / spot_name}.json")

    # Squeeze spot
    spot_name = "squeeze_bb"
    strategies = generate_squeeze_range()
    solution = create_preflop_solution(
        spot_name=spot_name,
        strategies=strategies,
        pot=8.0,  # Raise + call + blinds
        effective_stack=97.5,
    )
    with open(CACHE_DIR / f"{spot_name}.json", "w") as f:
        json.dump(solution, f, indent=2)
    print(f"Generated: {CACHE_DIR / spot_name}.json")

    print(f"\nGenerated {len(list(CACHE_DIR.glob('*.json')))} preflop cache files")


if __name__ == "__main__":
    main()
