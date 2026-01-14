#!/usr/bin/env python3
"""Precompute common postflop solver solutions.

Generates JSON cache files for common postflop spots:
- SRP (Single Raised Pot) cbet spots
- 3-bet pot cbet spots
- Common board textures
"""

import json
from pathlib import Path
from typing import Any

# Note: These imports are not directly used in this script but document the types
# that the generated cache files are compatible with
__all__ = ["main"]

# Output directory
CACHE_DIR = Path(__file__).parent.parent / "cache" / "postflop"


def generate_cbet_strategy(
    board_texture: str,
    position: str,
    pot_type: str = "srp",
) -> dict[str, dict[str, float]]:
    """Generate c-bet strategy for a board texture.

    Args:
        board_texture: Type of board (dry, wet, monotone, etc.)
        position: IP or OOP
        pot_type: 'srp' (single raised pot) or '3bet'

    Returns:
        Dict of hand -> action frequencies
    """
    # Base strategies vary by texture and position
    strategies: dict[str, dict[str, float]] = {}

    # Overpairs and sets - always betting
    value_hands = {
        "AA": {"bet": 1.0, "check": 0.0},
        "KK": {"bet": 0.9, "check": 0.1},
        "QQ": {"bet": 0.85, "check": 0.15},
        "JJ": {"bet": 0.75, "check": 0.25},
        "TT": {"bet": 0.7, "check": 0.3},
    }

    # Strong draws
    draw_hands = {
        "AhKh": {"bet": 0.7, "check": 0.3},  # Backdoor + overcards
        "AhQh": {"bet": 0.65, "check": 0.35},
        "KhQh": {"bet": 0.6, "check": 0.4},
        "JhTh": {"bet": 0.5, "check": 0.5},  # Gutshot + backdoors
        "Th9h": {"bet": 0.45, "check": 0.55},
    }

    # Air/weak hands
    weak_hands = {
        "7h2c": {"bet": 0.15, "check": 0.85},
        "8h3c": {"bet": 0.1, "check": 0.9},
        "9h4c": {"bet": 0.1, "check": 0.9},
        "6h2d": {"bet": 0.05, "check": 0.95},
    }

    # Adjust based on texture
    if board_texture == "dry":
        # More c-betting on dry boards
        for hand, actions in value_hands.items():
            strategies[hand] = {"bet": min(1.0, actions["bet"] + 0.1), "check": max(0.0, actions["check"] - 0.1)}
        for hand, actions in draw_hands.items():
            strategies[hand] = {"bet": min(1.0, actions["bet"] + 0.15), "check": max(0.0, actions["check"] - 0.15)}
        for hand, actions in weak_hands.items():
            strategies[hand] = {"bet": min(1.0, actions["bet"] + 0.1), "check": max(0.0, actions["check"] - 0.1)}

    elif board_texture == "wet":
        # Less c-betting on wet boards
        for hand, actions in value_hands.items():
            strategies[hand] = {"bet": max(0.0, actions["bet"] - 0.1), "check": min(1.0, actions["check"] + 0.1)}
        for hand, actions in draw_hands.items():
            strategies[hand] = {"bet": max(0.0, actions["bet"] - 0.05), "check": min(1.0, actions["check"] + 0.05)}
        for hand, actions in weak_hands.items():
            strategies[hand] = {"bet": max(0.0, actions["bet"] - 0.05), "check": min(1.0, actions["check"] + 0.05)}

    elif board_texture == "monotone":
        # Very selective on monotone boards
        for hand, actions in value_hands.items():
            strategies[hand] = {"bet": max(0.3, actions["bet"] - 0.3), "check": min(0.7, actions["check"] + 0.3)}
        for hand, actions in draw_hands.items():
            # Bet more with flush draws
            strategies[hand] = {"bet": min(1.0, actions["bet"] + 0.2), "check": max(0.0, actions["check"] - 0.2)}
        for hand, _actions in weak_hands.items():
            strategies[hand] = {"bet": 0.0, "check": 1.0}

    else:  # paired or other
        strategies.update(value_hands)
        strategies.update(draw_hands)
        strategies.update(weak_hands)

    # Adjust for position
    if position == "oop":
        # Check more OOP
        for hand in strategies:
            bet_freq = strategies[hand].get("bet", 0)
            strategies[hand] = {
                "bet": max(0.0, bet_freq - 0.15),
                "check": min(1.0, 1.0 - max(0.0, bet_freq - 0.15)),
            }

    # Adjust for 3-bet pots
    if pot_type == "3bet":
        # Higher frequency betting in 3-bet pots (range advantage)
        for hand in strategies:
            bet_freq = strategies[hand].get("bet", 0)
            strategies[hand] = {
                "bet": min(1.0, bet_freq + 0.1),
                "check": max(0.0, 1.0 - min(1.0, bet_freq + 0.1)),
            }

    return strategies


