# Project Plan

## Scope and constraints

- MVP scope only. No extra features outside AGENTS requirements.
- Tech stack: Next.js frontend, FastAPI backend, SQLite, Docker, OpenRouter.
- Auth for MVP: hardcoded user/password with secure cookie session handling only.
- Persistence model: Kanban board payload is stored as JSON in SQLite.
- One board per signed-in user.
- Local run target only.

## Global quality gates (strict minimum)

Every part must satisfy all of the following before it is considered done:

- Lint/type: frontend lint passes; TypeScript checks pass; backend static checks pass once introduced.
- Unit tests: all relevant logic added/changed in the part has direct unit tests.
- Integration tests: every new backend route or frontend-backend contract has integration coverage.
- End-to-end tests: each user-visible flow added/changed in the part has at least one Playwright path.
- Regression checks: previously passing tests remain green.
- No critical known defect is accepted to move to the next part.

## Test strategy by layer

- Unit:
	- Frontend component and utility behavior.
	- Backend pure logic and service/database helpers.
- Integration:
	- FastAPI route tests against app instance and temp database.
	- Frontend data/client integration where behavior crosses module boundaries.
- E2E:
	- Browser flows for login, Kanban interactions, and AI chat behavior.

## Part 1 - Planning and baseline docs

### Checklist

- [ ] Expand this plan with explicit tasks, tests, and success criteria.
- [ ] Create frontend/AGENTS.md documenting current frontend architecture.
- [ ] Add frontend coding conventions for all future frontend changes.
- [ ] Confirm user approval before any implementation in Parts 2-10.

### Tests (strict minimum)

- [ ] Documentation review pass by user.
- [ ] No code changes outside planning/docs artifacts.

### Success criteria

- The user explicitly approves docs before implementation begins.

## Part 2 - Scaffolding (Docker + FastAPI hello world)

### Checklist

- [ ] Create backend app skeleton in backend/.
- [ ] Add FastAPI app with health route and sample API route.
- [ ] Configure Docker build/run for full app container.
- [ ] Add scripts in scripts/ for start/stop on Windows, macOS, Linux.
- [ ] Serve a temporary static hello-world page from backend root.

### Tests (strict minimum)

- [ ] Unit: backend app config/bootstrap tests.
- [ ] Integration: GET / and GET /api/health return expected status/payload.
- [ ] E2E: container starts locally and hello-world page is reachable.

### Success criteria

- Single command path can start stack locally in Docker.
- Root page and API sample endpoint are both reachable.

## Part 3 - Static frontend served by backend

### Checklist

- [ ] Build frontend static assets in production mode.
- [ ] Wire FastAPI static serving so / renders Kanban UI.
- [ ] Remove temporary hello-world root response.
- [ ] Ensure path handling works in local Docker runtime.

### Tests (strict minimum)

- [ ] Unit: any new asset path resolver logic.
- [ ] Integration: backend serves generated frontend files at / and asset routes.
- [ ] E2E: page load shows Kanban board and 5 columns in containerized run.

### Success criteria

- The existing Kanban demo is reachable from backend-served root URL.

## Part 4 - MVP sign-in/sign-out (secure cookie session)

### Checklist

- [ ] Add login page/form requiring user/password.
- [ ] Validate credentials against fixed values (user/password).
- [ ] Issue secure session cookie on successful sign-in.
- [ ] Gate Kanban route behind authenticated session.
- [ ] Add logout endpoint/action clearing session cookie.

### Tests (strict minimum)

- [ ] Unit: auth/session helpers and credential validation logic.
- [ ] Integration: login success/failure, protected route access, logout behavior.
- [ ] E2E: unauthenticated user is redirected to login; valid login reaches board; logout returns to login.

### Success criteria

- No Kanban access without valid session cookie.
- Valid login/logout flow works consistently in browser.

## Part 5 - Database modeling (SQLite with JSON payload)

### Checklist

- [ ] Propose and document schema in docs/.
- [ ] Include users table and one-board-per-user model.
- [ ] Define board payload storage as JSON text column in SQLite.
- [ ] Define migration/bootstrap strategy for DB creation if missing.
- [ ] Obtain user sign-off before implementation in Part 6.

### Tests (strict minimum)

- [ ] Schema review checklist completed.
- [ ] User approves schema document explicitly.

### Success criteria

- Approved schema and persistence strategy are documented and unambiguous.

## Part 6 - Backend Kanban API + persistence

### Checklist

