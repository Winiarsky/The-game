from __future__ import annotations

import json
import math
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from board.settings import board_dimensions, load_board_config
from layered_scenarios import LAYERED_SCENARIO_FORMAT, compile_layered_scenario, validate_layered_scenario


DEFAULT_SCENARIOS_DIR = Path("scenarios")
DEFAULT_OUTPUT_DIR = Path("assets/scenario_maps")

CELL_SIZE_CM = 3.33
CELL_SIZE_MM = CELL_SIZE_CM * 10.0


TERRAIN_STYLES: dict[str, dict[str, str]] = {
    "blocked_field": {"fill": "#8f1d1d", "stroke": "#6a1212", "label": "Blocked"},
    "forest_field": {"fill": "#7caf6d", "stroke": "#48723d", "label": "Forest"},
    "bushes_field": {"fill": "#9bbb59", "stroke": "#6c7d30", "label": "Bushes"},
    "rumble_field": {"fill": "#d8b48a", "stroke": "#9d6f47", "label": "Rumble"},
    "dim_light_field": {"fill": "#c6d2f0", "stroke": "#7689b8", "label": "Dim"},
    "darkness_field": {"fill": "#70617e", "stroke": "#45394f", "label": "Dark"},
    "plain_field": {"fill": "#f7f7f7", "stroke": "#d2d2d2", "label": "Plain"},
}

ENEMY_STYLES: dict[str, dict[str, str]] = {
    "goblin_warrior": {"fill": "#c43d1f", "stroke": "#7e1d0d", "label": "GW"},
    "goblin_commando": {"fill": "#8d1f14", "stroke": "#4c0f09", "label": "GC"},
    "goblin_dog": {"fill": "#6d5637", "stroke": "#3e2f1b", "label": "GD"},
    "simple_enemy": {"fill": "#b60000", "stroke": "#630000", "label": "E"},
}


@dataclass(frozen=True)
class EnemyMarker:
    object_id: str
    name: str
    position: tuple[int, int]


@dataclass
class ScenarioMapData:
    scenario_name: str
    scenario_file: str
    rows: int
    cols: int
    starting_positions: list[tuple[int, int]]
    terrains: dict[tuple[int, int], str]
    obstacles: set[tuple[int, int]]
    enemies: list[EnemyMarker]
    walls: list[tuple[tuple[int, int], tuple[int, int]]]
    doors: list[tuple[tuple[int, int], tuple[int, int]]]
    rooms: list[dict[str, Any]]
    biome_name: str | None
    notes: list[str]


def load_board_dimensions(config_path: Path | None = None) -> tuple[int, int]:
    payload = load_board_config(config_path)
    return board_dimensions(payload)


