from __future__ import annotations

import math

from board import consts
from combat.stealth_runtime import has_status_id
from .base import emit_prompt_narration, format_board_selection_message


def _has_status(target, status_id: str) -> bool:
    has_status = getattr(target, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    statuses = getattr(target, "statuses", None)
    if not statuses:
        return False
    for status in statuses:
        if getattr(status, "id", None) == status_id:
            return True
    return False


def is_target_blocked_by_tags(target, tags: list[str] | tuple[str, ...] | None) -> bool:
    if not tags:
        return False
    statuses = getattr(target, "statuses", None) or []
    for status in statuses:
        data = getattr(status, "data", None) or {}
        immune_tags = set(data.get("immune_status_tags", []) or [])
        if immune_tags and immune_tags.intersection(tags):
            return True
    return False


def grid_distance_feet(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Police dystans w stopach przy zasadzie przekątnej 5/10 stóp."""

    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    diag = min(dx, dy)
    straight = abs(dx - dy)
    diag_cost = 5 * (diag + diag // 2)
    return diag_cost + straight * 5


def positions_within_range(
    board,
    source_pos: tuple[int, int],
    max_range_feet: int | None,
) -> list[tuple[int, int]]:
    if source_pos is None:
        return []

    rows = getattr(board, "rows", 0) or 0
    cols = getattr(board, "cols", 0) or 0
    if rows and cols:
        positions: list[tuple[int, int]] = []
        for row in range(rows):
            for col in range(cols):
                pos = (col, row)
                if max_range_feet is None or grid_distance_feet(source_pos, pos) <= max_range_feet:
                    positions.append(pos)
        return positions

    if max_range_feet is None:
        return []

    try:
        cells = max(1, int(math.ceil(float(max_range_feet) / 5.0)))
    except Exception:
        cells = 1
    positions = []
    for dx in range(-cells, cells + 1):
        for dy in range(-cells, cells + 1):
            pos = (source_pos[0] + dx, source_pos[1] + dy)
            if grid_distance_feet(source_pos, pos) <= max_range_feet:
                positions.append(pos)
    return positions


def pick_target_or_guess_square(
    ctx,
    source_pos: tuple[int, int],
    candidates: list[tuple[object, tuple[int, int], str]],
    *,
    max_range_feet: int | None,
    allowed_kinds: tuple[str, ...] = ("enemy", "hero"),
    tags: list[str] | None = None,
    guess_positions: list[tuple[int, int]] | None = None,
    target_color: list[int] | None = None,
    guess_color: list[int] | None = None,
) -> dict:
    """Pozwól wybrać normalny cel albo zgadnąć pole dla celu `undetected`.

    Zwraca słownik:
    - {"kind": "target", "target": obj, "pos": pos, "guessed": bool}
    - {"kind": "miss", "pos": guessed_pos, "guessed": True}
    - {"kind": "cancel"}
    """

    if not source_pos:
        return {"kind": "cancel"}

    valid: list[tuple[object, tuple[int, int], str]] = []
    for obj, pos, kind in list(candidates or []):
        if pos is None or kind not in allowed_kinds:
            continue
        if is_target_blocked_by_tags(obj, tags):
            continue
        if max_range_feet is not None and grid_distance_feet(source_pos, pos) > max_range_feet:
            continue
        valid.append((obj, pos, kind))

    if not valid:
        return {"kind": "cancel"}

    emit_prompt_narration(
        ctx.game,
        format_board_selection_message(
            "podswietlony cel albo pole do zgadniecia",
            max_range_feet=max_range_feet,
            alternative="Jesli przeciwnik jest niewykryty, mozesz wskazac jego pole na chybil trafil",
        ),
        source="targeting:pick_target_or_guess",
        dedupe_key="targeting:pick_target_or_guess:start",
        next_hint="Kliknij wybrany cel albo pole do zgadniecia na planszy.",
        input_mode="board_click",
        cancel_enabled=True,
        confirm_enabled=False,
    )

    visible: list[tuple[object, tuple[int, int], str]] = []
    undetected: list[tuple[object, tuple[int, int], str]] = []
    for obj, pos, kind in valid:
        if has_status_id(obj, "undetected"):
            undetected.append((obj, pos, kind))
        else:
            visible.append((obj, pos, kind))

    if not undetected:
        return {"kind": "cancel"}

    if target_color is None:
        target_color = [0, 80, 180]
    if guess_color is None:
        guess_color = list(consts.HIDDEN_REVEAL_RGB)

    if guess_positions is None:
        guess_positions = positions_within_range(getattr(ctx.game, "board", None), source_pos, max_range_feet)
    normalized_guess_positions = []
    seen_guess = set()
    for pos in list(guess_positions or []):
        normalized = tuple(pos)
        if normalized in seen_guess:
            continue
        seen_guess.add(normalized)
        normalized_guess_positions.append(normalized)

    if not normalized_guess_positions:
        return {"kind": "cancel"}

    led_map: dict[tuple[int, int], list[int]] = {}
    for pos in normalized_guess_positions:
        led_map[pos] = list(guess_color)
    for _obj, pos, _kind in visible:
        led_map[tuple(pos)] = list(target_color)

    if not led_map:
        return {"kind": "cancel"}

    positions = list(led_map.keys())
    colors = [led_map[pos] for pos in positions]

    choice = None
    try:
        try:
            ctx.game.conn.set_leds(positions, colors)
        except Exception:
            pass
        try:
            choice = ctx.game.conn.scan_board(positions)
        except Exception:
            choice = None
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass

    if choice is None or choice == source_pos:
        try:
            ctx.game.conn.cancel_scan()
        except Exception:
            pass
        return {"kind": "cancel"}

    for obj, pos, _kind in visible:
        if tuple(pos) == tuple(choice):
            player_prompt = getattr(ctx.game, "player_prompt", None)
            if player_prompt is not None and hasattr(player_prompt, "cancel_scope"):
                try:
                    player_prompt.cancel_scope("hero_turn:targeting")
                except Exception:
                    pass
            return {"kind": "target", "target": obj, "pos": tuple(pos), "guessed": False}
    for obj, pos, _kind in undetected:
        if tuple(pos) == tuple(choice):
            player_prompt = getattr(ctx.game, "player_prompt", None)
            if player_prompt is not None and hasattr(player_prompt, "cancel_scope"):
                try:
                    player_prompt.cancel_scope("hero_turn:targeting")
                except Exception:
                    pass
            return {"kind": "target", "target": obj, "pos": tuple(pos), "guessed": True}
    if tuple(choice) in seen_guess:
        player_prompt = getattr(ctx.game, "player_prompt", None)
        if player_prompt is not None and hasattr(player_prompt, "cancel_scope"):
            try:
                player_prompt.cancel_scope("hero_turn:targeting")
            except Exception:
                pass
        return {"kind": "miss", "pos": tuple(choice), "guessed": True}
    return {"kind": "cancel"}
