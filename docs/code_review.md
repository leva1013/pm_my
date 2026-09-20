# Code Review (2026-09-20)

Full-repo review of the PM MVP (FastAPI backend + Next.js frontend + Docker packaging), covering everything under `backend/`, `frontend/`, `scripts/`, and the Docker/compose setup, at the current state of `feature/part10-ai-sidebar-signoff` (Part 10 complete per `docs/PLAN.md`). Findings are ordered by severity. Two of the findings below (traversal, DB persistence) were empirically verified, not just inferred from reading code.

**Update (2026-09-20):** all Critical/High/Medium items (1-5) have been fixed and re-verified — see "Remediation status" under each and `docs/PLAN.md` → "Post-Part-10 remediation" for full test evidence. Items 6-10 (Low/Nit) are recorded but intentionally left open.

## Summary

| # | Severity | Area | Issue | Status |
|---|----------|------|-------|--------|
| 1 | Critical | Backend / security | Authenticated-user path traversal → arbitrary file read via the static-file fallback route | Fixed |
| 2 | High | Deployment / data | SQLite board data is never persisted outside the container; every stop/start cycle silently resets the board | Fixed |
| 3 | High | Testing / data hygiene | Test suite writes to the real, git-tracked SQLite file instead of an isolated temp DB | Fixed |
| 4 | Medium | Repo hygiene | `backend/data/pm.db` (a runtime data file) is committed to git | Fixed |
| 5 | Medium | AI contract | The JSON schema actually sent to OpenRouter is much looser than the approved contract in `docs/AI_STRUCTURED_OUTPUT_SCHEMA.md`, likely contributing to the known provider flakiness | Fixed |
| 6 | Low | Concurrency | Drag-and-drop autosave and AI chat mutation are two unsynchronized read-modify-write paths to the same board row | Open |
| 7 | Low | Security hardening | `SESSION_SECRET` / `SESSION_COOKIE_SECURE` are never overridden for the Docker deployment, so it ships with the dev-default fallback secret | Open |
| 8 | Low | Robustness | `_move_card` trusts `position >= 0` was already checked upstream; negative positions would silently misbehave if ever called without prior schema validation | Open |
| 9 | Nit | Frontend | AI-driven board update resets `isSaving`/`saveError` unconditionally, which can clobber the state of an unrelated in-flight drag-and-drop save | Open |
| 10 | Nit | Build reproducibility | `backend/requirements.txt` uses unpinned `>=` ranges with no lockfile, so backend image builds aren't reproducible | Open |

---

## 1. Critical — Path traversal / arbitrary file read (`backend/app/main.py:322-339`)

The catch-all static route joins the raw, attacker-controlled URL path directly onto the frontend dist directory with no containment check:

```python
@app.get("/{full_path:path}", include_in_schema=False)
def frontend_fallback(full_path: str, request: Request):
    ...
    dist_dir, index_file = files
    requested_path = dist_dir / full_path
    if requested_path.is_file():
        return FileResponse(requested_path)
```

`full_path` can contain `..` segments. Starlette's `path` converter does not strip or reject dot-segments, so a request like `GET /%2e%2e/%2e%2e/.env` escapes `dist_dir` and reads any file the process can access.

**Verified**: reproduced against a `TestClient` instance — a percent-encoded `..` segment (`/%2e%2e/secret/top-secret.txt`) returned the contents of a file placed outside the served directory with `200 OK`. (A literal `../` in the URL gets collapsed by the HTTP client before the request is sent, which is why the encoded form is needed to demonstrate it — the server itself performs no normalization or containment check.)

Impact: any authenticated session (and since credentials are the publicly-documented `user`/`password` hardcoded in `auth.py` and printed on the login page, this is effectively unauthenticated) can read arbitrary files inside the container/host process, including `backend/data/pm.db` (full board data) and, in a local `uvicorn --reload` run per the documented dev command, the repo's `.env` (which holds `OPENROUTER_API_KEY`).

**Action**: resolve the joined path and verify it is still contained within `dist_dir` before serving, e.g.:

```python
requested_path = (dist_dir / full_path).resolve()
if requested_path.is_relative_to(dist_dir.resolve()) and requested_path.is_file():
    return FileResponse(requested_path)
```

Add a regression test asserting that a traversal attempt (encoded or otherwise) never escapes `dist_dir`.

**Remediation**: `requested_path` is now resolved and checked with `Path.is_relative_to(dist_dir.resolve())` before serving. Re-verified with the exact `/%2e%2e/...` payload above against both `TestClient` and the live Docker container — no longer leaks. Regression test added in `backend/tests/test_app.py::test_frontend_fallback_rejects_path_traversal_outside_dist`.

## 2. High — Board data does not survive the documented stop/start cycle

`docker-compose.yml` declares no volume for `backend/data`, so `backend/data/pm.db` exists only in the container's writable layer. The documented normal workflow (`scripts/stop-server-*.sh` → `docker compose down --remove-orphans`, then `scripts/start-server-*.sh` → `docker compose up --build -d`) removes and recreates the container. `.dockerignore` excludes `*.db` from the build context, so the rebuilt image always starts from a clean DB seeded with `INITIAL_BOARD` — the previous board state is gone.

This directly contradicts `docs/PLAN.md` Part 6's stated success criterion: "Board state persists across reloads and server restarts for the same user." Restarting the process (`--reload`) is fine since the file lives on disk between reloads, but the container lifecycle documented in the scripts (and the "actual done bar" callout in `CLAUDE.md`) loses data every time.

**Action**: mount `backend/data` as a bind mount or named volume in `docker-compose.yml`, e.g.:

```yaml
services:
  app:
    ...
    volumes:
      - ./backend/data:/app/backend/data
```

Add this to the Docker sign-off checklist in `docs/PLAN.md` (stop → start → verify board unchanged) since the existing evidence log only exercises a single `up`/`down` pair without checking persistence across it.

**Remediation**: added `volumes: - ./backend/data:/app/backend/data` to `docker-compose.yml`. Re-verified by setting a marker via `PUT /api/board`, running `docker compose down` + `up --build -d`, and confirming the marker survived. Recorded in `docs/PLAN.md`.

## 3. High — Tests mutate the real, shared SQLite file

`backend/app/main.py:344` runs `app = create_app()` at import time with no `db_path`, which resolves to the real repo path `backend/data/pm.db` (`db.py:13-17`). Several tests in `backend/tests/test_app.py` also call `create_app()` (or `TestClient(create_app())`) without passing a `db_path` (e.g. `test_health_endpoint_returns_ok_payload`, `test_root_requires_authentication`, `test_login_page_renders_for_unauthenticated_user`, `test_login_failure_returns_401`, `test_login_success_redirects_and_sets_session_cookie`, `test_logout_clears_session_and_redirects`), so importing `backend.app.main` and running this file exercises the live, git-tracked database instead of an isolated one.

This is almost certainly why the working tree in this session started with `backend/data/pm.db` showing as modified — running the app or its test suite writes to a file that's also checked into git (see finding 4).

**Action**: every test that constructs an app should pass an explicit `tmp_path`-backed `db_path`, matching the pattern already used correctly in `test_board_api.py` and `test_ai_chat_api.py`. Consider also guarding the module-level `app = create_app()` behind `if __name__ != "__test__"`-style indirection, or lazily constructing it, so merely importing `backend.app.main` (which several test files do, to reach `main_module.call_openrouter_structured` for monkeypatching) has no side effect on disk.

**Remediation**: every `create_app()` call in `test_app.py` now passes an explicit `tmp_path`-backed `db_path`. Left the module-level `app = create_app()` in `main.py` as-is (required for the documented `uvicorn backend.app.main:app` entrypoint) — since `pm.db` is now gitignored (finding 4), importing the module still creates a local dev-only DB file, but it's no longer shared/tracked state.

## 4. Medium — Runtime database file is committed to git