- [ ] Implement DB initialization on startup if DB file does not exist.
- [ ] Implement API to fetch signed-in user's board.
- [ ] Implement API to update signed-in user's board JSON payload.
- [ ] Validate request payload shape and reject invalid updates.
- [ ] Ensure authorization ties board access to current session user.

### Tests (strict minimum)

- [ ] Unit: DB repository functions and payload validation.
- [ ] Integration: GET/PUT board routes, unauthorized access, invalid payload handling, first-run DB creation.
- [ ] E2E: login + update board + refresh preserves changes.

### Success criteria

- Board state persists across reloads and server restarts for the same user.

## Part 7 - Frontend/backend integration for persistent Kanban

### Checklist

- [ ] Replace local in-memory board initialization with backend fetch.
- [ ] Persist card/column edits and drag-drop updates via backend API.
- [ ] Add loading/error states for board fetch/update.
- [ ] Keep UI behavior and styling consistent with existing UX.

### Tests (strict minimum)

- [ ] Unit: frontend state reducers/helpers for server-driven updates.
- [ ] Integration: API client and UI data flow for fetch/update success and failure.
- [ ] E2E: add/edit/move/delete interactions persist after reload.

### Success criteria

- User interactions mutate persisted board state, not local-only state.

## Part 8 - OpenRouter connectivity smoke test

### Checklist

- [ ] Add backend AI client wrapper using OPENROUTER_API_KEY.
- [ ] Configure model as openai/gpt-oss-120b.
- [ ] Add simple protected endpoint that sends "2+2" prompt to verify connectivity.
- [ ] Add robust error mapping for missing key/network/provider failures.

### Tests (strict minimum)

- [ ] Unit: AI client request builder and response parser with mocks.
- [ ] Integration: endpoint behavior with mocked provider and error scenarios.
- [ ] E2E: optional guarded smoke test when API key is present.

### Success criteria

- Backend can complete a successful OpenRouter round-trip with expected response shape.

## Part 9 - Structured Outputs for chat + optional board mutation

### Checklist

- [ ] Propose structured output schema for user approval before implementation.
- [ ] Send current board JSON + chat history + user message to model.
- [ ] Validate AI response against approved schema.
- [ ] Apply optional board mutation atomically when valid mutation is returned.
- [ ] Persist updated board and return both assistant reply and resulting board state.

### Tests (strict minimum)

- [ ] Unit: schema validator, mutation applier, and conflict/error handling.
- [ ] Integration: endpoint with mocked model responses (valid, invalid, no-op, malformed).
- [ ] E2E: chat request resulting in no change and request resulting in board update.

### Success criteria

- AI output is strictly validated and cannot corrupt board data.
- Chat response and board updates are deterministic from validated output.

## Part 10 - Sidebar AI chat UI wired to structured outputs

### Checklist

- [x] Add right-side chat panel integrated into existing board layout.
- [x] Send user prompts to backend chat endpoint with session context.
- [x] Render conversation history with loading/error states.
- [x] Apply returned board updates to UI immediately after successful response.
- [x] Keep responsive behavior usable on desktop and mobile.

### Tests (strict minimum)

- [x] Unit: chat UI state transitions and message rendering logic.
- [x] Integration: frontend chat client, response handling, board refresh wiring.
- [x] E2E: end-to-end chat flow with both non-mutating and mutating AI responses.

### Success criteria

- User can chat in sidebar and see board auto-refresh when AI returns valid mutations.

### Execution evidence (2026-09-16)

- Backend regression: 35 passed.
- Frontend unit regression: 7 passed.
- Playwright regression: 8 passed, 1 skipped (OpenRouter smoke test when key is not set).
- Added e2e coverage for AI sidebar visibility and missing-key error behavior.
- Added deterministic e2e coverage for both AI non-mutating and AI mutating sidebar flows by mocking /api/ai/chat responses.
- Stabilized drag-drop e2e by creating and moving a test-local card instead of relying on pre-existing board IDs.
- External blocker for live mutating AI e2e: provider responses repeatedly returned invalid operation fields (empty required strings), resulting in 502 responses with details like `newTitle must be a non-empty string` and `columnId must be a non-empty string`.
- Containerized sign-off completed: `docker compose up -d --build` succeeded, `/api/health` returned `ok`, Playwright ran with 8 passed and 1 skipped, and `docker compose down` succeeded.

## Post-Part-10 remediation (2026-09-20)

Full-repo review (`docs/code_review.md`) surfaced a critical path-traversal bug and several persistence/hygiene/AI-contract gaps. Fixed and re-verified before returning to feature work:

