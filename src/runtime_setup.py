from __future__ import annotations

from collections import defaultdict
from typing import Any

from board import consts
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Interactables.entry_anchor import EntryAnchor
from GameObjects.Interactables.scenario_exit import ScenarioExit
from GameObjects.Obstacles.basic_obstacle import Obstacle
from GameObjects.Terrains.basic_terrain import BasicTerrain
from layered_scenarios import DEFAULT_SETUP_COLORS


DEFAULT_TERRAIN_PROMPTS: dict[str, str] = {
    "blocked": "Ustaw pola zablokowane na podświetlonych polach.",
    "bushes": "Ustaw trudny teren na podświetlonych polach.",
    "rumble": "Ustaw rumowiska na podświetlonych polach.",
}

SCENARIO_EXIT_SETUP_PALETTE: tuple[tuple[str, list[int]], ...] = (
    ("pomarańczowy", list(consts.SEEK_EXIT_RGB)),
    ("niebieski", list(consts.HERO_HIGHLIGHT_RGB)),
    ("zielony", list(consts.MOVE_TARGET_RGB)),
    ("fioletowy", list(consts.HIDDEN_REVEAL_RGB)),
)


def build_runtime_setup_plan(
    game,
    *,
    include_clear_prompt: bool = False,
    clear_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """Zbuduj setup plan z aktualnego runtime mapy/snapshotu.

    Plan jest liczony z bieżącego stanu planszy, więc nadaje się także do
    powrotu na wcześniej odwiedzoną mapę ze zmienionym stanem.
    """

    board = getattr(game, "board", None)
    if board is None:
        return []

    steps: list[dict[str, Any]] = []
    if include_clear_prompt:
        steps.append(
            {
                "kind": "clear_map",
                "label": "Clear previous map",
                "color": list(DEFAULT_SETUP_COLORS["biome"]),
                "positions": [],
                "edges": [],
                "prompt": str(clear_prompt or "Przygotuj miejsce na kolejną mapę i usuń poprzedni układ."),
                "confirmation_mode": "confirm_only",
            }
        )

    room_steps = _build_room_steps(board)
    steps.extend(room_steps)

    wall_edges = [
        {"a": list(tuple(a)), "b": list(tuple(b))}
        for a, b in sorted(
            (
                tuple(sorted(tuple(pos) for pos in edge_key))
                for edge_key in list(getattr(board, "walls", {}).keys())
                if len(edge_key) == 2
            ),
            key=lambda item: (item[0][1], item[0][0], item[1][1], item[1][0]),
        )
    ]
    if wall_edges:
        wall_positions = _unique_positions(
            [tuple(edge["a"]) for edge in wall_edges] + [tuple(edge["b"]) for edge in wall_edges]
        )
        steps.append(
            {
                "kind": "wall",
                "label": "Walls",
                "color": list(DEFAULT_SETUP_COLORS["wall"]),
                "positions": [list(pos) for pos in wall_positions],
                "edges": wall_edges,
                "prompt": "Ustaw ściany zgodnie z podświetlonymi krawędziami i potwierdź w UI.",
                "confirmation_mode": "confirm_only",
            }
        )

    terrain_groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    obstacle_positions: list[tuple[int, int]] = []
    enemy_positions: list[tuple[int, int]] = []
    interactable_positions: list[tuple[int, int]] = []
    scenario_exit_markers: list[dict[str, Any]] = []
    edge_interactable_endpoints: list[tuple[int, int]] = []

    rows = int(getattr(board, "rows", 0) or 0)
    cols = int(getattr(board, "cols", 0) or 0)
    for row in range(rows):
        for col in range(cols):
            pos = (col, row)
            cell = board.cell_at(pos)
            field = getattr(cell, "field", None)
            terrain_key = _terrain_setup_key(field)
            if terrain_key:
                terrain_groups[terrain_key].append(pos)
            occupant = getattr(cell, "occupant", None)
            if isinstance(occupant, Obstacle):
                obstacle_positions.append(pos)
            elif isinstance(occupant, BasicEnemy) and _enemy_is_setup_visible(game, occupant):
                enemy_positions.append(pos)
            for obj in list(getattr(cell, "interactables", []) or []):
                if _is_setup_visible_scenario_exit(obj):
                    scenario_exit_markers.append(
                        {
                            "position": pos,
                            "label": str(getattr(obj, "exit_label", None) or getattr(obj, "exit_id", "") or "Scenario exit").strip(),
                        }
                    )
                if _is_setup_visible_interactable(obj):
                    interactable_positions.append(pos)

    for edge_key, objects in list(getattr(board, "edge_interactables", {}).items()):
        if not any(_is_setup_visible_interactable(obj) for obj in list(objects or [])):
            continue
        for pos in edge_key:
            edge_interactable_endpoints.append(tuple(pos))

    for terrain_key, positions in sorted(terrain_groups.items(), key=lambda item: item[0]):
        steps.append(
            {
                "kind": "terrain",
                "label": terrain_key,
                "color": list(DEFAULT_SETUP_COLORS["object"]),
                "positions": [list(pos) for pos in _unique_positions(positions)],
                "edges": [],
                "prompt": DEFAULT_TERRAIN_PROMPTS.get(
                    terrain_key,
                    "Ustaw elementy terenu na podświetlonych polach.",
                ),
                "confirmation_mode": "confirm_only",
            }
        )

    if obstacle_positions:
        steps.append(
            {
                "kind": "obstacle",
                "label": "Obstacles",
                "color": list(DEFAULT_SETUP_COLORS["object"]),
                "positions": [list(pos) for pos in _unique_positions(obstacle_positions)],
                "edges": [],
                "prompt": "Ustaw przeszkody na podświetlonych polach.",
                "confirmation_mode": "confirm_only",
            }
        )

    interactable_positions = _unique_positions(interactable_positions)
    edge_interactable_endpoints = _unique_positions(edge_interactable_endpoints)
    if interactable_positions or edge_interactable_endpoints:
        steps.append(
            {
                "kind": "interactable",
                "label": "Interactables",
                "color": list(DEFAULT_SETUP_COLORS["door"]),
                "positions": [list(pos) for pos in interactable_positions + edge_interactable_endpoints],
                "edges": [],
                "prompt": "Ustaw widoczne elementy interaktywne mapy i potwierdź w UI.",
                "confirmation_mode": "confirm_only",
            }
        )

    if scenario_exit_markers:
        markers = _unique_scenario_exit_markers(scenario_exit_markers)
        colored_markers = []
        for idx, item in enumerate(markers):
            color_label, color = SCENARIO_EXIT_SETUP_PALETTE[idx % len(SCENARIO_EXIT_SETUP_PALETTE)]
            colored_markers.append({**item, "color_label": color_label, "color": list(color)})
        marker_lines = [
            f"- {item['label']}: LED {item['color_label']}, pole {tuple(item['position'])}"
            for item in colored_markers
        ]
        steps.append(
            {
                "kind": "scenario_exit",
                "label": "Scenario exits",
                "color": list(DEFAULT_SETUP_COLORS["door"]),
                "colors": [list(item["color"]) for item in colored_markers],
                "legend": [
                    {
                        "label": str(item["label"]),
                        "position": list(item["position"]),
                        "color_label": str(item["color_label"]),
                        "color": list(item["color"]),
                    }
                    for item in colored_markers
                ],
                "positions": [list(item["position"]) for item in colored_markers],
                "edges": [],
                "prompt": "Wskaż na planszy jawne przejścia scenariusza według kolorów LED:\n" + "\n".join(marker_lines),
                "confirmation_mode": "confirm_only",
            }
        )

    if enemy_positions:
        steps.append(
            {
                "kind": "enemy",
                "label": "Enemy spawns",
                "color": list(DEFAULT_SETUP_COLORS["enemy"]),
                "positions": [list(pos) for pos in _unique_positions(enemy_positions)],
                "edges": [],
                "prompt": "Ustaw figurki przeciwników na podświetlonych polach.",
                "confirmation_mode": "confirm_only",
            }
        )

    return steps


def _build_room_steps(board) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    rooms_meta = dict(getattr(board, "rooms_meta", {}) or {})
    room_positions = dict(getattr(board, "room_positions", {}) or {})
    for room_id in sorted(room_positions.keys()):
        positions = _unique_positions(room_positions.get(room_id) or [])
        if not positions:
            continue
        meta = dict(rooms_meta.get(room_id) or {})
        room_name = str(meta.get("name") or room_id)
        steps.append(
            {
                "kind": "room",
                "label": room_name,
                "color": list(DEFAULT_SETUP_COLORS["room"]),
                "positions": [list(pos) for pos in positions],
                "edges": [],
                "prompt": f"Przygotuj obszar mapy: {room_name}.",
                "confirmation_mode": "confirm_only",
            }
        )
    return steps


def _unique_positions(positions: list[tuple[int, int]] | set[tuple[int, int]] | tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, int]] = []
    for raw in positions:
        pos = (int(raw[0]), int(raw[1]))
        if pos in seen:
            continue
        seen.add(pos)
        result.append(pos)
    return sorted(result, key=lambda item: (item[1], item[0]))


