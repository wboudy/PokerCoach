"""WebSocket routes for real-time game state sync."""

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pokercoach.core.game_state import (
    Action,
    Board,
    Card,
    GameState,
    Hand,
    Player,
)

router = APIRouter()


def card_to_dict(card: Card) -> dict[str, str]:
    """Convert Card to JSON-serializable dict."""
    return {
        "rank": card.rank.value,
        "suit": card.suit.value,
    }


def hand_to_dict(hand: Hand) -> dict[str, Any]:
    """Convert Hand to JSON-serializable dict."""
    return {
        "cards": [card_to_dict(c) for c in hand.cards],
        "is_suited": hand.is_suited,
        "is_pair": hand.is_pair,
    }


def board_to_dict(board: Board) -> dict[str, Any]:
    """Convert Board to JSON-serializable dict."""
    return {
        "cards": [card_to_dict(c) for c in board.cards],
        "street": board.street.name if board.cards or len(board.cards) == 0 else "PREFLOP",
    }


def action_to_dict(action: Action) -> dict[str, Any]:
    """Convert Action to JSON-serializable dict."""
    return {
        "type": action.type.value,
        "amount": action.amount,
        "player_position": action.player_position.value if action.player_position else None,
    }


def player_to_dict(player: Player) -> dict[str, Any]:
    """Convert Player to JSON-serializable dict."""
    return {
        "position": player.position.value,
        "stack": player.stack,
        "hand": hand_to_dict(player.hand) if player.hand else None,
        "is_hero": player.is_hero,
    }


def game_state_to_dict(state: GameState) -> dict[str, Any]:
    """
    Convert GameState to JSON-serializable dict.

    This is used for WebSocket transmission to the coaching UI.
    """
    return {
        "game_type": state.game_type,
        "stakes": list(state.stakes),
        "players": [player_to_dict(p) for p in state.players],
        "hero_position": state.hero_position.value if state.hero_position else None,
        "board": board_to_dict(state.board),
        "pot": state.pot,
        "actions": [action_to_dict(a) for a in state.actions],
        "effective_stack": state.effective_stack,
        "street": state.street.name,
    }


class GameStateManager:
    """
    Manages WebSocket connections for real-time game state sync.

    Provides pub/sub functionality for game state updates from the
    vision module to connected coaching UI clients.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._current_state: GameState | None = None
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
            # Send current state if available
            if self._current_state is not None:
                await self._send_state(websocket, self._current_state)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast_state(self, state: GameState) -> None:
        """
        Broadcast game state update to all connected clients.

        Target latency: <500ms from vision capture to UI display.
        """
        start_time = time.monotonic()
        async with self._lock:
            self._current_state = state
            disconnected: list[WebSocket] = []

            for websocket in self._connections:
                try:
                    await self._send_state(websocket, state)
                except Exception:
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for ws in disconnected:
                self._connections.remove(ws)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        # Log if latency exceeds target (for monitoring)
        if elapsed_ms > 500:
            # In production, use proper logging
            pass

    async def _send_state(self, websocket: WebSocket, state: GameState) -> None:
        """Send game state to a single client."""
        message = {
            "type": "game_state_update",
            "timestamp": time.time(),
            "data": game_state_to_dict(state),
        }
        await websocket.send_json(message)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)

    @property
    def current_state(self) -> GameState | None:
        """Current game state."""
        return self._current_state


# Global game state manager instance
game_state_manager = GameStateManager()


@router.websocket("/ws/game-state")
async def game_state_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time game state updates.

    Clients connect to receive live game state updates from the vision module.
    Updates are pushed whenever the game state changes (new cards, actions, pot changes).

    Message format:
        {
            "type": "game_state_update",
            "timestamp": 1234567890.123,
            "data": {
                "game_type": "NLHE",
                "stakes": [1.0, 2.0],
                "board": {"cards": [...], "street": "FLOP"},
                "pot": 100.0,
                ...
            }
        }
    """
    await game_state_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Handle client commands if needed (e.g., ping/pong)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await game_state_manager.disconnect(websocket)


async def push_game_state(state: GameState) -> None:
    """
    Push a game state update to all connected clients.

    This function is called by the vision module when game state changes.

    Args:
        state: The new game state to broadcast
    """
    await game_state_manager.broadcast_state(state)
