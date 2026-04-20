from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import random
from typing import Any

from GameObjects.Obstacles.simple_obstacle import SimpleObstacle
from GameObjects.Terrains.blocked_field import BlockedField
from GameObjects.Walls.simple_wall import SimpleWall
from board_grid import BoardGrid
from board.settings import board_dimensions, load_board_config

ROWS, COLS = board_dimensions(load_board_config())

THREAT_BUDGETS = {
    "trivial": 40,
    "low": 60,
    "moderate": 80,
    "severe": 120,
    "extreme": 160,
}

PARTY_SIZE_ADJUSTMENT = {
    "trivial": 10,
    "low": 15,
    "moderate": 20,
    "severe": 30,
    "extreme": 40,
}

ENEMY_LEVELS = {
    "goblin_warrior": 0,
    "goblin_dog": 1,
    "goblin_commando": 2,
}

ENEMY_XP_BY_DELTA = {
    -4: 10,
    -3: 15,
    -2: 20,
    -1: 30,
    0: 40,
    1: 60,
    2: 80,
    3: 120,
    4: 160,
}

ENEMY_LABELS = {
    "goblin_warrior": "Goblin Warrior",
    "goblin_dog": "Goblin Dog",
    "goblin_commando": "Goblin Commando",
}

SUPPORTED_LAYOUTS = ("open_field", "split_lanes", "chokepoints")
SUPPORTED_BIOMES = ("forest", "ruined_village")
SUPPORTED_FORMATION_PACKS = ("fortifications", "ruins", "serpentine")
RANDOM_FORMATION_VALUES = {"", "none", "random", "losowy"}
PRESETS_DIR = Path(__file__).resolve().parent / "encounter_presets"
ALLOWED_TRIGGER_CONDITION_KINDS = {
    "distance",
    "walkable_distance",
    "attackable",
    "first_blood",
    "trap_activation",
    "action_id",
    "action_tag",
    "position",
}


@dataclass(frozen=True)
class FixedEnemyDirective:
    enemy_object_id: str
    position: tuple[int, int] | None = None
    config: dict[str, Any] = field(default_factory=dict)
    hidden: bool = False
    trigger_mode: str = "seek"
    reveal_dc: int = 18
    reveal_tags: tuple[str, ...] = ()
    trigger_positions: tuple[tuple[int, int], ...] = ()
    trigger_conditions: tuple[dict[str, Any], ...] = ()
    trigger_condition_mode: str = "any"
    ambush_mode: str = "join_end_of_round"


@dataclass(frozen=True)
class EncounterDirectives:
    must_include: tuple[str, ...] = ()
    fixed_enemies: tuple[FixedEnemyDirective, ...] = ()
    forbidden_cells: tuple[tuple[int, int], ...] = ()
    preferred_layout: str | None = None
    preset_id: str | None = None


@dataclass(frozen=True)
class EncounterRequest:
    biome: str
    threat: str
    seed: int
    party_level: int = 1
    party_size: int = 4
    enemy_family: str = "goblin"
    directives: EncounterDirectives = field(default_factory=EncounterDirectives)
    formation_pack: str | None = None


