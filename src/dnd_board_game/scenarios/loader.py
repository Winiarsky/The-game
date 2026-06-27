from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    EnvironmentSetupEntry,
    EnvironmentSetupType,
    SceneAbilityCheck,
    SceneInteraction,
    SceneObjective,
    SceneObjectiveCondition,
    SceneObject,
    SetupVisibility,
)
from dnd_board_game.exploration import (
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationOption,
    ExplorationOptionKind,
    ExplorationPoint,
    ExplorationResource,
    ExplorationZone,
    PartyPosition,
    SceneMode,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.rules import D20RollRequest, RollModifier, RollModifierType
from dnd_board_game.world import BLOCKING_TERRAIN, DIFFICULT_TERRAIN, BoardDimensions, BoardState, Coordinate


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
    interaction_label: str | None = None
    objective_id: str | None = None
    interactions: tuple[SceneInteraction, ...] = ()
    blocks_movement: bool | None = None
    allow_interaction_when_occupied_by_enemy: bool = False
    cover_bonus: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioObjectiveDefinition:
    id: str
    name: str
    description: str
    condition: SceneObjectiveCondition
    target_id: str | None = None
    flag_key: str | None = None
    flag_value: object = True


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    id: str
    name: str
    board_dimensions: BoardDimensions
    actors: tuple[ScenarioActorDefinition, ...]
    environment: tuple[ScenarioEnvironmentDefinition, ...]
    scene_mode: SceneMode = SceneMode.ENCOUNTER
    player_start_zones: tuple[tuple[Coordinate, ...], ...] = ()
    objectives: tuple[ScenarioObjectiveDefinition, ...] = ()
    exploration_zones: tuple[ExplorationZone, ...] = ()
    exploration_points: tuple[ExplorationPoint, ...] = ()
    exploration_challenges: tuple[ExplorationChallenge, ...] = ()
    exploration_resources: tuple[ExplorationResource, ...] = ()
    exploration_initial_resources: tuple[str, ...] = ()
    party_start_zone_id: str | None = None


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
    attack_sources_by_actor: dict[ActorId, AttackSource]
    environment: tuple[EnvironmentSetupEntry, ...]
    player_start_zones: tuple[tuple[Coordinate, ...], ...] = ()
    objectives: tuple[SceneObjective, ...] = ()
    scene_objects: tuple[SceneObject, ...] = ()


@dataclass(frozen=True, slots=True)
class LoadedExploration:
    scenario_id: str
    scenario_name: str
    board: BoardState
    actors: tuple[Actor, ...]
    zones: tuple[ExplorationZone, ...]
    points: tuple[ExplorationPoint, ...]
    challenges: tuple[ExplorationChallenge, ...]
    resources: tuple[ExplorationResource, ...]
    initial_resource_ids: tuple[str, ...]
    party_position: PartyPosition
    objectives: tuple[SceneObjective, ...] = ()


def load_scenario(path: str | Path) -> LoadedScenario:
    scenario_path = Path(path)
    data = _read_json(scenario_path)
    definition = _parse_scenario(data, scenario_path)
    _validate_scenario(definition)
    return LoadedScenario(definition=definition, path=scenario_path)


def build_encounter_from_scenario(loaded: LoadedScenario) -> LoadedEncounter:
    definition = loaded.definition
    board = BoardState(dimensions=definition.board_dimensions)
    _apply_environment_to_board(board, definition.environment)
    actors = tuple(_actor_from_definition(actor) for actor in definition.actors)
    attack_sources_by_actor = {
        ActorId(actor.id): _attack_source_from_definition(actor.attacks[0], f"attack_{actor.id}")
        for actor in definition.actors
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
    scene_objects = tuple(
        SceneObject(
            id=entry.id,
            name=entry.name,
            positions=entry.positions,
            interaction_label=entry.interaction_label or f"Wejdź w interakcję z {entry.name}",
            visibility=entry.visibility,
            objective_id=entry.objective_id,
            description=entry.description,
            interactions=entry.interactions,
            blocks_movement=_environment_blocks_movement(entry),
            allow_interaction_when_occupied_by_enemy=entry.allow_interaction_when_occupied_by_enemy,
            cover_bonus=entry.cover_bonus,
        )
        for entry in definition.environment
        if entry.setup_type in {EnvironmentSetupType.INTERACTABLE, EnvironmentSetupType.CONTAINER, EnvironmentSetupType.NPC}
        and entry.interaction_label is not None
    )
    objectives = tuple(
        SceneObjective(
            id=objective.id,
            name=objective.name,
            description=objective.description,
            condition=objective.condition,
            target_id=objective.target_id,
            flag_key=objective.flag_key,
            flag_value=objective.flag_value,
        )
        for objective in definition.objectives
    )
    return LoadedEncounter(
        scenario_id=definition.id,
        scenario_name=definition.name,
        board=board,
        actors=actors,
        attack_sources_by_actor=attack_sources_by_actor,
        environment=environment,
        player_start_zones=definition.player_start_zones,
        objectives=objectives,
        scene_objects=scene_objects,
    )


def build_exploration_from_scenario(loaded: LoadedScenario) -> LoadedExploration:
    definition = loaded.definition
    if definition.scene_mode != SceneMode.EXPLORATION:
        raise ValueError(f"Scenario {definition.id} is not an exploration scenario.")
    board = BoardState(dimensions=definition.board_dimensions)
    actors = tuple(_actor_from_definition(actor) for actor in definition.actors)
    start_zone = _zone_by_id(definition.exploration_zones, definition.party_start_zone_id)
    objectives = tuple(
        SceneObjective(
            id=objective.id,
            name=objective.name,
            description=objective.description,
            condition=objective.condition,
            target_id=objective.target_id,
            flag_key=objective.flag_key,
            flag_value=objective.flag_value,
        )
        for objective in definition.objectives
    )
    return LoadedExploration(
        scenario_id=definition.id,
        scenario_name=definition.name,
        board=board,
        actors=actors,
        zones=definition.exploration_zones,
        points=definition.exploration_points,
        challenges=definition.exploration_challenges,
        resources=definition.exploration_resources,
        initial_resource_ids=definition.exploration_initial_resources,
        party_position=PartyPosition(start_zone.id, start_zone.marker_position),
        objectives=objectives,
    )


def _parse_scenario(data: dict[str, Any], scenario_path: Path) -> ScenarioDefinition:
    board_data = _required_mapping(data, "board", "scenario")
    cols = int(board_data.get("cols", 20))
    rows = int(board_data.get("rows", 30))
    actors_data = _required_list(data, "actors", "scenario")
    environment_data = data.get("environment", [])
    if not isinstance(environment_data, list):
        raise ValueError("scenario.environment must be a list.")
    start_zones_data = data.get("player_start_zones", [])
    if not isinstance(start_zones_data, list):
        raise ValueError("scenario.player_start_zones must be a list.")
    objectives_data = data.get("objectives", [])
    if not isinstance(objectives_data, list):
        raise ValueError("scenario.objectives must be a list.")
    exploration_data = data.get("exploration", {})
    if exploration_data is None:
        exploration_data = {}
    if not isinstance(exploration_data, dict):
        raise ValueError("scenario.exploration must be an object.")
    scene_mode = _enum_value(SceneMode, str(data.get("scene_mode", SceneMode.ENCOUNTER.value)), "scenario.scene_mode")
    return ScenarioDefinition(
        id=str(_required(data, "id", "scenario")),
        name=str(_required(data, "name", "scenario")),
        board_dimensions=BoardDimensions(cols=cols, rows=rows),
        scene_mode=scene_mode,
        actors=tuple(_parse_actor(actor_data, scenario_path) for actor_data in actors_data),
        environment=tuple(_parse_environment(entry) for entry in environment_data),
        player_start_zones=tuple(_parse_start_zone(zone, "scenario.player_start_zones") for zone in start_zones_data),
        objectives=tuple(_parse_objective(entry) for entry in objectives_data),
        exploration_zones=tuple(_parse_exploration_zone(entry) for entry in exploration_data.get("zones", [])),
        exploration_points=tuple(_parse_exploration_point(entry) for entry in exploration_data.get("points", [])),
        exploration_challenges=tuple(_parse_exploration_challenge(entry) for entry in exploration_data.get("challenges", [])),
        exploration_resources=tuple(_parse_exploration_resource(entry) for entry in exploration_data.get("resources", [])),
        exploration_initial_resources=tuple(str(item) for item in exploration_data.get("initial_resources", [])),
        party_start_zone_id=str(exploration_data["party_start_zone"]) if "party_start_zone" in exploration_data else None,
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
        interaction_label=str(data["interaction_label"]) if "interaction_label" in data else None,
        objective_id=str(data["objective_id"]) if "objective_id" in data else None,
        interactions=_parse_interactions(data.get("interactions", []), entry_id),
        blocks_movement=bool(data["blocks_movement"]) if "blocks_movement" in data else None,
        allow_interaction_when_occupied_by_enemy=bool(data.get("allow_interaction_when_occupied_by_enemy", False)),
        cover_bonus=int(data.get("cover_bonus", data.get("cover", 0))),
    )


def _parse_start_zone(data: Any, field: str) -> tuple[Coordinate, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{field} entries must be lists.")
    return tuple(_parse_coordinate(position, field) for position in data)


def _parse_objective(data: dict[str, Any]) -> ScenarioObjectiveDefinition:
    if not isinstance(data, dict):
        raise ValueError("scenario.objectives entries must be objects.")
    objective_id = str(_required(data, "id", "objective"))
    return ScenarioObjectiveDefinition(
        id=objective_id,
        name=str(_required(data, "name", f"objective {objective_id}")),
        description=str(data.get("description", "")),
        condition=_enum_value(
            SceneObjectiveCondition,
            str(_required(data, "condition", f"objective {objective_id}")),
            f"objective {objective_id}.condition",
        ),
        target_id=str(data["target_id"]) if "target_id" in data else None,
        flag_key=str(data["flag_key"]) if "flag_key" in data else None,
        flag_value=data.get("flag_value", True),
    )


def _parse_exploration_zone(data: Any) -> ExplorationZone:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.zones entries must be objects.")
    zone_id = str(_required(data, "id", "exploration zone"))
    positions_data = _required_list(data, "positions", f"exploration zone {zone_id}")
    search_data = data.get("search", {})
    if search_data is None:
        search_data = {}
    if not isinstance(search_data, dict):
        raise ValueError(f"exploration zone {zone_id}.search must be an object.")
    return ExplorationZone(
        id=zone_id,
        name=str(_required(data, "name", f"exploration zone {zone_id}")),
        positions=tuple(_parse_coordinate(position, f"exploration zone {zone_id}.positions") for position in positions_data),
        color=_parse_color(data.get("color", "marker"), f"exploration zone {zone_id}.color"),
        anchor_position=_parse_coordinate(data["anchor_position"], f"exploration zone {zone_id}.anchor_position") if "anchor_position" in data else None,
        description=str(data.get("description", "")),
        visibility=_enum_value(
            SetupVisibility,
            str(data.get("visibility", SetupVisibility.VISIBLE.value)),
            f"exploration zone {zone_id}.visibility",
        ),
        available_if_flag=str(data["available_if_flag"]) if "available_if_flag" in data else None,
        available_if_value=data.get("available_if_value", True),
        options=tuple(_parse_exploration_option(entry, zone_id) for entry in data.get("options", [])),
        adjacent_zone_ids=tuple(str(item) for item in data.get("adjacent_zone_ids", [])),
        search_dc=int(search_data["dc"]) if "dc" in search_data else None,
        search_ability=str(search_data.get("ability", "wisdom")),
        search_skill=str(search_data["skill"]) if "skill" in search_data else "perception",
        search_reveals=tuple(str(item) for item in search_data.get("reveals", [])),
        search_success_flag=str(search_data["success_flag"]) if "success_flag" in search_data else None,
        search_failure_flag=str(search_data["failure_flag"]) if "failure_flag" in search_data else None,
    )


def _parse_exploration_option(data: Any, zone_id: str) -> ExplorationOption:
    if not isinstance(data, dict):
        raise ValueError(f"exploration zone {zone_id}.options entries must be objects.")
    option_id = str(_required(data, "id", f"exploration zone {zone_id}.option"))
    ability_check = data.get("ability_check")
    return ExplorationOption(
        id=option_id,
        label=str(_required(data, "label", f"exploration option {option_id}")),
        kind=_enum_value(
            ExplorationOptionKind,
            str(data.get("kind", ExplorationOptionKind.MESSAGE.value)),
            f"exploration option {option_id}.kind",
        ),
        color=_parse_color(data.get("color", "interactive"), f"exploration option {option_id}.color"),
        description=str(data.get("description", "")),
        message=str(data.get("message", "")),
        success_message=str(data.get("success_message", "")),
        failure_message=str(data.get("failure_message", "")),
        ability_check=_parse_scene_ability_check(ability_check, option_id) if ability_check is not None else None,
        allow_help=bool(data.get("allow_help", False)),
        success_flag=str(data["success_flag"]) if "success_flag" in data else None,
        failure_flag=str(data["failure_flag"]) if "failure_flag" in data else None,
        reveals=tuple(str(item) for item in data.get("reveals", [])),
    )


def _parse_exploration_point(data: Any) -> ExplorationPoint:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.points entries must be objects.")
    point_id = str(_required(data, "id", "exploration point"))
    positions_data = _required_list(data, "positions", f"exploration point {point_id}")
    return ExplorationPoint(
        id=point_id,
        name=str(_required(data, "name", f"exploration point {point_id}")),
        zone_id=str(_required(data, "zone_id", f"exploration point {point_id}")),
        positions=tuple(_parse_coordinate(position, f"exploration point {point_id}.positions") for position in positions_data),
        color=_parse_color(data.get("color", "interactive"), f"exploration point {point_id}.color"),
        visibility=_enum_value(
            SetupVisibility,
            str(data.get("visibility", SetupVisibility.VISIBLE.value)),
            f"exploration point {point_id}.visibility",
        ),
        description=str(data.get("description", "")),
    )


def _parse_exploration_challenge(data: Any) -> ExplorationChallenge:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.challenges entries must be objects.")
    challenge_id = str(_required(data, "id", "exploration challenge"))
    options_data = _required_list(data, "options", f"exploration challenge {challenge_id}")
    return ExplorationChallenge(
        id=challenge_id,
        zone_id=str(_required(data, "zone_id", f"exploration challenge {challenge_id}")),
        name=str(_required(data, "name", f"exploration challenge {challenge_id}")),
        progress_required=int(data.get("progress_required", 3)),
        completed_flag=str(_required(data, "completed_flag", f"exploration challenge {challenge_id}")),
        options=tuple(_parse_exploration_challenge_option(entry, challenge_id) for entry in options_data),
    )


def _parse_exploration_challenge_option(data: Any, challenge_id: str) -> ExplorationChallengeOption:
    if not isinstance(data, dict):
        raise ValueError(f"exploration challenge {challenge_id}.options entries must be objects.")
    option_id = str(_required(data, "id", f"exploration challenge {challenge_id}.option"))
    return ExplorationChallengeOption(
        id=option_id,
        label=str(_required(data, "label", f"exploration challenge option {option_id}")),
        ability_check=_parse_scene_ability_check(
            _required_mapping(data, "ability_check", f"exploration challenge option {option_id}"),
            option_id,
        ),
        progress_on_success=int(_required(data, "progress_on_success", f"exploration challenge option {option_id}")),
        progress_on_failure=int(data.get("progress_on_failure", 0)),
        color=_parse_color(data.get("color", "interactive"), f"exploration challenge option {option_id}.color"),
        description=str(data.get("description", "")),
        success_message=str(data.get("success_message", "")),
        failure_message=str(data.get("failure_message", "")),
        critical_failure_message=str(data.get("critical_failure_message", "")),
        tags=tuple(str(item) for item in data.get("tags", [])),
        unlocks_if_flag=str(data["unlocks_if_flag"]) if "unlocks_if_flag" in data else None,
        unlocks_if_resource_id=str(data["unlocks_if_resource_id"]) if "unlocks_if_resource_id" in data else None,
        success_noise=int(data.get("success_noise", 0)),
        failure_noise=int(data.get("failure_noise", 0)),
        critical_failure_noise=int(data.get("critical_failure_noise", 0)),
        quiet_success_margin=int(data["quiet_success_margin"]) if "quiet_success_margin" in data else None,
        quiet_on_natural_20=bool(data.get("quiet_on_natural_20", False)),
        success_complication=str(data["success_complication"]) if "success_complication" in data else None,
        failure_complication=str(data["failure_complication"]) if "failure_complication" in data else None,
        critical_failure_complication=str(data["critical_failure_complication"]) if "critical_failure_complication" in data else None,
    )


def _parse_exploration_resource(data: Any) -> ExplorationResource:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.resources entries must be objects.")
    resource_id = str(_required(data, "id", "exploration resource"))
    return ExplorationResource(
        id=resource_id,
        label=str(_required(data, "label", f"exploration resource {resource_id}")),
        bonus_tags=tuple(str(item) for item in data.get("bonus_tags", [])),
        modifier=int(data.get("modifier", 0)),
        advantage=bool(data.get("advantage", False)),
        mitigates_complications=tuple(str(item) for item in data.get("mitigates_complications", [])),
        mitigates_noise=int(data.get("mitigates_noise", 0)),
        unlocks_flags=tuple(str(item) for item in data.get("unlocks_flags", [])),
    )


def _parse_interactions(data: Any, environment_id: str) -> tuple[SceneInteraction, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"environment {environment_id}.interactions must be a list.")
    return tuple(_parse_interaction(entry, environment_id) for entry in data)


def _parse_interaction(data: Any, environment_id: str) -> SceneInteraction:
    if not isinstance(data, dict):
        raise ValueError(f"environment {environment_id}.interactions entries must be objects.")
    interaction_id = str(_required(data, "id", f"environment {environment_id}.interaction"))
    ability_check = data.get("ability_check")
    return SceneInteraction(
        id=interaction_id,
        label=str(_required(data, "label", f"interaction {interaction_id}")),
        description=str(data.get("description", "")),
        ability_check=_parse_scene_ability_check(ability_check, interaction_id) if ability_check is not None else None,
        success_flag=str(data["success_flag"]) if "success_flag" in data else None,
        failure_flag=str(data["failure_flag"]) if "failure_flag" in data else None,
        success_message=str(data.get("success_message", "")),
        failure_message=str(data.get("failure_message", "")),
    )


def _parse_scene_ability_check(data: Any, interaction_id: str) -> SceneAbilityCheck:
    if not isinstance(data, dict):
        raise ValueError(f"interaction {interaction_id}.ability_check must be an object.")
    modifiers_data = data.get("modifiers", [])
    if not isinstance(modifiers_data, list):
        raise ValueError(f"interaction {interaction_id}.ability_check.modifiers must be a list.")
    return SceneAbilityCheck(
        ability=str(_required(data, "ability", f"interaction {interaction_id}.ability_check")),
        skill=str(data["skill"]) if "skill" in data else None,
        dc=int(_required(data, "dc", f"interaction {interaction_id}.ability_check")),
        modifiers=tuple(_parse_roll_modifier(entry, interaction_id) for entry in modifiers_data),
    )


def _parse_roll_modifier(data: Any, interaction_id: str) -> RollModifier:
    if not isinstance(data, dict):
        raise ValueError(f"interaction {interaction_id}.ability_check.modifiers entries must be objects.")
    return RollModifier(
        label=str(_required(data, "label", f"interaction {interaction_id}.modifier")),
        value=int(_required(data, "value", f"interaction {interaction_id}.modifier")),
        modifier_type=_enum_value(
            RollModifierType,
            str(_required(data, "modifier_type", f"interaction {interaction_id}.modifier")),
            f"interaction {interaction_id}.modifier.modifier_type",
        ),
        stacking_key=str(data["stacking_key"]) if "stacking_key" in data else None,
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
    if definition.scene_mode == SceneMode.ENCOUNTER and not any(actor.faction == Faction.ENEMY for actor in definition.actors):
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
    for zone in definition.player_start_zones:
        for position in zone:
            if not definition.board_dimensions.in_bounds(position):
                raise ValueError("scenario.player_start_zones contains out of bounds coordinate.")
    environment_ids = {entry.id for entry in definition.environment}
    objective_ids = {objective.id for objective in definition.objectives}
    for entry in definition.environment:
        if entry.objective_id is not None and entry.objective_id not in objective_ids:
            raise ValueError(f"environment {entry.id}.objective_id references unknown objective.")
    for objective in definition.objectives:
        if objective.condition == SceneObjectiveCondition.INTERACT_WITH_OBJECT and objective.target_id not in environment_ids:
            raise ValueError(f"objective {objective.id}.target_id references unknown environment entry.")
        if objective.condition == SceneObjectiveCondition.FLAG_EQUALS and not objective.flag_key:
            raise ValueError(f"objective {objective.id}.flag_key is required for flag_equals.")
    if definition.scene_mode == SceneMode.EXPLORATION:
        _validate_exploration(definition)


def _validate_exploration(definition: ScenarioDefinition) -> None:
    if not definition.exploration_zones:
        raise ValueError("exploration scenario requires at least one zone.")
    zone_ids = {zone.id for zone in definition.exploration_zones}
    point_ids = {point.id for point in definition.exploration_points}
    resource_ids = {resource.id for resource in definition.exploration_resources}
    if definition.party_start_zone_id not in zone_ids:
        raise ValueError("exploration.party_start_zone references unknown zone.")
    for resource_id in definition.exploration_initial_resources:
        if resource_id not in resource_ids:
            raise ValueError(f"exploration.initial_resources references unknown resource: {resource_id}.")
    for zone in definition.exploration_zones:
        for position in zone.positions:
            if not definition.board_dimensions.in_bounds(position):
                raise ValueError(f"exploration zone {zone.id}.positions contains out of bounds coordinate.")
        if zone.anchor_position is not None:
            if not definition.board_dimensions.in_bounds(zone.anchor_position):
                raise ValueError(f"exploration zone {zone.id}.anchor_position is out of bounds.")
            if zone.anchor_position not in zone.positions:
                raise ValueError(f"exploration zone {zone.id}.anchor_position must be inside zone positions.")
        for adjacent_id in zone.adjacent_zone_ids:
            if adjacent_id not in zone_ids:
                raise ValueError(f"exploration zone {zone.id}.adjacent_zone_ids references unknown zone.")
        for point_id in zone.search_reveals:
            if point_id not in point_ids:
                raise ValueError(f"exploration zone {zone.id}.search.reveals references unknown point.")
    for point in definition.exploration_points:
        if point.zone_id not in zone_ids:
            raise ValueError(f"exploration point {point.id}.zone_id references unknown zone.")
        for position in point.positions:
            if not definition.board_dimensions.in_bounds(position):
                raise ValueError(f"exploration point {point.id}.positions contains out of bounds coordinate.")
    for challenge in definition.exploration_challenges:
        if challenge.zone_id not in zone_ids:
            raise ValueError(f"exploration challenge {challenge.id}.zone_id references unknown zone.")
        if challenge.progress_required <= 0:
            raise ValueError(f"exploration challenge {challenge.id}.progress_required must be positive.")
        if not challenge.completed_flag:
            raise ValueError(f"exploration challenge {challenge.id}.completed_flag cannot be empty.")
        if not challenge.options:
            raise ValueError(f"exploration challenge {challenge.id}.options must contain at least one option.")
        for option in challenge.options:
            if option.progress_on_success < 0 or option.progress_on_failure < 0:
                raise ValueError(f"exploration challenge option {option.id}.progress values must be non-negative.")
            if option.unlocks_if_resource_id is not None and option.unlocks_if_resource_id not in resource_ids:
                raise ValueError(
                    f"exploration challenge option {option.id}.unlocks_if_resource_id references unknown resource."
                )


def _apply_environment_to_board(board: BoardState, environment: tuple[ScenarioEnvironmentDefinition, ...]) -> None:
    for entry in environment:
        if entry.setup_type == EnvironmentSetupType.DIFFICULT_TERRAIN:
            for position in entry.positions:
                board.set_terrain(position, DIFFICULT_TERRAIN)
        if _environment_blocks_movement(entry):
            for position in entry.positions:
                board.set_terrain(position, BLOCKING_TERRAIN)


def _environment_blocks_movement(entry: ScenarioEnvironmentDefinition) -> bool:
    if entry.blocks_movement is not None:
        return entry.blocks_movement
    return entry.setup_type in {EnvironmentSetupType.BLOCKING_TERRAIN, EnvironmentSetupType.OBSTACLE}


def _zone_by_id(zones: tuple[ExplorationZone, ...], zone_id: str | None) -> ExplorationZone:
    for zone in zones:
        if zone.id == zone_id:
            return zone
    raise ValueError(f"Unknown exploration start zone: {zone_id}.")


def _parse_color(value: Any, field: str) -> tuple[int, int, int]:
    if isinstance(value, list | tuple) and len(value) == 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    named = {
        "active": LedColor.ACTIVE_ACTOR,
        "ally": LedColor.ALLY,
        "enemy": LedColor.ENEMY,
        "interactive": LedColor.INTERACTIVE_OBJECT,
        "marker": LedColor.MARKER,
        "movement": LedColor.MOVEMENT_RANGE,
        "multi": LedColor.MULTI_OPTION_TILE,
        "success": LedColor.INTERACTION_SUCCESS,
        "warning": LedColor.ENEMY_MOVEMENT_DESTINATION,
        "danger": LedColor.ATTACK_MISS,
    }
    if str(value) in named:
        return named[str(value)]
    raise ValueError(f"Unknown color for {field}: {value}.")


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
