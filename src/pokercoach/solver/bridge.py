"""Abstract solver bridge interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from pokercoach.core.game_state import Action, ActionType, GameState, Hand


@dataclass
class Strategy:
    """GTO strategy for a specific hand in a spot."""

    hand: Hand
    actions: dict[ActionType, float]  # Action -> Frequency

    @property
    def primary_action(self) -> ActionType:
        """Most frequent action."""
        return max(self.actions, key=lambda a: self.actions[a])

    def frequency(self, action: ActionType) -> float:
        """Get frequency for an action."""
        return self.actions.get(action, 0.0)


@dataclass
class Solution:
    """Complete solver solution for a game state."""

    game_state: GameState
    strategies: dict[str, Strategy]  # Hand string -> Strategy
    ev: dict[str, float] = field(default_factory=dict)  # Hand string -> EV
    convergence: float = 0.0  # Exploitability
    iterations: int = 0

    def get_strategy(self, hand: Hand) -> Optional[Strategy]:
        """Get strategy for a specific hand."""
        return self.strategies.get(str(hand))

    def get_ev(self, hand: Hand) -> Optional[float]:
        """Get EV for a specific hand."""
        return self.ev.get(str(hand))


class SolverBridge(ABC):
    """Abstract interface for GTO solver integration."""

    @abstractmethod
    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """
        Solve for GTO strategy.

        Args:
            game_state: Current game state
            iterations: Max iterations for convergence
            target_exploitability: Stop when exploitability below this

        Returns:
            Solution with strategies and EVs
        """
        pass

    @abstractmethod
    def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy:
        """
        Get GTO strategy for a specific hand.

        Args:
            game_state: Current game state
            hand: Hero's hand

        Returns:
            Strategy with action frequencies
        """
        pass

    @abstractmethod
    def get_ev(self, game_state: GameState, hand: Hand, action: Action) -> float:
        """
        Get expected value for a specific action.

        Args:
            game_state: Current game state
            hand: Hero's hand
            action: Action to evaluate

        Returns:
            Expected value in big blinds
        """
        pass

    @abstractmethod
    def compare_actions(
        self,
        game_state: GameState,
        hand: Hand,
        actions: list[Action],
    ) -> dict[Action, float]:
        """
        Compare EVs of multiple actions.

        Args:
            game_state: Current game state
            hand: Hero's hand
            actions: Actions to compare

        Returns:
            Dict mapping actions to EVs
        """
        pass