`backend/data/pm.db` is tracked (`git ls-files` confirms it), and the git status at the start of this session showed it as modified. `.gitignore` ignores `db.sqlite3` (a Django-template leftover) but not this project's actual `*.db` path. `.dockerignore` does exclude `*.db`, so the shipped image isn't affected, but the repo itself accumulates noisy binary diffs of whatever board state a developer happened to have locally, and (per finding 3) every local test run perturbs it further.

**Action**:
```
git rm --cached backend/data/pm.db
```
and add `backend/data/*.db` (or `backend/data/`) to `.gitignore`.

**Remediation**: done as described (`git rm --cached -f`, file remains on disk; `.gitignore` updated with `backend/data/*.db`).

## 5. Medium — OpenRouter-facing schema is weaker than the approved contract

`docs/AI_STRUCTURED_OUTPUT_SCHEMA.md` specifies (and was approved with) a `oneOf`-based JSON Schema where each operation type has its own `required` fields — e.g. `rename_column` requires `columnId` and `newTitle`, `create_card` requires `columnId` and `title`, etc.

The schema actually built by `structured_output_schema()` (`backend/app/ai_structured.py:15-42`) and sent to OpenRouter as `response_format.json_schema` with `strict: true` only requires `type`:

```python
"items": {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": sorted(ALLOWED_OPERATION_TYPES)}
    },
    "required": ["type"],
},
```

There's no `additionalProperties: false` and no per-type `required`/`oneOf` branching, so the provider's strict-mode constraint doesn't actually force `columnId`, `newTitle`, `cardId`, etc. to be present or non-empty. Server-side re-validation (`validate_structured_response`) correctly catches this before anything is applied, so this is not a correctness/security gap — `CLAUDE.md` is explicit that provider-side `strict: true` "is not a security boundary" — but it is a likely contributor to the flakiness already logged in `docs/PLAN.md` Part 10 ("provider responses repeatedly returned invalid operation fields (empty required strings)"). A stricter provider-side schema gives the model less room to emit incomplete operations in the first place.

