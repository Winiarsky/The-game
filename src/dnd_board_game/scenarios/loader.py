from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import AttackSource, AttackSourceType, EnvironmentSetupEntry, EnvironmentSetupType, SetupVisibility
from dnd_board_game.rules import D20RollRequest, RollModifier, RollModifierType
from dnd_board_game.world import BoardDimensions, BoardState, Coordinate


@dataclass(frozen=True, slots=True)
class ScenarioAttackDefinition:
    id: str
    name: str
    source_type: AttackSourceType
    range_feet: int
    attack_modifier: int
    damage_fixed: int | None
    damage_die_sides: int | None
    damage_modifier: int
    damage_type: str


@dataclass(frozen=True, slots=True)
class ScenarioActorDefinition:
    id: str
    name: str
    kind: str
    faction: Faction
    ac: int
    hp: int
    temp_hp: int
    speed_feet: int
    position: Coordinate
    ability_scores: AbilityScores
    attacks: tuple[ScenarioAttackDefinition, ...]
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioEnvironmentDefinition:
    id: str
    name: str
    setup_type: EnvironmentSetupType
    positions: tuple[Coordinate, ...]
    visibility: SetupVisibility
    description: str = ""


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    id: str
    name: str
    board_dimensions: BoardDimensions
    actors: tuple[ScenarioActorDefinition, ...]
    environment: tuple[ScenarioEnvironmentDefinition, ...]


@dataclass(frozen=True, slots=True)
class LoadedScenario:
    definition: ScenarioDefinition
    path: Path


@dataclass(frozen=True, slots=True)
class LoadedEncounter:
    scenario_id: str
    scenario_name: str
    board: BoardState
    actors: tuple[Actor, ...]
    hero_attack_source: AttackSource
    enemy_attack_sources: dict[ActorId, AttackSource]
    environment: tuple[EnvironmentSetupEntry, ...]


def load_scenario(path: str | Path) -> LoadedScenario:
    scenario_path = Path(path)
    data = _read_json(scenario_path)
    definition = _parse_scenario(data, scenario_path)
    _validate_scenario(definition)
    return LoadedScenario(definition=definition, path=scenario_path)


def build_encounter_from_scenario(loaded: LoadedScenario) -> LoadedEncounter:
    definition = loaded.definition
    board = BoardState(dimensions=definition.board_dimensions)
    actors = tuple(_actor_from_definition(actor) for actor in definition.actors)
    hero_definition = next(actor for actor in definition.actors if actor.faction == Faction.ALLY)
    hero_attack_source = _attack_source_from_definition(hero_definition.attacks[0], "attack_hero")
    enemy_attack_sources = {
        ActorId(actor.id): _attack_source_from_definition(actor.attacks[0], f"attack_{actor.id}")
        for actor in definition.actors
        if actor.faction == Faction.ENEMY
    }
    environment = tuple(
        EnvironmentSetupEntry(
            id=entry.id,
            name=entry.name,
            setup_type=entry.setup_type,
            positions=entry.positions,
            visibility=entry.visibility,
            description=entry.description,
        )
        for entry in definition.environment
    )
    return LoadedEncounter(
        scenario_id=definition.id,
        scenario_name=definition.name,
        board=board,
        actors=actors,
        hero_attack_source=hero_attack_source,
        enemy_attack_sources=enemy_attack_sources,
        environment=environment,
    )


def _parse_scenario(data: dict[str, Any], scenario_path: Path) -> ScenarioDefinition:
    board_data = _required_mapping(data, "board", "scenario")
    cols = int(board_data.get("cols", 20))
    rows = int(board_data.get("rows", 30))
    actors_data = _required_list(data, "actors", "scenario")
    environment_data = data.get("environment", [])
    if not isinstance(environment_data, list):
        raise ValueError("scenario.environment must be a list.")
    return ScenarioDefinition(
        id=str(_required(data, "id", "scenario")),
        name=str(_required(data, "name", "scenario")),
        board_dimensions=BoardDimensions(cols=cols, rows=rows),
        actors=tuple(_parse_actor(actor_data, scenario_path) for actor_data in actors_data),
        environment=tuple(_parse_environment(entry) for entry in environment_data),
    )