def _unique_scenario_exit_markers(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[tuple[int, int], str]] = set()
    result: list[dict[str, Any]] = []
    for raw in items:
        position = tuple(int(value) for value in tuple(raw.get("position") or ()))
        if len(position) != 2:
            continue
        label = str(raw.get("label") or "Scenario exit").strip()
        key = (position, label)
        if key in seen:
            continue
        seen.add(key)
        result.append({"position": position, "label": label})
    return sorted(result, key=lambda item: (item["position"][1], item["position"][0], item["label"]))


def _terrain_setup_key(field: Any) -> str | None:
    if field is None or not isinstance(field, BasicTerrain):
        return None
    name = str(getattr(field, "name", "") or "").strip().lower()
    if name == "basic" and bool(getattr(field, "walkable", True)) and int(getattr(field, "move_cost_bonus_feet", 0) or 0) == 0:
        return None
    if name:
        return name
    if not bool(getattr(field, "walkable", True)):
        return "blocked"
    if int(getattr(field, "move_cost_bonus_feet", 0) or 0) > 0:
        return "difficult"
    return field.__class__.__name__.lower()


def _enemy_is_setup_visible(game, enemy: BasicEnemy) -> bool:
    checker = getattr(game, "_is_enemy_combat_ready", None)
    if callable(checker):
        try:
            return bool(checker(enemy))
        except Exception:
            return False
    if getattr(enemy, "position", None) is None:
        return False
    try:
        return int(getattr(enemy, "hp", 1) or 0) > 0
    except Exception:
        return True


def _is_setup_visible_interactable(obj: Any) -> bool:
    if obj is None:
        return False
    if isinstance(obj, (EntryAnchor, ScenarioExit)):
        return False
    if hasattr(obj, "entry_anchor_id") or hasattr(obj, "exit_id"):
        return False
    if bool(getattr(obj, "hidden", False)) and not bool(getattr(obj, "revealed", False)):
        return False
    return True


def _is_setup_visible_scenario_exit(obj: Any) -> bool:
    if obj is None:
        return False
    if isinstance(obj, ScenarioExit):
        if bool(getattr(obj, "hidden", False)) and not bool(getattr(obj, "revealed", False)):
            return False
        return True
    if not hasattr(obj, "exit_id"):
        return False
    if bool(getattr(obj, "hidden", False)) and not bool(getattr(obj, "revealed", False)):
        return False
    return True
