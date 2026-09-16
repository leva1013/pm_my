VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_USER_KEY = "username"


def credentials_valid(username: str, password: str) -> bool:
    return username == VALID_USERNAME and password == VALID_PASSWORD


def is_authenticated(session: dict | None) -> bool:
    if not session:
        return False
    return session.get(SESSION_USER_KEY) == VALID_USERNAME


def session_username(session: dict | None) -> str | None:
    if not session:
        return None

    username = session.get(SESSION_USER_KEY)
    if not isinstance(username, str) or not username:
        return None

    return username
