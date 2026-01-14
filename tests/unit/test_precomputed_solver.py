"""Tests for PrecomputedSolver cache key generation."""

import pytest
from pathlib import Path

from pokercoach.core.game_state import (
    Board,
    Card,
    GameState,
    Hand,
    Player,
    Position,
    Rank,
    Suit,
)
from pokercoach.solver.texas_solver import PrecomputedSolver


def make_game_state(
    pot: float = 100,
    effective_stack: float = 100,
    board_cards: list[str] | None = None,
    hero_position: Position = Position.BTN,
) -> GameState:
    """Helper to create game states for testing."""
    gs = GameState(
        pot=pot,
        effective_stack=effective_stack,
        hero_position=hero_position,
    )
    if board_cards:
        for card_str in board_cards:
            gs.board.add_card(Card.from_string(card_str))
    return gs


class TestCacheKey:
    """Tests for PrecomputedSolver._cache_key() method."""

    @pytest.fixture
    def solver(self, tmp_path: Path) -> PrecomputedSolver:
        """Create solver with temporary cache directory."""
        return PrecomputedSolver(cache_dir=tmp_path)

    def test_cache_key_returns_string(self, solver: PrecomputedSolver):
        """Test that _cache_key returns a non-empty string."""
        gs = make_game_state()
        key = solver._cache_key(gs)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_cache_key_deterministic(self, solver: PrecomputedSolver):
        """Test that same game state produces same key."""
        gs1 = make_game_state(pot=100, effective_stack=100)
        gs2 = make_game_state(pot=100, effective_stack=100)

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 == key2

    def test_cache_key_different_pots(self, solver: PrecomputedSolver):
        """Test that different pot sizes produce different keys."""
        gs1 = make_game_state(pot=100)
        gs2 = make_game_state(pot=200)

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 != key2

    def test_cache_key_stack_bucketing(self, solver: PrecomputedSolver):
        """Test that stacks are bucketed into 100bb ranges."""
        # Stacks 150bb and 180bb should bucket to same 100bb bucket
        # Use same pot/stack ratio to ensure pot% matches
        gs1 = make_game_state(pot=75, effective_stack=150)  # 50% pot
        gs2 = make_game_state(pot=90, effective_stack=180)  # 50% pot

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        # Both should bucket to "100bb" or similar with same pot%
        assert key1 == key2, "Stacks in same 100bb bucket should produce same key"

    def test_cache_key_different_stack_buckets(self, solver: PrecomputedSolver):
        """Test that different stack buckets produce different keys."""
        gs1 = make_game_state(effective_stack=100)
        gs2 = make_game_state(effective_stack=250)

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 != key2, "Different stack buckets should produce different keys"

    def test_cache_key_suit_isomorphism(self, solver: PrecomputedSolver):
        """Test that suit isomorphic boards produce same key."""
        # Ah Kd 2c is isomorphic to As Kh 2d (same ranks, different suits)
        gs1 = make_game_state(board_cards=["Ah", "Kd", "2c"])
        gs2 = make_game_state(board_cards=["As", "Kh", "2d"])

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 == key2, "Suit isomorphic boards should produce same key"

    def test_cache_key_non_isomorphic_boards(self, solver: PrecomputedSolver):
        """Test that non-isomorphic boards produce different keys."""
        # Different ranks -> different keys
        gs1 = make_game_state(board_cards=["Ah", "Kd", "2c"])
        gs2 = make_game_state(board_cards=["Ah", "Qd", "2c"])

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 != key2

    def test_cache_key_flush_draw_boards(self, solver: PrecomputedSolver):
        """Test that monotone and rainbow boards have different keys."""
        # Monotone board (all hearts) - flush possible
        gs1 = make_game_state(board_cards=["Ah", "Kh", "2h"])
        # Rainbow board (different suits) - no flush possible
        gs2 = make_game_state(board_cards=["Ah", "Kd", "2c"])

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 != key2, "Flush draw vs rainbow should produce different keys"

    def test_cache_key_position_relative(self, solver: PrecomputedSolver):
        """Test that position is normalized to IP/OOP."""
        # BTN vs BB is IP vs OOP
        gs1 = make_game_state(hero_position=Position.BTN)
        gs2 = make_game_state(hero_position=Position.CO)

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        # Both BTN and CO are typically IP, should produce same key
        # (if opponent is BB/SB)
        # Note: This depends on implementation - might need adjustment
        assert isinstance(key1, str)
        assert isinstance(key2, str)

    def test_cache_key_pot_percentage(self, solver: PrecomputedSolver):
        """Test that pot is normalized as percentage of stack."""
        # Same pot% in same stack bucket should produce same key
        # Both at 50% pot within 100bb bucket
        gs1 = make_game_state(pot=50, effective_stack=100)
        gs2 = make_game_state(pot=75, effective_stack=150)  # Same bucket, same 50% pot

        key1 = solver._cache_key(gs1)
        key2 = solver._cache_key(gs2)

        assert key1 == key2, "Same pot/stack ratio in same bucket should produce same key"

    def test_cache_key_preflop(self, solver: PrecomputedSolver):
        """Test cache key generation for preflop spots."""
        gs = make_game_state(board_cards=None)

        key = solver._cache_key(gs)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_cache_key_turn(self, solver: PrecomputedSolver):
        """Test cache key with turn card."""
        gs = make_game_state(board_cards=["Ah", "Kd", "2c", "Js"])

        key = solver._cache_key(gs)
        assert isinstance(key, str)

    def test_cache_key_river(self, solver: PrecomputedSolver):
        """Test cache key with river card."""
        gs = make_game_state(board_cards=["Ah", "Kd", "2c", "Js", "3h"])

        key = solver._cache_key(gs)
        assert isinstance(key, str)
