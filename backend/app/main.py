from pathlib import Path
import os
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.app.auth import (
    SESSION_USER_KEY,
    credentials_valid,
    is_authenticated,
    session_username,
)
from backend.app.ai_client import AiClientError, call_openrouter_structured, run_smoke_test
from backend.app.ai_structured import validate_structured_response
from backend.app.board_operations import apply_operations
from backend.app.board_validation import validate_board_payload
from backend.app.db import (
    get_board_for_username,
    initialize_database,
    update_board_for_username,
)


def _resolve_frontend_dist(frontend_dist: Path | None = None) -> Path:
    if frontend_dist is not None:
        return frontend_dist

    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "backend" / "frontend_dist",
        repo_root / "frontend" / "out",
    ]

    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate

    return candidates[0]


def _frontend_not_built_response() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "frontend_not_built",
            "detail": "Frontend static build not found. Build frontend and copy output to backend/frontend_dist.",
        },
    )


def _login_page_html(error: bool = False) -> str:
    error_block = (
        '<p style="color:#b42318;margin:0 0 16px 0;">Invalid username or password.</p>'
        if error
        else ""
    )
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Sign in | Kanban Studio</title>
    <style>
      :root {{
        --secondary-purple: #753991;
        --navy-dark: #032147;
        --gray-text: #888888;
        --surface: #f7f8fb;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: radial-gradient(circle at 8% 10%, rgba(32,157,215,0.22), transparent 40%), var(--surface);
        font-family: Segoe UI, Arial, sans-serif;
        color: var(--navy-dark);
      }}
      .card {{
        width: min(420px, 92vw);
        background: #fff;
        border: 1px solid rgba(3,33,71,0.09);
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 16px 32px rgba(3,33,71,0.12);
      }}
      h1 {{ margin: 0 0 8px 0; }}
      p {{ margin: 0 0 20px 0; color: var(--gray-text); }}
      label {{ display: block; font-size: 0.9rem; margin-bottom: 6px; }}
      input {{
        width: 100%;
        box-sizing: border-box;
        border: 1px solid rgba(3,33,71,0.12);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 14px;
      }}
      button {{
        width: 100%;
        border: 0;
        border-radius: 999px;
        padding: 11px 14px;
        background: var(--secondary-purple);
        color: #fff;
        font-weight: 700;
        cursor: pointer;
      }}
      .hint {{ margin-top: 14px; font-size: 0.85rem; color: var(--gray-text); }}
      .hint code {{ background: #f0f2f8; border-radius: 5px; padding: 2px 5px; }}
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Sign in</h1>
      <p>Use the MVP credentials to open your board.</p>
      {error_block}
      <form method=\"post\" action=\"/api/auth/login\">
        <label for=\"username\">Username</label>
        <input id=\"username\" name=\"username\" type=\"text\" autocomplete=\"username\" required />
        <label for=\"password\">Password</label>
        <input id=\"password\" name=\"password\" type=\"password\" autocomplete=\"current-password\" required />
        <button type=\"submit\">Sign in</button>
      </form>
      <p class=\"hint\">For MVP: <code>user</code> / <code>password</code></p>
    </main>
  </body>
</html>
"""


def create_app(frontend_dist: Path | None = None, db_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Project Management MVP API")
    resolved_db_path = initialize_database(db_path)
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET", "pm-dev-session-secret-change-me"),
        session_cookie="pm_session",
        same_site="lax",
        https_only=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        max_age=60 * 60 * 12,
    )

    def _frontend_files() -> tuple[Path, Path] | None:
        dist_dir = _resolve_frontend_dist(frontend_dist)
        index_file = dist_dir / "index.html"
        if index_file.exists():
            return dist_dir, index_file
        return None

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pm-backend"}

    @app.post("/api/ai/smoke")
    def ai_smoke(request: Request):
        username = session_username(request.session)
        if not username:
            raise HTTPException(status_code=401, detail="Authentication required.")

        try:
            result = run_smoke_test()
        except AiClientError as exc:
            if exc.code == "missing_api_key":
                raise HTTPException(status_code=500, detail=exc.message) from exc
            if exc.code == "network_error":
                raise HTTPException(status_code=502, detail=exc.message) from exc
            if exc.code == "provider_error":
                raise HTTPException(status_code=502, detail=exc.message) from exc
            raise HTTPException(status_code=502, detail=exc.message) from exc

        return {
            "status": "ok",
            "model": result["model"],
            "prompt": result["prompt"],
            "response": result["response"],
        }

    @app.post("/api/ai/chat")
    async def ai_chat(request: Request):
        username = session_username(request.session)
        if not username:
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Request body must be an object.")

        user_message = payload.get("message")
        history = payload.get("history", [])

        if not isinstance(user_message, str) or not user_message.strip():
            raise HTTPException(status_code=422, detail="message must be a non-empty string.")

        if not isinstance(history, list):
            raise HTTPException(status_code=422, detail="history must be an array.")

        normalized_history: list[dict[str, str]] = []
        for item in history:
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail="history entries must be objects.")
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant", "system"}:
                raise HTTPException(status_code=422, detail="history role must be user, assistant, or system.")
            if not isinstance(content, str):
                raise HTTPException(status_code=422, detail="history content must be a string.")
            normalized_history.append({"role": role, "content": content})

        user_message_text = user_message.strip()
        # Backward-compatibility with earlier clients that appended the latest user turn to history.
        if (
            normalized_history
            and normalized_history[-1]["role"] == "user"
            and normalized_history[-1]["content"].strip() == user_message_text
        ):
            normalized_history = normalized_history[:-1]

        board = get_board_for_username(username=username, db_path=resolved_db_path)

        try:
            ai_response = call_openrouter_structured(
                board=board,
                history=normalized_history,
                user_message=user_message_text,
            )
        except AiClientError as exc:
            if exc.code == "missing_api_key":
                raise HTTPException(status_code=500, detail=exc.message) from exc
            if exc.code in {"network_error", "provider_error", "invalid_response"}:
                raise HTTPException(status_code=502, detail=exc.message) from exc
            raise HTTPException(status_code=502, detail=exc.message) from exc

        is_valid, error_message = validate_structured_response(ai_response)
        if not is_valid:
            raise HTTPException(status_code=502, detail=error_message)

        should_update = bool(ai_response["shouldUpdateBoard"])
        operations = ai_response["operations"]
        next_board = board

        if should_update:
            try:
                next_board = apply_operations(board=board, operations=operations)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid AI operation set: {exc}") from exc

            update_board_for_username(
                board=next_board,
                username=username,
                db_path=resolved_db_path,
            )

        return {
            "assistantMessage": ai_response["assistantMessage"],
            "appliedOperations": operations if should_update else [],
            "board": next_board,
        }

    @app.get("/api/board")
    def get_board(request: Request):
        username = session_username(request.session)
        if not username:
            raise HTTPException(status_code=401, detail="Authentication required.")

        return get_board_for_username(username=username, db_path=resolved_db_path)

    @app.put("/api/board")
    async def update_board(request: Request):
        username = session_username(request.session)
        if not username:
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        is_valid, error_message = validate_board_payload(payload)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_message)

        return update_board_for_username(
            board=payload,
            username=username,
            db_path=resolved_db_path,
        )

    @app.get("/login", include_in_schema=False)
    def login_page(request: Request):
        if is_authenticated(request.session):
            return RedirectResponse(url="/", status_code=303)
        return HTMLResponse(_login_page_html())

    @app.post("/api/auth/login")
    async def login(request: Request):
        body = (await request.body()).decode("utf-8")
        form = parse_qs(body)
        username = form.get("username", [""])[0].strip()
        password = form.get("password", [""])[0]

        if not credentials_valid(username, password):
            return HTMLResponse(_login_page_html(error=True), status_code=401)

        request.session[SESSION_USER_KEY] = username
        return RedirectResponse(url="/", status_code=303)

    @app.post("/api/auth/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/", include_in_schema=False)
    def root(request: Request):
        if not is_authenticated(request.session):
            return RedirectResponse(url="/login", status_code=303)

        files = _frontend_files()
        if files is None:
            return _frontend_not_built_response()

        _, index_file = files
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_fallback(full_path: str, request: Request):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        if not is_authenticated(request.session):
            return RedirectResponse(url="/login", status_code=303)

        files = _frontend_files()
        if files is None:
            return _frontend_not_built_response()

        dist_dir, index_file = files
        requested_path = dist_dir / full_path
        if requested_path.is_file():
            return FileResponse(requested_path)

        return FileResponse(index_file)

    return app


app = create_app()
