from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.main import create_app


def test_health_endpoint_returns_ok_payload() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pm-backend"}


def test_root_requires_authentication() -> None:
    client = TestClient(create_app())
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_page_renders_for_unauthenticated_user() -> None:
    client = TestClient(create_app())
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign in" in response.text


def test_login_failure_returns_401() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/auth/login",
        data={"username": "bad", "password": "creds"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_login_success_redirects_and_sets_session_cookie() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/auth/login",
        data={"username": "user", "password": "password"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "pm_session=" in response.headers.get("set-cookie", "")


def test_logout_clears_session_and_redirects() -> None:
    client = TestClient(create_app())
    client.post("/api/auth/login", data={"username": "user", "password": "password"})
    response = client.post("/api/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_root_returns_503_when_frontend_is_missing(tmp_path: Path) -> None:
    missing_dir = tmp_path / "not-built"
    client = TestClient(create_app(missing_dir))
    client.post("/api/auth/login", data={"username": "user", "password": "password"})

    response = client.get("/")

    assert response.status_code == 503
    assert response.json()["status"] == "frontend_not_built"


def test_root_serves_frontend_index_when_built(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><h1>Kanban Studio</h1></body></html>",
        encoding="utf-8",
    )

    client = TestClient(create_app(dist_dir))
    client.post("/api/auth/login", data={"username": "user", "password": "password"})
    response = client.get("/")

    assert response.status_code == 200
    assert "Kanban Studio" in response.text


def test_serves_next_static_assets_when_present(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    next_dir = dist_dir / "_next" / "static"
    next_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    (next_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")

    client = TestClient(create_app(dist_dir))
    client.post("/api/auth/login", data={"username": "user", "password": "password"})
    response = client.get("/_next/static/app.js")

    assert response.status_code == 200
    assert "console.log('ok');" in response.text