def load_scenario_data(
    scenario_path: Path,
    *,
    rows: int,
    cols: int,
) -> ScenarioMapData:
    payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    terrains: dict[tuple[int, int], str] = {}
    obstacles: set[tuple[int, int]] = set()
    enemies: list[EnemyMarker] = []
    walls_seen: set[frozenset[tuple[int, int]]] = set()
    walls: list[tuple[tuple[int, int], tuple[int, int]]] = []
    doors_seen: set[frozenset[tuple[int, int]]] = set()
    doors: list[tuple[tuple[int, int], tuple[int, int]]] = []

    raw_payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    if str(raw_payload.get("format") or "").strip().lower() == LAYERED_SCENARIO_FORMAT:
        layered_payload = validate_layered_scenario(raw_payload, rows=rows, cols=cols)
        payload = compile_layered_scenario(layered_payload, rows=rows, cols=cols)
    else:
        payload = raw_payload

    def add_wall(a: tuple[int, int], b: tuple[int, int]) -> None:
        if a == b:
            return
        key = frozenset((a, b))
        if key in walls_seen:
            return
        walls_seen.add(key)
        walls.append((a, b))

    def add_door(a: tuple[int, int], b: tuple[int, int]) -> None:
        if a == b:
            return
        key = frozenset((a, b))
        if key in doors_seen:
            return
        doors_seen.add(key)
        doors.append((a, b))

    def normalize_pos(raw: Any) -> tuple[int, int] | None:
        try:
            col, row = raw
            col = int(col)
            row = int(row)
        except Exception:
            return None
        if not (0 <= col < cols and 0 <= row < rows):
            return None
        return (col, row)

    def iter_positions(obj: dict[str, Any]) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for raw in obj.get("positions", []) or []:
            pos = normalize_pos(raw)
            if pos is not None:
                result.append(pos)
        for inst in obj.get("instances", []) or []:
            pos = normalize_pos(inst.get("position") or inst.get("pos"))
            if pos is not None:
                result.append(pos)
        return result

    for raw in payload.get("blocked_fields", []) or []:
        pos = normalize_pos(raw)
        if pos is not None:
            terrains[pos] = "blocked_field"

    for raw in payload.get("obstacles", []) or []:
        pos = normalize_pos(raw)
        if pos is not None:
            obstacles.add(pos)

    for wall in payload.get("walls", []) or []:
        a = normalize_pos(wall.get("a"))
        b = normalize_pos(wall.get("b"))
        if a is not None and b is not None:
            add_wall(a, b)

    for obj in payload.get("objects", []) or []:
        category = str(obj.get("category") or "").strip()
        object_id = str(obj.get("object_id") or "").strip()
        placement = str(obj.get("placement") or "cell").strip()

        if placement == "edge":
            for edge in obj.get("edges", []) or []:
                a = normalize_pos(edge.get("a"))
                b = normalize_pos(edge.get("b"))
                if a is not None and b is not None and category == "Interactables" and object_id == "door":
                    add_door(a, b)
                elif a is not None and b is not None:
                    add_wall(a, b)
            continue

        if category == "Terrains":
            for pos in iter_positions(obj):
                terrains[pos] = object_id
            continue

        if category == "Obstacles":
            for pos in iter_positions(obj):
                obstacles.add(pos)
            continue

        if category == "Enemies":
            for inst in obj.get("instances", []) or []:
                pos = normalize_pos(inst.get("position") or inst.get("pos"))
                if pos is None:
                    continue
                config = inst.get("config") or {}
                name = str(config.get("name") or object_id or "Enemy")
                enemies.append(EnemyMarker(object_id=object_id, name=name, position=pos))
            for pos in obj.get("positions", []) or []:
                normalized = normalize_pos(pos)
                if normalized is None:
                    continue
                enemies.append(EnemyMarker(object_id=object_id, name=object_id or "Enemy", position=normalized))

    starts: list[tuple[int, int]] = []
    for raw in payload.get("starting_positions", []) or []:
        pos = normalize_pos(raw)
        if pos is not None:
            starts.append(pos)

    notes = [str(item) for item in (payload.get("notes") or []) if str(item).strip()]
    rooms_meta = []
    biome_name = None
    for room in payload.get("rooms", []) or []:
        room_positions = []
        for raw in room.get("positions", []) or []:
            pos = normalize_pos(raw)
            if pos is not None:
                room_positions.append(pos)
        room_entry = {
            "id": str(room.get("id") or room.get("name") or ""),
            "name": str(room.get("name") or room.get("id") or ""),
            "color": room.get("color"),
            "positions": room_positions,
        }
        rooms_meta.append(room_entry)
        if room_entry["id"].startswith("biome_"):
            biome_name = room_entry["name"] or room_entry["id"]

    return ScenarioMapData(
        scenario_name=str(payload.get("name") or scenario_path.stem),
        scenario_file=scenario_path.name,
        rows=rows,
        cols=cols,
        starting_positions=starts,
        terrains=terrains,
        obstacles=obstacles,
        enemies=enemies,
        walls=walls,
        doors=doors,
        rooms=rooms_meta,
        biome_name=biome_name,
        notes=notes,
    )


def _wrap_lines(lines: list[str], *, max_chars: int = 38) -> list[str]:
    result: list[str] = []
    for line in lines:
        words = line.split()
        if not words:
            result.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            result.append(current)
            current = word
        result.append(current)
    return result


def _cell_origin(col: int, row: int, x0: float, y0: float) -> tuple[float, float]:
    return x0 + col * CELL_SIZE_MM, y0 + row * CELL_SIZE_MM


def _cell_center(col: int, row: int, x0: float, y0: float) -> tuple[float, float]:
    x, y = _cell_origin(col, row, x0, y0)
    return x + CELL_SIZE_MM / 2.0, y + CELL_SIZE_MM / 2.0


def _earth_tint(col: int, row: int) -> str:
    palette = ("#d8c7a2", "#d4bf96", "#cfb88c", "#dbc9a7")
    return palette[(col * 3 + row * 5) % len(palette)]


def _rock_points(col: int, row: int, *, x0: float, y0: float, inset: float = 5.0) -> str:
    x, y = _cell_origin(col, row, x0, y0)
    seed = (col * 17 + row * 11) % 7
    left = x + inset + (seed % 3)
    top = y + inset + ((seed + 1) % 4)
    right = x + CELL_SIZE_MM - inset - ((seed + 2) % 3)
    bottom = y + CELL_SIZE_MM - inset - ((seed + 3) % 4)
    mid_x = (left + right) / 2.0
    mid_y = (top + bottom) / 2.0
    points = [
        (left + 2.0, top),
        (mid_x + 4.0, top + 1.5),
        (right, mid_y - 4.0),
        (right - 3.0, bottom - 1.0),
        (mid_x - 5.0, bottom),
        (left, mid_y + 3.0),
    ]
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in points)


