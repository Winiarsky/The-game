from __future__ import annotations

import time

from board import consts


def _line_cells(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    cells: list[tuple[int, int]] = []
    while True:
        cells.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return cells


def _normalize_color(color: list[int] | tuple[int, int, int] | None, *, fallback: list[int]) -> list[int]:
    if not color:
        return list(fallback)
    values = [max(0, min(255, int(component))) for component in list(color)[:3]]
    while len(values) < 3:
        values.append(0)
    return values


def _scaled_color(color: list[int], factor: float) -> list[int]:
    factor = max(0.0, min(1.0, float(factor)))
    return [max(0, min(255, int(round(component * factor)))) for component in color[:3]]


def _normalize_palette(
    palette: list[list[int] | tuple[int, int, int]] | tuple[list[int] | tuple[int, int, int], ...] | None,
) -> list[list[int]]:
    normalized: list[list[int]] = []
    for color in list(palette or []):
        normalized.append(_normalize_color(color, fallback=[220, 220, 220]))
    return normalized


def _grid_steps_from(origin: tuple[int, int], pos: tuple[int, int]) -> int:
    return max(abs(int(pos[0]) - int(origin[0])), abs(int(pos[1]) - int(origin[1])))


def _supports_led_fx(conn) -> bool:
    if conn is None:
        return False
    if bool(getattr(conn, "enable_led_fx", False)):
        return True
    backend = str(getattr(conn, "backend", "") or "").strip().lower()
    return backend in {"hardware", "simulator"}


def animate_projectile_line(
    conn,
    start: tuple[int, int] | None,
    end: tuple[int, int] | None,
    *,
    trail_color: list[int] | tuple[int, int, int] | None = None,
    head_color: list[int] | tuple[int, int, int] | None = None,
    impact_color: list[int] | tuple[int, int, int] | None = None,
    palette: list[list[int] | tuple[int, int, int]] | tuple[list[int] | tuple[int, int, int], ...] | None = None,
    frame_delay_s: float | None = None,
    impact_hold_s: float | None = None,
    sleep_fn=time.sleep,
) -> bool:
    if not _supports_led_fx(conn) or start is None or end is None:
        return False

    path = _line_cells(tuple(start), tuple(end))
    if not path:
        return False

    trail_rgb = _normalize_color(trail_color, fallback=[50, 50, 50])
    head_rgb = _normalize_color(head_color, fallback=[220, 220, 220])
    palette_rgb = _normalize_palette(palette)
    impact_fallback = palette_rgb[-1] if palette_rgb else head_rgb
    impact_rgb = _normalize_color(impact_color, fallback=impact_fallback)
    dim_trail = _scaled_color(trail_rgb, 0.6)
    if frame_delay_s is None:
        frame_delay_s = float(getattr(consts, "PROJECTILE_LED_STEP_DELAY_S", 0.06) or 0.06)
    if impact_hold_s is None:
        impact_hold_s = float(getattr(consts, "PROJECTILE_LED_IMPACT_HOLD_S", 0.1) or 0.1)

    try:
        for idx in range(len(path)):
            lit_positions = list(path[: idx + 1])
            if palette_rgb:
                lit_colors = [_scaled_color(palette_rgb[pos_idx % len(palette_rgb)], 0.45) for pos_idx in range(len(lit_positions))]
                lit_colors[-1] = list(palette_rgb[idx % len(palette_rgb)])
            else:
                lit_colors = [list(dim_trail) for _ in lit_positions]
            if lit_colors:
                if not palette_rgb:
                    lit_colors[-1] = list(head_rgb)
            conn.set_leds(lit_positions, lit_colors)
            if frame_delay_s > 0:
                sleep_fn(frame_delay_s)

        if impact_hold_s > 0:
            impact_positions = [path[-1]]
            if len(path) >= 2:
                impact_positions.insert(0, path[-2])
            if palette_rgb:
                impact_colors = [_scaled_color(palette_rgb[max(0, len(path) - len(impact_positions) + idx) % len(palette_rgb)], 0.45) for idx in range(len(impact_positions))]
            else:
                impact_colors = [list(dim_trail) for _ in impact_positions]
            impact_colors[-1] = list(impact_rgb)
            conn.set_leds(impact_positions, impact_colors)
            sleep_fn(impact_hold_s)

        conn.leds_off()
        return True
    except Exception:
        try:
            conn.leds_off()
        except Exception:
            pass
        return False


def animate_area_wave(
    conn,
    origin: tuple[int, int] | None,
    area_positions: list[tuple[int, int]] | tuple[tuple[int, int], ...] | set[tuple[int, int]] | None,
    *,
    palette: list[list[int] | tuple[int, int, int]] | tuple[list[int] | tuple[int, int, int], ...] | None = None,
    include_origin: bool = True,
    frame_delay_s: float | None = None,
    hold_s: float | None = None,
    sleep_fn=time.sleep,
) -> bool:
    if not _supports_led_fx(conn) or origin is None:
        return False

    positions = [tuple(pos) for pos in list(area_positions or []) if pos is not None]
    if include_origin and origin not in positions:
        positions.append(tuple(origin))
    if not positions:
        return False

    palette_rgb = _normalize_palette(palette) or [
        [80, 140, 220],
        [150, 210, 255],
        [220, 240, 255],
    ]
    if frame_delay_s is None:
        frame_delay_s = float(getattr(consts, "AREA_LED_STEP_DELAY_S", 0.08) or 0.08)
    if hold_s is None:
        hold_s = float(getattr(consts, "AREA_LED_HOLD_S", 0.12) or 0.12)

    ordered = sorted(set(positions), key=lambda pos: (_grid_steps_from(origin, pos), int(pos[1]), int(pos[0])))
    by_ring: dict[int, list[tuple[int, int]]] = {}
    for pos in ordered:
        by_ring.setdefault(_grid_steps_from(origin, pos), []).append(pos)
    rings = sorted(by_ring.keys())

    try:
        for ring_idx, ring in enumerate(rings):
            lit_positions: list[tuple[int, int]] = []
            lit_colors: list[list[int]] = []
            for prev_idx, prev_ring in enumerate(rings[: ring_idx + 1]):
                ring_color = palette_rgb[min(prev_idx, len(palette_rgb) - 1)]
                dimmed = _scaled_color(ring_color, 0.45)
                highlight = list(ring_color)
                for pos in by_ring.get(prev_ring, []):
                    lit_positions.append(pos)
                    lit_colors.append(highlight if prev_ring == ring else dimmed)
            conn.set_leds(lit_positions, lit_colors)
            if frame_delay_s > 0:
                sleep_fn(frame_delay_s)

        if hold_s > 0:
            final_positions = list(ordered)
            final_colors = []
            for pos in final_positions:
                ring = _grid_steps_from(origin, pos)
                base = palette_rgb[min(rings.index(ring), len(palette_rgb) - 1)]
                final_colors.append(list(base))
            conn.set_leds(final_positions, final_colors)
            sleep_fn(hold_s)

        conn.leds_off()
        return True
    except Exception:
        try:
            conn.leds_off()
        except Exception:
            pass
        return False
