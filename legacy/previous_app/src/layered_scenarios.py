from __future__ import annotations

import copy
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from board.settings import board_dimensions, load_board_config


DEFAULT_SCENARIOS_DIR = Path("scenarios")
DEFAULT_LAYERED_SCENARIOS_DIR = Path("scenarios_layered")
LAYERED_SCENARIO_FORMAT = "layered_scenario_v1"

BIOME_PRESETS: dict[str, dict[str, Any]] = {
    "forest": {
        "room_id": "biome_forest",
        "name": "Forest Biome",
        "color": "#b9d6a2",
        "terrain": None,
    },
    "cave": {
        "room_id": "biome_cave",
        "name": "Cave Biome",
        "color": "#cfc8bf",
        "terrain": None,
    },
    "mountains": {
        "room_id": "biome_mountains",
        "name": "Mountain Biome",
        "color": "#d8d1c7",
        "terrain": None,
    },
    "ruins": {
        "room_id": "biome_ruins",
        "name": "Ruins Biome",
        "color": "#d8c8b0",
        "terrain": None,
    },
}

ROOM_TYPE_PRESETS: dict[str, dict[str, Any]] = {
    "stone_room": {
        "name": "Stone Room",
        "color": "#d6d9de",
        "terrain": "plain_field",
    },
    "garden_patch": {
        "name": "Garden Patch",
        "color": "#a4c96d",
        "terrain": "bushes_field",
    },
    "courtyard": {
        "name": "Courtyard",
        "color": "#d5c9ab",
        "terrain": "plain_field",
    },
}

DEFAULT_SETUP_COLORS: dict[str, list[int]] = {
    "biome": [40, 120, 255],
    "room": [0, 180, 255],
    "wall": [255, 140, 0],
    "door": [255, 220, 0],
    "object": [0, 255, 0],
    "enemy": [255, 0, 0],
    "hero_start": [0, 255, 255],
}


def list_scenario_names(
    scenarios_dir: Path | None = None,
    layered_dir: Path | None = None,
) -> list[str]:
    flat_dir = Path(scenarios_dir or DEFAULT_SCENARIOS_DIR)
    layered_root = Path(layered_dir or DEFAULT_LAYERED_SCENARIOS_DIR)
    names: set[str] = set()
    if flat_dir.exists():
        names.update(path.stem for path in flat_dir.glob("*.json"))
    if layered_root.exists():
        names.update(path.stem for path in layered_root.glob("*.json"))
    return sorted(names)


