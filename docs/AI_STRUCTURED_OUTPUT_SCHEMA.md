# Part 9 Structured Output Schema Proposal

## Goal

Define a strict AI response contract for chat that:

- always returns assistant text for the user
- optionally returns board mutations
- is safe to validate and apply deterministically

This proposal is for approval only. No implementation details are assumed beyond this contract.

## Top-level response shape

```json
{
  "assistantMessage": "string",
  "shouldUpdateBoard": true,
  "operations": [
    {
      "type": "rename_column",
      "columnId": "col-backlog",
      "newTitle": "Ideas"
    }
  ]
}
```

### Field rules

- `assistantMessage`:
  - required
  - non-empty string
  - shown in chat UI directly
- `shouldUpdateBoard`:
  - required boolean
  - if `false`, `operations` must be empty
- `operations`:
  - required array
  - may be empty
  - max length: 50
  - applied in order, atomically

## Allowed operation types

Only these operations are allowed in MVP:

1. `rename_column`
2. `create_card`
3. `edit_card`
4. `move_card`
5. `delete_card`

### 1) rename_column

```json
{
  "type": "rename_column",
  "columnId": "col-backlog",
  "newTitle": "Ideas"
}
```

Rules:

- `columnId` must exist
- `newTitle` non-empty, max 80 chars (trimmed)

### 2) create_card

```json
{
  "type": "create_card",
  "columnId": "col-progress",
  "title": "Draft release checklist",
  "details": "Cover testing and rollout steps"
}
```

Rules:

- `columnId` must exist
- `title` non-empty, max 160 chars
- `details` optional string, max 2000 chars
- backend generates card id
- new card is appended to target column

### 3) edit_card

```json
{
  "type": "edit_card",
  "cardId": "card-5",
  "title": "Design card layout v2",
  "details": "Improve spacing for dense boards"
}
```

Rules:

- `cardId` must exist
- `title` optional, if provided non-empty and max 160 chars
- `details` optional, if provided max 2000 chars
- at least one of `title` or `details` must be present

### 4) move_card

```json
{
  "type": "move_card",
  "cardId": "card-1",
  "toColumnId": "col-review",
  "position": 0
}
```

Rules:

- `cardId` must exist
- `toColumnId` must exist
- `position` optional integer `>=0`
- if `position` missing or out of range, append to end
- moving within same column is allowed

### 5) delete_card

```json
{
  "type": "delete_card",
  "cardId": "card-8"
}
```

Rules:

- `cardId` must exist
- remove card object and remove id from its column

## JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pm.local/schemas/ai-board-response.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["assistantMessage", "shouldUpdateBoard", "operations"],
  "properties": {
    "assistantMessage": {
      "type": "string",
      "minLength": 1,
      "maxLength": 4000
    },
    "shouldUpdateBoard": {
      "type": "boolean"
    },
    "operations": {
      "type": "array",
      "maxItems": 50,
      "items": {
        "oneOf": [
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "columnId", "newTitle"],
            "properties": {
              "type": { "const": "rename_column" },
              "columnId": { "type": "string", "minLength": 1 },
              "newTitle": { "type": "string", "minLength": 1, "maxLength": 80 }
            }
          },
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "columnId", "title"],
            "properties": {
              "type": { "const": "create_card" },
              "columnId": { "type": "string", "minLength": 1 },
              "title": { "type": "string", "minLength": 1, "maxLength": 160 },
              "details": { "type": "string", "maxLength": 2000 }
            }
          },
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "cardId"],
            "properties": {
              "type": { "const": "edit_card" },
              "cardId": { "type": "string", "minLength": 1 },
              "title": { "type": "string", "minLength": 1, "maxLength": 160 },
              "details": { "type": "string", "maxLength": 2000 }
            },
            "anyOf": [
              { "required": ["title"] },
              { "required": ["details"] }
            ]
          },
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "cardId", "toColumnId"],
            "properties": {
              "type": { "const": "move_card" },
              "cardId": { "type": "string", "minLength": 1 },
              "toColumnId": { "type": "string", "minLength": 1 },
              "position": { "type": "integer", "minimum": 0 }
            }
          },
          {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "cardId"],
            "properties": {
              "type": { "const": "delete_card" },
              "cardId": { "type": "string", "minLength": 1 }
            }
          }
        ]
      }
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "shouldUpdateBoard": { "const": false }
        },
        "required": ["shouldUpdateBoard"]
      },
      "then": {
        "properties": {
          "operations": { "maxItems": 0 }
        }
      }
    }
  ]
}
```

## Execution semantics

- Backend sends model:
  - current board JSON
  - conversation history
  - latest user message
  - explicit instruction to return only this schema
- Backend validates full response against schema
- If schema validation fails:
  - do not update board
  - return assistant fallback message and error-safe response
- If schema validation passes:
  - apply operations in order to current board
  - if any operation fails semantic checks (missing id, invalid position handling exception), reject entire mutation set
  - persist resulting board atomically

## Example responses

### A) Chat only, no board change

```json
{
  "assistantMessage": "You currently have 3 items in progress. I recommend finishing the review card first.",
  "shouldUpdateBoard": false,
  "operations": []
}
```

### B) Chat + multi-operation board update

```json
{
  "assistantMessage": "I renamed Backlog to Ideas and added a new card in In Progress.",
  "shouldUpdateBoard": true,
  "operations": [
    {
      "type": "rename_column",
      "columnId": "col-backlog",
      "newTitle": "Ideas"
    },
    {
      "type": "create_card",
      "columnId": "col-progress",
      "title": "Prepare demo narrative",
      "details": "Focus on customer pain points and outcomes"
    }
  ]
}
```

## Suggested response payload from backend chat endpoint

For Part 9 endpoint responses back to frontend:

```json
{
  "assistantMessage": "string",
  "appliedOperations": [
    { "type": "rename_column", "columnId": "col-backlog", "newTitle": "Ideas" }
  ],
  "board": {
    "columns": [],
    "cards": {}
  }
}
```

This keeps frontend state updates deterministic.

## Approval checklist

- [ ] Operation types are correct for MVP scope
- [ ] Field names and limits are acceptable
- [ ] Atomic all-or-nothing mutation behavior is acceptable
- [ ] Backend response shape to frontend is acceptable
