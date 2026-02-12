from __future__ import annotations


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
):
    """Zwróć (target, pos) jeśli gracz wybierze cel w zasięgu i dozwolonego typu.

    candidates: lista (obj, pos, kind) gdzie kind to "enemy" lub "hero".
    Jeśli brak validów, klik na własne pole lub wybór spoza listy -> (None, None).
    """

    if not source_pos:
        return None, None

    valid: list[tuple[object, tuple[int, int], str, int]] = []
    for obj, pos, kind in candidates:
        if pos is None or kind not in allowed_kinds:
            continue
        if max_range_feet is not None:
            dist = grid_distance_feet(source_pos, pos)
            if dist > max_range_feet:
                continue
        else:
            dist = grid_distance_feet(source_pos, pos)
        valid.append((obj, pos, kind, dist))

    if not valid:
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
        return None, None

    for obj, pos, kind, _dist in valid:
        if pos == choice:
            return obj, pos
    return None, None
