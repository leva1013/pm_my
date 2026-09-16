from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

from backend.app.board_defaults import INITIAL_BOARD

DEFAULT_DB_RELATIVE_PATH = Path("backend") / "data" / "pm.db"


def resolve_db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return db_path
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / DEFAULT_DB_RELATIVE_PATH


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(db_path: Path | None = None) -> Path:
    resolved = resolve_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    with _connect(resolved) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                board_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CHECK (json_valid(board_json))
            )
            """
        )

        _ensure_user_and_board(connection, "user")
        connection.commit()

    return resolved


def _ensure_user_and_board(connection: sqlite3.Connection, username: str) -> int:
    connection.execute(
        """
        INSERT INTO users (username)
        VALUES (?)
        ON CONFLICT(username) DO NOTHING
        """,
        (username,),
    )

    user_id_row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user_id_row is None:
        raise RuntimeError("Unable to resolve user id after ensure.")

    user_id = int(user_id_row["id"])

    board_json = json.dumps(copy.deepcopy(INITIAL_BOARD))
    connection.execute(
        """
        INSERT INTO boards (user_id, board_json)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, board_json),
    )

    return user_id


def get_board_for_username(username: str, db_path: Path | None = None) -> dict:
    resolved = resolve_db_path(db_path)
    with _connect(resolved) as connection:
        user_id = _ensure_user_and_board(connection, username)
        board_row = connection.execute(
            "SELECT board_json FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        connection.commit()

    if board_row is None:
        raise RuntimeError("Board row missing after ensure.")

    return json.loads(board_row["board_json"])


def update_board_for_username(board: dict, username: str, db_path: Path | None = None) -> dict:
    resolved = resolve_db_path(db_path)
    with _connect(resolved) as connection:
        user_id = _ensure_user_and_board(connection, username)
        board_json = json.dumps(board)

        connection.execute(
            """
            UPDATE boards
            SET board_json = ?, updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            WHERE user_id = ?
            """,
            (board_json, user_id),
        )
        connection.commit()

    return board
