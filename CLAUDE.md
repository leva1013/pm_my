# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Project Management MVP: a Next.js Kanban board served by a FastAPI backend, with an AI chat sidebar (via OpenRouter) that can read and mutate the board through validated structured operations. Single hardcoded user (`user`/`password`), one board per user, SQLite storage, everything packaged into one Docker image. See `AGENTS.md` for full business requirements/tech decisions, `docs/PLAN.md` for the part-by-part build plan and current status, `docs/DB_SCHEMA.md` for the SQLite schema, and `docs/AI_STRUCTURED_OUTPUT_SCHEMA.md` for the AI response contract.

Per-directory guides with more detail: `backend/AGENTS.md`, `frontend/AGENTS.md`, `scripts/AGENTS.md`.

## Commands

Backend (run from repo root; tests insert repo root onto `sys.path` themselves, no pytest config file exists):

```bash
pip install -r backend/requirements.txt
pytest backend/tests                     # all backend tests
pytest backend/tests/test_board_api.py   # single file
pytest backend/tests/test_board_api.py::test_get_board_requires_authentication  # single test
uvicorn backend.app.main:app --reload    # run backend directly (frontend must be built into backend/frontend_dist or frontend/out first, or / returns 503)
```

Frontend (run from `frontend/`):

```bash
npm install
npm run dev          # Next.js dev server
npm run lint
npm run build         # static export -> frontend/out (next.config.ts sets output: "export")
npm run test:unit     # Vitest
npm run test:e2e      # Playwright — expects the app already running at http://127.0.0.1:8000 (see playwright.config.ts), i.e. against the FastAPI server with a built frontend, not the Next dev server
npm run test:all       # unit then e2e
```

Full stack via Docker (this is the actual "done" bar for a part — see `docs/PLAN.md` execution evidence):

```bash
scripts/start-server-windows.ps1   # or start-server-mac.sh / start-server-linux.sh — docker compose up --build -d
scripts/stop-server-windows.ps1    # docker compose down --remove-orphans
```

`.env` at repo root holds `OPENROUTER_API_KEY` and is loaded by `docker-compose.yml` via `env_file`.

## Architecture

### Module layout

`backend/app/main.py` is a thin app factory: `create_app(frontend_dist=None, db_path=None)` initializes the DB, stores `frontend_dist`/`db_path` on `app.state`, adds the session middleware, and wires up routers from `backend/app/routes/` in a specific order (see below). Both `create_app` params exist so tests can inject a temp dist dir and temp DB file; `app = create_app()` at module scope is the `uvicorn backend.app.main:app` entrypoint. Route handlers live in `backend/app/routes/` (`health.py`, `board.py`, `ai.py`, `auth.py`, `frontend.py`), one module per concern; `backend/app/deps.py` holds the shared `require_username`/`get_db_path` FastAPI dependencies; `backend/app/login_page.py` holds the login page's inline HTML (not part of the Next app); `backend/app/paths.py` holds the single `REPO_ROOT` constant used for resolving default file paths.

### Request flow and static serving

`routes/frontend.py` owns `/`, and the catch-all `/{full_path:path}`; `routes/auth.py` owns `/login`. All three check session auth first (redirecting to `/login` if absent) before serving the static Next export, and the catch-all 404s any unmatched `api/*` path instead of falling through to the SPA shell. `frontend.router` is included **last** in `create_app()` since its catch-all route must not shadow the more specific API/auth routers registered before it. The catch-all resolves the requested path with `Path.resolve()` and checks `is_relative_to()` against the resolved dist dir before serving a file, so it cannot escape `frontend_dist` via `..` segments (including percent-encoded ones) — do not loosen this without adding back an explicit containment check.

### Auth

Session-cookie auth via Starlette's `SessionMiddleware` (`backend/app/auth.py`). Credentials are hardcoded (`user`/`password`); `SESSION_SECRET` and `SESSION_COOKIE_SECURE` are read from env (defaults are dev-only). Routes that require a session depend on `require_username` (`backend/app/deps.py`), a FastAPI dependency that resolves the session username and raises 401 if absent — new authenticated routes should use `username: str = Depends(require_username)` rather than re-checking `session_username(request.session)` by hand.

### Persistence

`backend/app/db.py` stores the whole board as a JSON blob per user (`boards.board_json`, schema in `docs/DB_SCHEMA.md`). `initialize_database()` creates tables and seeds the `user` row + its initial board (`board_defaults.py`) if missing; `get_board_for_username`/`update_board_for_username` re-run that same ensure-step on every call, so a missing row is self-healing rather than an error path. There is no versioning/locking — the whole document is replaced on write.

### Board validation and mutation

Two independent layers apply to any board write, whether from the `/api/board` PUT or from AI-driven changes:
- `board_validation.py` — structural validation of a full board document (columns/cards shape, cardIds reference real cards, no card in two columns).
- `board_operations.py` — `apply_operations()` takes a list of already-schema-validated operations and applies them to a deep copy of the board, then re-runs `validate_board_payload` on the result before it's accepted. Any failure (unknown id, invalid shape) raises `ValueError` and the whole operation set is rejected atomically — nothing partial is ever persisted.

### AI chat pipeline

`POST /api/ai/chat` in `routes/ai.py` is the orchestrator: normalize/validate the incoming message+history → call `ai_client.call_openrouter_structured()` → validate the response shape (`ai_structured.validate_structured_response`) → if `shouldUpdateBoard`, run it through `board_operations.apply_operations()` → persist → return `{assistantMessage, appliedOperations, board}`. The structured-output contract (allowed operation types: `rename_column`, `create_card`, `edit_card`, `move_card`, `delete_card`) is defined once in `ai_structured.py` and reused both as the OpenRouter `response_format.json_schema` (in `ai_client.py`) and as the server-side re-validation — never trust the model's JSON without re-validating server-side, since `strict: true` on the provider side is not a security boundary. `ai_client.py` accepts an injectable `request_fn` specifically so tests can mock the HTTP call instead of hitting OpenRouter. Model is fixed to `openai/gpt-oss-120b`. A known external flakiness (see `docs/PLAN.md` Part 10 evidence): the live model sometimes returns operations with empty required string fields, which correctly fails validation and surfaces as a 502 — this is expected provider behavior, not a bug to silently work around.

### Frontend data flow

`src/lib/kanban.ts` holds pure board types/logic (`moveCard` drag-drop reducer) with no I/O. `src/lib/boardApi.ts` and `src/lib/aiChatApi.ts` are the only fetch boundaries (`/api/board`, `/api/ai/chat`), both using `credentials: "same-origin"` for the session cookie. `KanbanBoard.tsx` owns board state and drag lifecycle and is where server state and local optimistic updates meet; `AiSidebar.tsx` is a self-contained chat panel that calls `sendAiChat` and, on a response with applied operations, hands the returned `board` back up so the UI refreshes immediately rather than re-fetching.

## Conventions

- Simplicity over defensiveness: no speculative abstractions, no unneeded validation beyond system boundaries (see `AGENTS.md` coding standards). Root-cause issues before patching; do not guess-and-check.
- No emojis anywhere (code, docs, commits).
- Frontend: keep pure/testable logic in `src/lib`, view-state orchestration in components; preserve `data-testid="column-<id>"` / `data-testid="card-<id>"` selectors used by Playwright; avoid `any` in TypeScript.
- Every backend route and frontend behavior change is expected to carry matching unit + integration + (for user-visible flows) Playwright coverage — this is enforced part-by-part in `docs/PLAN.md`, not just a suggestion.