def _bush_circle_offsets(col: int, row: int) -> list[tuple[float, float, float]]:
    base = (col * 13 + row * 7) % 5
    return [
        (-7.0, 1.0, 6.0 + (base % 2)),
        (0.0, -4.0, 7.5),
        (7.0, 1.5, 6.5 + ((base + 1) % 2)),
        (-2.0, 7.0, 6.0),
    ]


def _forest_circle_offsets(col: int, row: int) -> list[tuple[float, float, float]]:
    base = (col * 5 + row * 9) % 4
    return [
        (-8.0, -2.0, 7.5 + (base % 2)),
        (0.0, -6.0, 8.0),
        (8.0, -1.0, 7.0 + ((base + 1) % 2)),
        (-2.0, 7.0, 7.5),
    ]


def _pebble_offsets(col: int, row: int) -> list[tuple[float, float, float]]:
    base = (col * 19 + row * 23) % 6
    return [
        (-8.0, -3.0, 2.0 + (base % 2)),
        (-2.5, 4.0, 2.5),
        (6.0, -4.0, 2.0),
        (8.0, 5.0, 2.8),
        (-7.0, 8.0, 1.8),
    ]


def _wall_segment(
    a: tuple[int, int],
    b: tuple[int, int],
    *,
    x0: float,
    y0: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    sx, sy = _cell_origin(ax, ay, x0, y0)
    ex, ey = _cell_origin(bx, by, x0, y0)
    cell = CELL_SIZE_MM

    if abs(dx) + abs(dy) == 1:
        if dx == 1:
            x = sx + cell
            return (x, sy), (x, sy + cell)
        if dx == -1:
            x = sx
            return (x, sy), (x, sy + cell)
        if dy == 1:
            y = sy + cell
            return (sx, y), (sx + cell, y)
        y = sy
        return (sx, y), (sx + cell, y)

    quarter = cell * 0.24
    if dx == 1 and dy == 1:
        corner = (sx + cell, sy + cell)
        return (corner[0] - quarter, corner[1] - quarter), (corner[0] + quarter, corner[1] + quarter)
    if dx == -1 and dy == -1:
        corner = (sx, sy)
        return (corner[0] - quarter, corner[1] - quarter), (corner[0] + quarter, corner[1] + quarter)
    if dx == -1 and dy == 1:
        corner = (sx, sy + cell)
        return (corner[0] + quarter, corner[1] - quarter), (corner[0] - quarter, corner[1] + quarter)
    if dx == 1 and dy == -1:
        corner = (sx + cell, sy)
        return (corner[0] + quarter, corner[1] + quarter), (corner[0] - quarter, corner[1] - quarter)

    center_a = (sx + cell / 2.0, sy + cell / 2.0)
    center_b = (ex + cell / 2.0, ey + cell / 2.0)
    return center_a, center_b


def _wall_block_points(
    cx: float,
    cy: float,
    *,
    ux: float,
    uy: float,
    nx: float,
    ny: float,
    half_len: float,
    half_width: float,
) -> str:
    points = [
        (cx - ux * half_len - nx * half_width, cy - uy * half_len - ny * half_width),
        (cx + ux * half_len - nx * half_width, cy + uy * half_len - ny * half_width),
        (cx + ux * half_len + nx * half_width, cy + uy * half_len + ny * half_width),
        (cx - ux * half_len + nx * half_width, cy - uy * half_len + ny * half_width),
    ]
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in points)


