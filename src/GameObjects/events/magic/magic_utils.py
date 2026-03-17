from __future__ import annotations

from combat.stealth_runtime import has_status_id

from ..targeting import pick_target_or_guess_square


def grid_distance_feet(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Police dystans w stopach przy zasadzie przekątnej 5/10 stóp."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    diag = min(dx, dy)
    straight = abs(dx - dy)
    diag_cost = 5 * (diag + diag // 2)  # 1st diagonal 5, 2nd 10 (sum 15), 3rd 5, ...
    return diag_cost + straight * 5


def pick_target_in_range(
    ctx,
    source_pos: tuple[int, int],
    candidates: list[tuple[object, tuple[int, int], str]],
    *,
    max_range_feet: int | None,
    allowed_kinds: tuple[str, ...] = ("enemy", "hero"),
    tags: list[str] | None = None,
    allow_guess_undetected: bool = False,
    return_selection_details: bool = False,
):
    """Zwróć (target, pos) jeśli gracz wybierze cel w zasięgu i dozwolonego typu.

    candidates: lista (obj, pos, kind) gdzie kind to "enemy" lub "hero".
    Jeśli brak validów, klik na własne pole lub wybór spoza listy -> (None, None).
    """

    if not source_pos:
        return None, None

    from GameObjects.events.targeting import is_target_blocked_by_tags

    valid: list[tuple[object, tuple[int, int], str, int]] = []
    for obj, pos, kind in candidates:
        if pos is None or kind not in allowed_kinds:
            continue
        if is_target_blocked_by_tags(obj, tags):
            continue
        if max_range_feet is not None:
            dist = grid_distance_feet(source_pos, pos)
            if dist > max_range_feet:
                continue
        else:
            dist = grid_distance_feet(source_pos, pos)
        valid.append((obj, pos, kind, dist))

    if not valid:
        if return_selection_details:
            return {"kind": "cancel"}
        return None, None

    if allow_guess_undetected and any(has_status_id(obj, "undetected") for obj, _pos, _kind, _dist in valid):
        selection = pick_target_or_guess_square(
            ctx,
            source_pos,
            [(obj, pos, kind) for obj, pos, kind, _dist in valid],
            max_range_feet=max_range_feet,
            allowed_kinds=allowed_kinds,
            tags=tags,
        )
        if return_selection_details:
            return selection
        if selection.get("kind") == "target":
            return selection.get("target"), selection.get("pos")
        return None, None

    positions = [pos for _, pos, _, _ in valid]
    try:
        ctx.game.conn.set_leds(positions, [[0, 80, 180] for _ in positions])
    except Exception:
        pass

    choice = None
    try:
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
        if return_selection_details:
            return {"kind": "cancel"}
        return None, None

    for obj, pos, kind, _dist in valid:
        if pos == choice:
            if return_selection_details:
                return {"kind": "target", "target": obj, "pos": pos, "guessed": False}
            return obj, pos
    if return_selection_details:
        return {"kind": "cancel"}
    return None, None


def positions_within_range(board, source_pos: tuple[int, int], max_range_feet: int | None) -> list[tuple[int, int]]:
    if source_pos is None:
        return []
    positions: list[tuple[int, int]] = []
    rows = getattr(board, "rows", 0) or 0
    cols = getattr(board, "cols", 0) or 0
    for row in range(rows):
        for col in range(cols):
            pos = (col, row)
            if max_range_feet is None or grid_distance_feet(source_pos, pos) <= max_range_feet:
                positions.append(pos)
    return positions


def pick_position_in_range(
    ctx,
    source_pos: tuple[int, int],
    *,
    max_range_feet: int | None,
    color: list[int] | None = None,
) -> tuple[int, int] | None:
    """Pozwól wybrać pozycję na planszy w zasięgu."""
    if source_pos is None:
        return None
    positions = positions_within_range(ctx.game.board, source_pos, max_range_feet)
    if not positions:
        return None
    if color is None:
        color = [0, 80, 180]
    try:
        ctx.game.conn.set_leds(positions, [color for _ in positions])
        choice = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    if choice in positions:
        return choice
    return None
