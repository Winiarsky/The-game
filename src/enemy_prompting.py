from __future__ import annotations

import re
from typing import Any

from board import consts

_NUMBER_RE = re.compile(r"(?<!\*)\b([+-]?\d+)\b(?!\*)")


def emphasize_numbers(text: str | None) -> str:
    raw = str(text or "")
    return _NUMBER_RE.sub(r"**\1**", raw)


def enemy_prompt_step(
    game,
    title: str,
    *,
    prompt_long: str | None = None,
    source: str = "enemy_turn",
    log_message: str | None = None,
) -> None:
    """Pokaż blokujący prompt dla akcji przeciwnika, a log traktuj wtórnie."""
    text = emphasize_numbers(str(prompt_long or "").strip())
    message = str(log_message or title or "").strip()
    if message and hasattr(game, "ui_log"):
        try:
            game.ui_log(message)
        except Exception:
            pass
    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
        try:
            ui.prompt_info(str(title or "Przeciwnik"), prompt_long=text or None, source=source)
            return
        except Exception:
            pass
    conn = getattr(game, "conn", None)
    reader = getattr(conn, "read_card", None)
    if callable(reader):
        try:
            reader(text or str(title or "Przeciwnik"), source=source)
        except Exception:
            pass


def enemy_highlight(game, positions: list[tuple[int, int]], colors=None) -> None:
    if not positions:
        return
    if colors is None:
        colors = [consts.ENEMY_START_RGB for _ in positions]
    try:
        conn = getattr(game, "conn", None)
        if conn is not None and hasattr(conn, "set_leds"):
            conn.set_leds(positions, colors)
    except Exception:
        pass


def clear_enemy_highlight(game) -> None:
    try:
        conn = getattr(game, "conn", None)
        if conn is not None and hasattr(conn, "leds_off"):
            conn.leds_off()
    except Exception:
        pass


def format_roll_components(components: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None) -> str:
    if not components:
        return "Brak dodatkowych modyfikatorów."
    lines: list[str] = []
    for item in list(components or []):
        label = str(item.get("label", "Modyfikator") or "Modyfikator").strip()
        try:
            value = int(item.get("value", 0) or 0)
        except Exception:
            value = 0
        description = str(item.get("description", "") or "").strip()
        sign = "+" if value >= 0 else ""
        line = f"- {label}: **{sign}{value}**"
        if description:
            line = f"{line} ({description})"
        lines.append(line)
    return "\n".join(lines)