def _wall_fantasy_parts(
    a: tuple[int, int],
    b: tuple[int, int],
    *,
    x0: float,
    y0: float,
) -> list[str]:
    (x1, y1), (x2, y2) = _wall_segment(a, b, x0=x0, y0=y0)
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length <= 0.01:
        return []

    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux
    mid_x = (x1 + x2) / 2.0
    mid_y = (y1 + y2) / 2.0
    is_diagonal = abs(dx) > 0.1 and abs(dy) > 0.1

    parts = [
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#241b14" stroke-width="7.0" stroke-linecap="round" filter="url(#wall-shadow)" />',
        f'<line x1="{x1:.1f}" y1="{y1 + 0.2:.1f}" x2="{x2:.1f}" y2="{y2 + 0.2:.1f}" stroke="url(#wall-core)" stroke-width="5.8" stroke-linecap="round" />',
        f'<line x1="{x1:.1f}" y1="{y1 - 0.4:.1f}" x2="{x2:.1f}" y2="{y2 - 0.4:.1f}" stroke="#d4c7b4" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />',
        f'<line x1="{x1:.1f}" y1="{y1 + 1.2:.1f}" x2="{x2:.1f}" y2="{y2 + 1.2:.1f}" stroke="#3b3128" stroke-width="1.0" stroke-linecap="round" opacity="0.45" />',
    ]

    cap_radius = 2.2 if is_diagonal else 2.7
    for cx, cy in ((x1, y1), (x2, y2)):
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{cap_radius:.1f}" fill="#7a7066" stroke="#473e35" stroke-width="0.9" />'
        )
        parts.append(
            f'<circle cx="{cx - 0.4:.1f}" cy="{cy - 0.5:.1f}" r="{cap_radius - 1.0:.1f}" fill="#c4b9a6" opacity="0.48" />'
        )

    block_count = 2 if is_diagonal else max(2, int(round(length / 11.0)))
    gap = 1.1 if is_diagonal else 1.5
    usable_length = max(length - gap * (block_count + 1), block_count * 3.0)
    block_length = usable_length / block_count
    half_len = block_length / 2.0
    half_width = 2.4 if is_diagonal else 2.8
    cursor = -usable_length / 2.0 + half_len

    for idx in range(block_count):
        jitter = ((idx % 2) - 0.5) * (0.35 if is_diagonal else 0.6)
        center_along = cursor + idx * (block_length + gap)
        cx = mid_x + ux * center_along + nx * jitter
        cy = mid_y + uy * center_along + ny * jitter
        polygon = _wall_block_points(
            cx,
            cy,
            ux=ux,
            uy=uy,
            nx=nx,
            ny=ny,
            half_len=half_len,
            half_width=half_width,
        )
        crack_len = max(2.4, half_len * 0.9)
        crack_x1 = cx - ux * crack_len * 0.45 - nx * 0.6
        crack_y1 = cy - uy * crack_len * 0.45 - ny * 0.6
        crack_x2 = cx + ux * crack_len * 0.1 + nx * 0.4
        crack_y2 = cy + uy * crack_len * 0.1 + ny * 0.4
        crack_x3 = cx + ux * crack_len * 0.45 - nx * 0.5
        crack_y3 = cy + uy * crack_len * 0.45 - ny * 0.5
        parts.append(
            f'<polygon points="{polygon}" fill="url(#wall-core)" stroke="#4a4036" stroke-width="0.85" />'
        )
        parts.append(
            f'<polygon points="{polygon}" fill="url(#stone-speck)" opacity="0.28" />'
        )
        parts.append(
            f'<path d="M {crack_x1:.1f},{crack_y1:.1f} L {crack_x2:.1f},{crack_y2:.1f} L {crack_x3:.1f},{crack_y3:.1f}" stroke="#d7cebf" stroke-width="0.55" fill="none" opacity="0.55" />'
        )

    return parts


def _svg_open(total_width: float, total_height: float) -> list[str]:
    svg_width_cm = total_width / 10.0
    svg_height_cm = total_height / 10.0
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width_cm:.2f}cm" height="{svg_height_cm:.2f}cm" viewBox="0 0 {total_width:.1f} {total_height:.1f}">',
        "<defs>",
        '<linearGradient id="paper-bg" x1="0%" y1="0%" x2="0%" y2="100%">',
        '<stop offset="0%" stop-color="#e4d6b7" />',
        '<stop offset="100%" stop-color="#ccb789" />',
        '</linearGradient>',
        '<radialGradient id="ground-wash" cx="50%" cy="45%" r="70%">',
        '<stop offset="0%" stop-color="#e2d2ae" />',
        '<stop offset="100%" stop-color="#c7af7f" />',
        '</radialGradient>',
        '<linearGradient id="wall-core" x1="0%" y1="0%" x2="0%" y2="100%">',
        '<stop offset="0%" stop-color="#c7bbab" />',
        '<stop offset="45%" stop-color="#95887a" />',
        '<stop offset="100%" stop-color="#675d54" />',
        '</linearGradient>',
        '<pattern id="paper-fleck" width="24" height="24" patternUnits="userSpaceOnUse">',
        '<rect width="24" height="24" fill="none" />',
        '<circle cx="5" cy="6" r="0.8" fill="#b89e6e" opacity="0.35" />',
        '<circle cx="18" cy="8" r="1.1" fill="#b59662" opacity="0.28" />',
        '<circle cx="10" cy="16" r="0.9" fill="#a88755" opacity="0.25" />',
        '<circle cx="20" cy="19" r="0.8" fill="#b89e6e" opacity="0.26" />',
        '</pattern>',
        '<pattern id="stone-speck" width="18" height="18" patternUnits="userSpaceOnUse">',
        '<rect width="18" height="18" fill="none" />',
        '<circle cx="4" cy="5" r="1.3" fill="#7d7269" opacity="0.45" />',
        '<circle cx="12" cy="6" r="1.1" fill="#5c534d" opacity="0.5" />',
        '<circle cx="8" cy="13" r="1.4" fill="#8b8278" opacity="0.4" />',
        '</pattern>',
        '<filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="0.8" dy="1.6" stdDeviation="1.3" flood-color="#2e2418" flood-opacity="0.38" />',
        '</filter>',
        '<filter id="wall-shadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="1.0" dy="1.2" stdDeviation="1.1" flood-color="#120d08" flood-opacity="0.5" />',
        '</filter>',
        '<style>',
        '.axis { font: 400 6px "DejaVu Sans Mono", monospace; fill: #6c5a41; }',
        '.cell-label { font: 700 7px "DejaVu Sans Mono", monospace; fill: #fff; text-anchor: middle; dominant-baseline: middle; }',
        '.legend-label { font: 400 7px "DejaVu Sans Mono", monospace; fill: #222; }',
        '.legend-head { font: 700 8px "DejaVu Sans Mono", monospace; fill: #111; }',
        '.legend-meta { font: 400 7px "DejaVu Sans Mono", monospace; fill: #333; }',
        '</style>',
        "</defs>",
        f'<rect x="0" y="0" width="{total_width:.1f}" height="{total_height:.1f}" fill="url(#paper-bg)" />',
        f'<rect x="0" y="0" width="{total_width:.1f}" height="{total_height:.1f}" fill="url(#paper-fleck)" opacity="0.55" />',
    ]


