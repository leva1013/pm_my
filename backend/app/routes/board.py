from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.board_validation import validate_board_payload
from backend.app.db import get_board_for_username, update_board_for_username
from backend.app.deps import get_db_path, require_username

router = APIRouter()


@router.get("/api/board")
def get_board(
    username: str = Depends(require_username),
    db_path: Path = Depends(get_db_path),
):
    return get_board_for_username(username=username, db_path=db_path)


@router.put("/api/board")
async def update_board(
    request: Request,
    username: str = Depends(require_username),
    db_path: Path = Depends(get_db_path),
):
    payload = await request.json()
    is_valid, error_message = validate_board_payload(payload)
    if not is_valid:
        raise HTTPException(status_code=422, detail=error_message)

    return update_board_for_username(board=payload, username=username, db_path=db_path)