- Fixed path-traversal/arbitrary-file-read in the static-file fallback route (`backend/app/main.py`): `full_path` is now resolved and checked with `is_relative_to()` against the frontend dist directory before serving. Verified against both an in-process `TestClient` and the running Docker container with an encoded `..` payload (`/%2e%2e/...`) — confirmed it no longer escapes the served directory.
- Fixed board-data loss on container recreate: added a bind mount (`./backend/data:/app/backend/data`) to `docker-compose.yml`. Verified by setting a marker value via `PUT /api/board`, running `docker compose down` + `docker compose up --build -d` (the exact cycle `scripts/stop-server-*`/`start-server-*` perform), and confirming the marker survived.
- Fixed test isolation: every `create_app()` call in `backend/tests/test_app.py` now passes an explicit `tmp_path`-backed `db_path`, so running the suite no longer touches the shared dev database.
- Untracked `backend/data/pm.db` from git and added `backend/data/*.db` to `.gitignore` (file remains on disk, `.dockerignore` already kept it out of built images).
- Tightened `structured_output_schema()` in `backend/app/ai_structured.py` to send OpenRouter a `oneOf` schema with per-operation-type `required` fields and `additionalProperties: false`, matching the approved contract in `docs/AI_STRUCTURED_OUTPUT_SCHEMA.md`, instead of a schema that only constrained the `type` field.
- Fixed a pre-existing lint failure in `AiSidebar.tsx` (unescaped quotes) found while re-running the full check suite.

### Re-verification evidence (2026-09-20)

- Backend: `pytest backend/tests` — 37 passed (added a traversal regression test and a provider-schema shape test).
- Frontend: `npm run lint` clean, `npm run test:unit` — 7 passed, `npm run build` succeeded.
- Playwright against `uvicorn` with the built frontend: 8 passed, 1 skipped (no `OPENROUTER_API_KEY` in this shell).
- Playwright against the rebuilt Docker container: 8 passed, 1 skipped — same baseline as the original Part 10 sign-off.
- Manual persistence check across `docker compose down` + `up --build -d`: board marker value survived.
- Manual traversal check against the live container: encoded `..` payload now falls back to the SPA shell instead of leaking `backend/app/main.py`.

## Backend module refactor (2026-09-20)

`backend/app/main.py` had grown into a monolithic module (app factory, inline login-page HTML, and all nine routes). Split into a thin app factory plus focused modules/packages:

- `backend/app/main.py` — app factory only: initializes the DB, stores `frontend_dist`/`db_path` on `app.state`, adds session middleware, includes routers.
- `backend/app/routes/` (new package) — one router module per concern: `health.py`, `board.py`, `ai.py`, `auth.py`, `frontend.py` (static/SPA serving, including the traversal-safe catch-all).
- `backend/app/deps.py` (new) — shared `require_username`/`get_db_path` FastAPI dependencies, replacing the repeated hand-rolled `session_username(request.session)` check called out as a maintenance risk in `CLAUDE.md`.
- `backend/app/login_page.py` (new) — the inline login-page HTML, extracted out of route logic.
- `backend/app/paths.py` (new) — single `REPO_ROOT` constant, replacing the `Path(__file__).resolve().parents[N]` computation that was previously duplicated (and depth-fragile) across `main.py` and `db.py`.
- No route behavior, response shapes, or status codes changed. Two test files (`test_ai_chat_api.py`, `test_ai_smoke_api.py`) had their `monkeypatch.setattr` targets updated from `backend.app.main` to `backend.app.routes.ai`, since that's where `call_openrouter_structured`/`run_smoke_test` are now imported and called.
- `CLAUDE.md`'s architecture section updated to describe the new module layout.

### Re-verification evidence (2026-09-20, post-refactor)

- Backend: `pytest backend/tests` — 37 passed, no changes needed beyond the two monkeypatch-target updates above.
- Frontend: `npm run lint` clean, `npm run test:unit` — 7 passed (frontend untouched by this refactor).
- Docker: full rebuild (`docker compose up --build -d`) succeeded against the new package layout; `/api/health` OK.
- Playwright against the rebuilt container: 8 passed, 1 skipped — same baseline.
- Re-ran the path-traversal check against a file that only exists post-refactor (`backend/app/routes/board.py`): still blocked, falls back to the SPA shell.
- Re-ran the persistence check across a full `docker compose down` + `up --build -d` cycle with a fresh marker value: survived.

## Explicit hold points

- Hold point A: After Part 1 docs updates, wait for user approval.
- Hold point B: After Part 5 schema proposal, wait for user approval.
- Hold point C: Before Part 9 implementation, wait for user approval of structured output schema.