def _draw_grid_map(parts: list[str], data: ScenarioMapData, *, grid_x: float, grid_y: float) -> None:
    grid_width = data.cols * CELL_SIZE_MM
    grid_height = data.rows * CELL_SIZE_MM
    parts.append(
        f'<rect x="{grid_x:.1f}" y="{grid_y:.1f}" width="{grid_width:.1f}" height="{grid_height:.1f}" fill="url(#ground-wash)" stroke="#6b5538" stroke-width="1.2" rx="3" />'
    )
    parts.append(
        f'<rect x="{grid_x:.1f}" y="{grid_y:.1f}" width="{grid_width:.1f}" height="{grid_height:.1f}" fill="url(#paper-fleck)" opacity="0.18" />'
    )

    for row in range(data.rows):
        for col in range(data.cols):
            x, y = _cell_origin(col, row, grid_x, grid_y)
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" '
                f'fill="{_earth_tint(col, row)}" opacity="0.22" stroke="none" />'
            )

    for room in data.rooms:
        color = str(room.get("color") or "").strip()
        if not color:
            continue
        for col, row in sorted(room.get("positions") or [], key=lambda item: (item[1], item[0])):
            x, y = _cell_origin(col, row, grid_x, grid_y)
            parts.append(
                f'<rect x="{x + 0.6:.1f}" y="{y + 0.6:.1f}" width="{CELL_SIZE_MM - 1.2:.1f}" height="{CELL_SIZE_MM - 1.2:.1f}" '
                f'fill="{color}" opacity="0.14" stroke="none" />'
            )

    for (col, row), terrain_id in sorted(data.terrains.items(), key=lambda item: (item[0][1], item[0][0])):
        style = TERRAIN_STYLES.get(terrain_id, {"fill": "#ececec", "stroke": "#c9c9c9", "label": terrain_id})
        x, y = _cell_origin(col, row, grid_x, grid_y)
        cx, cy = _cell_center(col, row, grid_x, grid_y)
        if terrain_id == "blocked_field":
            parts.append(
                f'<rect x="{x + 1.4:.1f}" y="{y + 1.4:.1f}" width="{CELL_SIZE_MM - 2.8:.1f}" height="{CELL_SIZE_MM - 2.8:.1f}" '
                f'fill="#6f665d" stroke="#453e38" stroke-width="1.2" opacity="0.98" />'
            )
            parts.append(
                f'<rect x="{x + 1.4:.1f}" y="{y + 1.4:.1f}" width="{CELL_SIZE_MM - 2.8:.1f}" height="{CELL_SIZE_MM - 2.8:.1f}" '
                'fill="url(#stone-speck)" opacity="0.7" />'
            )
            for dx, dy, r in [(-8.0, -6.0, 5.2), (6.5, -4.0, 4.8), (-3.0, 7.0, 5.5), (8.0, 8.0, 4.6)]:
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r:.1f}" fill="#82776d" stroke="#5c524a" stroke-width="1.0" opacity="0.95" />'
                )
            parts.append(
                f'<path d="M {x + 5:.1f},{y + 8:.1f} L {x + 16:.1f},{y + 15:.1f} L {x + 9:.1f},{y + 25:.1f}" stroke="#d9d0c7" stroke-width="1.0" fill="none" opacity="0.7" />'
            )
            parts.append(
                f'<path d="M {x + 23:.1f},{y + 6:.1f} L {x + 19:.1f},{y + 17:.1f} L {x + 27:.1f},{y + 26:.1f}" stroke="#d9d0c7" stroke-width="1.0" fill="none" opacity="0.62" />'
            )
            continue
        if terrain_id == "forest_field":
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" fill="#6f9460" opacity="0.42" stroke="none" />'
            )
            for dx, dy, r in _forest_circle_offsets(col, row):
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy + 1.3:.1f}" r="{r:.1f}" fill="#314925" opacity="0.18" />'
                )
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r:.1f}" fill="#4b6d39" stroke="#34502a" stroke-width="0.9" opacity="0.96" />'
                )
            parts.append(
                f'<rect x="{cx - 1.1:.1f}" y="{cy + 3.0:.1f}" width="2.2" height="8.5" fill="#5d4026" opacity="0.8" />'
            )
            continue
        if terrain_id == "bushes_field":
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" fill="#8ba55a" opacity="0.34" stroke="none" />'
            )
            for dx, dy, r in _bush_circle_offsets(col, row):
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy + 1.0:.1f}" r="{r:.1f}" fill="#415126" opacity="0.16" />'
                )
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r:.1f}" fill="#6f8a37" stroke="#536629" stroke-width="0.8" opacity="0.96" />'
                )
            continue
        if terrain_id == "rumble_field":
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" fill="#b89067" opacity="0.48" stroke="none" />'
            )
            for dx, dy, r in _pebble_offsets(col, row):
                parts.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r:.1f}" fill="#8f6a46" stroke="#694728" stroke-width="0.55" opacity="0.92" />'
                )
            continue
        if terrain_id == "dim_light_field":
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" fill="#95a6d8" opacity="0.32" stroke="none" />'
            )
            continue
        if terrain_id == "darkness_field":
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" fill="#41364e" opacity="0.52" stroke="none" />'
            )
            continue
        if terrain_id == "blocked_field":
            continue
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_SIZE_MM:.1f}" height="{CELL_SIZE_MM:.1f}" '
            f'fill="{style["fill"]}" stroke="none" opacity="0.45" />'
        )

    for col in range(data.cols + 1):
        x = grid_x + col * CELL_SIZE_MM
        parts.append(
            f'<line x1="{x:.1f}" y1="{grid_y:.1f}" x2="{x:.1f}" y2="{grid_y + grid_height:.1f}" stroke="#866f4b" stroke-width="0.75" opacity="0.34" />'
        )
    for row in range(data.rows + 1):
        y = grid_y + row * CELL_SIZE_MM
        parts.append(
            f'<line x1="{grid_x:.1f}" y1="{y:.1f}" x2="{grid_x + grid_width:.1f}" y2="{y:.1f}" stroke="#866f4b" stroke-width="0.75" opacity="0.34" />'
        )

    for col in range(data.cols):
        x = grid_x + col * CELL_SIZE_MM + CELL_SIZE_MM / 2.0
        parts.append(f'<text x="{x:.1f}" y="{grid_y - 5:.1f}" class="axis" text-anchor="middle">{col}</text>')
    for row in range(data.rows):
        y = grid_y + row * CELL_SIZE_MM + CELL_SIZE_MM / 2.0 + 2.0
        parts.append(f'<text x="{grid_x - 6:.1f}" y="{y:.1f}" class="axis" text-anchor="end">{row}</text>')

    for col, row in sorted(data.obstacles, key=lambda item: (item[1], item[0])):
        x, y = _cell_origin(col, row, grid_x, grid_y)
        cx, cy = _cell_center(col, row, grid_x, grid_y)
        rock = _rock_points(col, row, x0=grid_x, y0=grid_y, inset=5.5)
        parts.append(
            f'<ellipse cx="{cx + 1.0:.1f}" cy="{cy + 6.0:.1f}" rx="10.5" ry="4.2" fill="#43352a" opacity="0.22" />'
        )
        parts.append(
            f'<polygon points="{rock}" fill="#7d756a" stroke="#443d36" stroke-width="1.4" filter="url(#soft-shadow)" />'
        )
        parts.append(
            f'<polygon points="{rock}" fill="url(#stone-speck)" opacity="0.5" />'
        )
        parts.append(
            f'<path d="M {x + 9:.1f},{y + 10:.1f} L {x + 18:.1f},{y + 8:.1f} L {x + 24:.1f},{y + 13:.1f}" stroke="#cbc1b6" stroke-width="0.9" fill="none" opacity="0.7" />'
        )

    for a, b in data.walls:
        parts.extend(_wall_fantasy_parts(a, b, x0=grid_x, y0=grid_y))
    for a, b in data.doors:
        ax, ay = _cell_center(a[0], a[1], grid_x, grid_y)
        bx, by = _cell_center(b[0], b[1], grid_x, grid_y)
        mx = (ax + bx) / 2.0
        my = (ay + by) / 2.0
        dx = bx - ax
        dy = by - ay
        if abs(dx) > abs(dy):
            parts.append(
                f'<line x1="{mx:.1f}" y1="{my - 5.2:.1f}" x2="{mx:.1f}" y2="{my + 5.2:.1f}" stroke="#bb8a20" stroke-width="4.2" stroke-linecap="round" />'
            )
            parts.append(
                f'<line x1="{mx:.1f}" y1="{my - 4.4:.1f}" x2="{mx:.1f}" y2="{my + 4.4:.1f}" stroke="#f3d37a" stroke-width="2.1" stroke-linecap="round" />'
            )
        else:
            parts.append(
                f'<line x1="{mx - 5.2:.1f}" y1="{my:.1f}" x2="{mx + 5.2:.1f}" y2="{my:.1f}" stroke="#bb8a20" stroke-width="4.2" stroke-linecap="round" />'
            )
            parts.append(
                f'<line x1="{mx - 4.4:.1f}" y1="{my:.1f}" x2="{mx + 4.4:.1f}" y2="{my:.1f}" stroke="#f3d37a" stroke-width="2.1" stroke-linecap="round" />'
            )


