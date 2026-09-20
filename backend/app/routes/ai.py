from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.ai_client import AiClientError, call_openrouter_structured, run_smoke_test
from backend.app.ai_structured import validate_structured_response
from backend.app.board_operations import apply_operations
from backend.app.db import get_board_for_username, update_board_for_username
from backend.app.deps import get_db_path, require_username

router = APIRouter()


def _map_ai_client_error(exc: AiClientError) -> HTTPException:
    status_code = 500 if exc.code == "missing_api_key" else 502
    return HTTPException(status_code=status_code, detail=exc.message)


@router.post("/api/ai/smoke")
def ai_smoke(username: str = Depends(require_username)):
    try:
        result = run_smoke_test()
    except AiClientError as exc:
        raise _map_ai_client_error(exc) from exc

    return {
        "status": "ok",
        "model": result["model"],
        "prompt": result["prompt"],
        "response": result["response"],
    }


def _normalize_history(history: object) -> list[dict[str, str]]:
    if not isinstance(history, list):
        raise HTTPException(status_code=422, detail="history must be an array.")

    normalized: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail="history entries must be objects.")
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant", "system"}:
            raise HTTPException(
                status_code=422, detail="history role must be user, assistant, or system."
            )
        if not isinstance(content, str):
            raise HTTPException(status_code=422, detail="history content must be a string.")
        normalized.append({"role": role, "content": content})

    return normalized


def _dedupe_trailing_user_turn(
    history: list[dict[str, str]], user_message: str
) -> list[dict[str, str]]:
    # Backward-compatibility with earlier clients that appended the latest user turn to history.
    if history and history[-1]["role"] == "user" and history[-1]["content"].strip() == user_message:
        return history[:-1]
    return history


@router.post("/api/ai/chat")
async def ai_chat(
    request: Request,
    username: str = Depends(require_username),
    db_path: Path = Depends(get_db_path),
):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Request body must be an object.")

    user_message = payload.get("message")
    if not isinstance(user_message, str) or not user_message.strip():
        raise HTTPException(status_code=422, detail="message must be a non-empty string.")
    user_message_text = user_message.strip()

    normalized_history = _normalize_history(payload.get("history", []))
    normalized_history = _dedupe_trailing_user_turn(normalized_history, user_message_text)

    board = get_board_for_username(username=username, db_path=db_path)

    try:
        ai_response = call_openrouter_structured(
            board=board,
            history=normalized_history,
            user_message=user_message_text,
        )
    except AiClientError as exc:
        raise _map_ai_client_error(exc) from exc

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

        update_board_for_username(board=next_board, username=username, db_path=db_path)

    return {
        "assistantMessage": ai_response["assistantMessage"],
        "appliedOperations": operations if should_update else [],
        "board": next_board,
    }
