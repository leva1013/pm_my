from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.ai_structured import validate_structured_response
from backend.app.board_defaults import INITIAL_BOARD
from backend.app.board_operations import apply_operations


def test_structured_response_validation_accepts_valid_payload() -> None:
    payload = {
        "assistantMessage": "Done.",
        "shouldUpdateBoard": True,
        "operations": [
            {
                "type": "rename_column",
                "columnId": "col-backlog",
                "newTitle": "Ideas",
            }
        ],
    }

    is_valid, error = validate_structured_response(payload)
    assert is_valid
    assert error == ""


def test_structured_response_rejects_operations_on_false_update() -> None:
    payload = {
        "assistantMessage": "No update.",
        "shouldUpdateBoard": False,
        "operations": [{"type": "delete_card", "cardId": "card-1"}],
    }

    is_valid, error = validate_structured_response(payload)
    assert not is_valid
    assert "must be empty" in error


def test_apply_operations_is_atomic_and_applies_changes() -> None:
    result = apply_operations(
        board=INITIAL_BOARD,
        operations=[
            {
                "type": "rename_column",
                "columnId": "col-backlog",
                "newTitle": "Ideas",
            },
            {
                "type": "move_card",
                "cardId": "card-1",
                "toColumnId": "col-review",
                "position": 0,
            },
        ],
    )

    assert result["columns"][0]["title"] == "Ideas"
    review_column = next(c for c in result["columns"] if c["id"] == "col-review")
    assert review_column["cardIds"][0] == "card-1"
    assert INITIAL_BOARD["columns"][0]["title"] == "Backlog"


def test_apply_operations_rejects_invalid_semantics() -> None:
    try:
        apply_operations(
            board=INITIAL_BOARD,
            operations=[
                {
                    "type": "move_card",
                    "cardId": "missing-card",
                    "toColumnId": "col-review",
                }
            ],
        )
    except ValueError as exc:
        assert "missing-card" in str(exc)
        return

    raise AssertionError("Expected semantic validation failure")
