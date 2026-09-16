# Database schema proposal (Part 5)

## Goals

- Support multiple users in schema while MVP login remains fixed to one credential.
- Store exactly one board per user for MVP.
- Persist the full board payload as JSON in SQLite.
- Keep schema minimal and easy to migrate.

## Proposed SQLite tables

### users

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

### boards

```sql
CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  board_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CHECK (json_valid(board_json))
);
```

## Why this shape

- `users.username` is unique for future multi-user support.
- `boards.user_id UNIQUE` enforces one board per user at the DB level.
- `board_json` stores the full Kanban payload exactly as used by frontend/backend contracts.
- `CHECK (json_valid(board_json))` ensures only valid JSON is persisted.

## JSON payload contract (initial)

The persisted JSON document in `boards.board_json` will match this shape:

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "Example", "details": "Text" }
  }
}
```

## Bootstrap/migration strategy

1. On backend startup, create DB file if missing.
2. Run `CREATE TABLE IF NOT EXISTS` statements for `users` and `boards`.
3. Ensure MVP user row exists: `username = 'user'`.
4. Ensure that user has one board row; if absent, insert with initial board JSON.

## Access pattern for Part 6

- Read board:
  - Resolve session username to `users.id`.
  - `SELECT board_json FROM boards WHERE user_id = ?`.
- Update board:
  - Validate JSON payload shape in app layer.
  - `UPDATE boards SET board_json = ?, updated_at = now WHERE user_id = ?`.

## Non-goals for MVP

- No board history/versioning table.
- No optimistic locking/version field yet.
- No per-card relational modeling yet (board remains JSON document).
