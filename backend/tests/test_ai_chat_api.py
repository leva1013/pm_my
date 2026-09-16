from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import backend.app.main as main_module
from backend.app.ai_client import AiClientError
from backend.app.main import create_app


def _client(tmp_path: Path) -> TestClient:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")

    db_path = tmp_path / "pm.db"
    return TestClient(create_app(frontend_dist=dist_dir, db_path=db_path))


def _login(client: TestClient) -> None:
    client.post("/api/auth/login", data={"username": "user", "password": "password"})


def test_chat_requires_authentication(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post("/api/ai/chat", json={"message": "hi", "history": []})
    assert response.status_code == 401


def test_chat_rejects_bad_request_shape(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "", "history": []})
    assert response.status_code == 422


def test_chat_noop_response_keeps_board(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    def fake_structured(**kwargs):
        return {
            "assistantMessage": "No changes needed.",
            "shouldUpdateBoard": False,
            "operations": [],
        }

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)

    before = client.get("/api/board").json()
    response = client.post("/api/ai/chat", json={"message": "status?", "history": []})
    after = client.get("/api/board").json()

    assert response.status_code == 200
    assert response.json()["assistantMessage"] == "No changes needed."
    assert response.json()["appliedOperations"] == []
    assert before == after


def test_chat_applies_and_persists_valid_operations(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    def fake_structured(**kwargs):
        return {
            "assistantMessage": "I renamed backlog.",
            "shouldUpdateBoard": True,
            "operations": [
                {
                    "type": "rename_column",
                    "columnId": "col-backlog",
                    "newTitle": "Ideas",
                }
            ],
        }

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)
    response = client.post("/api/ai/chat", json={"message": "rename backlog", "history": []})

    assert response.status_code == 200
    assert response.json()["board"]["columns"][0]["title"] == "Ideas"

    read_again = client.get("/api/board")
    assert read_again.status_code == 200
    assert read_again.json()["columns"][0]["title"] == "Ideas"


def test_chat_rejects_invalid_ai_structure(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    def fake_structured(**kwargs):
        return {
            "assistantMessage": "Bad",
            "shouldUpdateBoard": False,
            "operations": [{"type": "delete_card", "cardId": "card-1"}],
        }

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)
    response = client.post("/api/ai/chat", json={"message": "bad", "history": []})

    assert response.status_code == 502


def test_chat_maps_ai_client_errors(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    def fake_structured(**kwargs):
        raise AiClientError("network_error", "Network error")

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)
    response = client.post("/api/ai/chat", json={"message": "hello", "history": []})

    assert response.status_code == 502


def test_chat_rejects_invalid_semantic_ops(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    def fake_structured(**kwargs):
        return {
            "assistantMessage": "Will move missing card.",
            "shouldUpdateBoard": True,
            "operations": [
                {
                    "type": "move_card",
                    "cardId": "missing-card",
                    "toColumnId": "col-review",
                }
            ],
        }

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)
    response = client.post("/api/ai/chat", json={"message": "move it", "history": []})

    assert response.status_code == 422


def test_chat_deduplicates_trailing_user_message(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _login(client)

    captured_history: list[dict[str, str]] | None = None

    def fake_structured(**kwargs):
        nonlocal captured_history
        captured_history = kwargs["history"]
        return {
            "assistantMessage": "No update.",
            "shouldUpdateBoard": False,
            "operations": [],
        }

    monkeypatch.setattr(main_module, "call_openrouter_structured", fake_structured)

    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Rename backlog",
            "history": [{"role": "user", "content": "Rename backlog"}],
        },
    )

    assert response.status_code == 200
    assert captured_history == []
