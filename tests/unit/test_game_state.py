"""Tests for core game state models."""

import pytest

from pokercoach.core.game_state import (
    Action,
    ActionType,
    Board,
    Card,
    GameState,
    Hand,
    Position,
    Rank,
    Street,
    Suit,
)


class TestCard:
    """Tests for Card class."""

    def test_card_creation(self):
        card = Card(rank=Rank.ACE, suit=Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES

    def test_card_from_string(self):
        card = Card.from_string("As")
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES

        card = Card.from_string("Td")
        assert card.rank == Rank.TEN
        assert card.suit == Suit.DIAMONDS

    def test_card_str(self):
        card = Card(rank=Rank.KING, suit=Suit.HEARTS)
        assert str(card) == "Kh"

    def test_invalid_card_string(self):
        with pytest.raises(ValueError):
            Card.from_string("invalid")

        with pytest.raises(ValueError):
            Card.from_string("A")


class TestHand:
    """Tests for Hand class."""

    def test_hand_creation(self):
        c1 = Card(rank=Rank.ACE, suit=Suit.SPADES)
        c2 = Card(rank=Rank.KING, suit=Suit.SPADES)
        hand = Hand(cards=(c1, c2))
        assert hand.is_suited
        assert not hand.is_pair

    def test_hand_from_string(self):
        hand = Hand.from_string("AsKs")
        assert hand.cards[0].rank == Rank.ACE
        assert hand.cards[1].rank == Rank.KING
        assert hand.is_suited

    def test_pair_detection(self):
        hand = Hand.from_string("AhAd")
        assert hand.is_pair
        assert not hand.is_suited

    def test_hand_str(self):
        hand = Hand.from_string("QhJh")
        assert str(hand) == "QhJh"


class TestBoard:
    """Tests for Board class."""

    def test_empty_board(self):
        board = Board()
        assert board.street == Street.PREFLOP
        assert len(board.cards) == 0

    def test_flop(self):
        board = Board()
        board.add_card(Card.from_string("As"))
        board.add_card(Card.from_string("Kd"))
        board.add_card(Card.from_string("Qh"))
        assert board.street == Street.FLOP
        assert len(board.cards) == 3

    def test_turn(self):
        board = Board()
        for card in ["As", "Kd", "Qh", "Jc"]:
            board.add_card(Card.from_string(card))
        assert board.street == Street.TURN

    def test_river(self):
        board = Board()
        for card in ["As", "Kd", "Qh", "Jc", "Ts"]:
            board.add_card(Card.from_string(card))
        assert board.street == Street.RIVER

    def test_board_overflow(self):
        board = Board()
        for card in ["As", "Kd", "Qh", "Jc", "Ts"]:
            board.add_card(Card.from_string(card))

        with pytest.raises(ValueError):
            board.add_card(Card.from_string("9h"))


class TestAction:
    """Tests for Action class."""

    def test_fold(self):
        action = Action(type=ActionType.FOLD)
        assert str(action) == "fold"

    def test_bet_with_amount(self):
        action = Action(type=ActionType.BET, amount=10.0)
        assert str(action) == "bet 10.0"

    def test_raise_with_amount(self):
        action = Action(type=ActionType.RAISE, amount=25.5)
        assert str(action) == "raise 25.5"


class TestGameState:
    """Tests for GameState class."""

    def test_default_game_state(self):
        state = GameState()
        assert state.game_type == "NLHE"
        assert state.stakes == (1.0, 2.0)
        assert state.street == Street.PREFLOP

    def test_add_action(self):
        state = GameState()
        state.pot = 3.0  # Blinds

        action = Action(type=ActionType.CALL, amount=2.0)
        state.add_action(action)

        assert len(state.actions) == 1
        assert state.pot == 5.0


class TestToSolverFormat:
    """Tests for GameState.to_solver_format() method."""

    def test_preflop_basic(self):
        """Test preflop state with minimal info."""
        state = GameState()
        state.pot = 3.0  # SB + BB
        state.effective_stack = 100.0

        result = state.to_solver_format()

        assert "set_pot 3" in result
        assert "set_effective_stack 100" in result
        # No board for preflop
        assert "set_board" not in result

    def test_flop_with_board(self):
        """Test flop state includes board cards."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 97.0

        # Add flop cards
        for card_str in ["As", "Kd", "Qh"]:
            state.board.add_card(Card.from_string(card_str))

        result = state.to_solver_format()

        assert "set_pot 10" in result
        assert "set_effective_stack 97" in result
        assert "set_board As,Kd,Qh" in result

    def test_turn_with_board(self):
        """Test turn state includes all 4 board cards."""
        state = GameState()
        state.pot = 25.0
        state.effective_stack = 85.0

        for card_str in ["Qs", "Jh", "2c", "9d"]:
            state.board.add_card(Card.from_string(card_str))

        result = state.to_solver_format()

        assert "set_board Qs,Jh,2c,9d" in result
        assert state.street == Street.TURN

    def test_river_with_board(self):
        """Test river state includes all 5 board cards."""
        state = GameState()
        state.pot = 50.0
        state.effective_stack = 70.0

        for card_str in ["As", "Kd", "Qh", "Jc", "Ts"]:
            state.board.add_card(Card.from_string(card_str))

        result = state.to_solver_format()

        assert "set_board As,Kd,Qh,Jc,Ts" in result
        assert state.street == Street.RIVER

    def test_action_history_included(self):
        """Test that action history is included as comment."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 95.0

        # Add a raise action
        action = Action(
            type=ActionType.RAISE,
            amount=6.0,
            player_position=Position.BTN,
        )
        state.add_action(action)

        result = state.to_solver_format()

        assert "# Action history:" in result
        assert "BTN" in result
        assert "raise" in result

    def test_format_action_history_fold(self):
        """Test fold action formatting."""
        state = GameState()
        state.pot = 3.0

        action = Action(type=ActionType.FOLD, player_position=Position.SB)
        state.add_action(action)

        history = state._format_action_history()

        assert "SB fold" in history

    def test_format_action_history_bet_pot_percent(self):
        """Test bet formatted as pot percentage."""
        state = GameState()
        state.pot = 10.0

        # Add flop so we're postflop
        for card_str in ["As", "Kd", "Qh"]:
            state.board.add_card(Card.from_string(card_str))

        # Bet 50% of pot (5 into 10)
        action = Action(
            type=ActionType.BET,
            amount=5.0,
            player_position=Position.BB,
        )
        state.add_action(action)

        history = state._format_action_history()

        # Should show bet as percentage - pot was 10 (3 blinds + 7 earlier)
        # Running pot starts at 3 (SB + BB = 1 + 2)
        # So 5/3 = 167% pot
        assert "BB bet" in history
        assert "%" in history

    def test_format_action_history_raise_preflop_xbb(self):
        """Test preflop raise formatted as xBB."""
        state = GameState(stakes=(1.0, 2.0))
        state.pot = 3.0  # SB + BB

        # Raise to 6BB (3x)
        action = Action(
            type=ActionType.RAISE,
            amount=6.0,
            player_position=Position.BTN,
        )
        state.add_action(action)

        history = state._format_action_history()

        assert "BTN raise 3.0x" in history

    def test_format_action_history_call(self):
        """Test call action formatting."""
        state = GameState()
        state.pot = 3.0

        action = Action(
            type=ActionType.CALL,
            amount=2.0,
            player_position=Position.SB,
        )
        state.add_action(action)

        history = state._format_action_history()

        assert "SB call" in history

    def test_format_action_history_check(self):
        """Test check action formatting."""
        state = GameState()
        state.pot = 10.0

        action = Action(type=ActionType.CHECK, player_position=Position.BB)
        state.add_action(action)

        history = state._format_action_history()

        assert "BB check" in history

    def test_format_action_history_allin(self):
        """Test all-in action formatting as xBB."""
        state = GameState(stakes=(1.0, 2.0))
        state.pot = 10.0

        action = Action(
            type=ActionType.ALL_IN,
            amount=100.0,
            player_position=Position.BTN,
        )
        state.add_action(action)

        history = state._format_action_history()

        assert "BTN all-in 50.0x" in history  # 100/2 BB

    def test_format_action_history_multiple_actions(self):
        """Test formatting multiple actions."""
        state = GameState(stakes=(1.0, 2.0))
        state.pot = 3.0

        # BTN raises to 6
        state.add_action(
            Action(type=ActionType.RAISE, amount=6.0, player_position=Position.BTN)
        )
        # SB folds
        state.add_action(Action(type=ActionType.FOLD, player_position=Position.SB))
        # BB calls
        state.add_action(
            Action(type=ActionType.CALL, amount=4.0, player_position=Position.BB)
        )

        history = state._format_action_history()

        assert "BTN raise 3.0x" in history
        assert "SB fold" in history
        assert "BB call" in history
        # Should be comma-separated
        assert ", " in history

    def test_format_action_history_empty(self):
        """Test empty action history."""
        state = GameState()

        history = state._format_action_history()

        assert history == ""

    def test_format_action_without_position(self):
        """Test action formatting when position is not set."""
        state = GameState()
        state.pot = 3.0

        # Action without player_position
        action = Action(type=ActionType.FOLD)
        state.add_action(action)

        history = state._format_action_history()

        assert "fold" in history


class TestToSolverConfig:
    """Tests for GameState.to_solver_config() method."""

    def test_basic_config(self):
        """Test basic config generation."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        result = state.to_solver_config()

        assert "set_pot 10" in result
        assert "set_effective_stack 100" in result
        assert "set_thread_num 6" in result
        assert "set_accuracy 0.3" in result
        assert "set_max_iteration 1000" in result
        assert "build_tree" in result
        assert "start_solve" in result

    def test_config_with_ranges(self):
        """Test config includes provided ranges."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        result = state.to_solver_config(
            ip_range="AA,KK,QQ,AKs",
            oop_range="AA,KK,QQ,JJ,TT,AKs,AKo",
        )

        assert "set_range_ip AA,KK,QQ,AKs" in result
        assert "set_range_oop AA,KK,QQ,JJ,TT,AKs,AKo" in result

    def test_config_with_custom_bet_sizes(self):
        """Test config with custom bet sizes."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        result = state.to_solver_config(
            bet_sizes={"flop": [25, 50, 100], "turn": [75], "river": [50, 150]},
        )

        assert "set_bet_sizes oop,flop,bet,25" in result
        assert "set_bet_sizes ip,flop,bet,50" in result
        assert "set_bet_sizes oop,turn,bet,75" in result
        assert "set_bet_sizes ip,river,bet,150" in result

    def test_config_with_board(self):
        """Test config includes board for postflop."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        for card_str in ["As", "Kd", "Qh"]:
            state.board.add_card(Card.from_string(card_str))

        result = state.to_solver_config()

        assert "set_board As,Kd,Qh" in result

    def test_config_custom_solver_params(self):
        """Test config with custom solver parameters."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        result = state.to_solver_config(
            threads=12,
            accuracy=0.1,
            max_iterations=5000,
        )

        assert "set_thread_num 12" in result
        assert "set_accuracy 0.1" in result
        assert "set_max_iteration 5000" in result

    def test_config_includes_raise_sizes(self):
        """Test that config includes raise sizes in addition to bet sizes."""
        state = GameState()
        state.pot = 10.0
        state.effective_stack = 100.0

        result = state.to_solver_config(
            bet_sizes={"flop": [50]},
        )

        assert "set_bet_sizes oop,flop,bet,50" in result
        assert "set_bet_sizes oop,flop,raise,50" in result
        assert "set_bet_sizes ip,flop,bet,50" in result
        assert "set_bet_sizes ip,flop,raise,50" in result
