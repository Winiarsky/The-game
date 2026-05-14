from __future__ import annotations

from typing import Any


def expand_room_positions(payload: dict[str, Any]) -> dict[str, Any]:
    """Expand compact room position helpers into explicit board coordinates."""
    rooms = payload.get("rooms")
    if not isinstance(rooms, list):
        return payload
    for room in rooms:
        if not isinstance(room, dict):
            continue
        if room.get("positions"):
            continue
        if bool(room.get("full_board")):
            room["positions"] = [[x, y] for y in range(30) for x in range(20)]
            continue
        rect = room.get("positions_rect")
        if isinstance(rect, list) and len(rect) == 4:
            try:
                x1, y1, x2, y2 = [int(value) for value in rect]
            except Exception:
                continue
            room["positions"] = [[x, y] for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)]
    return payload
