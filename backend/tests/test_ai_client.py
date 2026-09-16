from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.ai_client import AiClientError, call_openrouter, call_openrouter_structured


def test_call_openrouter_builds_request_and_extracts_content() -> None:
    captured: dict[str, object] = {}

    def fake_request(url: str, headers: dict, payload: dict, timeout: float) -> dict:
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": "4",
                    }
                }
            ]
        }

    result = call_openrouter(
        prompt="What is 2+2?",
        api_key="test-key",
        request_fn=fake_request,
    )

    assert result == "4"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert isinstance(captured["headers"], dict)
    assert isinstance(captured["payload"], dict)


def test_call_openrouter_rejects_missing_key() -> None:
    try:
        call_openrouter(prompt="What is 2+2?", api_key="")
    except AiClientError as exc:
        assert exc.code == "missing_api_key"
        return

    raise AssertionError("Expected missing_api_key error")


def test_call_openrouter_rejects_invalid_response_shape() -> None:
    def fake_request(url: str, headers: dict, payload: dict, timeout: float) -> dict:
        return {"choices": []}

    try:
        call_openrouter(
            prompt="What is 2+2?",
            api_key="test-key",
            request_fn=fake_request,
        )
    except AiClientError as exc:
        assert exc.code == "invalid_response"
        return

    raise AssertionError("Expected invalid_response error")


def test_call_openrouter_structured_builds_history_and_board_prompt() -> None:
    captured: dict[str, object] = {}

    def fake_request(url: str, headers: dict, payload: dict, timeout: float) -> dict:
        captured["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"assistantMessage":"ok","shouldUpdateBoard":false,"operations":[]}',
                    }
                }
            ]
        }

    result = call_openrouter_structured(
        board={"columns": [], "cards": {}},
        history=[{"role": "user", "content": "hello"}],
        user_message="summarize",
        api_key="test-key",
        request_fn=fake_request,
    )

    assert result["assistantMessage"] == "ok"
    assert result["shouldUpdateBoard"] is False
    assert isinstance(captured["payload"], dict)
    messages = captured["payload"]["messages"]
    assert messages[-1]["content"] == "summarize"


def test_call_openrouter_structured_rejects_non_json_content() -> None:
    def fake_request(url: str, headers: dict, payload: dict, timeout: float) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": "not-json",
                    }
                }
            ]
        }

    try:
        call_openrouter_structured(
            board={"columns": [], "cards": {}},
            history=[],
            user_message="test",
            api_key="test-key",
            request_fn=fake_request,
        )
    except AiClientError as exc:
        assert exc.code == "invalid_response"
        return

    raise AssertionError("Expected invalid_response error")