@dataclass(frozen=True)
class SetupBatch:
    kind: str
    object_id: str
    prompt: str
    confirmation_mode: str
    positions: tuple[tuple[int, int], ...] = ()
    edges: tuple[tuple[tuple[int, int], tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class HiddenEnemySpawnSpec:
    enemy_object_id: str
    enemy_config: dict[str, Any]
    spawn_position: tuple[int, int]
    reveal_dc: int = 18
    reveal_tags: tuple[str, ...] = ()
    trigger_mode: str = "seek"
    trigger_positions: tuple[tuple[int, int], ...] = ()
    trigger_conditions: tuple[dict[str, Any], ...] = ()
    trigger_condition_mode: str = "any"
    ambush_mode: str = "join_end_of_round"
    description_on_reveal: str | None = None


@dataclass(frozen=True)
class ResolvedEncounter:
    scenario_payload: dict[str, Any]
    setup_plan: tuple[SetupBatch, ...]
    hidden_spawns: tuple[HiddenEnemySpawnSpec, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FormationShape:
    shape_id: str
    obstacles: tuple[tuple[int, int], ...] = ()
    cover: tuple[tuple[int, int], ...] = ()
    difficult: tuple[tuple[int, int], ...] = ()
    rubble: tuple[tuple[int, int], ...] = ()
    walls: tuple[tuple[tuple[int, int], tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class FormationSlot:
    slot_id: str
    anchor: tuple[int, int]
    allowed_rotations: tuple[int, ...] = (0,)
    max_footprint: tuple[int, int] = (4, 4)
    protected_cells: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class LayoutTemplate:
    layout_id: str
    hero_starts: tuple[tuple[int, int], ...]
    enemy_positions: tuple[tuple[int, int], ...]
    hidden_enemy_positions: tuple[tuple[int, int], ...]
    blocked: tuple[tuple[int, int], ...]
    cover: tuple[tuple[int, int], ...]
    difficult: tuple[tuple[int, int], ...]
    rubble: tuple[tuple[int, int], ...]
    obstacles: tuple[tuple[int, int], ...]
    walls: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    trap_positions: tuple[tuple[int, int], ...]
    rooms: tuple[tuple[int, int], ...]
    formation_slots: tuple[FormationSlot, ...]


@dataclass(frozen=True)
class ResolvedFormation:
    pack_id: str
    slot_id: str
    shape_id: str
    anchor: tuple[int, int]
    rotation: int
    obstacles: tuple[tuple[int, int], ...] = ()
    cover: tuple[tuple[int, int], ...] = ()
    difficult: tuple[tuple[int, int], ...] = ()
    rubble: tuple[tuple[int, int], ...] = ()
    walls: tuple[tuple[tuple[int, int], tuple[int, int]], ...] = ()


@lru_cache(maxsize=32)
def _load_preset_definition(normalized_preset_id: str) -> dict[str, Any]:
    preset_path = PRESETS_DIR / f"{normalized_preset_id}.json"
    if not preset_path.exists():
        raise ValueError(f"Nieznany preset encounteru: {normalized_preset_id}")
    try:
        return json.loads(preset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Niepoprawny JSON presetu encounteru {normalized_preset_id}: {exc}") from exc


def preset_directives(preset_id: str | None) -> EncounterDirectives:
    normalized = str(preset_id or "").strip().lower()
    if normalized in RANDOM_FORMATION_VALUES:
        return EncounterDirectives()
    payload = _load_preset_definition(normalized)

    def _normalize_trigger_positions(item: dict[str, Any]) -> tuple[tuple[int, int], ...]:
        raw_positions = item.get("trigger_positions")
        if raw_positions is None and item.get("trigger_zone") is not None:
            raw_positions = [item.get("trigger_zone")]
        return tuple(tuple(pos) for pos in (raw_positions or []))

    def _normalize_trigger_condition_mode(item: dict[str, Any]) -> str:
        mode = str(item.get("trigger_condition_mode") or "any").strip().lower()
        if mode not in {"any", "all"}:
            raise ValueError(f"Nieobsługiwany trigger_condition_mode: {mode}")
        return mode

    def _normalize_ambush_mode(item: dict[str, Any]) -> str:
        mode = str(item.get("ambush_mode") or "join_end_of_round").strip().lower()
        if mode not in {"join_end_of_round", "interrupt_action"}:
            raise ValueError(f"Nieobsługiwany ambush_mode: {mode}")
        return mode

    def _normalize_trigger_conditions(item: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        raw_conditions = item.get("trigger_conditions")
        if raw_conditions is None:
            legacy_positions = _normalize_trigger_positions(item)
            if legacy_positions:
                raw_conditions = [{"kind": "position", "positions": [list(pos) for pos in legacy_positions]}]
            else:
                raw_conditions = []

        normalized: list[dict[str, Any]] = []
        for raw in list(raw_conditions or []):
            if not isinstance(raw, dict):
                raise ValueError(f"Niepoprawny trigger condition: {raw!r}")
            condition = dict(raw)
            kind = str(condition.get("kind") or "").strip().lower()
            if kind not in ALLOWED_TRIGGER_CONDITION_KINDS:
                raise ValueError(f"Nieobsługiwany trigger condition kind: {kind}")
            normalized_condition: dict[str, Any] = {"kind": kind}
            if kind == "distance":
                if "max_feet" not in condition:
                    raise ValueError("Trigger condition 'distance' wymaga pola 'max_feet'.")
                normalized_condition["max_feet"] = int(condition["max_feet"])
            elif kind == "walkable_distance":
                if "max_move_actions" not in condition:
                    raise ValueError("Trigger condition 'walkable_distance' wymaga pola 'max_move_actions'.")
                normalized_condition["max_move_actions"] = int(condition["max_move_actions"])
            elif kind == "attackable":
                scope = str(condition.get("weapon_scope") or "active").strip().lower()
                if scope != "active":
                    raise ValueError("v1 wspiera tylko attackable.weapon_scope='active'.")
                normalized_condition["weapon_scope"] = scope
            elif kind == "first_blood":
                side = str(condition.get("side") or "any").strip().lower()
                if side not in {"any", "heroes", "enemies"}:
                    raise ValueError(f"Nieobsługiwane first_blood.side: {side}")
                normalized_condition["side"] = side
            elif kind == "trap_activation":
                trap_id = str(condition.get("trap_id") or "").strip()
                if not trap_id:
                    raise ValueError("Trigger condition 'trap_activation' wymaga pola 'trap_id'.")
                normalized_condition["trap_id"] = trap_id
            elif kind in {"action_id", "action_tag"}:
                value = str(condition.get("value") or "").strip()
                if not value:
                    raise ValueError(f"Trigger condition '{kind}' wymaga pola 'value'.")
                normalized_condition["value"] = value
            elif kind == "position":
                raw_positions = condition.get("positions")
                if raw_positions is None:
                    raise ValueError("Trigger condition 'position' wymaga pola 'positions'.")
                positions = [tuple(map(int, pos)) for pos in list(raw_positions or [])]
                if not positions:
                    raise ValueError("Trigger condition 'position' wymaga niepustej listy positions.")
                normalized_condition["positions"] = [list(pos) for pos in positions]
            normalized.append(normalized_condition)
        return tuple(normalized)

    fixed_enemies = tuple(
        FixedEnemyDirective(
            enemy_object_id=str(item.get("enemy_object_id") or "").strip(),
            position=tuple(item["position"]) if item.get("position") is not None else None,
            config=dict(item.get("config") or {}),
            hidden=bool(item.get("hidden", False)),
            trigger_mode=str(item.get("trigger_mode") or "seek"),
            reveal_dc=int(item.get("reveal_dc", 18)),
            reveal_tags=tuple(item.get("reveal_tags") or ()),
            trigger_positions=_normalize_trigger_positions(item),
            trigger_conditions=_normalize_trigger_conditions(item),
            trigger_condition_mode=_normalize_trigger_condition_mode(item),
            ambush_mode=_normalize_ambush_mode(item),
        )
        for item in (payload.get("fixed_enemies") or [])
    )
    return EncounterDirectives(
        must_include=tuple(str(item).strip() for item in (payload.get("must_include") or []) if str(item).strip()),
        fixed_enemies=fixed_enemies,
        forbidden_cells=tuple(tuple(pos) for pos in (payload.get("forbidden_cells") or [])),
        preferred_layout=str(payload.get("preferred_layout")).strip() if payload.get("preferred_layout") is not None else None,
        preset_id=str(payload.get("preset_id") or normalized).strip() or normalized,
    )


def _encounter_budget(request: EncounterRequest) -> int:
    base = THREAT_BUDGETS[str(request.threat or "moderate").strip().lower()]
    diff = max(-2, min(2, int(request.party_size) - 4))
    if diff == 0:
        return int(base)
    adjustment = PARTY_SIZE_ADJUSTMENT[str(request.threat or "moderate").strip().lower()]
    return int(base + diff * adjustment)


def _enemy_xp(enemy_object_id: str, party_level: int) -> int:
    enemy_level = int(ENEMY_LEVELS[enemy_object_id])
    delta = max(-4, min(4, enemy_level - int(party_level)))
    return int(ENEMY_XP_BY_DELTA[delta])


def _normalize_forbidden(directives: EncounterDirectives) -> set[tuple[int, int]]:
    return {tuple(map(int, pos)) for pos in (directives.forbidden_cells or ())}


def _condition_positions(trigger_conditions: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None) -> tuple[tuple[int, int], ...]:
    positions: list[tuple[int, int]] = []
    for condition in list(trigger_conditions or []):
        if str(condition.get("kind") or "").strip().lower() != "position":
            continue
        for raw_pos in list(condition.get("positions") or []):
            positions.append(tuple(map(int, raw_pos)))
    return tuple(positions)


def _pick_layout(request: EncounterRequest, rng: random.Random) -> str:
    preferred = str(request.directives.preferred_layout or "").strip().lower()
    if preferred:
        return preferred
    options = list(SUPPORTED_LAYOUTS)
    if str(request.biome).strip().lower() == "ruined_village":
        weights = [2, 3, 5]
    else:
        weights = [4, 4, 2]
    return rng.choices(options, weights=weights, k=1)[0]


def _enemy_name(enemy_object_id: str, index: int) -> str:
    base = ENEMY_LABELS.get(enemy_object_id, enemy_object_id.replace("_", " ").title())
    if enemy_object_id == "goblin_warrior":
        suffix = chr(ord("A") + max(0, index - 1))
        return f"{base} {suffix}"
    if index > 1:
        return f"{base} {index}"
    return base


def _rotate_rel(pos: tuple[int, int], rotation: int) -> tuple[int, int]:
    x, y = map(int, pos)
    turns = int(rotation) % 4
    if turns == 0:
        return (x, y)
    if turns == 1:
        return (y, -x)
    if turns == 2:
        return (-x, -y)
    return (-y, x)


def _normalize_rotated_cells(cells: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    if not cells:
        return ()
    min_x = min(pos[0] for pos in cells)
    min_y = min(pos[1] for pos in cells)
    return tuple((pos[0] - min_x, pos[1] - min_y) for pos in cells)


def _stamp_relative_positions(
    positions: tuple[tuple[int, int], ...],
    *,
    anchor: tuple[int, int],
    rotation: int,
) -> tuple[tuple[int, int], ...]:
    rotated = tuple(_rotate_rel(pos, rotation) for pos in positions)
    normalized = _normalize_rotated_cells(rotated)
    ax, ay = map(int, anchor)
    return tuple((ax + pos[0], ay + pos[1]) for pos in normalized)


def _stamp_formation_geometry(
    shape: FormationShape,
    *,
    anchor: tuple[int, int],
    rotation: int,
) -> dict[str, tuple]:
    rotated_obstacles = tuple(_rotate_rel(pos, rotation) for pos in shape.obstacles)
    rotated_cover = tuple(_rotate_rel(pos, rotation) for pos in shape.cover)
    rotated_difficult = tuple(_rotate_rel(pos, rotation) for pos in shape.difficult)
    rotated_rubble = tuple(_rotate_rel(pos, rotation) for pos in shape.rubble)
    rotated_wall_points = tuple(_rotate_rel(point, rotation) for edge in shape.walls for point in edge)

    footprint_source = rotated_obstacles + rotated_cover + rotated_difficult + rotated_rubble + rotated_wall_points
    normalized_all = _normalize_rotated_cells(footprint_source)
    if footprint_source:
        min_x = min(pos[0] for pos in footprint_source)
        min_y = min(pos[1] for pos in footprint_source)
    else:
        min_x = 0
        min_y = 0

    def _shift_and_translate(points: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
        if not points:
            return ()
        ax, ay = map(int, anchor)
        return tuple((ax + pos[0] - min_x, ay + pos[1] - min_y) for pos in points)

    obstacle_cells = _shift_and_translate(rotated_obstacles)
    cover_cells = _shift_and_translate(rotated_cover)
    difficult_cells = _shift_and_translate(rotated_difficult)
    rubble_cells = _shift_and_translate(rotated_rubble)
    shifted_wall_points = _shift_and_translate(rotated_wall_points)
    stamped_walls = tuple(
        (shifted_wall_points[index], shifted_wall_points[index + 1])
        for index in range(0, len(shifted_wall_points), 2)
    )

    footprint_cells = tuple(
        (anchor[0] + pos[0], anchor[1] + pos[1])
        for pos in normalized_all
    )
    width = 0
    height = 0
    if footprint_cells:
        xs = [pos[0] for pos in footprint_cells]
        ys = [pos[1] for pos in footprint_cells]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
    return {
        "obstacles": obstacle_cells,
        "cover": cover_cells,
        "difficult": difficult_cells,
        "rubble": rubble_cells,
        "walls": stamped_walls,
        "width": width,
        "height": height,
    }


def _formation_library() -> dict[str, tuple[FormationShape, ...]]:
    return {
        "fortifications": (
            FormationShape(
                shape_id="screen_line",
                obstacles=((0, 0), (1, 0), (2, 0)),
                cover=((0, 1), (1, 1), (2, 1)),
                walls=(((0, 0), (1, 0)), ((1, 0), (2, 0))),
            ),
            FormationShape(
                shape_id="bunker_L",
                obstacles=((0, 0), (0, 1), (1, 1)),
                cover=((1, 0), (2, 1)),
                difficult=((1, 2),),
                walls=(((0, 1), (0, 2)), ((0, 2), (1, 2))),
            ),
            FormationShape(
                shape_id="wall_window",
                obstacles=((0, 0), (2, 0), (0, 1), (2, 1)),
                cover=((1, 1),),
                difficult=((1, 0),),
                walls=(((0, 2), (1, 2)), ((1, 2), (2, 2))),
            ),
        ),
        "ruins": (
            FormationShape(
                shape_id="u_bend",
                obstacles=((0, 0), (2, 0), (0, 1), (1, 1), (2, 1)),
                cover=((0, 2), (2, 2)),
                difficult=((1, 0),),
                rubble=((1, 2),),
            ),
            FormationShape(
                shape_id="rubble_island",
                obstacles=((1, 1),),
                cover=((1, 0), (0, 1), (2, 1)),
                difficult=((1, 2),),
                rubble=((0, 0), (2, 0), (0, 2), (2, 2)),
            ),
            FormationShape(
                shape_id="broken_tetris",
                obstacles=((0, 0), (1, 0), (1, 1), (2, 1)),
                difficult=((1, 2),),
                rubble=((0, 1), (2, 0)),
                walls=(((0, 2), (1, 2)),),
            ),
        ),
        "serpentine": (
            FormationShape(
                shape_id="zigzag",
                obstacles=((0, 0), (1, 0), (1, 1), (2, 1)),
                cover=((0, 2), (2, 2)),
                difficult=((0, 1), (2, 0)),
            ),
            FormationShape(
                shape_id="hook_turn",
                obstacles=((0, 0), (0, 1), (1, 1)),
                cover=((1, 0), (2, 1)),
                difficult=((1, 2), (2, 2)),
                walls=(((1, 1), (2, 1)),),
            ),
            FormationShape(
                shape_id="narrow_gate",
                obstacles=((0, 0), (2, 0), (0, 1), (2, 1)),
                cover=((1, 2),),
                difficult=((1, 0), (1, 1)),
                walls=(((0, 2), (0, 3)), ((2, 2), (2, 3))),
            ),
        ),
    }


def _layout_templates() -> dict[str, LayoutTemplate]:
    all_positions = tuple((col, row) for row in range(ROWS) for col in range(COLS))
    return {
        "open_field": LayoutTemplate(
            layout_id="open_field",
            hero_starts=((1, 11), (2, 11), (3, 11), (1, 12), (2, 12), (3, 12)),
            enemy_positions=((14, 3), (16, 5), (17, 7), (18, 10), (15, 10), (13, 8)),
            hidden_enemy_positions=((16, 3), (17, 4), (18, 4)),
            blocked=((7, 5), (8, 5), (11, 5), (12, 5)),
            cover=((5, 8), (15, 4)),
            difficult=((4, 13), (5, 13), (16, 9), (17, 9)),
            rubble=((8, 10), (9, 10), (12, 12), (13, 12)),
            obstacles=(),
            walls=(((6, 6), (7, 6)), ((12, 8), (13, 8))),
            trap_positions=((8, 11), (14, 8)),
            rooms=all_positions,
            formation_slots=(
                FormationSlot("north_west_screen", anchor=(3, 3), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((1, 11), (2, 11), (3, 11))),
                FormationSlot("center_lane", anchor=(8, 7), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((8, 11),)),
                FormationSlot("north_mid", anchor=(10, 1), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((14, 3), (16, 3), (17, 4))),
            ),
        ),
        "split_lanes": LayoutTemplate(
            layout_id="split_lanes",
            hero_starts=((0, 6), (1, 6), (2, 6), (0, 7), (1, 7), (2, 7)),
            enemy_positions=((7, 8), (12, 7), (16, 2), (18, 11), (18, 8), (15, 7)),
            hidden_enemy_positions=((16, 3), (17, 10), (18, 10)),
            blocked=((8, 5), (9, 5), (8, 6), (9, 6), (11, 9), (12, 9), (11, 10), (12, 10)),
            cover=((4, 4), (16, 2), (16, 3)),
            difficult=((17, 10), (18, 10), (17, 11), (18, 11)),
            rubble=((3, 6), (4, 6), (13, 7), (14, 7)),
            obstacles=(),
            walls=(((7, 4), (8, 4)), ((14, 8), (15, 8))),
            trap_positions=((9, 7), (15, 6)),
            rooms=all_positions,
            formation_slots=(
                FormationSlot("top_lane", anchor=(3, 2), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((0, 6), (1, 6), (2, 6))),
                FormationSlot("mid_bridge", anchor=(9, 1), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((12, 7), (15, 6))),
                FormationSlot("south_lane", anchor=(13, 8), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((18, 8), (18, 11), (17, 10), (18, 10))),
            ),
        ),
        "chokepoints": LayoutTemplate(
            layout_id="chokepoints",
            hero_starts=((0, 7), (1, 7), (2, 7), (0, 8), (1, 8), (2, 8)),
            enemy_positions=((7, 8), (13, 7), (17, 4), (18, 12), (16, 6), (12, 5)),
            hidden_enemy_positions=((17, 5), (16, 4), (15, 6)),
            blocked=((5, 3), (6, 3), (5, 4), (6, 4), (10, 9), (11, 9), (10, 10), (11, 10)),
            cover=((17, 5), (14, 6), (4, 8)),
            difficult=((13, 8), (14, 8), (15, 8), (16, 8)),
            rubble=((3, 7), (4, 7), (9, 8), (10, 8), (11, 8)),
            obstacles=(),
            walls=(((6, 5), (7, 5)), ((15, 5), (16, 5))),
            trap_positions=((8, 7), (13, 6)),
            rooms=all_positions,
            formation_slots=(
                FormationSlot("left_hook", anchor=(2, 4), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((0, 7), (1, 7), (2, 7), (4, 8))),
                FormationSlot("upper_choke", anchor=(8, 1), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((12, 5), (13, 6), (13, 7))),
                FormationSlot("lower_right", anchor=(13, 9), allowed_rotations=(0, 1, 2, 3), max_footprint=(4, 4), protected_cells=((16, 8), (18, 12), (13, 7))),
            ),
        ),
    }


def _pick_formation_pack(request: EncounterRequest, layout_id: str, rng: random.Random) -> str:
    requested = str(request.formation_pack or "").strip().lower()
    if requested and requested not in RANDOM_FORMATION_VALUES:
        if requested not in SUPPORTED_FORMATION_PACKS:
            raise ValueError(f"Nieobsługiwana paczka formacji: {request.formation_pack}")
        return requested

    biome = str(request.biome or "").strip().lower()
    options = list(SUPPORTED_FORMATION_PACKS)
    if biome == "ruined_village":
        weights = [2, 6, 2]
    elif layout_id == "split_lanes":
        weights = [5, 2, 3]
    else:
        weights = [2, 2, 6]
    return rng.choices(options, weights=weights, k=1)[0]


def _protected_positions_for_formations(
    request: EncounterRequest,
    layout: LayoutTemplate,
    forbidden: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    protected = set(layout.hero_starts)
    protected.update(layout.enemy_positions)
    protected.update(layout.hidden_enemy_positions)
    protected.update(layout.trap_positions)
    protected.update(layout.blocked)
    protected.update(layout.obstacles)
    protected.update(forbidden)
    for directive in request.directives.fixed_enemies or ():
        if directive.position is not None:
            protected.add(tuple(map(int, directive.position)))
        for trigger_pos in directive.trigger_positions or ():
            protected.add(tuple(map(int, trigger_pos)))
        for trigger_pos in _condition_positions(directive.trigger_conditions):
            protected.add(tuple(map(int, trigger_pos)))
    return protected


def _base_wall_edges(layout: LayoutTemplate) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for a, b in layout.walls:
        first = tuple(map(int, a))
        second = tuple(map(int, b))
        edges.add((first, second) if first < second else (second, first))
    return edges


def _occupied_base_cells(layout: LayoutTemplate) -> set[tuple[int, int]]:
    occupied = set(layout.blocked)
    occupied.update(layout.obstacles)
    return occupied


def _choose_formations(
    request: EncounterRequest,
    layout: LayoutTemplate,
    pack_id: str,
    rng: random.Random,
) -> tuple[ResolvedFormation, ...]:
    shapes = list(_formation_library()[pack_id])
    slots = list(layout.formation_slots)
    if len(shapes) < 2 or len(slots) < 2:
        return ()

    chosen_shapes = rng.sample(shapes, k=2)
    chosen_slots = rng.sample(slots, k=2)

    protected_cells = _protected_positions_for_formations(request, layout, _normalize_forbidden(request.directives))
    occupied_cells = _occupied_base_cells(layout)
    occupied_wall_edges = _base_wall_edges(layout)
    placed_cells: set[tuple[int, int]] = set()
    placed_wall_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    resolved: list[ResolvedFormation] = []

    for shape, slot in zip(chosen_shapes, chosen_slots):
        rotation = rng.choice(list(slot.allowed_rotations or (0,)))
        stamped = _stamp_formation_geometry(shape, anchor=slot.anchor, rotation=rotation)
        width = int(stamped["width"])
        height = int(stamped["height"])
        if width > int(slot.max_footprint[0]) or height > int(slot.max_footprint[1]):
            raise ValueError(f"Formacja {shape.shape_id} nie mieści się w slocie {slot.slot_id}.")

        cell_positions = set(stamped["obstacles"]) | set(stamped["cover"]) | set(stamped["difficult"]) | set(stamped["rubble"])
        cell_positions.update(point for edge in stamped["walls"] for point in edge)
        if any(not (0 <= col < COLS and 0 <= row < ROWS) for col, row in cell_positions):
            raise ValueError(f"Formacja {shape.shape_id} wychodzi poza planszę w slocie {slot.slot_id}.")
        if cell_positions & set(slot.protected_cells):
            raise ValueError(f"Formacja {shape.shape_id} narusza chronione pola slotu {slot.slot_id}.")
        if cell_positions & protected_cells:
            raise ValueError(f"Formacja {shape.shape_id} koliduje z chronioną geometrią encounteru.")
        if cell_positions & occupied_cells:
            raise ValueError(f"Formacja {shape.shape_id} koliduje z bazową geometrią layoutu.")
        if cell_positions & placed_cells:
            raise ValueError(f"Formacja {shape.shape_id} koliduje z inną formacją.")

        normalized_edges = {
            (edge[0], edge[1]) if edge[0] < edge[1] else (edge[1], edge[0])
            for edge in stamped["walls"]
        }
        if normalized_edges & occupied_wall_edges:
            raise ValueError(f"Formacja {shape.shape_id} koliduje z bazową ścianą layoutu.")
        if normalized_edges & placed_wall_edges:
            raise ValueError(f"Formacja {shape.shape_id} koliduje ze ścianą innej formacji.")

        placed_cells.update(cell_positions)
        placed_wall_edges.update(normalized_edges)
        resolved.append(
            ResolvedFormation(
                pack_id=pack_id,
                slot_id=slot.slot_id,
                shape_id=shape.shape_id,
                anchor=slot.anchor,
                rotation=rotation,
                obstacles=tuple(stamped["obstacles"]),
                cover=tuple(stamped["cover"]),
                difficult=tuple(stamped["difficult"]),
                rubble=tuple(stamped["rubble"]),
                walls=tuple(stamped["walls"]),
            )
        )
    return tuple(resolved)


def _build_roster(request: EncounterRequest, layout: LayoutTemplate, rng: random.Random) -> tuple[list[dict[str, Any]], list[HiddenEnemySpawnSpec], int]:
    budget = _encounter_budget(request)
    spent = 0
    visible: list[dict[str, Any]] = []
    hidden_specs: list[HiddenEnemySpawnSpec] = []
    visible_positions = list(layout.enemy_positions)
    hidden_positions = list(layout.hidden_enemy_positions)
    forbidden = _normalize_forbidden(request.directives)
    visible_positions = [pos for pos in visible_positions if pos not in forbidden]
    hidden_positions = [pos for pos in hidden_positions if pos not in forbidden]

    def reserve_position(explicit: tuple[int, int] | None, *, hidden: bool) -> tuple[int, int] | None:
        pool = hidden_positions if hidden else visible_positions
        if explicit is not None:
            pos = tuple(map(int, explicit))
            if pos in forbidden:
                raise ValueError(f"Pole {pos} jest zabronione przez directives.")
            if pos in pool:
                pool.remove(pos)
            return pos
        if not pool:
            return None
        return pool.pop(0)

    def add_enemy(
        enemy_object_id: str,
        *,
        hidden: bool,
        config: dict[str, Any] | None = None,
        position: tuple[int, int] | None = None,
        trigger_mode: str = "seek",
        reveal_dc: int = 18,
        reveal_tags: tuple[str, ...] = (),
        trigger_positions: tuple[tuple[int, int], ...] = (),
        trigger_conditions: tuple[dict[str, Any], ...] = (),
        trigger_condition_mode: str = "any",
        ambush_mode: str = "join_end_of_round",
    ) -> None:
        nonlocal spent
        xp = _enemy_xp(enemy_object_id, request.party_level)
        pos = reserve_position(position, hidden=hidden)
        if pos is None:
            raise ValueError("Brak dostępnych pozycji dla przeciwnika.")
        final_config = dict(config or {})
        if hidden:
            normalized_trigger_positions = tuple(tuple(map(int, pos)) for pos in (trigger_positions or ()))
            normalized_trigger_conditions = tuple(dict(item) for item in (trigger_conditions or ()))
            if not normalized_trigger_positions and not normalized_trigger_conditions and str(trigger_mode or "").strip().lower() in {"on_enter", "seek_or_on_enter"}:
                normalized_trigger_positions = (pos,)
            if not normalized_trigger_conditions and normalized_trigger_positions:
                normalized_trigger_conditions = (
                    {
                        "kind": "position",
                        "positions": [list(item) for item in normalized_trigger_positions],
                    },
                )
            hidden_specs.append(
                HiddenEnemySpawnSpec(
                    enemy_object_id=enemy_object_id,
                    enemy_config=final_config,
                    spawn_position=pos,
                    reveal_dc=int(reveal_dc),
                    reveal_tags=tuple(reveal_tags or ()),
                    trigger_mode=str(trigger_mode or "seek"),
                    trigger_positions=normalized_trigger_positions,
                    trigger_conditions=normalized_trigger_conditions,
                    trigger_condition_mode=str(trigger_condition_mode or "any"),
                    ambush_mode=str(ambush_mode or "join_end_of_round"),
                    description_on_reveal=f"Zasadzka! {ENEMY_LABELS.get(enemy_object_id, enemy_object_id)} wychodzi z ukrycia.",
                )
            )
        else:
            visible.append(
                {
                    "object_id": enemy_object_id,
                    "position": pos,
                    "config": final_config,
                }
            )
        spent += xp

    fixed = list(request.directives.fixed_enemies or ())
    for directive in fixed:
        if spent + _enemy_xp(directive.enemy_object_id, request.party_level) > budget:
            raise ValueError("Fixed enemy directives przekraczają budżet encounteru.")
        add_enemy(
            directive.enemy_object_id,
            hidden=bool(directive.hidden),
            config=dict(directive.config or {}),
            position=directive.position,
            trigger_mode=directive.trigger_mode,
            reveal_dc=directive.reveal_dc,
            reveal_tags=tuple(directive.reveal_tags or ()),
            trigger_positions=tuple(directive.trigger_positions or ()),
            trigger_conditions=tuple(dict(item) for item in (directive.trigger_conditions or ())),
            trigger_condition_mode=directive.trigger_condition_mode,
            ambush_mode=directive.ambush_mode,
        )

    must_include = list(request.directives.must_include or ())
    for enemy_object_id in must_include:
        if any(item["object_id"] == enemy_object_id for item in visible) or any(spec.enemy_object_id == enemy_object_id for spec in hidden_specs):
            continue
        xp = _enemy_xp(enemy_object_id, request.party_level)
        if spent + xp > budget:
            continue
        add_enemy(enemy_object_id, hidden=False)

    weighted_choices = [
        ("goblin_warrior", 5),
        ("goblin_dog", 3),
        ("goblin_commando", 2 if request.threat in {"moderate", "severe", "extreme"} else 1),
    ]
    while True:
        available = [(enemy_id, weight) for enemy_id, weight in weighted_choices if spent + _enemy_xp(enemy_id, request.party_level) <= budget]
        if not available:
            break
        enemy_id = rng.choices([item[0] for item in available], weights=[item[1] for item in available], k=1)[0]
        add_enemy(enemy_id, hidden=False)
        if len(visible) >= 6:
            break

    if not visible:
        if spent + _enemy_xp("goblin_warrior", request.party_level) > budget:
            raise ValueError("Budżet encounteru nie pozwala na żadnego widocznego przeciwnika.")
        add_enemy("goblin_warrior", hidden=False)

    if request.directives.preset_id == "commando_ambush" and hidden_specs:
        pass
    elif request.threat in {"severe", "extreme"} and hidden_positions and spent + _enemy_xp("goblin_warrior", request.party_level) <= budget:
        add_enemy(
            "goblin_warrior",
            hidden=True,
            trigger_mode="seek_or_on_enter",
            reveal_dc=18,
            reveal_tags=("undetected", "ambush"),
            trigger_positions=(),
            trigger_conditions=(),
            trigger_condition_mode="any",
            ambush_mode="join_end_of_round",
        )

    for index, item in enumerate(visible, start=1):
        config = dict(item["config"])
        config.setdefault("name", _enemy_name(item["object_id"], index))
        item["config"] = config
    for index, item in enumerate(hidden_specs, start=1):
        cfg = dict(item.enemy_config)
        cfg.setdefault("name", _enemy_name(item.enemy_object_id, len(visible) + index))
        hidden_specs[index - 1] = HiddenEnemySpawnSpec(
            enemy_object_id=item.enemy_object_id,
            enemy_config=cfg,
            spawn_position=item.spawn_position,
            reveal_dc=item.reveal_dc,
            reveal_tags=item.reveal_tags,
            trigger_mode=item.trigger_mode,
            trigger_positions=item.trigger_positions,
            trigger_conditions=tuple(dict(cond) for cond in (item.trigger_conditions or ())),
            trigger_condition_mode=item.trigger_condition_mode,
            ambush_mode=item.ambush_mode,
            description_on_reveal=item.description_on_reveal,
        )

    return visible, hidden_specs, spent


def _terrain_object_id_for_biome(biome: str, zone_name: str) -> str:
    biome = str(biome or "forest").strip().lower()
    if zone_name == "cover":
        return "forest_field" if biome == "forest" else "rumble_field"
    if zone_name == "difficult":
        return "bushes_field" if biome == "forest" else "rumble_field"
    return zone_name


def _combine_positions(
    base: tuple[tuple[int, int], ...],
    formations: tuple[ResolvedFormation, ...],
    attr_name: str,
) -> list[list[int]]:
    combined = list(base)
    for formation in formations:
        combined.extend(getattr(formation, attr_name))
    unique_positions: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for pos in combined:
        normalized = tuple(pos)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_positions.append(normalized)
    return [list(pos) for pos in unique_positions]


def _combine_edges(
    base: tuple[tuple[tuple[int, int], tuple[int, int]], ...],
    formations: tuple[ResolvedFormation, ...],
) -> list[dict[str, list[int]]]:
    edges = list(base)
    for formation in formations:
        edges.extend(formation.walls)
    return [{"a": list(a), "b": list(b)} for a, b in edges]


def _build_setup_plan(payload: dict[str, Any]) -> tuple[SetupBatch, ...]:
    batches: list[SetupBatch] = []
    for obj in list(payload.get("objects") or []):
        category = str(obj.get("category") or "")
        object_id = str(obj.get("object_id") or "")
        if category == "Terrains":
            positions = tuple(tuple(pos) for pos in (obj.get("positions") or []))
            if not positions:
                continue
            prompt = {
                "blocked_field": "Ustaw pola zablokowane na podświetlonych polach.",
                "forest_field": "Ustaw pola osłony na podświetlonych polach.",
                "bushes_field": "Ustaw trudny teren na podświetlonych polach.",
                "rumble_field": "Ustaw rumowiska na podświetlonych polach.",
            }.get(object_id, "Ustaw elementy terenu na podświetlonych polach.")
            batches.append(
                SetupBatch(
                    kind="terrain",
                    object_id=object_id,
                    prompt=prompt,
                    confirmation_mode="click_all",
                    positions=positions,
                )
            )
        elif category == "Obstacles":
            positions = tuple(tuple(pos) for pos in (obj.get("positions") or []))
            if positions:
                batches.append(
                    SetupBatch(
                        kind="obstacles",
                        object_id=object_id,
                        prompt="Ustaw przeszkody na podświetlonych polach.",
                        confirmation_mode="click_all",
                        positions=positions,
                    )
                )
        elif category == "Walls":
            edges = tuple((tuple(edge["a"]), tuple(edge["b"])) for edge in (obj.get("edges") or []))
            if edges:
                endpoints = tuple(sorted({tuple(a) for a, _ in edges}.union({tuple(b) for _, b in edges})))
                batches.append(
                    SetupBatch(
                        kind="walls",
                        object_id=object_id,
                        prompt="Ustaw ściany zgodnie z podświetlonymi krawędziami i potwierdź w UI.",
                        confirmation_mode="confirm_only",
                        positions=endpoints,
                        edges=edges,
                    )
                )
        elif category == "Enemies":
            instances = obj.get("instances") or []
            positions = tuple(tuple(inst.get("position")) for inst in instances if inst.get("position") is not None)
            if positions:
                batches.append(
                    SetupBatch(
                        kind="visible_enemies",
                        object_id=object_id,
                        prompt=f"Ustaw {ENEMY_LABELS.get(object_id, object_id)} na podświetlonych polach.",
                        confirmation_mode="click_all",
                        positions=positions,
                    )
                )
    return tuple(batches)


def _scenario_payload(
    request: EncounterRequest,
    layout: LayoutTemplate,
    visible: list[dict[str, Any]],
    hidden_specs: list[HiddenEnemySpawnSpec],
    xp_total: int,
    *,
    formation_pack: str,
    formations: tuple[ResolvedFormation, ...],
) -> dict[str, Any]:
    biome = str(request.biome).strip().lower()
    cover_object_id = _terrain_object_id_for_biome(biome, "cover")
    difficult_object_id = _terrain_object_id_for_biome(biome, "difficult")
    objects: list[dict[str, Any]] = [
        {
            "category": "Terrains",
            "object_id": "blocked_field",
            "placement": "cell",
            "positions": [list(pos) for pos in layout.blocked],
        },
        {
            "category": "Terrains",
            "object_id": cover_object_id,
            "placement": "cell",
            "positions": _combine_positions(layout.cover, formations, "cover"),
        },
        {
            "category": "Terrains",
            "object_id": difficult_object_id,
            "placement": "cell",
            "positions": _combine_positions(layout.difficult, formations, "difficult"),
        },
        {
            "category": "Terrains",
            "object_id": "rumble_field",
            "placement": "cell",
            "positions": _combine_positions(layout.rubble, formations, "rubble"),
        },
        {
            "category": "Obstacles",
            "object_id": "simple_obstacle",
            "placement": "cell",
            "positions": _combine_positions(layout.obstacles, formations, "obstacles"),
        },
        {
            "category": "Walls",
            "object_id": "simple_wall",
            "placement": "edge",
            "edges": _combine_edges(layout.walls, formations),
        },
    ]

    by_enemy: dict[str, list[dict[str, Any]]] = {}
    for item in visible:
        by_enemy.setdefault(item["object_id"], []).append(
            {
                "position": list(item["position"]),
                "config": dict(item["config"]),
            }
        )
    for enemy_object_id, instances in by_enemy.items():
        objects.append(
            {
                "category": "Enemies",
                "object_id": enemy_object_id,
                "placement": "cell",
                "instances": instances,
            }
        )

    if layout.trap_positions:
        objects.append(
            {
                "category": "Interactables",
                "object_id": "dart_launcher_trap",
                "placement": "cell",
                "instances": [
                    {
                        "position": list(pos),
                        "config": {},
                    }
                    for pos in layout.trap_positions
                ],
            }
        )

    if hidden_specs:
        hidden_instances: list[dict[str, Any]] = []
        for index, spec in enumerate(hidden_specs, start=1):
            trigger_positions = tuple(spec.trigger_positions or _condition_positions(spec.trigger_conditions) or (spec.spawn_position,))
            for trigger_pos in trigger_positions:
                hidden_instances.append(
                    {
                        "position": list(trigger_pos),
                        "config": {
                            "enemy_object_id": spec.enemy_object_id,
                            "enemy_config": dict(spec.enemy_config),
                            "spawn_position": list(spec.spawn_position),
                            "reveal_dc": spec.reveal_dc,
                            "reveal_tags": list(spec.reveal_tags),
                            "trigger_mode": spec.trigger_mode,
                            "trigger_positions": [list(pos) for pos in trigger_positions],
                            "trigger_conditions": [dict(condition) for condition in spec.trigger_conditions],
                            "trigger_condition_mode": spec.trigger_condition_mode,
                            "ambush_mode": spec.ambush_mode,
                            "spawn_group_id": f"hidden_spawn:{index}:{spec.enemy_object_id}:{spec.spawn_position[0]}:{spec.spawn_position[1]}",
                            "description_on_reveal": spec.description_on_reveal,
                        },
                    }
                )
        objects.append(
            {
                "category": "Interactables",
                "object_id": "hidden_enemy_spawn",
                "placement": "cell",
                "instances": hidden_instances,
            }
        )

    metadata = {
        "flow": "combat_only",
        "scenario_type": "encounter",
        "biome": biome,
        "layout": layout.layout_id,
        "seed": int(request.seed),
        "threat": str(request.threat),
        "xp_budget": _encounter_budget(request),
        "xp_total": int(xp_total),
        "party_level": int(request.party_level),
        "party_size": int(request.party_size),
        "formation_pack": formation_pack,
        "formations_used": [
            {
                "pack_id": formation.pack_id,
                "slot_id": formation.slot_id,
                "shape_id": formation.shape_id,
                "anchor": list(formation.anchor),
                "rotation": int(formation.rotation),
            }
            for formation in formations
        ],
    }
    return {
        "name": f"Encounter {biome} {layout.layout_id}",
        "description": f"Proceduralny encounter {biome}, threat {request.threat}.",
        "mode": "encounter",
        "metadata": metadata,
        "starting_positions": [list(pos) for pos in layout.hero_starts],
        "objects": objects,
        "rooms": [
            {
                "id": "encounter_zone",
                "name": "Strefa encounteru",
                "positions": [list(pos) for pos in layout.rooms],
            }
        ],
    }


def _validate_payload(payload: dict[str, Any]) -> None:
    board = BoardGrid(rows=ROWS, cols=COLS)
    for obj in list(payload.get("objects") or []):
        category = str(obj.get("category") or "")
        object_id = str(obj.get("object_id") or "")
        if category == "Terrains":
            for raw_pos in list(obj.get("positions") or []):
                pos = tuple(raw_pos)
                if object_id == "blocked_field":
                    board.set_field(pos, BlockedField())
        elif category == "Obstacles":
            for raw_pos in list(obj.get("positions") or []):
                board.place(SimpleObstacle(), tuple(raw_pos))
        elif category == "Walls":
            for edge in list(obj.get("edges") or []):
                board.add_wall(tuple(edge["a"]), tuple(edge["b"]), wall_cls=SimpleWall)
    hero_starts = [tuple(pos) for pos in list(payload.get("starting_positions") or [])]
    enemy_positions: list[tuple[int, int]] = []
    for obj in list(payload.get("objects") or []):
        if str(obj.get("category") or "") != "Enemies":
            continue
        for instance in list(obj.get("instances") or []):
            pos = instance.get("position")
            if pos is not None:
                enemy_positions.append(tuple(pos))
    if not hero_starts or not enemy_positions:
        raise ValueError("Encounter wymaga startów bohaterów i widocznych przeciwników.")
    for hero_pos in hero_starts:
        if not board.in_bounds(hero_pos):
            raise ValueError(f"Pozycja startowa bohatera poza planszą: {hero_pos}")
        if not board.can_enter(hero_pos, allow_occupied=True):
            raise ValueError(f"Nieprawidłowa pozycja startowa bohatera: {hero_pos}")
    for enemy_pos in enemy_positions:
        if not board.in_bounds(enemy_pos):
            raise ValueError(f"Pozycja przeciwnika poza planszą: {enemy_pos}")


def generate_encounter(request: EncounterRequest) -> ResolvedEncounter:
    biome = str(request.biome or "").strip().lower()
    threat = str(request.threat or "").strip().lower()
    if biome not in SUPPORTED_BIOMES:
        raise ValueError(f"Nieobsługiwany biome: {request.biome}")
    if threat not in THREAT_BUDGETS:
        raise ValueError(f"Nieobsługiwany threat: {request.threat}")
    if str(request.enemy_family or "").strip().lower() != "goblin":
        raise ValueError("v1 obsługuje tylko rodzinę goblinów.")

    rng = random.Random(int(request.seed))
    templates = _layout_templates()
    layout_id = _pick_layout(request, rng)
    if layout_id not in templates:
        raise ValueError(f"Nieobsługiwany layout: {layout_id}")
    layout = templates[layout_id]
    formation_pack = _pick_formation_pack(request, layout_id, rng)
    formations = _choose_formations(request, layout, formation_pack, rng)
    visible, hidden_specs, xp_total = _build_roster(request, layout, rng)
    payload = _scenario_payload(
        request,
        layout,
        visible,
        hidden_specs,
        xp_total,
        formation_pack=formation_pack,
        formations=formations,
    )
    _validate_payload(payload)
    setup_plan = _build_setup_plan(payload)
    metadata = dict(payload["metadata"])
    metadata["hidden_spawns"] = [asdict(spec) for spec in hidden_specs]
    payload["setup_plan"] = [asdict(batch) for batch in setup_plan]
    return ResolvedEncounter(
        scenario_payload=payload,
        setup_plan=setup_plan,
        hidden_spawns=tuple(hidden_specs),
        metadata=metadata,
    )
