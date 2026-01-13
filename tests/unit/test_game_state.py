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