def resolve_scenario_payload(
    scenario_name: str,
    *,
    scenarios_dir: Path | None = None,
    layered_dir: Path | None = None,
    rows: int | None = None,
    cols: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    flat_dir = Path(scenarios_dir or DEFAULT_SCENARIOS_DIR)
    layered_root = Path(layered_dir or DEFAULT_LAYERED_SCENARIOS_DIR)

    flat_path = flat_dir / f"{scenario_name}.json"
    layered_path = layered_root / f"{scenario_name}.json"
    if flat_path.exists():
        payload = json.loads(flat_path.read_text(encoding="utf-8"))
        return payload, {"kind": "runtime", "path": flat_path}
    if layered_path.exists():
        layered_payload = load_layered_scenario(layered_path, rows=rows, cols=cols)
        compiled = compile_layered_scenario(layered_payload, rows=rows, cols=cols)
        return compiled, {"kind": "layered", "path": layered_path, "layered_payload": layered_payload}
    raise FileNotFoundError(f"Nie znaleziono scenariusza '{scenario_name}' w {flat_dir} ani {layered_root}.")


def load_layered_scenario(
    path_or_name: str | Path,
    *,
    layered_dir: Path | None = None,
    rows: int | None = None,
    cols: int | None = None,
) -> dict[str, Any]:
    layered_root = Path(layered_dir or DEFAULT_LAYERED_SCENARIOS_DIR)
    path = Path(path_or_name)
    if not path.exists():
        path = layered_root / f"{path_or_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_layered_scenario(payload, rows=rows, cols=cols)
    validated["_source_path"] = str(path)
    return validated


def validate_layered_scenario(
    payload: dict[str, Any],
    *,
    rows: int | None = None,
    cols: int | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Scenariusz warstwowy musi byc obiektem JSON.")
    if str(payload.get("format") or "").strip().lower() != LAYERED_SCENARIO_FORMAT:
        raise ValueError(f"Scenariusz warstwowy musi miec format='{LAYERED_SCENARIO_FORMAT}'.")

    board_rows, board_cols = _board_dims(rows=rows, cols=cols)
    normalized = copy.deepcopy(payload)
    biome = _normalize_biome(normalized.get("biome"))
    rooms = [_normalize_room(room, rows=board_rows, cols=board_cols) for room in list(normalized.get("rooms") or [])]
    room_positions: dict[str, set[tuple[int, int]]] = {}
    occupied_cells: dict[tuple[int, int], str] = {}
    for room in rooms:
        rid = room["room_id"]
        positions = set(room["positions"])
        room_positions[rid] = positions
        for pos in positions:
            if pos in occupied_cells:
                raise ValueError(
                    f"Room '{rid}' naklada sie z roomem '{occupied_cells[pos]}' na polu {pos}."
                )
            occupied_cells[pos] = rid

    walls = [_normalize_edge_spec(item, rows=board_rows, cols=board_cols, default_object_id="simple_wall") for item in list(normalized.get("walls") or [])]
    doors = [_normalize_edge_spec(item, rows=board_rows, cols=board_cols, default_object_id="door") for item in list(normalized.get("doors") or [])]
    objects = [_normalize_object_spec(item, rows=board_rows, cols=board_cols) for item in list(normalized.get("objects") or [])]
    enemies = [_normalize_enemy_spec(item, rows=board_rows, cols=board_cols) for item in list(normalized.get("enemies") or [])]
    starts = [_normalize_pos(item, rows=board_rows, cols=board_cols) for item in list(normalized.get("starting_positions") or [])]

    normalized["biome"] = biome
    normalized["rooms"] = rooms
    normalized["walls"] = walls
    normalized["doors"] = doors
    normalized["objects"] = objects
    normalized["enemies"] = enemies
    normalized["starting_positions"] = [list(pos) for pos in starts]
    return normalized


def compile_layered_scenario(
    layered_payload: dict[str, Any],
    *,
    rows: int | None = None,
    cols: int | None = None,
) -> dict[str, Any]:
    payload = validate_layered_scenario(layered_payload, rows=rows, cols=cols)
    board_rows, board_cols = _board_dims(rows=rows, cols=cols)
    setup_plan = build_layered_setup_plan(payload, rows=board_rows, cols=board_cols)

    runtime_rooms: list[dict[str, Any]] = []
    terrain_groups: dict[str, set[tuple[int, int]]] = defaultdict(set)
    runtime_objects: list[dict[str, Any]] = []
    enemy_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    obstacle_groups: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)

    biome = payload["biome"]
    biome_room_positions = [(col, row) for row in range(board_rows) for col in range(board_cols)]
    runtime_rooms.append(
        {
            "id": biome["room_id"],
            "name": biome["name"],
            "color": biome["color"],
            "positions": [list(pos) for pos in biome_room_positions],
        }
    )
    if biome.get("terrain"):
        terrain_groups[str(biome["terrain"])].update(biome_room_positions)

    for room in payload["rooms"]:
        runtime_rooms.append(
            {
                "id": room["room_id"],
                "name": room["name"],
                "color": room["color"],
                "positions": [list(pos) for pos in room["positions"]],
            }
        )
        if room.get("terrain"):
            terrain_groups[str(room["terrain"])].update(tuple(pos) for pos in room["positions"])

    for object_id, positions in sorted(terrain_groups.items()):
        runtime_objects.append(
            {
                "category": "Terrains",
                "object_id": object_id,
                "placement": "cell",
                "positions": [list(pos) for pos in sorted(positions, key=lambda item: (item[1], item[0]))],
            }
        )

    for spec in payload["objects"]:
        category = str(spec["category"])
        object_id = str(spec["object_id"])
        placement = str(spec.get("placement") or "cell")
        if placement == "edge":
            runtime_objects.append(
                {
                    "category": category,
                    "object_id": object_id,
                    "placement": "edge",
                    "edges": [
                        {
                            "a": list(edge["a"]),
                            "b": list(edge["b"]),
                            **({"config": dict(edge["config"])} if edge.get("config") else {}),
                        }
                        for edge in spec["edges"]
                    ],
                }
            )
            continue
        positions = [tuple(pos) for pos in spec.get("positions") or []]
        instances = [
            {
                "position": list(tuple(inst["position"])),
                **({"config": dict(inst["config"])} if inst.get("config") else {}),
            }
            for inst in list(spec.get("instances") or [])
        ]
        if positions:
            obstacle_groups[(category, object_id)].update(positions)
        if instances:
            runtime_objects.append(
                {
                    "category": category,
                    "object_id": object_id,
                    "placement": "cell",
                    "instances": instances,
                }
            )

    for (category, object_id), positions in sorted(obstacle_groups.items(), key=lambda item: (item[0][0], item[0][1])):
        runtime_objects.append(
            {
                "category": category,
                "object_id": object_id,
                "placement": "cell",
                "positions": [list(pos) for pos in sorted(positions, key=lambda item: (item[1], item[0]))],
            }
        )

    for spec in payload["enemies"]:
        enemy_groups[str(spec["object_id"])].append(
            {
                "position": list(tuple(spec["position"])),
                **({"config": dict(spec["config"])} if spec.get("config") else {}),
            }
        )
    for object_id, instances in sorted(enemy_groups.items()):
        runtime_objects.append(
            {
                "category": "Enemies",
                "object_id": object_id,
                "placement": "cell",
                "instances": instances,
            }
        )

    if payload["walls"]:
        runtime_objects.append(
            {
                "category": "Walls",
                "object_id": "simple_wall",
                "placement": "edge",
                "edges": [{"a": list(spec["a"]), "b": list(spec["b"])} for spec in payload["walls"]],
            }
        )
    if payload["doors"]:
        runtime_objects.append(
            {
                "category": "Interactables",
                "object_id": "door",
                "placement": "edge",
                "edges": [
                    {
                        "a": list(spec["a"]),
                        "b": list(spec["b"]),
                        **({"config": dict(spec["config"])} if spec.get("config") else {}),
                    }
                    for spec in payload["doors"]
                ],
            }
        )

    runtime_payload = {
        "name": payload.get("name") or "Layered Scenario",
        "description": payload.get("description") or "",
        "notes": list(payload.get("notes") or []),
        "starting_positions": [list(pos) for pos in payload["starting_positions"]],
        "rooms": runtime_rooms,
        "objects": runtime_objects,
        "setup_plan": copy.deepcopy(setup_plan),
        "metadata": {
            **dict(payload.get("metadata") or {}),
            "source_format": LAYERED_SCENARIO_FORMAT,
            "biome_id": biome["biome_id"],
            "layered_source_path": payload.get("_source_path"),
        },
    }
    return runtime_payload


def build_layered_setup_plan(
    layered_payload: dict[str, Any],
    *,
    rows: int | None = None,
    cols: int | None = None,
) -> list[dict[str, Any]]:
    payload = validate_layered_scenario(layered_payload, rows=rows, cols=cols)
    steps: list[dict[str, Any]] = []
    for room in payload["rooms"]:
        steps.append(
            {
                "kind": "room",
                "label": str(room["name"]),
                "color": list(DEFAULT_SETUP_COLORS["room"]),
                "positions": [list(pos) for pos in room["positions"]],
                "edges": [],
                "prompt": f"Ułóż room: {room['name']}.",
            }
        )
    if payload["walls"]:
        steps.append(
            {
                "kind": "wall",
                "label": "Walls",
                "color": list(DEFAULT_SETUP_COLORS["wall"]),
                "positions": [list(pos) for pos in _edge_endpoints(payload["walls"])],
                "edges": [{"a": list(edge["a"]), "b": list(edge["b"])} for edge in payload["walls"]],
                "prompt": "Ustaw ściany na podświetlonych krawędziach.",
            }
        )
    if payload["doors"]:
        steps.append(
            {
                "kind": "door",
                "label": "Doors",
                "color": list(DEFAULT_SETUP_COLORS["door"]),
                "positions": [list(pos) for pos in _edge_endpoints(payload["doors"])],
                "edges": [{"a": list(edge["a"]), "b": list(edge["b"])} for edge in payload["doors"]],
                "prompt": "Ustaw drzwi na podświetlonych krawędziach.",
            }
        )
    object_positions: list[tuple[int, int]] = []
    enemy_positions: list[tuple[int, int]] = []
    for spec in payload["objects"]:
        object_positions.extend(tuple(pos) for pos in spec.get("positions") or [])
        object_positions.extend(tuple(inst["position"]) for inst in list(spec.get("instances") or []))
    for enemy in payload["enemies"]:
        enemy_positions.append(tuple(enemy["position"]))
    if object_positions:
        steps.append(
            {
                "kind": "object",
                "label": "Objects",
                "color": list(DEFAULT_SETUP_COLORS["object"]),
                "positions": [list(pos) for pos in sorted(set(object_positions), key=lambda item: (item[1], item[0]))],
                "edges": [],
                "prompt": "Ustaw obiekty na podświetlonych polach.",
            }
        )
    if enemy_positions:
        steps.append(
            {
                "kind": "enemy",
                "label": "Enemy spawns",
                "color": list(DEFAULT_SETUP_COLORS["enemy"]),
                "positions": [list(pos) for pos in sorted(set(enemy_positions), key=lambda item: (item[1], item[0]))],
                "edges": [],
                "prompt": "Ustaw figurki przeciwników na podświetlonych polach.",
            }
        )
    if payload["starting_positions"]:
        steps.append(
            {
                "kind": "hero_start",
                "label": "Hero starts",
                "color": list(DEFAULT_SETUP_COLORS["hero_start"]),
                "positions": [list(pos) for pos in payload["starting_positions"]],
                "edges": [],
                "prompt": "Ustaw bohaterów na polach startowych.",
            }
        )
    return steps


def _board_dims(*, rows: int | None = None, cols: int | None = None) -> tuple[int, int]:
    if rows is not None and cols is not None:
        return int(rows), int(cols)
    cfg = load_board_config()
    return board_dimensions(cfg)


def _normalize_biome(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        biome_id = raw.strip().lower()
        spec = dict(BIOME_PRESETS.get(biome_id) or {})
        if not spec:
            raise ValueError(f"Nieznany biome: {raw}")
        return {"biome_id": biome_id, **spec}
    if not isinstance(raw, dict):
        raise ValueError("Pole 'biome' musi być stringiem albo obiektem.")
    biome_id = str(raw.get("biome_id") or raw.get("id") or "").strip().lower()
    preset = dict(BIOME_PRESETS.get(biome_id) or {})
    if not biome_id or not preset:
        raise ValueError(f"Nieznany biome: {biome_id or raw!r}")
    return {
        "biome_id": biome_id,
        "room_id": str(raw.get("room_id") or preset["room_id"]),
        "name": str(raw.get("name") or preset["name"]),
        "color": str(raw.get("color") or preset["color"]),
        "terrain": raw.get("terrain", preset.get("terrain")),
    }


def _normalize_room(room: dict[str, Any], *, rows: int, cols: int) -> dict[str, Any]:
    if not isinstance(room, dict):
        raise ValueError("Każdy room musi być obiektem.")
    room_type = str(room.get("room_type") or room.get("type") or "").strip().lower()
    preset = dict(ROOM_TYPE_PRESETS.get(room_type) or {})
    if not room_type or not preset:
        raise ValueError(f"Nieznany room_type: {room_type or room!r}")
    room_id = str(room.get("room_id") or room.get("id") or "").strip()
    if not room_id:
        raise ValueError("Room musi mieć room_id.")
    if room.get("positions"):
        positions = [_normalize_pos(item, rows=rows, cols=cols) for item in list(room.get("positions") or [])]
    else:
        try:
            origin = _normalize_pos(room.get("origin"), rows=rows, cols=cols)
            size_raw = room.get("size") or []
            width = int(size_raw[0])
            height = int(size_raw[1])
        except Exception as exc:
            raise ValueError(f"Room '{room_id}' wymaga positions albo origin+size.") from exc
        if width <= 0 or height <= 0:
            raise ValueError(f"Room '{room_id}' ma niepoprawny rozmiar {room.get('size')}.")
        positions = []
        for row_idx in range(origin[1], origin[1] + height):
            for col_idx in range(origin[0], origin[0] + width):
                positions.append(_normalize_pos((col_idx, row_idx), rows=rows, cols=cols))
    return {
        "room_id": room_id,
        "room_type": room_type,
        "name": str(room.get("name") or preset["name"]),
        "color": str(room.get("color") or preset["color"]),
        "terrain": room.get("terrain", preset.get("terrain")),
        "positions": [tuple(pos) for pos in positions],
    }


def _normalize_edge_spec(
    item: dict[str, Any],
    *,
    rows: int,
    cols: int,
    default_object_id: str,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Spec krawędzi musi być obiektem.")
    a = _normalize_pos(item.get("a"), rows=rows, cols=cols)
    b = _normalize_pos(item.get("b"), rows=rows, cols=cols)
    if max(abs(a[0] - b[0]), abs(a[1] - b[1])) != 1:
        raise ValueError(f"Krawędź {a}-{b} musi łączyć sąsiednie pola.")
    return {
        "object_id": str(item.get("object_id") or default_object_id),
        "a": a,
        "b": b,
        "config": dict(item.get("config") or {}),
    }


def _normalize_object_spec(item: dict[str, Any], *, rows: int, cols: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Obiekt scenariusza musi być obiektem.")
    category = str(item.get("category") or "").strip()
    object_id = str(item.get("object_id") or "").strip()
    if not category or not object_id:
        raise ValueError(f"Obiekt wymaga category i object_id: {item!r}")
    placement = str(item.get("placement") or "cell").strip().lower()
    if placement == "edge":
        edges = [
            _normalize_edge_spec(edge, rows=rows, cols=cols, default_object_id=object_id)
            for edge in list(item.get("edges") or [])
        ]
        return {"category": category, "object_id": object_id, "placement": "edge", "edges": edges}
    positions = [_normalize_pos(pos, rows=rows, cols=cols) for pos in list(item.get("positions") or [])]
    instances = []
    for inst in list(item.get("instances") or []):
        if not isinstance(inst, dict):
            raise ValueError(f"Niepoprawna instancja obiektu {object_id}: {inst!r}")
        instances.append(
            {
                "position": _normalize_pos(inst.get("position") or inst.get("pos"), rows=rows, cols=cols),
                "config": dict(inst.get("config") or {}),
            }
        )
    return {
        "category": category,
        "object_id": object_id,
        "placement": "cell",
        "positions": positions,
        "instances": instances,
    }


def _normalize_enemy_spec(item: dict[str, Any], *, rows: int, cols: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Enemy spec musi być obiektem.")
    object_id = str(item.get("object_id") or "").strip()
    if not object_id:
        raise ValueError(f"Enemy wymaga object_id: {item!r}")
    return {
        "object_id": object_id,
        "position": _normalize_pos(item.get("position"), rows=rows, cols=cols),
        "config": dict(item.get("config") or {}),
    }


def _normalize_pos(raw: Any, *, rows: int, cols: int) -> tuple[int, int]:
    try:
        col, row = raw
        col = int(col)
        row = int(row)
    except Exception as exc:
        raise ValueError(f"Niepoprawna pozycja: {raw!r}") from exc
    if not (0 <= col < cols and 0 <= row < rows):
        raise ValueError(f"Pozycja {(col, row)} jest poza planszą {cols}x{rows}.")
    return (col, row)


def _edge_endpoints(edges: list[dict[str, Any]]) -> list[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for edge in edges:
        result.add(tuple(edge["a"]))
        result.add(tuple(edge["b"]))
    return sorted(result, key=lambda item: (item[1], item[0]))
