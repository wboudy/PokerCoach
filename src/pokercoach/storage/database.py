"""Database access layer."""

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pokercoach.storage.models import Base, HandRecord, PlayerRecord, SessionRecord


class Database:
    """Database manager for PokerCoach."""

    def __init__(self, db_path: Path | None = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database. If None, uses in-memory database.
        """
        if db_path:
            self.engine = create_engine(f"sqlite:///{db_path}")
        else:
            self.engine = create_engine("sqlite:///:memory:")

        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self._session_factory()

    def add_player(self, player_id: str, site: str = "") -> PlayerRecord:
        """Add or get existing player."""
        with self.get_session() as session:
            player = (
                session.query(PlayerRecord)
                .filter_by(player_id=player_id)
                .first()
            )
            if not player:
                player = PlayerRecord(player_id=player_id, site=site)
                session.add(player)
                session.commit()
                session.refresh(player)
            return player

    def get_player(self, player_id: str) -> PlayerRecord | None:
        """Get player by ID."""
        with self.get_session() as session:
            return (
                session.query(PlayerRecord)
                .filter_by(player_id=player_id)
                .first()
            )

    def update_player_stats(
        self,
        player_id: str,
        stats: dict[str, Any],
    ) -> PlayerRecord | None:
        """Update player statistics."""
        with self.get_session() as session:
            player = (
                session.query(PlayerRecord)
                .filter_by(player_id=player_id)
                .first()
            )
            if player:
                for key, value in stats.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                session.commit()
                session.refresh(player)
            return player

    def add_session(
        self,
        session_id: str,
        site: str = "",
        game_type: str = "NLHE",
        stakes: str = "",
    ) -> SessionRecord:
        """Add a new analysis session."""
        with self.get_session() as db_session:
            record = SessionRecord(
                session_id=session_id,
                site=site,
                game_type=game_type,
                stakes=stakes,
            )
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)
            return record

    def add_hand(
        self,
        hand_id: str,
        session_record: SessionRecord,
        hero_hand: str = "",
        board: str = "",
        position: str = "",
    ) -> HandRecord:
        """Add a hand record."""
        with self.get_session() as db_session:
            record = HandRecord(
                hand_id=hand_id,
                session_id=session_record.id,
                hero_hand=hero_hand,
                board=board,
                position=position,
            )
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)
            return record

    def get_recent_sessions(self, limit: int = 10) -> list[SessionRecord]:
        """Get most recent analysis sessions."""
        with self.get_session() as session:
            return (
                session.query(SessionRecord)
                .order_by(SessionRecord.timestamp.desc())
                .limit(limit)
                .all()
            )

    def get_player_hands(
        self,
        player_id: str,
        limit: int = 100,
    ) -> list[HandRecord]:
        """Get hands involving a player."""
        with self.get_session() as session:
            player = (
                session.query(PlayerRecord)
                .filter_by(player_id=player_id)
                .first()
            )
            if not player:
                return []
            return (
                session.query(HandRecord)
                .filter_by(player_id=player.id)
                .order_by(HandRecord.timestamp.desc())
                .limit(limit)
                .all()
            )
