"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PokerCoach API",
        description="AI-powered poker coaching system",
        version="0.1.0",
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
