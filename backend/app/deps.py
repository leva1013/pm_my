from pathlib import Path

from fastapi import HTTPException, Request

from backend.app.auth import session_username


def require_username(request: Request) -> str:
    username = session_username(request.session)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return username


def get_db_path(request: Request) -> Path:
    return request.app.state.db_path