def _parse_actor(data: dict[str, Any], scenario_path: Path) -> ScenarioActorDefinition:
    if not isinstance(data, dict):
        raise ValueError("scenario.actors entries must be objects.")
    source_ref = data.get("source_ref")
    merged: dict[str, Any] = {}
    if source_ref is not None:
        merged.update(_read_json(_content_ref_path(scenario_path, "monsters", str(source_ref))))
    merged.update(data)

    attacks_data = merged.get("attacks")
    if attacks_data is None:
        attacks_data = []
    if not isinstance(attacks_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.attacks must be a list.")
    item_refs = merged.get("item_refs", [])
    if not isinstance(item_refs, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.item_refs must be a list.")
    for item_ref in item_refs:
        item = _read_json(_content_ref_path(scenario_path, "items", str(item_ref)))
        attacks_data.extend(item.get("attacks", []))

    actor_id = str(_required(merged, "id", "actor"))
    attacks = tuple(_parse_attack(attack, actor_id) for attack in attacks_data)
    if not attacks:
        raise ValueError(f"actor {actor_id}.attacks must contain at least one attack.")
    return ScenarioActorDefinition(
        id=actor_id,
        name=str(_required(merged, "name", f"actor {actor_id}")),
        kind=str(_required(merged, "kind", f"actor {actor_id}")),
        faction=_enum_value(Faction, str(_required(merged, "faction", f"actor {actor_id}")), f"actor {actor_id}.faction"),
        ac=int(_required(merged, "ac", f"actor {actor_id}")),
        hp=int(_required(merged, "hp", f"actor {actor_id}")),
        temp_hp=int(merged.get("temp_hp", 0)),
        speed_feet=int(_required(merged, "speed_feet", f"actor {actor_id}")),
        position=_parse_coordinate(_required(merged, "position", f"actor {actor_id}"), f"actor {actor_id}.position"),
        ability_scores=_parse_ability_scores(_required_mapping(merged, "ability_scores", f"actor {actor_id}")),
        attacks=attacks,
        source_ref=str(source_ref) if source_ref is not None else None,
    )


def _parse_attack(data: dict[str, Any], actor_id: str) -> ScenarioAttackDefinition:
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.attacks entries must be objects.")
    attack_id = str(_required(data, "id", f"actor {actor_id}.attack"))
    damage = _required_mapping(data, "damage", f"attack {attack_id}")
    return ScenarioAttackDefinition(
        id=attack_id,
        name=str(_required(data, "name", f"attack {attack_id}")),
        source_type=_enum_value(
            AttackSourceType,
            str(_required(data, "source_type", f"attack {attack_id}")),
            f"attack {attack_id}.source_type",
        ),
        range_feet=int(_required(data, "range_feet", f"attack {attack_id}")),
        attack_modifier=int(_required(data, "attack_modifier", f"attack {attack_id}")),
        damage_fixed=_parse_damage_fixed(damage),
        damage_die_sides=_parse_damage_die(damage),
        damage_modifier=int(damage.get("modifier", 0)),
        damage_type=str(_required(damage, "damage_type", f"attack {attack_id}.damage")),
    )


def _parse_environment(data: dict[str, Any]) -> ScenarioEnvironmentDefinition:
    if not isinstance(data, dict):
        raise ValueError("scenario.environment entries must be objects.")
    entry_id = str(_required(data, "id", "environment"))
    positions_data = _required_list(data, "positions", f"environment {entry_id}")
    return ScenarioEnvironmentDefinition(
        id=entry_id,
        name=str(_required(data, "name", f"environment {entry_id}")),
        setup_type=_enum_value(
            EnvironmentSetupType,
            str(_required(data, "type", f"environment {entry_id}")),
            f"environment {entry_id}.type",
        ),
        positions=tuple(_parse_coordinate(position, f"environment {entry_id}.positions") for position in positions_data),
        visibility=_enum_value(
            SetupVisibility,
            str(data.get("visibility", SetupVisibility.VISIBLE.value)),
            f"environment {entry_id}.visibility",
        ),
        description=str(data.get("description", "")),
    )


def _actor_from_definition(definition: ScenarioActorDefinition) -> Actor:
    return Actor(
        id=ActorId(definition.id),
        name=definition.name,
        ac=definition.ac,
        hp=definition.hp,
        temp_hp=definition.temp_hp,
        speed_feet=definition.speed_feet,
        position=definition.position,
        faction=definition.faction,
        ability_scores=definition.ability_scores,
    )


def _attack_source_from_definition(definition: ScenarioAttackDefinition, stacking_key: str) -> AttackSource:
    return AttackSource(
        name=definition.name,
        source_type=definition.source_type,
        range_feet=definition.range_feet,
        attack_roll_request=D20RollRequest(
            modifiers=(
                RollModifier(
                    f"Premia ataku: {definition.name}",
                    definition.attack_modifier,
                    RollModifierType.CUSTOM,
                    stacking_key=stacking_key,
                ),
            )
        ),
        damage_hint=_damage_hint(definition),
        damage_fixed=definition.damage_fixed,
        damage_die_sides=definition.damage_die_sides,
        damage_modifier=definition.damage_modifier,
        damage_type=definition.damage_type,
    )


def _validate_scenario(definition: ScenarioDefinition) -> None:
    if not any(actor.faction == Faction.ALLY for actor in definition.actors):
        raise ValueError("scenario.actors must include at least one ally.")
    if not any(actor.faction == Faction.ENEMY for actor in definition.actors):
        raise ValueError("scenario.actors must include at least one enemy.")
    for actor in definition.actors:
        if not definition.board_dimensions.in_bounds(actor.position):
            raise ValueError(f"actor {actor.id}.position is out of board bounds.")
        for attack in actor.attacks:
            _enum_value(AttackSourceType, attack.source_type.value, f"attack {attack.id}.source_type")
            from dnd_board_game.combat import DamageType

            _enum_value(DamageType, attack.damage_type, f"attack {attack.id}.damage.damage_type")
    for entry in definition.environment:
        for position in entry.positions:
            if not definition.board_dimensions.in_bounds(position):
                raise ValueError(f"environment {entry.id}.positions contains out of bounds coordinate.")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _content_ref_path(scenario_path: Path, category: str, ref: str) -> Path:
    root = scenario_path.parent.parent
    filename = ref if ref.endswith(".json") else f"{ref}.json"
    return root / category / filename


def _parse_ability_scores(data: dict[str, Any]) -> AbilityScores:
    return AbilityScores(
        strength=int(data.get("strength", 10)),
        dexterity=int(data.get("dexterity", 10)),
        constitution=int(data.get("constitution", 10)),
        intelligence=int(data.get("intelligence", 10)),
        wisdom=int(data.get("wisdom", 10)),
        charisma=int(data.get("charisma", 10)),
    )


def _parse_coordinate(value: Any, field: str) -> Coordinate:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ValueError(f"{field} must be [col, row].")
    return Coordinate(int(value[0]), int(value[1]))


def _parse_damage_die(data: dict[str, Any]) -> int | None:
    dice = data.get("dice")
    if dice is None:
        return None
    text = str(dice).lower().strip()
    if not text.startswith("1d"):
        raise ValueError("damage.dice supports only MVP format '1dN'.")
    return int(text[2:])


def _parse_damage_fixed(data: dict[str, Any]) -> int | None:
    fixed = data.get("fixed")
    return None if fixed is None else int(fixed)


def _damage_hint(definition: ScenarioAttackDefinition) -> str:
    if definition.damage_fixed is not None:
        base = str(definition.damage_fixed)
    elif definition.damage_die_sides is None:
        base = "damage"
    else:
        base = f"1d{definition.damage_die_sides}"
    if definition.damage_modifier:
        sign = "+" if definition.damage_modifier > 0 else "-"
        base = f"{base} {sign} {abs(definition.damage_modifier)}"
    return f"{base} {definition.damage_type}"


def _required(data: dict[str, Any], field: str, context: str) -> Any:
    if field not in data:
        raise ValueError(f"Missing required field: {context}.{field}.")
    return data[field]


def _required_mapping(data: dict[str, Any], field: str, context: str) -> dict[str, Any]:
    value = _required(data, field, context)
    if not isinstance(value, dict):
        raise ValueError(f"{context}.{field} must be an object.")
    return value


def _required_list(data: dict[str, Any], field: str, context: str) -> list[Any]:
    value = _required(data, field, context)
    if not isinstance(value, list):
        raise ValueError(f"{context}.{field} must be a list.")
    return value


def _enum_value(enum_type, value: str, field: str):
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"Unknown value for {field}: {value}.") from exc
