"""Tests for HandRepository class."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pokercoach.storage.hand_repository import HandRepository
from pokercoach.storage.models import (
    ActionRecord,
    ActionType,
    Base,
    HandRecord,
    PlayerRecord,
    Position,
    SessionRecord,
    Street,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database and session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    """Create a HandRepository instance."""
    return HandRepository(db_session)


@pytest.fixture
def sample_session(db_session):
    """Create a sample session record."""
    session_record = SessionRecord(
        session_id="session-001",
        site="PokerStars",
        game_type="NLHE",
        stakes="1/2",
    )
    db_session.add(session_record)
    db_session.commit()
    return session_record


@pytest.fixture
def sample_player(db_session):
    """Create a sample player record."""
    player = PlayerRecord(
        player_id="hero123",
        site="PokerStars",
    )
    db_session.add(player)
    db_session.commit()
    return player


@pytest.fixture
def sample_hand(sample_session, sample_player):
    """Create a sample hand record (not yet saved)."""
    return HandRecord(
        hand_id="hand-001",
        session_id=sample_session.id,
        player_id=sample_player.id,
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        hero_card1="As",
        hero_card2="Kd",
        hero_hand="AsKd",
        position=Position.BTN,
        table_size=6,
    )


class TestHandRepositorySaveHand:
    """Tests for save_hand() method."""

    def test_save_new_hand(self, repository, sample_hand):
        """Test saving a new hand record."""
        saved = repository.save_hand(sample_hand)

        assert saved.id is not None
        assert saved.hand_id == "hand-001"
        assert saved.hero_card1 == "As"
        assert saved.hero_card2 == "Kd"

    def test_save_hand_returns_with_id(self, repository, sample_hand):
        """Test that saved hand has a database ID."""
        saved = repository.save_hand(sample_hand)

        assert saved.id is not None
        assert isinstance(saved.id, int)

    def test_update_existing_hand(self, repository, sample_hand):
        """Test updating an existing hand."""
        # Save initial hand
        saved = repository.save_hand(sample_hand)
        original_id = saved.id

        # Create a new hand with same hand_id but different data
        updated_hand = HandRecord(
            hand_id="hand-001",
            hero_card1="Qs",
            hero_card2="Qd",
            hero_hand="QsQd",
            position=Position.CO,
        )

        # Save should update, not create new
        result = repository.save_hand(updated_hand)

        assert result.id == original_id
        assert result.hero_card1 == "Qs"
        assert result.hero_card2 == "Qd"
        assert result.position == Position.CO

    def test_save_multiple_hands(self, repository, sample_session, sample_player):
        """Test saving multiple distinct hands."""
        hands = []
        for i in range(3):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
                timestamp=datetime(2024, 1, 15, 10, i, 0),
            )
            hands.append(repository.save_hand(hand))

        assert len(hands) == 3
        assert all(h.id is not None for h in hands)
        assert len(set(h.id for h in hands)) == 3  # All unique IDs


class TestHandRepositoryGetHandById:
    """Tests for get_hand_by_id() method."""

    def test_get_existing_hand(self, repository, sample_hand):
        """Test retrieving an existing hand by ID."""
        repository.save_hand(sample_hand)

        found = repository.get_hand_by_id("hand-001")

        assert found is not None
        assert found.hand_id == "hand-001"
        assert found.hero_card1 == "As"

    def test_get_nonexistent_hand(self, repository):
        """Test retrieving a hand that doesn't exist."""
        found = repository.get_hand_by_id("nonexistent")

        assert found is None


class TestHandRepositoryGetHandsBySession:
    """Tests for get_hands_by_session() method."""

    def test_get_hands_by_session_string_id(
        self, repository, sample_session, sample_player
    ):
        """Test getting hands by session string ID."""
        # Create multiple hands in the session
        for i in range(5):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
                timestamp=datetime(2024, 1, 15, 10, i, 0),
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_session("session-001")

        assert len(hands) == 5

    def test_get_hands_by_session_int_id(
        self, repository, sample_session, sample_player
    ):
        """Test getting hands by session database ID."""
        for i in range(3):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_session(sample_session.id)

        assert len(hands) == 3

    def test_get_hands_by_session_with_limit(
        self, repository, sample_session, sample_player
    ):
        """Test limiting the number of returned hands."""
        for i in range(10):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_session("session-001", limit=3)

        assert len(hands) == 3

    def test_get_hands_by_nonexistent_session(self, repository):
        """Test getting hands from a session that doesn't exist."""
        hands = repository.get_hands_by_session("nonexistent")

        assert hands == []

    def test_get_hands_by_session_ordered_by_timestamp(
        self, repository, sample_session, sample_player
    ):
        """Test that hands are ordered by timestamp."""
        # Create hands out of order
        times = [
            datetime(2024, 1, 15, 12, 0, 0),
            datetime(2024, 1, 15, 10, 0, 0),
            datetime(2024, 1, 15, 11, 0, 0),
        ]
        for i, ts in enumerate(times):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
                timestamp=ts,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_session("session-001")

        # Should be ordered by timestamp ascending
        assert hands[0].timestamp < hands[1].timestamp < hands[2].timestamp


