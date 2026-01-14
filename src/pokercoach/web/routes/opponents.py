"""Opponent database API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()


class PlayerStats(BaseModel):
    """Player statistics."""

    player_id: str = Field(
        ...,
        description="Unique identifier for the player",
        example="villain_123",
    )
    hands_played: int = Field(
        ...,
        description="Total hands observed against this player",
        example=1250,
    )
    vpip: float = Field(
        ...,
        description="Voluntarily Put money In Pot percentage",
        example=24.5,
    )
    pfr: float = Field(
        ...,
        description="Pre-Flop Raise percentage",
        example=18.2,
    )
    three_bet: float = Field(
        ...,
        description="3-bet percentage",
        example=7.5,
    )
    fold_to_3bet: float = Field(
        ...,
        description="Fold to 3-bet percentage",
        example=62.0,
    )
    cbet_flop: float = Field(
        ...,
        description="Continuation bet on flop percentage",
        example=68.5,
    )
    aggression_factor: float = Field(
        ...,
        description="Aggression factor (bets+raises / calls)",
        example=2.8,
    )
    player_type: str = Field(
        ...,
        description="Categorized player type (TAG, LAG, NIT, FISH, etc.)",
        example="TAG",
    )
    confidence: str = Field(
        ...,
        description="Confidence level in stats (low, medium, high)",
        example="medium",
    )


class PlayerProfile(BaseModel):
    """Full player profile."""

    player_id: str = Field(
        ...,
        description="Unique identifier for the player",
        example="villain_123",
    )
    stats: PlayerStats = Field(
        ...,
        description="Player's aggregated statistics",
    )
    exploits: list[str] = Field(
        ...,
        description="List of recommended exploitative adjustments",
        example=["3bet light vs their wide BTN opens", "Barrel turns when they fold to aggression"],
    )
    notes: str = Field(
        ...,
        description="User's personal notes about the player",
        example="Tends to tilt after losing big pots. Overvalues top pair.",
    )


class ExploitRecommendation(BaseModel):
    """Exploitation recommendation."""

    action: str = Field(
        ...,
        description="The action to take",
        example="3bet",
    )
    adjustment: str = Field(
        ...,
        description="Specific adjustment from GTO baseline",
        example="Increase 3bet frequency by 15% from blinds",
    )
    reason: str = Field(
        ...,
        description="Explanation for the adjustment",
        example="Villain folds to 3bet 62% of the time (GTO ~55%)",
    )
    confidence: str = Field(
        ...,
        description="Confidence level in this recommendation",
        example="high",
    )


@router.get("/", response_model=list[PlayerStats])
async def list_players(limit: int = 50) -> list[PlayerStats]:
    """Get all tracked players."""
    # TODO: Implement database query
    return []


@router.get("/{player_id}", response_model=PlayerProfile)
async def get_player(player_id: str) -> PlayerProfile:
    """Get a player's full profile."""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Player not found")


@router.get("/{player_id}/exploits", response_model=list[ExploitRecommendation])
async def get_exploits(player_id: str) -> list[ExploitRecommendation]:
    """Get exploitation recommendations for a player."""
    # TODO: Implement exploitation engine
    return []


@router.post("/{player_id}/notes")
async def update_notes(player_id: str, notes: str) -> dict:
    """Update notes for a player."""
    # TODO: Implement database update
    return {"status": "updated", "player_id": player_id}


@router.get("/search/{query}", response_model=list[PlayerStats])
async def search_players(query: str, limit: int = 20) -> list[PlayerStats]:
    """Search for players by ID."""
    # TODO: Implement search
    return []
