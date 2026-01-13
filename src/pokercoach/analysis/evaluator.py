"""Hand evaluation against GTO strategy."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from pokercoach.analysis.parser import ParsedHand
from pokercoach.core.game_state import Action, ActionType, GameState
from pokercoach.solver.bridge import SolverBridge, Strategy


class DecisionQuality(Enum):
    """Quality rating for a decision."""

    BLUNDER = auto()  # > 1 BB EV loss
    MISTAKE = auto()  # 0.5 - 1 BB EV loss
    INACCURACY = auto()  # 0.1 - 0.5 BB EV loss
    GOOD = auto()  # < 0.1 BB EV loss, not optimal
    EXCELLENT = auto()  # Optimal or near-optimal


@dataclass
class ActionEvaluation:
    """Evaluation of a single action."""

    action_taken: Action
    optimal_action: Action
    ev_taken: float
    ev_optimal: float
    ev_loss: float
    quality: DecisionQuality
    explanation: str = ""


@dataclass
class HandEvaluation:
    """Complete evaluation of a hand."""

    hand_id: str
    action_evaluations: list[ActionEvaluation]
    total_ev_loss: float
    accuracy_score: float  # 0-100 like chess.com

    @property
    def blunders(self) -> int:
        return sum(1 for e in self.action_evaluations if e.quality == DecisionQuality.BLUNDER)

    @property
    def mistakes(self) -> int:
        return sum(1 for e in self.action_evaluations if e.quality == DecisionQuality.MISTAKE)

    @property
    def inaccuracies(self) -> int:
        return sum(1 for e in self.action_evaluations if e.quality == DecisionQuality.INACCURACY)


class HandEvaluator:
    """Evaluate played hands against GTO strategy."""

    # EV loss thresholds in big blinds
    BLUNDER_THRESHOLD = 1.0
    MISTAKE_THRESHOLD = 0.5
    INACCURACY_THRESHOLD = 0.1

    def __init__(self, solver: SolverBridge):
        self.solver = solver

    def classify_decision(self, ev_loss: float) -> DecisionQuality:
        """
        Classify decision quality based on EV loss.

        Args:
            ev_loss: EV loss in big blinds

        Returns:
            DecisionQuality rating
        """
        if ev_loss >= self.BLUNDER_THRESHOLD:
            return DecisionQuality.BLUNDER
        elif ev_loss >= self.MISTAKE_THRESHOLD:
            return DecisionQuality.MISTAKE
        elif ev_loss >= self.INACCURACY_THRESHOLD:
            return DecisionQuality.INACCURACY
        elif ev_loss > 0.01:
            return DecisionQuality.GOOD
        else:
            return DecisionQuality.EXCELLENT

    def evaluate_action(
        self,
        game_state: GameState,
        action_taken: Action,
    ) -> ActionEvaluation:
        """
        Evaluate a single action against GTO.

        Args:
            game_state: State when action was taken
            action_taken: The action that was taken

        Returns:
            ActionEvaluation with comparison to GTO
        """
        hero = game_state.hero
        if hero is None or hero.hand is None:
            raise ValueError("Hero hand required for evaluation")

        # Get GTO strategy and EVs
        strategy = self.solver.get_strategy(game_state, hero.hand)
        optimal_action = strategy.primary_action

        # Calculate EVs
        ev_taken = self.solver.get_ev(game_state, hero.hand, action_taken)
        ev_optimal = self.solver.get_ev(
            game_state,
            hero.hand,
            Action(type=optimal_action),
        )

        ev_loss = max(0, ev_optimal - ev_taken)
        quality = self.classify_decision(ev_loss)

        return ActionEvaluation(
            action_taken=action_taken,
            optimal_action=Action(type=optimal_action),
            ev_taken=ev_taken,
            ev_optimal=ev_optimal,
            ev_loss=ev_loss,
            quality=quality,
        )

    def evaluate_hand(self, parsed_hand: ParsedHand) -> HandEvaluation:
        """
        Evaluate all hero decisions in a hand.

        Args:
            parsed_hand: Parsed hand from history

        Returns:
            HandEvaluation with all action evaluations
        """
        evaluations: list[ActionEvaluation] = []
        total_ev_loss = 0.0

        # Reconstruct game state at each decision point
        # and evaluate hero's action
        # TODO: Implement full hand replay and evaluation

        raise NotImplementedError("Full hand evaluation not yet implemented")

    def evaluate_session(
        self,
        hands: list[ParsedHand],
    ) -> dict[str, HandEvaluation]:
        """
        Evaluate all hands in a session.

        Args:
            hands: List of parsed hands

        Returns:
            Dict mapping hand_id to HandEvaluation
        """
        results = {}
        for hand in hands:
            try:
                results[hand.hand_id] = self.evaluate_hand(hand)
            except Exception as e:
                print(f"Error evaluating hand {hand.hand_id}: {e}")
                continue
        return results

    def calculate_accuracy(self, evaluations: list[HandEvaluation]) -> float:
        """
        Calculate overall accuracy score like chess.com.

        Returns a score from 0-100.
        """
        if not evaluations:
            return 100.0

        total_decisions = sum(len(e.action_evaluations) for e in evaluations)
        if total_decisions == 0:
            return 100.0

        # Weight by decision quality
        weights = {
            DecisionQuality.EXCELLENT: 100,
            DecisionQuality.GOOD: 90,
            DecisionQuality.INACCURACY: 70,
            DecisionQuality.MISTAKE: 40,
            DecisionQuality.BLUNDER: 0,
        }

        total_score = 0
        for evaluation in evaluations:
            for action_eval in evaluation.action_evaluations:
                total_score += weights[action_eval.quality]

        return total_score / total_decisions