class TestHandRepositoryGetHandsByPlayer:
    """Tests for get_hands_by_player() method."""

    def test_get_hands_by_player_string_id(
        self, repository, sample_session, sample_player
    ):
        """Test getting hands by player string ID."""
        for i in range(5):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_player("hero123")

        assert len(hands) == 5

    def test_get_hands_by_player_int_id(
        self, repository, sample_session, sample_player
    ):
        """Test getting hands by player database ID."""
        for i in range(3):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_player(sample_player.id)

        assert len(hands) == 3

    def test_get_hands_by_player_with_limit(
        self, repository, sample_session, sample_player
    ):
        """Test limiting the number of returned hands."""
        for i in range(10):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_player("hero123", limit=4)

        assert len(hands) == 4

    def test_get_hands_by_nonexistent_player(self, repository):
        """Test getting hands for a player that doesn't exist."""
        hands = repository.get_hands_by_player("nonexistent")

        assert hands == []

    def test_get_hands_by_player_only_their_hands(
        self, repository, db_session, sample_session
    ):
        """Test that only the specified player's hands are returned."""
        # Create two players
        player1 = PlayerRecord(player_id="player1", site="PokerStars")
        player2 = PlayerRecord(player_id="player2", site="PokerStars")
        db_session.add_all([player1, player2])
        db_session.commit()

        # Create hands for each player
        for i in range(3):
            hand = HandRecord(
                hand_id=f"p1-hand-{i}",
                session_id=sample_session.id,
                player_id=player1.id,
            )
            repository.save_hand(hand)

        for i in range(5):
            hand = HandRecord(
                hand_id=f"p2-hand-{i}",
                session_id=sample_session.id,
                player_id=player2.id,
            )
            repository.save_hand(hand)

        # Should only return player1's hands
        hands = repository.get_hands_by_player("player1")

        assert len(hands) == 3
        assert all(h.player_id == player1.id for h in hands)


class TestHandRepositoryGetHandsBySpot:
    """Tests for get_hands_by_spot() method."""

    def test_get_hands_by_position(
        self, repository, sample_session, sample_player
    ):
        """Test filtering hands by position."""
        positions = [Position.BTN, Position.BTN, Position.CO, Position.SB]
        for i, pos in enumerate(positions):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
                position=pos,
            )
            repository.save_hand(hand)

        btn_hands = repository.get_hands_by_spot(position=Position.BTN)

        assert len(btn_hands) == 2
        assert all(h.position == Position.BTN for h in btn_hands)

    def test_get_hands_by_position_string(
        self, repository, sample_session, sample_player
    ):
        """Test filtering hands by position using string."""
        hand = HandRecord(
            hand_id="hand-001",
            session_id=sample_session.id,
            player_id=sample_player.id,
            position=Position.CO,
        )
        repository.save_hand(hand)

        co_hands = repository.get_hands_by_spot(position="CO")

        assert len(co_hands) == 1
        assert co_hands[0].position == Position.CO

    def test_get_hands_by_street(
        self, repository, db_session, sample_session, sample_player
    ):
        """Test filtering hands by street."""
        # Create hands with actions on different streets
        hand1 = HandRecord(
            hand_id="hand-001",
            session_id=sample_session.id,
            player_id=sample_player.id,
        )
        repository.save_hand(hand1)

        # Add preflop action to hand1
        action1 = ActionRecord(
            hand_id=hand1.id,
            sequence=1,
            street=Street.PREFLOP,
            action_type=ActionType.RAISE,
        )
        db_session.add(action1)

        hand2 = HandRecord(
            hand_id="hand-002",
            session_id=sample_session.id,
            player_id=sample_player.id,
        )
        repository.save_hand(hand2)

        # Add flop action to hand2
        action2 = ActionRecord(
            hand_id=hand2.id,
            sequence=1,
            street=Street.FLOP,
            action_type=ActionType.BET,
        )
        db_session.add(action2)
        db_session.commit()

        flop_hands = repository.get_hands_by_spot(street=Street.FLOP)

        assert len(flop_hands) == 1
        assert flop_hands[0].hand_id == "hand-002"

    def test_get_hands_by_position_and_street(
        self, repository, db_session, sample_session, sample_player
    ):
        """Test filtering by both position and street."""
        hand = HandRecord(
            hand_id="hand-001",
            session_id=sample_session.id,
            player_id=sample_player.id,
            position=Position.BTN,
        )
        repository.save_hand(hand)

        action = ActionRecord(
            hand_id=hand.id,
            sequence=1,
            street=Street.FLOP,
            action_type=ActionType.BET,
        )
        db_session.add(action)
        db_session.commit()

        # Filter by both position and street
        hands = repository.get_hands_by_spot(
            position=Position.BTN,
            street=Street.FLOP,
        )

        assert len(hands) == 1
        assert hands[0].hand_id == "hand-001"

    def test_get_hands_by_spot_with_player_filter(
        self, repository, db_session, sample_session
    ):
        """Test filtering by spot and player."""
        player1 = PlayerRecord(player_id="player1", site="PokerStars")
        player2 = PlayerRecord(player_id="player2", site="PokerStars")
        db_session.add_all([player1, player2])
        db_session.commit()

        # Create hands for both players at BTN
        for pid, player in [(player1.id, "player1"), (player2.id, "player2")]:
            for i in range(2):
                hand = HandRecord(
                    hand_id=f"{player}-btn-{i}",
                    session_id=sample_session.id,
                    player_id=pid,
                    position=Position.BTN,
                )
                repository.save_hand(hand)

        hands = repository.get_hands_by_spot(
            position=Position.BTN,
            player_id="player1",
        )

        assert len(hands) == 2
        assert all(h.player_id == player1.id for h in hands)

    def test_get_hands_by_spot_with_limit(
        self, repository, sample_session, sample_player
    ):
        """Test limiting results when filtering by spot."""
        for i in range(10):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
                position=Position.BTN,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_spot(position=Position.BTN, limit=3)

        assert len(hands) == 3

    def test_get_hands_by_spot_no_filters(
        self, repository, sample_session, sample_player
    ):
        """Test getting all hands when no filters specified."""
        for i in range(3):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        hands = repository.get_hands_by_spot()

        assert len(hands) == 3


