from __future__ import annotations

import copy
import uuid
from typing import Any

from backend.app.board_validation import validate_board_payload


def apply_operations(board: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    next_board = copy.deepcopy(board)

    for operation in operations:
        op_type = operation["type"]

        if op_type == "rename_column":
            _rename_column(next_board, operation)
        elif op_type == "create_card":
            _create_card(next_board, operation)
        elif op_type == "edit_card":
            _edit_card(next_board, operation)
        elif op_type == "move_card":
            _move_card(next_board, operation)
        elif op_type == "delete_card":
            _delete_card(next_board, operation)
        else:
            raise ValueError("Unsupported operation type.")

    is_valid, error = validate_board_payload(next_board)
    if not is_valid:
        raise ValueError(error)

    return next_board


def _column(board: dict[str, Any], column_id: str) -> dict[str, Any]:
    columns = board.get("columns", [])
    for column in columns:
        if column.get("id") == column_id:
            return column
    raise ValueError(f"Column {column_id} not found.")


def _find_card_column(board: dict[str, Any], card_id: str) -> dict[str, Any]:
    columns = board.get("columns", [])
    for column in columns:
        if card_id in column.get("cardIds", []):
            return column
    raise ValueError(f"Card {card_id} is not assigned to a column.")


def _rename_column(board: dict[str, Any], operation: dict[str, Any]) -> None:
    column = _column(board, operation["columnId"])
    column["title"] = operation["newTitle"].strip()


def _create_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    column = _column(board, operation["columnId"])
    cards = board["cards"]
    card_id = f"card-ai-{uuid.uuid4().hex[:10]}"
    cards[card_id] = {
        "id": card_id,
        "title": operation["title"].strip(),
        "details": operation.get("details", "").strip(),
    }
    column["cardIds"].append(card_id)


def _edit_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    cards = board["cards"]
    card_id = operation["cardId"]
    card = cards.get(card_id)
    if not isinstance(card, dict):
        raise ValueError(f"Card {card_id} not found.")

    if "title" in operation:
        card["title"] = operation["title"].strip()
    if "details" in operation:
        card["details"] = operation["details"].strip()


def _move_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id = operation["cardId"]
    target_column = _column(board, operation["toColumnId"])
    source_column = _find_card_column(board, card_id)

    source_column["cardIds"].remove(card_id)

    position = operation.get("position")
    target_cards = target_column["cardIds"]
    if not isinstance(position, int) or position >= len(target_cards):
        target_cards.append(card_id)
        return

    target_cards.insert(position, card_id)


def _delete_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id = operation["cardId"]
    cards = board["cards"]
    if card_id not in cards:
        raise ValueError(f"Card {card_id} not found.")

    source_column = _find_card_column(board, card_id)
    source_column["cardIds"].remove(card_id)
    del cards[card_id]
