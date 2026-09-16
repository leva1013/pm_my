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


def test_smoke_requires_authentication(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post("/api/ai/smoke")

    assert response.status_code == 401


def test_smoke_success_with_mocked_provider(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    client.post("/api/auth/login", data={"username": "user", "password": "password"})

    def fake_smoke() -> dict[str, str]:
        return {
            "model": "openai/gpt-oss-120b",
            "prompt": "What is 2+2? Reply with only the number.",
            "response": "4",
        }

    monkeypatch.setattr(main_module, "run_smoke_test", fake_smoke)
    response = client.post("/api/ai/smoke")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["response"] == "4"


def test_smoke_maps_missing_key_error(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    client.post("/api/auth/login", data={"username": "user", "password": "password"})

    def fake_smoke() -> dict[str, str]:
        raise AiClientError("missing_api_key", "OPENROUTER_API_KEY is not set.")

    monkeypatch.setattr(main_module, "run_smoke_test", fake_smoke)
    response = client.post("/api/ai/smoke")

    assert response.status_code == 500
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_smoke_maps_provider_errors(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    client.post("/api/auth/login", data={"username": "user", "password": "password"})

    def fake_smoke() -> dict[str, str]:
        raise AiClientError("provider_error", "Provider returned status 500")

    monkeypatch.setattr(main_module, "run_smoke_test", fake_smoke)
    response = client.post("/api/ai/smoke")

    assert response.status_code == 502
    assert "Provider returned status" in response.json()["detail"]
