"""Repository for hand storage and retrieval operations."""

from typing import cast

from sqlalchemy.orm import Session, joinedload

from pokercoach.storage.models import (
    ActionRecord,
    HandRecord,
    PlayerRecord,
    Position,
    SessionRecord,
    Street,
)


class HandRepository:
    """Repository for storing and retrieving poker hands.

    Provides CRUD operations for HandRecord entities with support
    for querying by session, player, and spot (position + street).
    """

    def __init__(self, session: Session):
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session

    def save_hand(self, hand: HandRecord) -> HandRecord:
        """Save a hand record to the database.

        If the hand already exists (by hand_id), it will be updated.
        Otherwise, a new record is created.

        Args:
            hand: HandRecord to save.

        Returns:
            The saved HandRecord with updated id.
        """
        # Check if hand already exists
        existing = (
            self._session.query(HandRecord)
            .filter_by(hand_id=hand.hand_id)
            .first()
        )

        if existing:
            # Update existing hand
            for attr in [
                'session_id', 'player_id', 'timestamp',
                'hero_card1', 'hero_card2', 'hero_hand',
                'flop_card1', 'flop_card2', 'flop_card3',
                'turn_card', 'river_card', 'board',
                'position', 'table_size', 'button_seat', 'hero_seat',
                'hand_type', 'is_suited', 'is_pocket_pair',
                'is_broadway', 'is_connected',
                'went_to_showdown', 'pot_won', 'final_pot',
                'hero_invested', 'hero_won',
                'accuracy_score', 'total_ev_loss', 'has_blunder',
                'raw_data', 'analysis_data',
            ]:
                value = getattr(hand, attr)
                if value is not None:
                    setattr(existing, attr, value)
            self._session.commit()
            self._session.refresh(existing)
            return existing
        else:
            # Add new hand
            self._session.add(hand)
            self._session.commit()
            self._session.refresh(hand)
            return hand

    def get_hand_by_id(self, hand_id: str) -> HandRecord | None:
        """Get a hand by its unique hand_id.

        Args:
            hand_id: The unique identifier of the hand.

        Returns:
            The HandRecord if found, None otherwise.
        """
        return (
            self._session.query(HandRecord)
            .options(joinedload(HandRecord.actions))
            .filter_by(hand_id=hand_id)
            .first()
        )

    def get_hands_by_session(
        self,
        session_id: str | int,
        limit: int | None = None,
    ) -> list[HandRecord]:
        """Get all hands from a specific session.

        Args:
            session_id: Either the session's string ID or database integer ID.
            limit: Maximum number of hands to return (optional).

        Returns:
            List of HandRecord objects from the session, ordered by timestamp.
        """
        # Handle both string session_id and integer database id
        db_session_id: int
        if isinstance(session_id, str):
            session_record = (
                self._session.query(SessionRecord)
                .filter_by(session_id=session_id)
                .first()
            )
            if not session_record:
                return []
            db_session_id = cast(int, session_record.id)
        else:
            db_session_id = session_id

        query = (
            self._session.query(HandRecord)
            .options(joinedload(HandRecord.actions))
            .filter_by(session_id=db_session_id)
            .order_by(HandRecord.timestamp)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_hands_by_player(
        self,
        player_id: str | int,
        limit: int | None = None,
    ) -> list[HandRecord]:
        """Get hands involving a specific player.

        Args:
            player_id: Either the player's string ID or database integer ID.
            limit: Maximum number of hands to return (optional).

        Returns:
            List of HandRecord objects for the player, ordered by timestamp desc.
        """
        # Handle both string player_id and integer database id
        db_player_id: int
        if isinstance(player_id, str):
            player_record = (
                self._session.query(PlayerRecord)
                .filter_by(player_id=player_id)
                .first()
            )
            if not player_record:
                return []
            db_player_id = cast(int, player_record.id)
        else:
            db_player_id = player_id

        query = (
            self._session.query(HandRecord)
            .options(joinedload(HandRecord.actions))
            .filter_by(player_id=db_player_id)
            .order_by(HandRecord.timestamp.desc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_hands_by_spot(
        self,
        position: Position | str | None = None,
        street: Street | str | None = None,
        player_id: str | int | None = None,
        limit: int | None = None,
    ) -> list[HandRecord]:
        """Get hands matching a specific spot (position and/or street).

        A "spot" in poker refers to a particular situation, typically defined
        by position and the street where action occurs.

        Args:
            position: Filter by hero's position (e.g., Position.BTN, "BTN").
            street: Filter by street where significant action occurred.
                   If provided, only returns hands with actions on that street.
            player_id: Optional filter by player (string ID or database ID).
            limit: Maximum number of hands to return (optional).

        Returns:
            List of HandRecord objects matching the criteria.
        """
        query = self._session.query(HandRecord).options(
            joinedload(HandRecord.actions)
        )

        # Filter by position
        if position is not None:
            if isinstance(position, str):
                position = Position(position)
            query = query.filter(HandRecord.position == position)

        # Filter by player
        if player_id is not None:
            db_player_id: int
            if isinstance(player_id, str):
                player_record = (
                    self._session.query(PlayerRecord)
                    .filter_by(player_id=player_id)
                    .first()
                )
                if not player_record:
                    return []
                db_player_id = cast(int, player_record.id)
            else:
                db_player_id = player_id
            query = query.filter(HandRecord.player_id == db_player_id)

        # Filter by street (hands that have actions on this street)
        if street is not None:
            if isinstance(street, str):
                street = Street(street)
            # Join with actions to find hands with actions on the given street
            query = query.join(HandRecord.actions).filter(
                ActionRecord.street == street
            ).distinct()

        query = query.order_by(HandRecord.timestamp.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def delete_hand(self, hand_id: str) -> bool:
        """Delete a hand by its unique hand_id.

        Args:
            hand_id: The unique identifier of the hand to delete.

        Returns:
            True if the hand was deleted, False if not found.
        """
        hand = (
            self._session.query(HandRecord)
            .filter_by(hand_id=hand_id)
            .first()
        )
        if hand:
            # Delete associated actions first
            self._session.query(ActionRecord).filter_by(hand_id=hand.id).delete()
            self._session.delete(hand)
            self._session.commit()
            return True
        return False

    def count_hands(
        self,
        session_id: str | int | None = None,
        player_id: str | int | None = None,
    ) -> int:
        """Count hands matching the given criteria.

        Args:
            session_id: Optional filter by session.
            player_id: Optional filter by player.

        Returns:
            The count of matching hands.
        """
        query = self._session.query(HandRecord)

        if session_id is not None:
            db_session_id: int
            if isinstance(session_id, str):
                session_record = (
                    self._session.query(SessionRecord)
                    .filter_by(session_id=session_id)
                    .first()
                )
                if not session_record:
                    return 0
                db_session_id = cast(int, session_record.id)
            else:
                db_session_id = session_id
            query = query.filter(HandRecord.session_id == db_session_id)

        if player_id is not None:
            db_player_id: int
            if isinstance(player_id, str):
                player_record = (
                    self._session.query(PlayerRecord)
                    .filter_by(player_id=player_id)
                    .first()
                )
                if not player_record:
                    return 0
                db_player_id = cast(int, player_record.id)
            else:
                db_player_id = player_id
            query = query.filter(HandRecord.player_id == db_player_id)

        return query.count()
