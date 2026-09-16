from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.main import create_app


def _authed_client(tmp_path: Path) -> TestClient:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")

    db_path = tmp_path / "pm.db"
    client = TestClient(create_app(frontend_dist=dist_dir, db_path=db_path))
    client.post("/api/auth/login", data={"username": "user", "password": "password"})
    return client


def test_database_is_created_and_schema_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "pm.db"
    assert not db_path.exists()

    create_app(db_path=db_path)

    assert db_path.exists()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert "users" in tables
    assert "boards" in tables


def test_get_board_requires_authentication(tmp_path: Path) -> None:
    db_path = tmp_path / "pm.db"
    client = TestClient(create_app(db_path=db_path))

    response = client.get("/api/board")

    assert response.status_code == 401


def test_get_board_returns_seeded_board(tmp_path: Path) -> None:
    client = _authed_client(tmp_path)

    response = client.get("/api/board")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("columns"), list)
    assert isinstance(payload.get("cards"), dict)
    assert len(payload["columns"]) == 5


def test_put_board_rejects_invalid_payload(tmp_path: Path) -> None:
    client = _authed_client(tmp_path)

    response = client.put("/api/board", json={"not": "a-board"})

    assert response.status_code == 422


def test_put_board_persists_updates(tmp_path: Path) -> None:
    client = _authed_client(tmp_path)

    board = client.get("/api/board").json()
    board["columns"][0]["title"] = "Updated Backlog"

    update_response = client.put("/api/board", json=board)
    assert update_response.status_code == 200

    next_read = client.get("/api/board")
    assert next_read.status_code == 200
    assert next_read.json()["columns"][0]["title"] == "Updated Backlog"
