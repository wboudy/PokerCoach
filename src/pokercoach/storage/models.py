"""Database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


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
    """Individual hand record."""

    __tablename__ = "hands"

    id = Column(Integer, primary_key=True)
    hand_id = Column(String(255), unique=True, nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    timestamp = Column(DateTime)

    # Hand data
    hero_hand = Column(String(10))
    board = Column(String(50))
    position = Column(String(10))
    pot_won = Column(Float)

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
