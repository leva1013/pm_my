from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.auth import SESSION_USER_KEY, credentials_valid, is_authenticated
from backend.app.login_page import render_login_page

router = APIRouter()


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    if is_authenticated(request.session):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(render_login_page())


@router.post("/api/auth/login")
async def login(request: Request):
    body = (await request.body()).decode("utf-8")
    form = parse_qs(body)
    username = form.get("username", [""])[0].strip()
    password = form.get("password", [""])[0]

    if not credentials_valid(username, password):
        return HTMLResponse(render_login_page(error=True), status_code=401)

    request.session[SESSION_USER_KEY] = username
    return RedirectResponse(url="/", status_code=303)


@router.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