def create_postflop_solution(
    spot_name: str,
    board: list[str],
    strategies: dict[str, dict[str, float]],
    pot: float,
    effective_stack: float,
    position: str,
) -> dict[str, Any]:
    """Create a postflop solution JSON structure.

    Args:
        spot_name: Name of the spot
        board: List of board cards
        strategies: Dict of hand -> action frequencies
        pot: Pot size in BB
        effective_stack: Effective stack in BB
        position: 'ip' or 'oop'

    Returns:
        Solution dict for JSON serialization
    """
    return {
        "spot_name": spot_name,
        "board": board,
        "pot": pot,
        "effective_stack": effective_stack,
        "street": "flop" if len(board) == 3 else "turn" if len(board) == 4 else "river",
        "position": position,
        "strategies": strategies,
        "metadata": {
            "generated_by": "precompute_postflop.py",
            "source": "approximated_gto",
        },
    }


def main():
    """Generate all postflop cache files."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Common board textures
    board_configs = [
        # Dry boards
        ("dry_high", ["As", "7d", "2c"], "dry"),
        ("dry_mid", ["Ks", "8d", "3c"], "dry"),
        ("dry_low", ["9s", "5d", "2c"], "dry"),

        # Wet boards
        ("wet_connected", ["Js", "Td", "9c"], "wet"),
        ("wet_two_tone", ["Qh", "Jh", "7c"], "wet"),
        ("wet_broadway", ["Ks", "Qd", "Jc"], "wet"),

        # Monotone boards
        ("mono_high", ["Ah", "Kh", "5h"], "monotone"),
        ("mono_mid", ["Jh", "8h", "3h"], "monotone"),

        # Paired boards
        ("paired_high", ["Ks", "Kd", "7c"], "paired"),
        ("paired_low", ["7s", "7d", "2c"], "paired"),
    ]

    # Generate for each board in both positions and pot types
    for board_name, board_cards, texture in board_configs:
        for position in ["ip", "oop"]:
            for pot_type in ["srp", "3bet"]:
                spot_name = f"{board_name}_{position}_{pot_type}"

                # Set pot/stack based on pot type
                if pot_type == "srp":
                    pot = 6.0  # Standard SRP
                    stack = 94.0
                else:  # 3bet
                    pot = 18.0  # Standard 3bet pot
                    stack = 82.0

                strategies = generate_cbet_strategy(texture, position, pot_type)
                solution = create_postflop_solution(
                    spot_name=spot_name,
                    board=board_cards,
                    strategies=strategies,
                    pot=pot,
                    effective_stack=stack,
                    position=position,
                )

                output_file = CACHE_DIR / f"{spot_name}.json"
                with open(output_file, "w") as f:
                    json.dump(solution, f, indent=2)
                print(f"Generated: {output_file}")

    print(f"\nGenerated {len(list(CACHE_DIR.glob('*.json')))} postflop cache files")


if __name__ == "__main__":
    main()
