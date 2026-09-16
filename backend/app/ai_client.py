from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from backend.app.ai_structured import structured_output_schema

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


@dataclass
class AiClientError(Exception):
    code: str
    message: str


def _build_payload(prompt: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }


def _extract_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AiClientError("invalid_response", "Provider response missing choices array.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise AiClientError("invalid_response", "Provider response choice is invalid.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise AiClientError("invalid_response", "Provider response message is invalid.")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AiClientError("invalid_response", "Provider response content is missing.")

    return content.strip()


def _extract_json_response(response_json: dict[str, Any]) -> dict[str, Any]:
    text = _extract_text(response_json)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AiClientError("invalid_response", f"Structured response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AiClientError("invalid_response", "Structured response must be a JSON object.")

    return parsed


def _default_request(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise AiClientError(
            "provider_error",
            f"Provider returned status {response.status_code}: {response.text}",
        )

    return response.json()


def call_openrouter(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    url: str = OPENROUTER_URL,
    request_fn: Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]] | None = None,
) -> str:
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise AiClientError("missing_api_key", "OPENROUTER_API_KEY is not set.")

    payload = _build_payload(prompt=prompt, model=model)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    request_impl = request_fn or _default_request
    try:
        raw_response = request_impl(url, headers, payload, 30.0)
    except AiClientError:
        raise
    except httpx.HTTPError as exc:
        raise AiClientError("network_error", f"Network error: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise AiClientError("provider_error", f"Unexpected provider error: {exc}") from exc

    return _extract_text(raw_response)


def run_smoke_test() -> dict[str, str]:
    prompt = "What is 2+2? Reply with only the number."
    response_text = call_openrouter(prompt=prompt)

    return {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "response": response_text,
    }


def call_openrouter_structured(
    *,
    board: dict[str, Any],
    history: list[dict[str, str]],
    user_message: str,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    url: str = OPENROUTER_URL,
    request_fn: Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise AiClientError("missing_api_key", "OPENROUTER_API_KEY is not set.")

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a project management assistant for a Kanban board. "
                "Respond only with JSON that matches the provided schema. "
                "If shouldUpdateBoard is true, every required operation field must be a non-empty string "
                "and must reference valid IDs from the current board. "
                "If you are uncertain, set shouldUpdateBoard to false and return operations as an empty array."
            ),
        },
        {
            "role": "system",
            "content": f"Current board JSON: {json.dumps(board)}",
        },
    ]

    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role not in {"user", "assistant", "system"}:
            role = "user"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "pm_ai_board_response",
                "strict": True,
                "schema": structured_output_schema(),
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    request_impl = request_fn or _default_request
    try:
        raw_response = request_impl(url, headers, payload, 45.0)
    except AiClientError:
        raise
    except httpx.HTTPError as exc:
        raise AiClientError("network_error", f"Network error: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise AiClientError("provider_error", f"Unexpected provider error: {exc}") from exc

    return _extract_json_response(raw_response)
