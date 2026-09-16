def validate_board_payload(payload: object) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Board payload must be a JSON object."

    columns = payload.get("columns")
    cards = payload.get("cards")

    if not isinstance(columns, list):
        return False, "Field 'columns' must be an array."

    if not isinstance(cards, dict):
        return False, "Field 'cards' must be an object."

    card_ids = set()
    for card_key, card_value in cards.items():
        if not isinstance(card_key, str):
            return False, "All card keys must be strings."
        if not isinstance(card_value, dict):
            return False, "Each card must be an object."
        if card_value.get("id") != card_key:
            return False, "Each card object's id must match its key."
        if not isinstance(card_value.get("title"), str):
            return False, "Each card must include a string title."
        if not isinstance(card_value.get("details"), str):
            return False, "Each card must include a string details field."
        card_ids.add(card_key)

    seen_ids = set()
    for column in columns:
        if not isinstance(column, dict):
            return False, "Each column must be an object."
        if not isinstance(column.get("id"), str):
            return False, "Each column must include a string id."
        if not isinstance(column.get("title"), str):
            return False, "Each column must include a string title."
        column_card_ids = column.get("cardIds")
        if not isinstance(column_card_ids, list):
            return False, "Each column must include a cardIds array."

        for card_id in column_card_ids:
            if not isinstance(card_id, str):
                return False, "cardIds entries must be strings."
            if card_id not in card_ids:
                return False, "All cardIds entries must reference a card object."
            if card_id in seen_ids:
                return False, "A card id cannot appear in multiple columns."
            seen_ids.add(card_id)

    return True, ""