def render_svg(data: ScenarioMapData) -> str:
    left_margin = 14.0
    top_margin = 14.0
    right_margin = 14.0
    bottom_margin = 14.0
    grid_width = data.cols * CELL_SIZE_MM
    grid_height = data.rows * CELL_SIZE_MM
    total_width = left_margin + grid_width + right_margin
    total_height = top_margin + grid_height + bottom_margin
    grid_x = left_margin
    grid_y = top_margin

    parts = _svg_open(total_width, total_height)
    _draw_grid_map(parts, data, grid_x=grid_x, grid_y=grid_y)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_legend_svg(data: ScenarioMapData) -> str:
    left_margin = 16.0
    top_margin = 16.0
    width = 210.0
    wrapped_notes = _wrap_lines(data.notes, max_chars=34)

    legend_cursor = top_margin + 8.0
    legend_cursor += 12.0
    legend_cursor += 9.0
    legend_cursor += 14.0
    legend_cursor += 13.0 * 5.0
    if data.biome_name:
        legend_cursor += 13.0
    legend_cursor += 16.0
    legend_cursor += 16.0
    legend_cursor += 11.0 + float(len(ENEMY_STYLES) * 12)
    legend_cursor += 13.0 + 40.0
    if wrapped_notes:
        legend_cursor += 16.0 + float(len(wrapped_notes) * 9)
    total_height = legend_cursor + 20.0

    parts = _svg_open(width, total_height)
    legend_x = left_margin
    legend_cursor = top_margin + 8.0

    parts.append(
        f'<rect x="{legend_x - 8:.1f}" y="{top_margin - 8:.1f}" width="{width - 2 * left_margin + 8:.1f}" height="{total_height - top_margin - 8:.1f}" fill="#fafafa" stroke="#d0d0d0" />'
    )
    parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-head">Legenda</text>')
    legend_cursor += 12.0
    parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-meta">siatka {data.cols}x{data.rows}</text>')
    legend_cursor += 9.0
    parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-meta">1 kratka = {CELL_SIZE_CM:.2f} cm</text>')
    legend_cursor += 14.0

    def add_legend_box(fill: str, stroke: str, label: str, *, text_fill: str = "#222") -> None:
        nonlocal legend_cursor
        parts.append(
            f'<rect x="{legend_x:.1f}" y="{legend_cursor - 6.5:.1f}" width="10" height="10" fill="{fill}" stroke="{stroke}" stroke-width="1.2" />'
        )
        parts.append(
            f'<text x="{legend_x + 16:.1f}" y="{legend_cursor + 1.2:.1f}" class="legend-label" fill="{text_fill}">{escape(label)}</text>'
        )
        legend_cursor += 13.0

    add_legend_box("#8f1d1d", "#6a1212", "Blocked field", text_fill="#111")
    add_legend_box("#7caf6d", "#48723d", "Forest cover")
    add_legend_box("#9bbb59", "#6c7d30", "Bushes / difficult")
    add_legend_box("#d8b48a", "#9d6f47", "Rumble / difficult")
    add_legend_box("#424242", "#111111", "Obstacle")
    if data.biome_name:
        add_legend_box("#b9d6a2", "#87a86f", f"Biome: {data.biome_name}")

    parts.append(
        f'<line x1="{legend_x:.1f}" y1="{legend_cursor - 1.0:.1f}" x2="{legend_x + 10:.1f}" y2="{legend_cursor - 1.0:.1f}" stroke="#111111" stroke-width="3.4" stroke-linecap="round" />'
    )
    parts.append(
        f'<text x="{legend_x + 16:.1f}" y="{legend_cursor + 1.2:.1f}" class="legend-label">Wall / blocked edge</text>'
    )
    legend_cursor += 16.0
    parts.append(
        f'<line x1="{legend_x:.1f}" y1="{legend_cursor - 1.0:.1f}" x2="{legend_x + 10:.1f}" y2="{legend_cursor - 1.0:.1f}" stroke="#bb8a20" stroke-width="4.2" stroke-linecap="round" />'
    )
    parts.append(
        f'<line x1="{legend_x:.1f}" y1="{legend_cursor - 1.0:.1f}" x2="{legend_x + 10:.1f}" y2="{legend_cursor - 1.0:.1f}" stroke="#f3d37a" stroke-width="2.1" stroke-linecap="round" />'
    )
    parts.append(
        f'<text x="{legend_x + 16:.1f}" y="{legend_cursor + 1.2:.1f}" class="legend-label">Door / passage edge</text>'
    )
    legend_cursor += 16.0

    parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-head">Enemy tokens</text>')
    legend_cursor += 11.0
    for enemy_id, style in ENEMY_STYLES.items():
        parts.append(
            f'<circle cx="{legend_x + 5:.1f}" cy="{legend_cursor - 2.0:.1f}" r="5" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="1.4" />'
        )
        parts.append(
            f'<text x="{legend_x + 5:.1f}" y="{legend_cursor - 0.8:.1f}" style="font: 700 5px &quot;DejaVu Sans Mono&quot;, monospace; fill: #fff; text-anchor: middle; dominant-baseline: middle;">{style["label"]}</text>'
        )
        parts.append(
            f'<text x="{legend_x + 16:.1f}" y="{legend_cursor:.1f}" class="legend-label">{escape(enemy_id)}</text>'
        )
        legend_cursor += 12.0

    parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor + 2:.1f}" class="legend-head">Counts</text>')
    legend_cursor += 13.0
    counts = [
        f"terrains: {len(data.terrains)}",
        f"obstacles: {len(data.obstacles)}",
        f"walls: {len(data.walls)}",
        f"doors: {len(data.doors)}",
        f"enemies: {len(data.enemies)}",
    ]
    for line in counts:
        parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-label">{escape(line)}</text>')
        legend_cursor += 10.0

    if wrapped_notes:
        legend_cursor += 4.0
        parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-head">Notes</text>')
        legend_cursor += 12.0
        for line in wrapped_notes:
            parts.append(f'<text x="{legend_x:.1f}" y="{legend_cursor:.1f}" class="legend-label">{escape(line)}</text>')
            legend_cursor += 9.0

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_scenario_map_file(
    scenario_path: Path,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    rows: int | None = None,
    cols: int | None = None,
) -> Path:
    if rows is None or cols is None:
        rows, cols = load_board_dimensions()
    data = load_scenario_data(scenario_path, rows=rows, cols=cols)
    svg = render_svg(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{scenario_path.stem}.svg"
    output_path.write_text(svg, encoding="utf-8")
    return output_path


def render_scenario_legend_file(
    scenario_path: Path,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    rows: int | None = None,
    cols: int | None = None,
) -> Path:
    if rows is None or cols is None:
        rows, cols = load_board_dimensions()
    data = load_scenario_data(scenario_path, rows=rows, cols=cols)
    svg = render_legend_svg(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{scenario_path.stem}_legend.svg"
    output_path.write_text(svg, encoding="utf-8")
    return output_path


def render_scenario_files(
    scenario_path: Path,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    rows: int | None = None,
    cols: int | None = None,
) -> tuple[Path, Path]:
    if rows is None or cols is None:
        rows, cols = load_board_dimensions()
    map_path = render_scenario_map_file(scenario_path, output_dir=output_dir, rows=rows, cols=cols)
    legend_path = render_scenario_legend_file(scenario_path, output_dir=output_dir, rows=rows, cols=cols)
    return map_path, legend_path


def render_all_scenarios(
    *,
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    rows: int | None = None,
    cols: int | None = None,
) -> list[Path]:
    if rows is None or cols is None:
        rows, cols = load_board_dimensions()
    generated: list[Path] = []
    for scenario_path in sorted(scenarios_dir.glob("*.json")):
        map_path, legend_path = render_scenario_files(
            scenario_path,
            output_dir=output_dir,
            rows=rows,
            cols=cols,
        )
        generated.extend([map_path, legend_path])
    return generated


__all__ = [
    "CELL_SIZE_CM",
    "CELL_SIZE_MM",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SCENARIOS_DIR",
    "ScenarioMapData",
    "load_board_dimensions",
    "load_scenario_data",
    "render_all_scenarios",
    "render_legend_svg",
    "render_scenario_files",
    "render_scenario_legend_file",
    "render_scenario_map_file",
    "render_svg",
]