**Action**: build `structured_output_schema()` from the same `oneOf` shape documented in `docs/AI_STRUCTURED_OUTPUT_SCHEMA.md` (or generate the doc's schema from a single shared source) so the two stay in sync and the provider is actually constrained the way the approved design says it should be.

**Remediation**: `structured_output_schema()` now builds a `oneOf` branch per operation type with `additionalProperties: false` and the correct per-type `required` fields, matching the doc. The top-level "operations must be empty when `shouldUpdateBoard` is false" cross-field rule is intentionally *not* mirrored as a JSON Schema `if/then` (that construct isn't reliably supported by provider strict modes); it continues to be enforced server-side by `validate_structured_response`, which is the actual security boundary per `CLAUDE.md`. Added `test_provider_schema_requires_per_operation_type_fields` to lock in the shape.

## 6. Low — Unsynchronized writers to the same board row

Two independent paths read-then-write the same board document with no locking or version check:
- `PUT /api/board` (drag/drop, rename, add/delete card), queued client-side per tab via `saveQueueRef` in `KanbanBoard.tsx:27,54-67`.
- `POST /api/ai/chat`, which reads the board fresh from the DB on the backend, applies operations, and persists (`main.py:220-253`).

If a user drags a card (queuing a save) and then sends an AI chat message before that save lands, the AI call may read a stale board and its subsequent write can silently discard the drag-drop change (or vice versa). `docs/DB_SCHEMA.md` explicitly lists "no optimistic locking/version field yet" as an accepted MVP non-goal, so this may be intentional, but it's worth calling out explicitly next to that note (or in `docs/PLAN.md`) since it's a real, reachable data-loss scenario in normal single-user usage, not just a multi-user concern.

**Action**: no code change required for MVP scope, but document the known race explicitly rather than only implying it via "no locking," so a future contributor doesn't rediscover it as a surprise bug.

## 7. Low — Session hardening flags are never set for the shipped deployment

`SESSION_SECRET` defaults to the hardcoded string `"pm-dev-session-secret-change-me"` (`main.py:138`) and `SESSION_COOKIE_SECURE` defaults to `"false"` (`main.py:141`) unless overridden by environment variables. Neither is set in `.env` or `docker-compose.yml`, so the documented "done bar" Docker deployment (`docker compose up --build -d`) runs with both defaults — a publicly-visible session-signing secret and a non-`Secure` session cookie.

Given the MVP's hardcoded, publicly-displayed credentials, the actual risk this adds is marginal, but `docs/PLAN.md` Part 4 explicitly calls for "secure cookie session handling," so it's worth either setting a real `SESSION_SECRET` in `.env`/compose or adding a one-line note that the defaults are accepted as-is for a local-only MVP.

**Action**: add `SESSION_SECRET` to `.env`/`docker-compose.yml`'s `env_file`, or explicitly document in `docs/PLAN.md`/`AGENTS.md` that the fallback is intentional for local-only scope.

## 8. Low — `_move_card` doesn't re-check `position >= 0`

`backend/app/board_operations.py:82-95`:

```python
position = operation.get("position")
target_cards = target_column["cardIds"]
if not isinstance(position, int) or position >= len(target_cards):
    target_cards.append(card_id)
    return
target_cards.insert(position, card_id)
```

A negative `position` passes `isinstance(position, int)` and (for small magnitudes) fails the `>= len(...)` check, falling through to `list.insert(position, ...)`, which Python interprets as "from the end" — not the intended "append" fallback. This is currently unreachable because `validate_structured_response`'s `move_card` branch already rejects `position < 0` before `apply_operations` is ever called, but `apply_operations` has no such guard of its own, so it's one refactor away from a live bug if it's ever called from a second call site without going through the schema validator first.

**Action**: add `or position < 0` to the fallback condition in `_move_card` so the function is safe on its own, independent of the caller.

## 9. Nit — AI board update clobbers unrelated save-state UI

`KanbanBoard.tsx:153-157`:

```tsx
const handleAiBoardUpdate = (nextBoard: BoardData) => {
  setBoard(nextBoard);
  setSaveError(null);
  setIsSaving(false);
};
```

If a drag-and-drop save is genuinely in flight (`saveQueueRef` promise unresolved) when an AI chat response lands, this unconditionally clears `isSaving`/`saveError`, which can hide a real save failure that resolves moments later. Low impact (cosmetic), but worth a quick fix given `enqueueSave` already tracks queue state — e.g. only clear these if the queue is idle.

## 10. Nit — Backend dependencies are unpinned with no lockfile

`backend/requirements.txt` uses `>=` ranges (`fastapi>=0.116.0`, etc.) and there's no `uv.lock`/`requirements.lock` checked in, so `RUN uv pip install --system --no-cache -r /tmp/requirements.txt` in the Dockerfile can resolve different versions on different build days. The frontend has the equivalent problem mitigated by `package-lock.json`, which is already committed and used correctly. `AGENTS.md`'s "use latest versions" standard is presumably why `>=` was chosen deliberately, so this is a minor reproducibility trade-off to be aware of rather than a defect — worth a lockfile once the project moves past MVP iteration speed.

---

## What's solid

- The two-layer validation model (`board_validation.py` structural checks + `ai_structured.py` server-side re-validation of the AI response, re-run again by `apply_operations` before persisting) is a genuinely good defense-in-depth pattern and is well covered by tests (`test_ai_structured.py`, `test_ai_chat_api.py`).
- `apply_operations`'s atomicity (deep-copy, validate-then-return-or-raise, nothing partial ever persisted) is correctly implemented and tested.
- Frontend/backend contract boundaries are clean — `boardApi.ts`/`aiChatApi.ts` are the only fetch call sites, and `kanban.ts` keeps drag/drop reducer logic pure and unit-testable.
- Test pyramid is genuinely followed (unit + integration + Playwright per changed behavior), matching the strict per-part bar in `docs/PLAN.md`.
- No `any` in the frontend, consistent `data-testid` selectors, and the AI-client injectable `request_fn` pattern makes provider calls fully mockable without hitting the network.
