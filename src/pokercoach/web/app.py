"""FastAPI application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pokercoach.llm.coach import CoachConfig, PokerCoach
from pokercoach.solver.texas_solver import PrecomputedSolver, TexasSolverBridge, TexasSolverConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup: Create global coach instance
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Please set it before starting the application."
        )

    # Get TexasSolver path from environment (optional)
    solver_path = os.environ.get("TEXASSOLVER_PATH")

    # Default cache directory for precomputed solutions
    cache_dir = Path(__file__).parent.parent.parent.parent / "solver_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create fallback solver if binary path is provided
    fallback_solver = None
    if solver_path:
        binary_path = Path(solver_path)
        if binary_path.exists():
            config = TexasSolverConfig(binary_path=binary_path)
            fallback_solver = TexasSolverBridge(config)

    # Create PrecomputedSolver with cache and optional fallback
    solver = PrecomputedSolver(
        cache_dir=cache_dir,
        fallback_solver=fallback_solver,
        timeout=30.0,
    )

    # Create PokerCoach instance
    coach_config = CoachConfig(api_key=api_key)
    app.state.coach = PokerCoach(coach_config, solver)

    yield

    # Shutdown: Flush any pending cache
    if hasattr(app.state, "coach") and hasattr(app.state.coach.solver, "flush_pending_cache"):
        app.state.coach.solver.flush_pending_cache()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PokerCoach API",
        description="AI-powered poker coaching system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # React dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from pokercoach.web.routes import analysis, coach, game_state, opponents

    app.include_router(coach.router, prefix="/api/coach", tags=["coach"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    app.include_router(opponents.router, prefix="/api/opponents", tags=["opponents"])
    app.include_router(game_state.router, prefix="/api", tags=["game-state"])

    @app.get("/")
    async def root():
        return {"message": "PokerCoach API", "version": "0.1.0"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


# Create default app instance
app = create_app()
