import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from backend.app.db import initialize_database
from backend.app.routes import ai, auth, board, frontend, health


def create_app(frontend_dist: Path | None = None, db_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Project Management MVP API")
    app.state.db_path = initialize_database(db_path)
    app.state.frontend_dist = frontend_dist

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET", "pm-dev-session-secret-change-me"),
        session_cookie="pm_session",
        same_site="lax",
        https_only=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        max_age=60 * 60 * 12,
    )

    app.include_router(health.router)
    app.include_router(ai.router)
    app.include_router(board.router)
    app.include_router(auth.router)
    # frontend.router owns the "/" and "/{full_path:path}" catch-all routes and must
    # be included last so the more specific routers above get first refusal.
    app.include_router(frontend.router)

    return app


app = create_app()
