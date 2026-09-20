from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from backend.app.auth import is_authenticated
from backend.app.paths import REPO_ROOT

router = APIRouter()


def resolve_frontend_dist(frontend_dist: Path | None = None) -> Path:
    if frontend_dist is not None:
        return frontend_dist

    candidates = [
        REPO_ROOT / "backend" / "frontend_dist",
        REPO_ROOT / "frontend" / "out",
    ]

    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate

    return candidates[0]


def _frontend_not_built_response() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "frontend_not_built",
            "detail": "Frontend static build not found. Build frontend and copy output to backend/frontend_dist.",
        },
    )


def _frontend_files(request: Request) -> tuple[Path, Path] | None:
    dist_dir = resolve_frontend_dist(request.app.state.frontend_dist)
    index_file = dist_dir / "index.html"
    if index_file.exists():
        return dist_dir, index_file
    return None


@router.get("/", include_in_schema=False)
def root(request: Request):
    if not is_authenticated(request.session):
        return RedirectResponse(url="/login", status_code=303)

    files = _frontend_files(request)
    if files is None:
        return _frontend_not_built_response()

    _, index_file = files
    return FileResponse(index_file)


@router.get("/{full_path:path}", include_in_schema=False)
def frontend_fallback(full_path: str, request: Request):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    if not is_authenticated(request.session):
        return RedirectResponse(url="/login", status_code=303)

    files = _frontend_files(request)
    if files is None:
        return _frontend_not_built_response()

    dist_dir, index_file = files
    dist_dir_resolved = dist_dir.resolve()
    requested_path = (dist_dir / full_path).resolve()
    if requested_path.is_relative_to(dist_dir_resolved) and requested_path.is_file():
        return FileResponse(requested_path)

    return FileResponse(index_file)
