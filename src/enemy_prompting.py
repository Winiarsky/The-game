from __future__ import annotations

import re
from typing import Any

from board import consts
from communication import make_enemy_turn_communication

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
    blocking: bool = True,
    semantic_type: str | None = None,
    dedupe_key: str | None = None,
    next_hint: str | None = None,
    continue_hint: str | None = None,
    communication: dict[str, Any] | None = None,
    emit_log: bool | None = None,
) -> None:
    """Pokaż blokujący prompt dla akcji przeciwnika, a log traktuj wtórnie."""
    text = emphasize_numbers(str(prompt_long or "").strip())
    message = str(log_message or title or "").strip()
    effective_emit_log = bool(emit_log) if emit_log is not None else not bool(blocking)
    effective_semantic = str(semantic_type or ("required_action" if blocking else "status_update"))
    envelope = dict(communication or {}) or make_enemy_turn_communication(
        title=str(title or "Przeciwnik"),
        body_markdown=text or message or str(title or "Przeciwnik"),
        dedupe_key=str(dedupe_key or source or title or "enemy"),
        blocking=blocking,
        semantic_type=effective_semantic,
        next_hint=next_hint,
        continue_hint=continue_hint,
    )
    if effective_emit_log and message and hasattr(game, "ui_log"):
        try:
            game.ui_log(message, communication=envelope)
        except Exception:
            pass
    if not blocking:
        return
    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
        try:
            ui.prompt_info(
                str(title or "Przeciwnik"),
                prompt_long=text or None,
                source=source,
                communication=envelope,
            )
            return
        except Exception:
            pass
    if message and not effective_emit_log and hasattr(game, "ui_log"):
        try:
            game.ui_log(message, communication=envelope)
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
