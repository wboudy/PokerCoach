"""Analysis API routes."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()


class SessionSummary(BaseModel):
    """Summary of an analysis session."""

    session_id: str = Field(
        ...,
        description="Unique identifier for the session",
        example="session_2024_01_15_001",
    )
    hands_played: int = Field(
        ...,
        description="Total number of hands in the session",
        example=847,
    )
    accuracy_score: float = Field(
        ...,
        description="Overall accuracy score (0-100)",
        example=78.5,
    )
    total_ev_loss: float = Field(
        ...,
        description="Total EV lost in big blinds",
        example=12.3,
    )
    blunders: int = Field(
        ...,
        description="Number of major mistakes (>2bb EV loss)",
        example=3,
    )
    mistakes: int = Field(
        ...,
        description="Number of moderate mistakes (0.5-2bb EV loss)",
        example=8,
    )
    inaccuracies: int = Field(
        ...,
        description="Number of minor mistakes (<0.5bb EV loss)",
        example=15,
    )


class HandAnalysis(BaseModel):
    """Analysis of a single hand."""

    hand_id: str = Field(
        ...,
        description="Unique identifier for the hand",
        example="hand_123456789",
    )
    hero_hand: str = Field(
        ...,
        description="Hero's hole cards",
        example="AsKs",
    )
    board: str = Field(
        ...,
        description="Full board (space-separated)",
        example="Ah 7d 2c 9s Kh",
    )
    accuracy_score: float = Field(
        ...,
        description="Accuracy score for this hand (0-100)",
        example=85.0,
    )
    ev_loss: float = Field(
        ...,
        description="EV lost in this hand (in big blinds)",
        example=0.45,
    )
    decisions: list[dict] = Field(
        ...,
        description="List of decision points with analysis",
        example=[
            {"street": "preflop", "action": "raise", "ev_diff": 0.0},
            {"street": "flop", "action": "cbet", "ev_diff": -0.2},
        ],
    )


class LeakSummary(BaseModel):
    """Summary of detected leaks."""

    name: str = Field(
        ...,
        description="Name of the detected leak",
        example="Over-folding to river raises",
    )
    description: str = Field(
        ...,
        description="Detailed description of the leak",
        example="You fold 68% to river raises vs GTO of 45%. Exploitable by bluff-heavy villains.",
    )
    severity: float = Field(
        ...,
        description="Severity score (0-10)",
        example=7.5,
    )
    sample_size: int = Field(
        ...,
        description="Number of situations in the sample",
        example=42,
    )
    avg_ev_loss: float = Field(
        ...,
        description="Average EV loss per occurrence (in big blinds)",
        example=1.8,
    )


@router.post("/upload")
async def upload_hand_history(file: UploadFile = File(...)) -> dict:
    """
    Upload hand history file for analysis.

    Supports PokerStars and PHH formats.
    """
    # TODO: Implement file upload and parsing
    return {
        "status": "received",
        "filename": file.filename,
        "message": "Hand history parsing not yet implemented",
    }


@router.get("/sessions", response_model=list[SessionSummary])
async def get_sessions(limit: int = 10) -> list[SessionSummary]:
    """Get recent analysis sessions."""
    # TODO: Implement database query
    return []


@router.get("/sessions/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str) -> SessionSummary:
    """Get a specific session's summary."""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{session_id}/hands", response_model=list[HandAnalysis])
async def get_session_hands(session_id: str) -> list[HandAnalysis]:
    """Get all hands from a session."""
    # TODO: Implement database query
    return []


@router.get("/hands/{hand_id}", response_model=HandAnalysis)
async def get_hand(hand_id: str) -> HandAnalysis:
    """Get detailed analysis of a specific hand."""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Hand not found")


@router.get("/leaks", response_model=list[LeakSummary])
async def get_leaks(limit: int = 5) -> list[LeakSummary]:
    """Get top detected leaks across all sessions."""
    # TODO: Implement leak detection
    return []
