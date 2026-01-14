"""Integration tests for WebSocket game state sync."""

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from pokercoach.core.game_state import (
    Action,
    ActionType,
    Board,
    Card,
    GameState,
    Hand,
    Player,
    Position,
    Rank,
    Suit,
)
from pokercoach.web.app import app
from pokercoach.web.routes.game_state import (
    game_state_manager,
    game_state_to_dict,
    push_game_state,
)


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_game_state_manager():
    """Reset game state manager before each test."""
    game_state_manager._current_state = None
    game_state_manager._connections = []
    yield
    game_state_manager._current_state = None
    game_state_manager._connections = []


@pytest.fixture
def sample_game_state() -> GameState:
    """Create a sample game state for testing."""
    hero_hand = Hand(
        cards=(
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.SPADES),
        )
    )

    hero = Player(
        position=Position.BTN,
        stack=100.0,
        hand=hero_hand,
        is_hero=True,
    )

    villain = Player(
        position=Position.BB,
        stack=95.0,
        hand=None,
        is_hero=False,
    )

    board = Board()
    board.add_card(Card(rank=Rank.QUEEN, suit=Suit.SPADES))
    board.add_card(Card(rank=Rank.JACK, suit=Suit.HEARTS))
    board.add_card(Card(rank=Rank.TWO, suit=Suit.HEARTS))

    return GameState(
        game_type="NLHE",
        stakes=(1.0, 2.0),
        players=[hero, villain],
        hero_position=Position.BTN,
        board=board,
        pot=15.0,
        actions=[
            Action(type=ActionType.RAISE, amount=6.0, player_position=Position.BTN),
            Action(type=ActionType.CALL, amount=4.0, player_position=Position.BB),
        ],
        effective_stack=95.0,
    )


class TestGameStateSerialization:
    """Test game state serialization for WebSocket transmission."""

    def test_game_state_to_dict(self, sample_game_state: GameState):
        """Test converting GameState to dict."""
        result = game_state_to_dict(sample_game_state)

        assert result["game_type"] == "NLHE"
        assert result["stakes"] == [1.0, 2.0]
        assert result["pot"] == 15.0
        assert result["effective_stack"] == 95.0
        assert result["street"] == "FLOP"
        assert result["hero_position"] == "BTN"

    def test_board_serialization(self, sample_game_state: GameState):
        """Test board cards are properly serialized."""
        result = game_state_to_dict(sample_game_state)

        board = result["board"]
        assert len(board["cards"]) == 3
        assert board["cards"][0]["rank"] == "Q"
        assert board["cards"][0]["suit"] == "s"
        assert board["street"] == "FLOP"

    def test_player_serialization(self, sample_game_state: GameState):
        """Test players are properly serialized."""
        result = game_state_to_dict(sample_game_state)

        players = result["players"]
        assert len(players) == 2

        # Hero
        hero = players[0]
        assert hero["position"] == "BTN"
        assert hero["stack"] == 100.0
        assert hero["is_hero"] is True
        assert hero["hand"] is not None
        assert hero["hand"]["cards"][0]["rank"] == "A"
        assert hero["hand"]["cards"][0]["suit"] == "s"

        # Villain
        villain = players[1]
        assert villain["position"] == "BB"
        assert villain["is_hero"] is False
        assert villain["hand"] is None

    def test_action_serialization(self, sample_game_state: GameState):
        """Test actions are properly serialized."""
        result = game_state_to_dict(sample_game_state)

        actions = result["actions"]
        assert len(actions) == 2
        assert actions[0]["type"] == "raise"
        assert actions[0]["amount"] == 6.0
        assert actions[0]["player_position"] == "BTN"

    def test_json_serializable(self, sample_game_state: GameState):
        """Test that the dict is fully JSON serializable."""
        result = game_state_to_dict(sample_game_state)
        # Should not raise
        json_str = json.dumps(result)
        # And should round-trip
        parsed = json.loads(json_str)
        assert parsed["pot"] == 15.0


class TestWebSocketConnection:
    """Test WebSocket connection handling."""

    def test_websocket_connect(self, client: TestClient):
        """Test WebSocket connection establishment."""
        with client.websocket_connect("/api/ws/game-state") as websocket:
            # Connection should be established
            assert websocket is not None

    def test_websocket_ping_pong(self, client: TestClient):
        """Test ping/pong messages."""
        with client.websocket_connect("/api/ws/game-state") as websocket:
            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response


class TestGameStateSync:
    """Test game state synchronization via WebSocket."""

    def test_game_state_sync(self, client: TestClient, sample_game_state: GameState):
        """
        Test that game state updates are received via WebSocket.

        This is the main acceptance test for the bead.
        """
        with client.websocket_connect("/api/ws/game-state") as websocket:
            # Broadcast a game state update
            run_async(push_game_state(sample_game_state))

            # Receive the update
            response = websocket.receive_json()

            # Verify message structure
            assert response["type"] == "game_state_update"
            assert "timestamp" in response
            assert "data" in response

            # Verify game state data
            data = response["data"]
            assert data["game_type"] == "NLHE"
            assert data["pot"] == 15.0
            assert data["street"] == "FLOP"
            assert len(data["board"]["cards"]) == 3

    def test_multiple_state_updates(self, client: TestClient, sample_game_state: GameState):
        """Test multiple sequential game state updates."""
        with client.websocket_connect("/api/ws/game-state") as websocket:
            # Send first update
            run_async(push_game_state(sample_game_state))
            response1 = websocket.receive_json()
            assert response1["data"]["pot"] == 15.0

            # Modify state and send second update
            sample_game_state.pot = 30.0
            sample_game_state.board.add_card(Card(rank=Rank.SEVEN, suit=Suit.CLUBS))

            run_async(push_game_state(sample_game_state))
            response2 = websocket.receive_json()

            assert response2["data"]["pot"] == 30.0
            assert response2["data"]["street"] == "TURN"
            assert len(response2["data"]["board"]["cards"]) == 4

    def test_latency_target(self, client: TestClient, sample_game_state: GameState):
        """Test that game state sync meets <500ms latency target."""
        with client.websocket_connect("/api/ws/game-state") as websocket:
            start_time = time.monotonic()

            run_async(push_game_state(sample_game_state))
            response = websocket.receive_json()

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Verify latency is under 500ms
            assert elapsed_ms < 500, f"Latency {elapsed_ms:.1f}ms exceeds 500ms target"
            assert response["type"] == "game_state_update"


class TestGameStateManager:
    """Test GameStateManager functionality."""

    def test_connection_count(self, client: TestClient):
        """Test connection counting."""
        initial_count = game_state_manager.connection_count

        with client.websocket_connect("/api/ws/game-state"):
            assert game_state_manager.connection_count == initial_count + 1

        # After disconnect
        # Note: TestClient may not immediately reflect disconnect in sync tests

    def test_current_state_tracking(self, sample_game_state: GameState):
        """Test that current state is tracked."""
        run_async(game_state_manager.broadcast_state(sample_game_state))

        assert game_state_manager.current_state is not None
        assert game_state_manager.current_state.pot == sample_game_state.pot

    def test_new_connection_receives_current_state(
        self, client: TestClient, sample_game_state: GameState
    ):
        """Test that new connections receive current state immediately."""
        # First, set a current state
        run_async(game_state_manager.broadcast_state(sample_game_state))

        # New connection should receive current state
        with client.websocket_connect("/api/ws/game-state") as websocket:
            response = websocket.receive_json()
            assert response["type"] == "game_state_update"
            assert response["data"]["pot"] == sample_game_state.pot
