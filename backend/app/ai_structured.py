from __future__ import annotations

from typing import Any


ALLOWED_OPERATION_TYPES = {
    "rename_column",
    "create_card",
    "edit_card",
    "move_card",
    "delete_card",
}


def _operation_schema(
    op_type: str, required: list[str], properties: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["type", *required],
        "properties": {"type": {"const": op_type}, **properties},
    }


def _operation_schemas() -> list[dict[str, Any]]:
    return [
        _operation_schema(
            "rename_column",
            ["columnId", "newTitle"],
            {
                "columnId": {"type": "string", "minLength": 1},
                "newTitle": {"type": "string", "minLength": 1, "maxLength": 80},
            },
        ),
        _operation_schema(
            "create_card",
            ["columnId", "title"],
            {
                "columnId": {"type": "string", "minLength": 1},
                "title": {"type": "string", "minLength": 1, "maxLength": 160},
                "details": {"type": "string", "maxLength": 2000},
            },
        ),
        _operation_schema(
            "edit_card",
            ["cardId"],
            {
                "cardId": {"type": "string", "minLength": 1},
                "title": {"type": "string", "minLength": 1, "maxLength": 160},
                "details": {"type": "string", "maxLength": 2000},
            },
        ),
        _operation_schema(
            "move_card",
            ["cardId", "toColumnId"],
            {
                "cardId": {"type": "string", "minLength": 1},
                "toColumnId": {"type": "string", "minLength": 1},
                "position": {"type": "integer", "minimum": 0},
            },
        ),
        _operation_schema(
            "delete_card",
            ["cardId"],
            {"cardId": {"type": "string", "minLength": 1}},
        ),
    ]


def structured_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["assistantMessage", "shouldUpdateBoard", "operations"],
        "properties": {
            "assistantMessage": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
            },
            "shouldUpdateBoard": {"type": "boolean"},
            # shouldUpdateBoard == false => operations must be empty is enforced by
            # validate_structured_response, not here: cross-field conditionals
            # (JSON Schema if/then) aren't reliably supported by provider strict modes.
            "operations": {
                "type": "array",
                "maxItems": 50,
                "items": {"oneOf": _operation_schemas()},
            },
        },
    }


def validate_structured_response(payload: object) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Structured response must be a JSON object."

    assistant_message = payload.get("assistantMessage")
    should_update = payload.get("shouldUpdateBoard")
    operations = payload.get("operations")

    if not isinstance(assistant_message, str) or not assistant_message.strip():
        return False, "assistantMessage must be a non-empty string."

    if not isinstance(should_update, bool):
        return False, "shouldUpdateBoard must be a boolean."

    if not isinstance(operations, list):
        return False, "operations must be an array."

    if len(operations) > 50:
        return False, "operations cannot exceed 50 items."

    if not should_update and operations:
        return False, "operations must be empty when shouldUpdateBoard is false."

    for operation in operations:
        is_valid, message = _validate_operation(operation)
        if not is_valid:
            return False, message

    return True, ""


def _validate_operation(operation: object) -> tuple[bool, str]:
    if not isinstance(operation, dict):
        return False, "Each operation must be an object."

    op_type = operation.get("type")
    if op_type not in ALLOWED_OPERATION_TYPES:
        return False, "Unsupported operation type."

    if op_type == "rename_column":
        return _require_non_empty_str(operation, "columnId") and _require_non_empty_str(
            operation, "newTitle", max_length=80
        )

    if op_type == "create_card":
        ok1 = _require_non_empty_str(operation, "columnId")
        ok2 = _require_non_empty_str(operation, "title", max_length=160)
        if not (ok1[0] and ok2[0]):
            return ok1 if not ok1[0] else ok2
        details = operation.get("details", "")
        if not isinstance(details, str):
            return False, "create_card.details must be a string if provided."
        if len(details) > 2000:
            return False, "create_card.details exceeds max length 2000."
        return True, ""

    if op_type == "edit_card":
        ok = _require_non_empty_str(operation, "cardId")
        if not ok[0]:
            return ok

        has_title = "title" in operation
        has_details = "details" in operation
        if not has_title and not has_details:
            return False, "edit_card requires title and/or details."

        if has_title:
            ok_title = _require_non_empty_str(operation, "title", max_length=160)
            if not ok_title[0]:
                return ok_title

        if has_details:
            details = operation.get("details")
            if not isinstance(details, str):
                return False, "edit_card.details must be a string."
            if len(details) > 2000:
                return False, "edit_card.details exceeds max length 2000."

        return True, ""

    if op_type == "move_card":
        ok1 = _require_non_empty_str(operation, "cardId")
        ok2 = _require_non_empty_str(operation, "toColumnId")
        if not (ok1[0] and ok2[0]):
            return ok1 if not ok1[0] else ok2

        if "position" in operation:
            position = operation.get("position")
            if not isinstance(position, int) or position < 0:
                return False, "move_card.position must be an integer >= 0."
        return True, ""

    if op_type == "delete_card":
        return _require_non_empty_str(operation, "cardId")

    return False, "Unsupported operation type."


def _require_non_empty_str(
    payload: dict[str, object],
    key: str,
    *,
    max_length: int | None = None,
) -> tuple[bool, str]:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return False, f"{key} must be a non-empty string."
    if max_length is not None and len(value.strip()) > max_length:
        return False, f"{key} exceeds max length {max_length}."
    return True, ""
