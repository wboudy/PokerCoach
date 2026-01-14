"""Coach API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from pokercoach.core.game_state import Card, GameState, Hand
from pokercoach.core.game_state import Position as GamePosition
from pokercoach.llm.coach import PokerCoach

router = APIRouter()


def _get_coach(request: Request) -> PokerCoach:
    """Get the coach instance from app state."""
    if not hasattr(request.app.state, "coach"):
        raise HTTPException(
            status_code=503,
            detail="Coach service not initialized. Check server logs.",
        )
    return request.app.state.coach


def _build_game_state(
    hand: Optional[str] = None,
    board: Optional[str] = None,
    position: Optional[str] = None,
    pot_size: Optional[float] = None,
    to_call: Optional[float] = None,
    effective_stack: Optional[float] = 100.0,
) -> GameState:
    """Build a GameState from query parameters."""
    game_state = GameState(
        pot=pot_size if pot_size is not None and pot_size > 0 else 3.0,
        effective_stack=effective_stack if effective_stack else 100.0,
    )

    # Parse position
    if position:
        try:
            game_state.hero_position = GamePosition(position.upper())
        except (ValueError, KeyError):
            game_state.hero_position = GamePosition.BTN

    # Parse board cards
    if board and board.strip():
        board_cards = board.replace(",", " ").split()
        for card_str in board_cards:
            card_str = card_str.strip()
            if len(card_str) >= 2:
                try:
                    card = Card.from_string(card_str)
                    game_state.board.add_card(card)
                except (ValueError, KeyError):
                    pass  # Skip invalid cards

    return game_state


class CoachQuery(BaseModel):
    """Request model for coach queries."""

    question: str = Field(
        ...,
        description="Natural language poker question",
        example="Should I 3bet AKo from SB vs BTN open?",
    )
    hand: Optional[str] = Field(
        default=None,
        description="Hero's hole cards in standard notation",
        example="AhKs",
    )
    board: Optional[str] = Field(
        default=None,
        description="Community cards (space-separated)",
        example="Qh Jd Tc",
    )
    position: Optional[str] = Field(
        default=None,
        description="Hero's position at the table",
        example="SB",
    )
    pot_size: Optional[float] = Field(
        default=None,
        description="Current pot size in big blinds",
        example=6.5,
    )
    to_call: Optional[float] = Field(
        default=None,
        description="Amount to call in big blinds",
        example=2.5,
    )
    effective_stack: Optional[float] = Field(
        default=100.0,
        description="Effective stack size in big blinds",
        example=100.0,
    )


class CoachResponse(BaseModel):
    """Response model for coach queries."""

    answer: str = Field(
        ...,
        description="Coach's natural language response",
        example="With AKo from SB vs BTN open, you should 3bet to around 10bb.",
    )
    strategy: Optional[dict] = Field(
        default=None,
        description="Recommended action frequencies",
        example={"3bet": 0.85, "call": 0.15, "fold": 0.0},
    )
    ev_comparison: Optional[dict] = Field(
        default=None,
        description="EV comparison of available actions",
        example={"3bet_ev": 1.2, "call_ev": 0.8, "fold_ev": 0.0},
    )


@router.post("/ask", response_model=CoachResponse)
async def ask_coach(query: CoachQuery, request: Request) -> CoachResponse:
    """
    Ask the poker coach a question.

    The coach will use GTO solver tools to provide
    mathematically optimal advice.
    """
    coach = _get_coach(request)

    # Build game state from query parameters
    game_state = _build_game_state(
        hand=query.hand,
        board=query.board,
        position=query.position,
        pot_size=query.pot_size,
        to_call=query.to_call,
        effective_stack=query.effective_stack,
    )

    try:
        # Call the coach with the question and game state
        answer = coach.ask(query.question, game_state)
        return CoachResponse(
            answer=answer,
            strategy=None,
            ev_comparison=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing coach request: {str(e)}",
        )


class GTOQuery(BaseModel):
    """Request for direct GTO query."""

    hand: str = Field(
        ...,
        description="Hero's hole cards in standard notation",
        example="AhKs",
    )
    board: str = Field(
        default="",
        description="Community cards (space-separated)",
        example="Qh Jd Tc",
    )
    position: str = Field(
        ...,
        description="Hero's position at the table",
        example="SB",
    )
    pot_size: float = Field(
        default=0,
        description="Current pot size in big blinds",
        example=6.5,
    )
    to_call: float = Field(
        default=0,
        description="Amount to call in big blinds",
        example=2.5,
    )
    effective_stack: float = Field(
        default=100,
        description="Effective stack size in big blinds",
        example=100.0,
    )


class GTOResponse(BaseModel):
    """Response with GTO strategy."""

    hand: str = Field(
        ...,
        description="The queried hand",
        example="AhKs",
    )
    actions: dict[str, float] = Field(
        ...,
        description="Action frequencies (action -> frequency)",
        example={"fold": 0.0, "call": 0.35, "raise": 0.65},
    )
    ev: Optional[float] = Field(
        default=None,
        description="Expected value of the optimal mixed strategy",
        example=1.45,
    )


@router.post("/gto", response_model=GTOResponse)
async def query_gto(query: GTOQuery, request: Request) -> GTOResponse:
    """
    Query GTO strategy directly.

    Returns optimal action frequencies for the given spot.
    """
    coach = _get_coach(request)

    # Build game state from query
    game_state = _build_game_state(
        hand=query.hand,
        board=query.board,
        position=query.position,
        pot_size=query.pot_size,
        to_call=query.to_call,
        effective_stack=query.effective_stack,
    )

    # Parse hero's hand
    try:
        hero_hand = Hand.from_string(query.hand)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid hand format: {query.hand}. Use format like 'AsKs' or 'AhKd'.",
        )

    try:
        # Get strategy from solver
        strategy = coach.solver.get_strategy(game_state, hero_hand)

        # Convert actions to string keys for JSON response
        actions_dict = {
            action_type.value: frequency
            for action_type, frequency in strategy.actions.items()
        }

        return GTOResponse(
            hand=query.hand,
            actions=actions_dict,
            ev=None,  # EV not implemented in current solver
        )
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No cached solution available for this spot. {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying GTO strategy: {str(e)}",
        )