class TestHandRepositoryDeleteHand:
    """Tests for delete_hand() method."""

    def test_delete_existing_hand(self, repository, sample_hand):
        """Test deleting an existing hand."""
        repository.save_hand(sample_hand)

        result = repository.delete_hand("hand-001")

        assert result is True
        assert repository.get_hand_by_id("hand-001") is None

    def test_delete_nonexistent_hand(self, repository):
        """Test deleting a hand that doesn't exist."""
        result = repository.delete_hand("nonexistent")

        assert result is False

    def test_delete_hand_removes_actions(
        self, repository, db_session, sample_hand
    ):
        """Test that deleting a hand also removes its actions."""
        saved = repository.save_hand(sample_hand)

        # Add actions to the hand
        action = ActionRecord(
            hand_id=saved.id,
            sequence=1,
            street=Street.PREFLOP,
            action_type=ActionType.RAISE,
        )
        db_session.add(action)
        db_session.commit()

        # Delete the hand
        repository.delete_hand("hand-001")

        # Verify actions are also deleted
        remaining_actions = (
            db_session.query(ActionRecord)
            .filter_by(hand_id=saved.id)
            .count()
        )
        assert remaining_actions == 0


class TestHandRepositoryCountHands:
    """Tests for count_hands() method."""

    def test_count_all_hands(self, repository, sample_session, sample_player):
        """Test counting all hands."""
        for i in range(5):
            hand = HandRecord(
                hand_id=f"hand-{i:03d}",
                session_id=sample_session.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        count = repository.count_hands()

        assert count == 5

    def test_count_hands_by_session(
        self, repository, db_session, sample_player
    ):
        """Test counting hands by session."""
        session1 = SessionRecord(session_id="session-1", game_type="NLHE")
        session2 = SessionRecord(session_id="session-2", game_type="NLHE")
        db_session.add_all([session1, session2])
        db_session.commit()

        for i in range(3):
            hand = HandRecord(
                hand_id=f"s1-hand-{i}",
                session_id=session1.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        for i in range(7):
            hand = HandRecord(
                hand_id=f"s2-hand-{i}",
                session_id=session2.id,
                player_id=sample_player.id,
            )
            repository.save_hand(hand)

        count1 = repository.count_hands(session_id="session-1")
        count2 = repository.count_hands(session_id="session-2")

        assert count1 == 3
        assert count2 == 7

    def test_count_hands_by_player(
        self, repository, db_session, sample_session
    ):
        """Test counting hands by player."""
        player1 = PlayerRecord(player_id="player1", site="PokerStars")
        player2 = PlayerRecord(player_id="player2", site="PokerStars")
        db_session.add_all([player1, player2])
        db_session.commit()

        for i in range(4):
            hand = HandRecord(
                hand_id=f"p1-hand-{i}",
                session_id=sample_session.id,
                player_id=player1.id,
            )
            repository.save_hand(hand)

        for i in range(2):
            hand = HandRecord(
                hand_id=f"p2-hand-{i}",
                session_id=sample_session.id,
                player_id=player2.id,
            )
            repository.save_hand(hand)

        count1 = repository.count_hands(player_id="player1")
        count2 = repository.count_hands(player_id="player2")

        assert count1 == 4
        assert count2 == 2

    def test_count_hands_nonexistent_session(self, repository):
        """Test counting hands for a nonexistent session."""
        count = repository.count_hands(session_id="nonexistent")

        assert count == 0

    def test_count_hands_nonexistent_player(self, repository):
        """Test counting hands for a nonexistent player."""
        count = repository.count_hands(player_id="nonexistent")

        assert count == 0
