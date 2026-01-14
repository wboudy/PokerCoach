"""Database models for poker hand storage and analysis."""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Position(str, Enum):
    """Poker table positions."""

    BTN = "BTN"
    SB = "SB"
    BB = "BB"
    UTG = "UTG"
    UTG1 = "UTG1"
    UTG2 = "UTG2"
    MP = "MP"
    MP1 = "MP1"
    MP2 = "MP2"
    HJ = "HJ"
    CO = "CO"


class Street(str, Enum):
    """Betting streets in poker."""

    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(str, Enum):
    """Types of player actions."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
    POST_SB = "post_sb"
    POST_BB = "post_bb"
    POST_ANTE = "post_ante"


class HandType(str, Enum):
    """Hand strength categories for querying."""

    HIGH_CARD = "high_card"
    PAIR = "pair"
    TWO_PAIR = "two_pair"
    THREE_OF_KIND = "three_of_kind"
    STRAIGHT = "straight"
    FLUSH = "flush"
    FULL_HOUSE = "full_house"
    FOUR_OF_KIND = "four_of_kind"
    STRAIGHT_FLUSH = "straight_flush"
    ROYAL_FLUSH = "royal_flush"


class PlayerRecord(Base):
    """Tracked player record."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    player_id = Column(String(255), unique=True, nullable=False, index=True)
    site = Column(String(100))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

    # Stats (cached for quick access)
    hands_played = Column(Integer, default=0)
    vpip = Column(Float, default=0)
    pfr = Column(Float, default=0)
    three_bet = Column(Float, default=0)
    fold_to_3bet = Column(Float, default=0)
    cbet_flop = Column(Float, default=0)
    aggression_factor = Column(Float, default=0)

    # Classification
    player_type = Column(String(50))

    # Relationships
    hands = relationship("HandRecord", back_populates="player")
    actions = relationship("ActionRecord", back_populates="player")


class SessionRecord(Base):
    """Analysis session record."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    site = Column(String(100))
    game_type = Column(String(50))
    stakes = Column(String(50))

    # Stats
    hands_played = Column(Integer, default=0)
    accuracy_score = Column(Float)
    total_ev_loss = Column(Float)
    blunders = Column(Integer, default=0)
    mistakes = Column(Integer, default=0)
    inaccuracies = Column(Integer, default=0)

    # Relationships
    hands = relationship("HandRecord", back_populates="session")


class HandRecord(Base):
    """Individual hand record with full board and hero holding information."""

    __tablename__ = "hands"

    id = Column(Integer, primary_key=True)
    hand_id = Column(String(255), unique=True, nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    timestamp = Column(DateTime)

    # Hero holdings (stored as 4-char string, e.g., "AsKd")
    hero_card1 = Column(String(2))
    hero_card2 = Column(String(2))
    hero_hand = Column(String(10))  # Legacy field for compatibility

    # Board cards (stored individually for querying)
    flop_card1 = Column(String(2))
    flop_card2 = Column(String(2))
    flop_card3 = Column(String(2))
    turn_card = Column(String(2))
    river_card = Column(String(2))
    board = Column(String(50))  # Legacy field: full board as string

    # Position and table info
    position = Column(SQLEnum(Position))
    table_size = Column(Integer)  # 2-10 players
    button_seat = Column(Integer)
    hero_seat = Column(Integer)

    # Hand categorization for efficient querying
    hand_type = Column(SQLEnum(HandType))
    is_suited = Column(Integer, default=0)  # 0 or 1
    is_pocket_pair = Column(Integer, default=0)  # 0 or 1
    is_broadway = Column(Integer, default=0)  # 0 or 1
    is_connected = Column(Integer, default=0)  # 0 or 1

    # Betting summary
    went_to_showdown = Column(Integer, default=0)
    pot_won = Column(Float)
    final_pot = Column(Float)
    hero_invested = Column(Float)
    hero_won = Column(Float)

    # Analysis
    accuracy_score = Column(Float)
    total_ev_loss = Column(Float)
    has_blunder = Column(Integer, default=0)

    # Raw data (JSON)
    raw_data = Column(Text)
    analysis_data = Column(Text)

    # Relationships
    session = relationship("SessionRecord", back_populates="hands")
    player = relationship("PlayerRecord", back_populates="hands")
    actions = relationship(
        "ActionRecord", back_populates="hand", order_by="ActionRecord.sequence"
    )

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("ix_hands_player_position", "player_id", "position"),
        Index("ix_hands_player_hand_type", "player_id", "hand_type"),
        Index("ix_hands_position_hand_type", "position", "hand_type"),
        Index("ix_hands_session_timestamp", "session_id", "timestamp"),
    )


class ActionRecord(Base):
    """Individual betting action within a hand.

    Stores the complete action history for a hand, allowing replay
    and detailed analysis of betting patterns.
    """

    __tablename__ = "actions"

    id = Column(Integer, primary_key=True)
    hand_id = Column(Integer, ForeignKey("hands.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"))

    # Action sequence
    sequence = Column(Integer, nullable=False)  # Order within the hand
    street = Column(SQLEnum(Street), nullable=False)
    street_sequence = Column(Integer)  # Order within the street

    # Action details
    action_type = Column(SQLEnum(ActionType), nullable=False)
    amount = Column(Float)  # Bet/raise amount (null for fold/check)
    total_bet = Column(Float)  # Total committed this street
    pot_before = Column(Float)  # Pot size before action
    pot_after = Column(Float)  # Pot size after action
    stack_before = Column(Float)  # Player stack before action
    stack_after = Column(Float)  # Player stack after action

    # Position context
    position = Column(SQLEnum(Position))
    is_hero = Column(Integer, default=0)  # 0 or 1

    # Analysis (for hero actions)
    ev_loss = Column(Float)
    optimal_action = Column(String(50))
    is_blunder = Column(Integer, default=0)
    is_mistake = Column(Integer, default=0)
    is_inaccuracy = Column(Integer, default=0)

    # Relationships
    hand = relationship("HandRecord", back_populates="actions")
    player = relationship("PlayerRecord", back_populates="actions")

    # Indexes for querying action patterns
    __table_args__ = (
        Index("ix_actions_hand_sequence", "hand_id", "sequence"),
        Index("ix_actions_player_street", "player_id", "street"),
        Index("ix_actions_player_action", "player_id", "action_type"),
        Index("ix_actions_street_action", "street", "action_type"),
    )
