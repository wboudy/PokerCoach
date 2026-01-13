"""Coach API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CoachQuery(BaseModel):
    """Request model for coach queries."""

    question: str
    hand: Optional[str] = None
    board: Optional[str] = None
    position: Optional[str] = None
    pot_size: Optional[float] = None
    to_call: Optional[float] = None
    effective_stack: Optional[float] = 100.0


class CoachResponse(BaseModel):
    """Response model for coach queries."""

    answer: str
    strategy: Optional[dict] = None
    ev_comparison: Optional[dict] = None


@router.post("/ask", response_model=CoachResponse)
async def ask_coach(query: CoachQuery) -> CoachResponse:
    """
    Ask the poker coach a question.

    The coach will use GTO solver tools to provide
    mathematically optimal advice.
    """
    # TODO: Integrate with PokerCoach LLM
    return CoachResponse(
        answer="Coach integration not yet implemented.",
        strategy=None,
        ev_comparison=None,
    )


class GTOQuery(BaseModel):
    """Request for direct GTO query."""

    hand: str
    board: str = ""
    position: str
    pot_size: float = 0
    to_call: float = 0
    effective_stack: float = 100


class GTOResponse(BaseModel):
    """Response with GTO strategy."""

    hand: str
    actions: dict[str, float]  # Action -> Frequency
    ev: Optional[float] = None


@router.post("/gto", response_model=GTOResponse)
async def query_gto(query: GTOQuery) -> GTOResponse:
    """
    Query GTO strategy directly.

    Returns optimal action frequencies for the given spot.
    """
    # TODO: Integrate with solver
    return GTOResponse(
        hand=query.hand,
        actions={
            "fold": 0.0,
            "call": 0.5,
            "raise": 0.5,
        },
        ev=None,
    )
