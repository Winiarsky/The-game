from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    PreparableSpell,
    SpellPreparationProfile,
)
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    HealingSource,
    HealingSourceType,
    SpellCastingKind,
    SpellArea,
    SpellAreaShape,
    SpellSlotState,
    EnvironmentSetupEntry,
    EnvironmentSetupType,
    SceneAbilityCheck,
    SceneInteraction,
    SceneInteractionCondition,
    SceneInteractionEffect,
    SceneObjective,
    SceneObjectiveCondition,
    SceneObject,
    SetupVisibility,
)
from dnd_board_game.exploration import (
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationEncounterTrigger,
    ExplorationOptionBonus,
    ExplorationSituationalModifier,
    ExplorationSituationalModifierSource,
    EncounterOutcome,
    ExplorationOption,
    ExplorationOptionKind,
    ExplorationPoint,
    ExplorationResource,
    ExplorationZone,
    ImprovisedToolUse,
    ItemBreakageRisk,
    LlmChallengePolicy,
    LlmContext,
    LlmDcTier,
    NpcInteraction,
    NpcIntentPermission,
    NpcInteractionPolicy,
    NpcLockedInformation,
    PartyPosition,
    SceneMode,
    EncounterTriggerCondition,
    mechanic_tool,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import D20RollRequest, RollMode, RollModifier, RollModifierType
from dnd_board_game.world import BLOCKING_TERRAIN, DIFFICULT_TERRAIN, BoardDimensions, BoardState, Coordinate


KNOWN_LLM_CONSEQUENCE_TYPES = frozenset(
    {
        "add_noise",
        "add_complication",
        "reveal_point",
        "set_flag",
        "grant_resource",
        "consume_resource",
        "unlock_option",
        "none",
    }
)
KNOWN_LLM_PREPARATION_EFFECT_TYPES = frozenset(
    {
        "modifier",
        "reduce_negative_effect",
        "advantage",
        "disadvantage",
        "effect_boost",
        "unlock_option",
        "grant_resource",
    }
)


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
    ability: str | None = None
    spell_level: int = 0
    area: SpellArea | None = None
    save_ability: str | None = None
    save_dc: int = 0
    save_damage_on_success: str = "none"
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True


@dataclass(frozen=True, slots=True)
class ScenarioHealingDefinition:
    id: str
    name: str
    source_type: HealingSourceType
    range_feet: int
    healing_fixed: int | None
    healing_die_sides: int | None
    healing_modifier: int
    spell_level: int = 0
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True


@dataclass(frozen=True, slots=True)
class ScenarioCombatActionDefinition:
    id: str
    name: str
    action_type: str
    label: str
    value: int = 0
    ability: str | None = None
    duration: str = "next_turn_start"
    target_faction: str = "self"
    spell_level: int = 0
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True
    concentration: bool = False
    source_item_id: str | None = None


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
    spell_slots: tuple[SpellSlotState, ...]
    spell_save_dc: int
    inventory: tuple[InventoryItem, ...]
    spell_ids: tuple[str, ...]
    spell_preparation: SpellPreparationProfile | None
    attacks: tuple[ScenarioAttackDefinition, ...]
    healing_sources: tuple[ScenarioHealingDefinition, ...] = ()
    combat_actions: tuple[ScenarioCombatActionDefinition, ...] = ()
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
    exploration_encounter_triggers: tuple[ExplorationEncounterTrigger, ...] = ()
    party_start_zone_id: str | None = None
    llm_context: LlmContext = LlmContext()


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
    attack_source_options_by_actor: dict[ActorId, tuple[AttackSource, ...]]
    healing_sources_by_actor: dict[ActorId, tuple[HealingSource, ...]]
    combat_actions_by_actor: dict[ActorId, tuple[ScenarioCombatActionDefinition, ...]]
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
    encounter_triggers: tuple[ExplorationEncounterTrigger, ...] = ()
    environment: tuple[EnvironmentSetupEntry, ...] = ()
    llm_context: LlmContext = LlmContext()
    objectives: tuple[SceneObjective, ...] = ()


def load_scenario(path: str | Path) -> LoadedScenario:
    scenario_path = Path(path)
    data, loaded_path = _load_scenario_data(scenario_path)
    definition = _parse_scenario(data, loaded_path)
    _validate_scenario(definition)
    return LoadedScenario(definition=definition, path=loaded_path)


def build_encounter_from_scenario(loaded: LoadedScenario) -> LoadedEncounter:
    definition = loaded.definition
    board = BoardState(dimensions=definition.board_dimensions)
    _apply_environment_to_board(board, definition.environment)
    actors = tuple(_actor_from_definition(actor) for actor in definition.actors)
    attack_source_options_by_actor = {
        ActorId(actor.id): tuple(
            _attack_source_from_definition(attack, f"attack_{actor.id}:{attack.id}") for attack in actor.attacks
        )
        for actor in definition.actors
    }
    attack_sources_by_actor = {actor_id: sources[0] for actor_id, sources in attack_source_options_by_actor.items() if sources}
    healing_sources_by_actor = {
        ActorId(actor.id): tuple(_healing_source_from_definition(source) for source in actor.healing_sources)
        for actor in definition.actors
        if actor.healing_sources
    }
    combat_actions_by_actor = {
        ActorId(actor.id): actor.combat_actions
        for actor in definition.actors
        if actor.combat_actions
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
        if entry.interaction_label is not None
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
        attack_source_options_by_actor=attack_source_options_by_actor,
        healing_sources_by_actor=healing_sources_by_actor,
        combat_actions_by_actor=combat_actions_by_actor,
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
    _apply_environment_to_board(board, definition.environment)
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
        encounter_triggers=definition.exploration_encounter_triggers,
        environment=tuple(
            EnvironmentSetupEntry(
                id=entry.id,
                name=entry.name,
                setup_type=entry.setup_type,
                positions=entry.positions,
                visibility=entry.visibility,
                description=entry.description,
            )
            for entry in definition.environment
        ),
        party_position=PartyPosition(start_zone.id, start_zone.marker_position),
        llm_context=definition.llm_context,
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
        exploration_encounter_triggers=tuple(_parse_exploration_encounter_trigger(entry) for entry in exploration_data.get("encounter_triggers", [])),
        party_start_zone_id=str(exploration_data["party_start_zone"]) if "party_start_zone" in exploration_data else None,
        llm_context=_parse_llm_context(data.get("llm_context", {}), "scenario.llm_context"),
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
    healing_data = merged.get("healing_sources", [])
    if not isinstance(healing_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.healing_sources must be a list.")
    combat_actions_data = merged.get("combat_actions", [])
    if not isinstance(combat_actions_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.combat_actions must be a list.")
    item_refs = merged.get("item_refs", [])
    if not isinstance(item_refs, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.item_refs must be a list.")
    inventory_data = merged.get("inventory", [])
    if not isinstance(inventory_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.inventory must be a list.")
    inventory_items: list[InventoryItem] = []
    for item_ref in item_refs:
        item = _read_json(_content_ref_path(scenario_path, "items", str(item_ref)))
        inventory_items.append(_inventory_item_from_item_data(item, quantity=1, equipped=True, source_ref=str(item_ref)))
        attacks_data.extend(item.get("attacks", []))
        healing_data.extend(item.get("healing_sources", []))
        combat_actions_data.extend(_combat_actions_with_item_source(item.get("combat_actions", []), str(item_ref)))
    for item_entry in inventory_data:
        item, inventory_item = _parse_inventory_entry(item_entry, scenario_path, actor_id=str(merged.get("id", "<unknown>")))
        inventory_items.append(inventory_item)
        if inventory_item.equipped:
            attacks_data.extend(item.get("attacks", []))
            healing_data.extend(item.get("healing_sources", []))
        combat_actions_data.extend(_combat_actions_with_item_source(item.get("combat_actions", []), inventory_item.id))

    actor_id = str(_required(merged, "id", "actor"))
    attacks = tuple(_parse_attack(attack, actor_id) for attack in attacks_data)
    if not attacks:
        raise ValueError(f"actor {actor_id}.attacks must contain at least one attack.")
    healing_sources = tuple(_parse_healing_source(source, actor_id) for source in healing_data)
    combat_actions = tuple(_parse_combat_action(action, actor_id) for action in combat_actions_data)
    spell_slots = _parse_spell_slots(merged.get("spell_slots", {}), actor_id)
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
        spell_slots=spell_slots,
        spell_save_dc=int(merged.get("spell_save_dc", 0)),
        inventory=tuple(inventory_items),
        spell_ids=_spell_ids_for_actor(attacks, healing_sources, combat_actions),
        spell_preparation=_parse_spell_preparation(
            merged.get("spell_preparation"),
            actor_id=actor_id,
            attacks=attacks,
            healing_sources=healing_sources,
            combat_actions=combat_actions,
            spell_slots=spell_slots,
        ),
        attacks=attacks,
        healing_sources=healing_sources,
        combat_actions=combat_actions,
        source_ref=str(source_ref) if source_ref is not None else None,
    )


def _spell_ids_for_actor(
    attacks: tuple[ScenarioAttackDefinition, ...],
    healing_sources: tuple[ScenarioHealingDefinition, ...],
    combat_actions: tuple[ScenarioCombatActionDefinition, ...],
) -> tuple[str, ...]:
    ids: list[str] = []
    ids.extend(attack.id for attack in attacks if attack.source_type == AttackSourceType.SPELL)
    ids.extend(source.id for source in healing_sources if source.source_type == HealingSourceType.SPELL)
    ids.extend(action.id for action in combat_actions if action.casting_kind != SpellCastingKind.NONE)
    return tuple(dict.fromkeys(ids))


def _parse_spell_preparation(
    data: Any,
    *,
    actor_id: str,
    attacks: tuple[ScenarioAttackDefinition, ...],
    healing_sources: tuple[ScenarioHealingDefinition, ...],
    combat_actions: tuple[ScenarioCombatActionDefinition, ...],
    spell_slots: tuple[SpellSlotState, ...],
) -> SpellPreparationProfile | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.spell_preparation must be an object.")
    known_spells: dict[str, PreparableSpell] = {}
    for source in (*attacks, *healing_sources, *combat_actions):
        casting_kind = source.casting_kind
        if casting_kind != SpellCastingKind.LEVELED:
            continue
        known_spells[source.id] = PreparableSpell(source.id, source.name, source.spell_level)
    available_ids = _parse_string_tuple(
        data.get("available_spell_ids", []),
        f"actor {actor_id}.spell_preparation.available_spell_ids",
    )
    unknown = set(available_ids) - set(known_spells)
    if unknown:
        raise ValueError(
            f"actor {actor_id}.spell_preparation references unknown leveled spells: "
            f"{', '.join(sorted(unknown))}."
        )
    maximum_spell_level = max((slot.level for slot in spell_slots), default=0)
    unavailable_levels = tuple(
        spell_id for spell_id in available_ids if known_spells[spell_id].level > maximum_spell_level
    )
    if unavailable_levels:
        raise ValueError(
            f"actor {actor_id}.spell_preparation contains spells above available slot levels: "
            f"{', '.join(unavailable_levels)}."
        )
    return SpellPreparationProfile(
        source_label=str(data.get("source_label") or "dostępna lista czarów"),
        preparation_limit=int(_required(data, "preparation_limit", f"actor {actor_id}.spell_preparation")),
        available_spells=tuple(known_spells[spell_id] for spell_id in available_ids),
        prepared_spell_ids=_parse_string_tuple(
            data.get("default_prepared_spell_ids", []),
            f"actor {actor_id}.spell_preparation.default_prepared_spell_ids",
        ),
        always_prepared_spell_ids=_parse_string_tuple(
            data.get("always_prepared_spell_ids", []),
            f"actor {actor_id}.spell_preparation.always_prepared_spell_ids",
        ),
    )


def _combat_actions_with_item_source(actions: Any, item_id: str) -> list[dict[str, Any]]:
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise ValueError(f"item {item_id}.combat_actions must be a list.")
    result: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError(f"item {item_id}.combat_actions entries must be objects.")
        item_action = dict(action)
        item_action.setdefault("source_item_id", item_id)
        result.append(item_action)
    return result


def _parse_inventory_entry(item_entry: Any, scenario_path: Path, actor_id: str) -> tuple[dict[str, Any], InventoryItem]:
    if not isinstance(item_entry, dict):
        raise ValueError(f"actor {actor_id}.inventory entries must be objects.")
    item_ref = item_entry.get("item_ref", item_entry.get("ref"))
    if item_ref is not None:
        item_data = _read_json(_content_ref_path(scenario_path, "items", str(item_ref)))
        item_id = str(item_data.get("id", item_ref))
        name = str(item_data.get("name", item_id))
        kind = str(item_data.get("kind", "item"))
        source_ref = str(item_ref)
    else:
        item_data = item_entry
        item_id = str(_required(item_entry, "id", f"actor {actor_id}.inventory"))
        name = str(_required(item_entry, "name", f"actor {actor_id}.inventory {item_id}"))
        kind = str(item_entry.get("kind", "item"))
        source_ref = None
    quantity = int(item_entry.get("quantity", 1))
    if quantity < 0:
        raise ValueError(f"actor {actor_id}.inventory {item_id}.quantity must be non-negative.")
    inventory_item = InventoryItem(
        id=item_id,
        name=str(item_entry.get("name", name)),
        kind=str(item_entry.get("kind", kind)),
        quantity=quantity,
        equipped=bool(item_entry.get("equipped", True)),
        source_ref=source_ref,
        broken=bool(item_entry.get("broken", False)),
    )
    return item_data, inventory_item


def _inventory_item_from_item_data(
    item: dict[str, Any],
    *,
    quantity: int,
    equipped: bool,
    source_ref: str | None,
) -> InventoryItem:
    item_id = str(_required(item, "id", f"item {source_ref or '<inline>'}"))
    return InventoryItem(
        id=item_id,
        name=str(item.get("name", item_id)),
        kind=str(item.get("kind", "item")),
        quantity=quantity,
        equipped=equipped,
        source_ref=source_ref,
        broken=bool(item.get("broken", False)),
    )


def _parse_attack(data: dict[str, Any], actor_id: str) -> ScenarioAttackDefinition:
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.attacks entries must be objects.")
    attack_id = str(_required(data, "id", f"actor {actor_id}.attack"))
    damage = _required_mapping(data, "damage", f"attack {attack_id}")
    source_type = _enum_value(
        AttackSourceType,
        str(_required(data, "source_type", f"attack {attack_id}")),
        f"attack {attack_id}.source_type",
    )
    spell_level = int(data.get("spell_level", 0))
    return ScenarioAttackDefinition(
        id=attack_id,
        name=str(_required(data, "name", f"attack {attack_id}")),
        source_type=source_type,
        range_feet=int(_required(data, "range_feet", f"attack {attack_id}")),
        attack_modifier=int(_required(data, "attack_modifier", f"attack {attack_id}")),
        damage_fixed=_parse_damage_fixed(damage),
        damage_die_sides=_parse_damage_die(damage),
        damage_modifier=int(damage.get("modifier", 0)),
        damage_type=str(_required(damage, "damage_type", f"attack {attack_id}.damage")),
        ability=str(data["ability"]) if "ability" in data else None,
        spell_level=spell_level,
        area=_parse_spell_area(data.get("area"), f"attack {attack_id}.area"),
        save_ability=str(data["save_ability"]) if "save_ability" in data else None,
        save_dc=int(data.get("save_dc", 0)),
        save_damage_on_success=str(data.get("save_damage_on_success", "none")),
        casting_kind=_parse_spell_casting_kind(data.get("casting_kind"), source_type, spell_level, f"attack {attack_id}.casting_kind"),
        prepared=bool(data.get("prepared", True)),
    )


def _parse_healing_source(data: dict[str, Any], actor_id: str) -> ScenarioHealingDefinition:
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.healing_sources entries must be objects.")
    source_id = str(_required(data, "id", f"actor {actor_id}.healing_source"))
    healing = _required_mapping(data, "healing", f"healing source {source_id}")
    source_type = _enum_value(
        HealingSourceType,
        str(_required(data, "source_type", f"healing source {source_id}")),
        f"healing source {source_id}.source_type",
    )
    spell_level = int(data.get("spell_level", 0))
    return ScenarioHealingDefinition(
        id=source_id,
        name=str(_required(data, "name", f"healing source {source_id}")),
        source_type=source_type,
        range_feet=int(_required(data, "range_feet", f"healing source {source_id}")),
        healing_fixed=_parse_damage_fixed(healing),
        healing_die_sides=_parse_damage_die(healing),
        healing_modifier=int(healing.get("modifier", 0)),
        spell_level=spell_level,
        casting_kind=_parse_spell_casting_kind(
            data.get("casting_kind"),
            source_type,
            spell_level,
            f"healing source {source_id}.casting_kind",
        ),
        prepared=bool(data.get("prepared", True)),
    )


def _parse_combat_action(data: dict[str, Any], actor_id: str) -> ScenarioCombatActionDefinition:
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.combat_actions entries must be objects.")
    action_id = str(_required(data, "id", f"actor {actor_id}.combat_action"))
    action_type = str(_required(data, "action_type", f"combat action {action_id}"))
    spell_level = int(data.get("spell_level", 0))
    source_type = AttackSourceType.SPELL if action_type.startswith("concentration_") else AttackSourceType.CUSTOM
    return ScenarioCombatActionDefinition(
        id=action_id,
        name=str(_required(data, "name", f"combat action {action_id}")),
        action_type=action_type,
        label=str(data.get("label", data.get("name", action_id))),
        value=int(data.get("value", 0)),
        ability=str(data["ability"]) if "ability" in data else None,
        duration=str(data.get("duration", "next_turn_start")),
        target_faction=str(data.get("target_faction", "self")),
        spell_level=spell_level,
        casting_kind=_parse_spell_casting_kind(
            data.get("casting_kind"),
            source_type,
            spell_level,
            f"combat action {action_id}.casting_kind",
        ),
        prepared=bool(data.get("prepared", True)),
        concentration=bool(data.get("concentration", False)),
        source_item_id=str(data["source_item_id"]) if "source_item_id" in data else None,
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
        image=str(data.get("image", "")),
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
        llm_context=_parse_llm_context(data.get("llm_context", {}), f"exploration zone {zone_id}.llm_context"),
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
        requires_setup=bool(data.get("requires_setup", True)),
        npc_interaction=_parse_npc_interaction(data.get("npc_interaction"), point_id),
    )


def _parse_npc_interaction(data: Any, point_id: str) -> NpcInteraction | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"exploration point {point_id}.npc_interaction must be an object.")
    policy_data = data.get("policy", {})
    if policy_data is None:
        policy_data = {}
    if not isinstance(policy_data, dict):
        raise ValueError(f"exploration point {point_id}.npc_interaction.policy must be an object.")
    dc_range = policy_data.get("dc_range", [5, 25])
    if not isinstance(dc_range, list | tuple) or len(dc_range) != 2:
        raise ValueError(f"exploration point {point_id}.npc_interaction.policy.dc_range must be [min, max].")
    dc_min = int(dc_range[0])
    dc_max = int(dc_range[1])
    if dc_min > dc_max:
        raise ValueError(f"exploration point {point_id}.npc_interaction.policy.dc_range min cannot exceed max.")
    return NpcInteraction(
        name=str(data.get("name", data.get("public_name", point_id))),
        public_description=str(_required(data, "public_description", f"npc interaction {point_id}")),
        gm_context=str(data.get("gm_context", "")),
        personality=str(data.get("personality", "")),
        current_state=str(data.get("current_state", "")),
        dialogue_intro=str(data.get("dialogue_intro", "")),
        capabilities=tuple(str(item) for item in data.get("capabilities", [])),
        locked_information=tuple(
            _parse_npc_locked_information(entry, point_id)
            for entry in data.get("locked_information", [])
        ),
        policy=NpcInteractionPolicy(
            allowed_actions=tuple(str(item) for item in policy_data.get("allowed_actions", [])),
            intent_permissions=_parse_npc_intent_permissions(policy_data.get("intent_permissions", {}), point_id),
            allowed_flags=tuple(str(item) for item in policy_data.get("allowed_flags", [])),
            allowed_effect_types=tuple(str(item).strip() for item in policy_data.get("allowed_effect_types", ["set_flag"]) if str(item).strip()),
            allowed_abilities=tuple(str(item) for item in policy_data.get("allowed_abilities", [])),
            allowed_skills=tuple(str(item) for item in policy_data.get("allowed_skills", [])),
            dc_min=dc_min,
            dc_max=dc_max,
        ),
    )


def _parse_npc_intent_permissions(data: Any, point_id: str) -> tuple[NpcIntentPermission, ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ValueError(f"exploration point {point_id}.npc_interaction.policy.intent_permissions must be an object.")
    permissions: list[NpcIntentPermission] = []
    for raw_intent, raw_permission in data.items():
        intent = str(raw_intent).strip().lower()
        if not intent:
            raise ValueError(f"exploration point {point_id}.npc_interaction.policy.intent_permissions contains empty intent.")
        if isinstance(raw_permission, str):
            permission_data: dict[str, Any] = {"status": raw_permission}
        elif isinstance(raw_permission, dict):
            permission_data = raw_permission
        else:
            raise ValueError(
                f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent} must be string or object."
            )
        status = str(permission_data.get("status", "")).strip().lower()
        if status not in {"allowed", "allowed_with_consequence", "allowed_with_context", "locked", "blocked"}:
            raise ValueError(
                f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.status is invalid."
            )
        limits = permission_data.get("limits")
        if limits is not None and not isinstance(limits, dict):
            raise ValueError(
                f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.limits must be an object."
            )
        consequences = permission_data.get("consequences")
        if consequences is not None and not isinstance(consequences, dict):
            raise ValueError(
                f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.consequences must be an object."
            )
        permissions.append(
            NpcIntentPermission(
                intent=intent,
                status=status,
                notes=str(permission_data.get("notes", "")),
                unlock_if_flags=tuple(str(item) for item in permission_data.get("unlock_if_flags", [])),
                limits=limits,
                consequences=consequences,
                reveals=tuple(str(item) for item in permission_data.get("reveals", [])),
            )
        )
    return tuple(permissions)


def _parse_npc_locked_information(data: Any, point_id: str) -> NpcLockedInformation:
    if not isinstance(data, dict):
        raise ValueError(f"exploration point {point_id}.npc_interaction.locked_information entries must be objects.")
    info_id = str(_required(data, "id", f"npc interaction {point_id}.locked_information"))
    return NpcLockedInformation(
        id=info_id,
        label=str(_required(data, "label", f"npc locked information {info_id}")),
        text=str(_required(data, "text", f"npc locked information {info_id}")),
        reveal_if_flags=tuple(str(item) for item in data.get("reveal_if_flags", [])),
        sets_flags=tuple(str(item) for item in data.get("sets_flags", [])),
        effects_on_reveal=_parse_effects(data.get("effects_on_reveal", []), f"npc locked information {info_id}.effects_on_reveal"),
    )


def _parse_effects(data: Any, field: str) -> tuple[dict[str, object], ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"{field} must be a list.")
    effects: list[dict[str, object]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{field}[{index}] must be an object.")
        effect_type = str(item.get("type", "")).strip()
        if not effect_type:
            raise ValueError(f"{field}[{index}].type cannot be empty.")
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError(f"{field}[{index}].parameters must be an object.")
        effects.append({"type": effect_type, "parameters": dict(parameters)})
    return tuple(effects)


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
        reveals_on_complete=tuple(str(item) for item in data.get("reveals_on_complete", [])),
        llm_context=_parse_llm_context(data.get("llm_context", {}), f"exploration challenge {challenge_id}.llm_context"),
        llm_policy=_parse_llm_challenge_policy(data.get("llm_policy", {}), f"exploration challenge {challenge_id}.llm_policy"),
    )


def _parse_exploration_challenge_option(data: Any, challenge_id: str) -> ExplorationChallengeOption:
    if not isinstance(data, dict):
        raise ValueError(f"exploration challenge {challenge_id}.options entries must be objects.")
    option_id = str(_required(data, "id", f"exploration challenge {challenge_id}.option"))
    requirements = data.get("requires", {})
    if requirements is None:
        requirements = {}
    if not isinstance(requirements, dict):
        raise ValueError(f"exploration challenge option {option_id}.requires must be an object.")
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
        requires_item_ids=_parse_string_tuple(
            data.get("requires_item_ids", requirements.get("items", [])),
            f"exploration challenge option {option_id}.requires.items",
        ),
        requires_spell_ids=_parse_string_tuple(
            data.get("requires_spell_ids", requirements.get("spells", [])),
            f"exploration challenge option {option_id}.requires.spells",
        ),
        requires_ability_scores=_parse_required_ability_scores(
            data.get("requires_ability_scores", requirements.get("ability_scores", {})),
            option_id,
        ),
        bonuses=_parse_exploration_option_bonuses(data.get("bonuses", []), option_id),
        mechanic_id=str(data["mechanic_id"]) if "mechanic_id" in data else None,
        roll_mode=RollMode(str(data.get("roll_mode", RollMode.NORMAL.value))),
        situational_modifiers=_parse_exploration_situational_modifiers(
            data.get("situational_modifiers", []),
            option_id,
        ),
        improvised_tool=_parse_improvised_tool(data.get("improvised_tool"), option_id),
    )


def _parse_exploration_option_bonuses(data: Any, option_id: str) -> tuple[ExplorationOptionBonus, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"exploration challenge option {option_id}.bonuses must be a list.")
    result: list[ExplorationOptionBonus] = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"exploration challenge option {option_id}.bonuses[{index}] must be an object.")
        source_type = str(entry.get("source_type", entry.get("source", "")))
        if source_type not in {"item", "spell"}:
            raise ValueError(f"exploration challenge option {option_id}.bonuses[{index}].source_type must be item or spell.")
        source_id = str(_required(entry, "id", f"exploration challenge option {option_id}.bonuses[{index}]"))
        label = str(entry.get("label", source_id))
        breakage_data = entry.get("breakage")
        breakage_risk = None
        if breakage_data is not None:
            if not isinstance(breakage_data, dict):
                raise ValueError(f"exploration challenge option {option_id}.bonuses[{index}].breakage must be an object.")
            breakage_risk = ItemBreakageRisk(
                chance_percent=int(_required(breakage_data, "chance_percent", f"exploration challenge option {option_id}.bonuses[{index}].breakage")),
                trigger=str(breakage_data.get("trigger", "critical_failure")),
            )
        result.append(
            ExplorationOptionBonus(
                source_type=source_type,
                source_id=source_id,
                label=label,
                modifier=int(entry.get("modifier", 0)),
                spell_level=int(entry.get("spell_level", 0)),
                consume=bool(entry.get("consume", False)),
                breakage_risk=breakage_risk,
            )
        )
    return tuple(result)


def _parse_exploration_situational_modifiers(data: Any, option_id: str) -> tuple[ExplorationSituationalModifier, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"exploration challenge option {option_id}.situational_modifiers must be a list.")
    result: list[ExplorationSituationalModifier] = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"exploration challenge option {option_id}.situational_modifiers[{index}] must be an object.")
        result.append(
            ExplorationSituationalModifier(
                label=str(_required(entry, "label", f"exploration challenge option {option_id}.situational_modifiers[{index}]")),
                modifier=int(entry.get("modifier", 0)),
                source=ExplorationSituationalModifierSource(str(entry.get("source", "gm"))),
                reason=str(_required(entry, "reason", f"exploration challenge option {option_id}.situational_modifiers[{index}]")),
                roll_mode=RollMode(str(entry.get("roll_mode", RollMode.NORMAL.value))),
            )
        )
    return tuple(result)


def _parse_improvised_tool(data: Any, option_id: str) -> ImprovisedToolUse | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"exploration challenge option {option_id}.improvised_tool must be an object.")
    return ImprovisedToolUse(
        label=str(_required(data, "label", f"exploration challenge option {option_id}.improvised_tool")),
        source=ExplorationSituationalModifierSource(str(data.get("source", "gm"))),
        source_detail=str(_required(data, "source_detail", f"exploration challenge option {option_id}.improvised_tool")),
        effect_modifier=int(data.get("effect_modifier", 1)),
        risk=str(data.get("risk", "")),
        reason=str(_required(data, "reason", f"exploration challenge option {option_id}.improvised_tool")),
    )


def _parse_required_ability_scores(data: Any, option_id: str) -> tuple[tuple[str, int], ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ValueError(f"exploration challenge option {option_id}.requires.ability_scores must be an object.")
    result: list[tuple[str, int]] = []
    for ability, minimum in data.items():
        ability_name = str(ability)
        if ability_name not in {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}:
            raise ValueError(f"exploration challenge option {option_id}.requires.ability_scores has unknown ability: {ability_name}.")
        result.append((ability_name, int(minimum)))
    return tuple(result)


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
        consume_on_use=bool(data.get("consume_on_use", False)),
    )


def _parse_exploration_encounter_trigger(data: Any) -> ExplorationEncounterTrigger:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.encounter_triggers entries must be objects.")
    trigger_id = str(_required(data, "id", "exploration encounter trigger"))
    condition = _enum_value(
        EncounterTriggerCondition,
        str(_required(data, "condition", f"exploration encounter trigger {trigger_id}")),
        f"exploration encounter trigger {trigger_id}.condition",
    )
    return ExplorationEncounterTrigger(
        id=trigger_id,
        name=str(_required(data, "name", f"exploration encounter trigger {trigger_id}")),
        description=str(data.get("description", "")),
        encounter_scenario=str(_required(data, "encounter_scenario", f"exploration encounter trigger {trigger_id}")),
        condition=condition,
        challenge_id=str(data["challenge_id"]) if "challenge_id" in data else None,
        noise=int(data["noise"]) if "noise" in data else None,
        flag_key=str(data["flag_key"]) if "flag_key" in data else None,
        flag_value=data.get("flag_value", True),
        point_id=str(data["point_id"]) if "point_id" in data else None,
        outcome_on_victory=_parse_encounter_outcome(
            data.get("outcome_on_victory"),
            f"exploration encounter trigger {trigger_id}.outcome_on_victory",
        ),
        outcome_on_defeat=_parse_encounter_outcome(
            data.get("outcome_on_defeat"),
            f"exploration encounter trigger {trigger_id}.outcome_on_defeat",
        ),
    )


def _parse_encounter_outcome(data: Any, field: str) -> EncounterOutcome | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    return EncounterOutcome(
        title=str(data.get("title", "")),
        body=str(data.get("body", "")),
        effects=_parse_effects(data.get("effects", []), f"{field}.effects"),
        next_instruction=str(data.get("next_instruction", "")),
    )


def _parse_llm_context(data: Any, field: str) -> LlmContext:
    if data is None:
        return LlmContext()
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    return LlmContext(
        summary=str(data.get("summary", "")),
        available_materials=_parse_string_tuple(data.get("available_materials", []), f"{field}.available_materials"),
        forbidden_assumptions=_parse_string_tuple(data.get("forbidden_assumptions", []), f"{field}.forbidden_assumptions"),
        reasonable_approaches=_parse_string_tuple(data.get("reasonable_approaches", []), f"{field}.reasonable_approaches"),
        impossible_approaches=_parse_string_tuple(data.get("impossible_approaches", []), f"{field}.impossible_approaches"),
        risk_notes=_parse_string_tuple(data.get("risk_notes", []), f"{field}.risk_notes"),
    )


def _parse_llm_challenge_policy(data: Any, field: str) -> LlmChallengePolicy:
    if data is None or data == {}:
        return LlmChallengePolicy()
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    defaults = LlmChallengePolicy()
    dc_min, dc_max = _parse_int_range(data.get("dc_range", [5, 25]), f"{field}.dc_range")
    progress_success_min, progress_success_max = _parse_int_range(
        data.get("progress_on_success_range", [1, 3]),
        f"{field}.progress_on_success_range",
    )
    progress_failure_min, progress_failure_max = _parse_int_range(
        data.get("progress_on_failure_range", [0, 1]),
        f"{field}.progress_on_failure_range",
    )
    preparation_modifier_min, preparation_modifier_max = _parse_int_range(
        data.get("preparation_modifier_range", [1, 2]),
        f"{field}.preparation_modifier_range",
    )
    negative_effect_reduction_min, negative_effect_reduction_max = _parse_int_range(
        data.get("negative_effect_reduction_range", [1, 1]),
        f"{field}.negative_effect_reduction_range",
    )
    effect_boost_min, effect_boost_max = _parse_int_range(
        data.get("effect_boost_range", [1, 1]),
        f"{field}.effect_boost_range",
    )
    dc_tiers, allowed_difficulty_tiers, default_difficulty_tier, difficulty_guidance = _parse_dc_policy(
        data.get("dc_policy", {}),
        f"{field}.dc_policy",
    )
    return LlmChallengePolicy(
        allowed_local_skills=_parse_string_tuple(data.get("allowed_local_skills", ["crafting"]), f"{field}.allowed_local_skills"),
        allowed_approach_tags=_parse_string_tuple(data.get("allowed_approach_tags", list(defaults.allowed_approach_tags)), f"{field}.allowed_approach_tags"),
        allowed_complications=_parse_string_tuple(data.get("allowed_complications", list(defaults.allowed_complications)), f"{field}.allowed_complications"),
        allowed_consequence_types=_parse_string_tuple(
            data.get("allowed_consequence_types", list(defaults.allowed_consequence_types)),
            f"{field}.allowed_consequence_types",
        ),
        allowed_preparation_effect_types=_parse_string_tuple(
            data.get("allowed_preparation_effect_types", list(defaults.allowed_preparation_effect_types)),
            f"{field}.allowed_preparation_effect_types",
        ),
        allowed_grant_resource_ids=_parse_string_tuple(
            data.get("allowed_grant_resource_ids", list(defaults.allowed_grant_resource_ids)),
            f"{field}.allowed_grant_resource_ids",
        ),
        allowed_unlock_option_ids=_parse_string_tuple(
            data.get("allowed_unlock_option_ids", list(defaults.allowed_unlock_option_ids)),
            f"{field}.allowed_unlock_option_ids",
        ),
        max_resources_per_attempt=int(data.get("max_resources_per_attempt", 1)),
        dc_min=dc_min,
        dc_max=dc_max,
        progress_success_min=progress_success_min,
        progress_success_max=progress_success_max,
        progress_failure_min=progress_failure_min,
        progress_failure_max=progress_failure_max,
        preparation_modifier_min=preparation_modifier_min,
        preparation_modifier_max=preparation_modifier_max,
        negative_effect_reduction_min=negative_effect_reduction_min,
        negative_effect_reduction_max=negative_effect_reduction_max,
        effect_boost_min=effect_boost_min,
        effect_boost_max=effect_boost_max,
        dc_tiers=dc_tiers,
        allowed_difficulty_tiers=allowed_difficulty_tiers,
        default_difficulty_tier=default_difficulty_tier,
        difficulty_guidance=difficulty_guidance,
    )


def _parse_dc_policy(data: Any, field: str) -> tuple[tuple[LlmDcTier, ...], tuple[str, ...], str | None, tuple[str, ...]]:
    if data is None or data == {}:
        return (), (), None, ()
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    raw_tiers = data.get("tiers", {})
    if not isinstance(raw_tiers, dict):
        raise ValueError(f"{field}.tiers must be an object.")
    tiers: list[LlmDcTier] = []
    for tier_id, tier_data in raw_tiers.items():
        normalized_id = str(tier_id).strip()
        if not normalized_id:
            raise ValueError(f"{field}.tiers contains an empty tier id.")
        if isinstance(tier_data, int):
            tiers.append(LlmDcTier(normalized_id, tier_data))
            continue
        if not isinstance(tier_data, dict):
            raise ValueError(f"{field}.tiers.{normalized_id} must be an object or integer.")
        tiers.append(
            LlmDcTier(
                id=normalized_id,
                dc=int(_required(tier_data, "dc", f"{field}.tiers.{normalized_id}")),
                label=str(tier_data.get("label", "")),
                guidance=str(tier_data.get("guidance", "")),
            )
        )
    allowed = _parse_string_tuple(data.get("allowed_tiers", [tier.id for tier in tiers]), f"{field}.allowed_tiers")
    default = str(data["default_tier"]).strip() if "default_tier" in data and data["default_tier"] is not None else None
    guidance = _parse_string_tuple(data.get("guidance", []), f"{field}.guidance")
    return tuple(tiers), allowed, default, guidance


def _parse_int_range(data: Any, field: str) -> tuple[int, int]:
    if not isinstance(data, list) or len(data) != 2:
        raise ValueError(f"{field} must be a two-item list.")
    minimum = int(data[0])
    maximum = int(data[1])
    if minimum > maximum:
        raise ValueError(f"{field} minimum cannot be greater than maximum.")
    return minimum, maximum


def _parse_string_tuple(data: Any, field: str) -> tuple[str, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"{field} must be a list.")
    return tuple(str(item) for item in data)


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
        conditions=_parse_interaction_conditions(data.get("conditions", []), interaction_id),
        effects=_parse_interaction_effects(data.get("effects", []), interaction_id),
    )


def _parse_interaction_conditions(data: Any, interaction_id: str) -> tuple[SceneInteractionCondition, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"interaction {interaction_id}.conditions must be a list.")
    return tuple(
        SceneInteractionCondition(
            condition_type=str(_required(_require_mapping(entry, f"interaction {interaction_id}.conditions"), "type", f"interaction {interaction_id}.condition")),
            parameters=_parse_interaction_parameters(entry.get("parameters", {}), f"interaction {interaction_id}.condition"),
        )
        for entry in data
    )


def _parse_interaction_effects(data: Any, interaction_id: str) -> tuple[SceneInteractionEffect, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"interaction {interaction_id}.effects must be a list.")
    return tuple(
        SceneInteractionEffect(
            effect_type=str(_required(_require_mapping(entry, f"interaction {interaction_id}.effects"), "type", f"interaction {interaction_id}.effect")),
            parameters=_parse_interaction_parameters(entry.get("parameters", {}), f"interaction {interaction_id}.effect"),
        )
        for entry in data
    )


def _require_mapping(data: Any, field: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{field} entries must be objects.")
    return data


def _parse_interaction_parameters(data: Any, field: str) -> tuple[tuple[str, object], ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ValueError(f"{field}.parameters must be an object.")
    return tuple(sorted((str(key), value) for key, value in data.items()))


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
        max_hp=definition.hp,
        ability_scores=definition.ability_scores,
        spell_slots=definition.spell_slots,
        spell_save_dc=definition.spell_save_dc,
        inventory=definition.inventory,
        spell_ids=definition.spell_ids,
        spell_preparation=definition.spell_preparation,
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
        id=definition.id,
        ability=definition.ability,
        spell_level=definition.spell_level,
        area=definition.area,
        save_ability=definition.save_ability,
        save_dc=definition.save_dc,
        save_damage_on_success=definition.save_damage_on_success,
        casting_kind=definition.casting_kind,
        prepared=definition.prepared,
    )


def _healing_source_from_definition(definition: ScenarioHealingDefinition) -> HealingSource:
    return HealingSource(
        id=definition.id,
        name=definition.name,
        source_type=definition.source_type,
        range_feet=definition.range_feet,
        healing_hint=_healing_hint(definition),
        healing_fixed=definition.healing_fixed,
        healing_die_sides=definition.healing_die_sides,
        healing_modifier=definition.healing_modifier,
        spell_level=definition.spell_level,
        casting_kind=definition.casting_kind,
        prepared=definition.prepared,
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
    actor_item_ids = {item.id for actor in definition.actors for item in actor.inventory}
    actor_spell_ids = {spell_id for actor in definition.actors for spell_id in actor.spell_ids}
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
        for point_id in challenge.reveals_on_complete:
            point = next((candidate for candidate in definition.exploration_points if candidate.id == point_id), None)
            if point is None:
                raise ValueError(
                    f"exploration challenge {challenge.id}.reveals_on_complete references unknown point: {point_id}."
                )
            point_zone = next((zone for zone in definition.exploration_zones if zone.id == point.zone_id), None)
            reveal_unlocked_by_challenge = (
                point_zone is not None
                and point_zone.available_if_flag == challenge.completed_flag
                and point_zone.available_if_value is True
            )
            if point.zone_id != challenge.zone_id and not reveal_unlocked_by_challenge:
                raise ValueError(
                    f"exploration challenge {challenge.id}.reveals_on_complete references point outside challenge zone "
                    f"or challenge-unlocked zone: {point_id}."
                )
        _validate_llm_challenge_policy(challenge, resource_ids)
        option_ids = {option.id for option in challenge.options}
        unknown_unlock_options = set(challenge.llm_policy.allowed_unlock_option_ids) - option_ids
        if unknown_unlock_options:
            raise ValueError(
                f"exploration challenge {challenge.id}.llm_policy.allowed_unlock_option_ids references unknown options: "
                f"{', '.join(sorted(unknown_unlock_options))}."
            )
        unknown_grant_resources = set(challenge.llm_policy.allowed_grant_resource_ids) - resource_ids
        if unknown_grant_resources:
            raise ValueError(
                f"exploration challenge {challenge.id}.llm_policy.allowed_grant_resource_ids references unknown resources: "
                f"{', '.join(sorted(unknown_grant_resources))}."
            )
        for option in challenge.options:
            if option.progress_on_success < 0 or option.progress_on_failure < 0:
                raise ValueError(f"exploration challenge option {option.id}.progress values must be non-negative.")
            if option.mechanic_id is not None:
                try:
                    mechanic_tool(option.mechanic_id)
                except ValueError as exc:
                    raise ValueError(f"exploration challenge option {option.id}.mechanic_id is unknown: {option.mechanic_id}.") from exc
            if option.unlocks_if_resource_id is not None and option.unlocks_if_resource_id not in resource_ids:
                raise ValueError(
                    f"exploration challenge option {option.id}.unlocks_if_resource_id references unknown resource."
                )
            unknown_items = set(option.requires_item_ids) - actor_item_ids
            if unknown_items:
                raise ValueError(
                    f"exploration challenge option {option.id}.requires.items references unknown actor inventory items: "
                    f"{', '.join(sorted(unknown_items))}."
                )
            unknown_spells = set(option.requires_spell_ids) - actor_spell_ids
            if unknown_spells:
                raise ValueError(
                    f"exploration challenge option {option.id}.requires.spells references unknown actor spells: "
                    f"{', '.join(sorted(unknown_spells))}."
                )
            for bonus in option.bonuses:
                if bonus.source_type == "item" and bonus.source_id not in actor_item_ids:
                    raise ValueError(
                        f"exploration challenge option {option.id}.bonuses references unknown actor inventory item: "
                        f"{bonus.source_id}."
                    )
                if bonus.source_type == "spell" and bonus.source_id not in actor_spell_ids:
                    raise ValueError(
                        f"exploration challenge option {option.id}.bonuses references unknown actor spell: "
                        f"{bonus.source_id}."
                    )
    challenge_ids = {challenge.id for challenge in definition.exploration_challenges}
    for trigger in definition.exploration_encounter_triggers:
        if trigger.condition == EncounterTriggerCondition.NOISE_AT_LEAST:
            if trigger.challenge_id not in challenge_ids:
                raise ValueError(f"exploration encounter trigger {trigger.id}.challenge_id references unknown challenge.")
            if trigger.noise is None:
                raise ValueError(f"exploration encounter trigger {trigger.id}.noise is required for noise_at_least.")
        elif trigger.condition == EncounterTriggerCondition.FLAG_EQUALS:
            if not trigger.flag_key:
                raise ValueError(f"exploration encounter trigger {trigger.id}.flag_key is required for flag_equals.")
        elif trigger.condition == EncounterTriggerCondition.POINT_REVEALED:
            if trigger.point_id not in point_ids:
                raise ValueError(f"exploration encounter trigger {trigger.id}.point_id references unknown point.")


def _validate_llm_challenge_policy(challenge: ExplorationChallenge, resource_ids: set[str]) -> None:
    policy = challenge.llm_policy
    if policy.max_resources_per_attempt < 0:
        raise ValueError(f"exploration challenge {challenge.id}.llm_policy.max_resources_per_attempt must be non-negative.")
    if policy.dc_min > policy.dc_max:
        raise ValueError(f"exploration challenge {challenge.id}.llm_policy.dc_range minimum cannot exceed maximum.")
    if policy.progress_success_min > policy.progress_success_max:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.progress_on_success_range minimum cannot exceed maximum."
        )
    if policy.progress_failure_min > policy.progress_failure_max:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.progress_on_failure_range minimum cannot exceed maximum."
        )
    if policy.preparation_modifier_min > policy.preparation_modifier_max:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.preparation_modifier_range minimum cannot exceed maximum."
        )
    if policy.negative_effect_reduction_min > policy.negative_effect_reduction_max:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.negative_effect_reduction_range minimum cannot exceed maximum."
        )
    if policy.effect_boost_min > policy.effect_boost_max:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.effect_boost_range minimum cannot exceed maximum."
        )
    unknown_consequence_types = set(policy.allowed_consequence_types) - KNOWN_LLM_CONSEQUENCE_TYPES
    if unknown_consequence_types:
        raise ValueError(
            "exploration challenge "
            f"{challenge.id}.llm_policy.allowed_consequence_types contains unknown values: "
            f"{', '.join(sorted(unknown_consequence_types))}."
        )
    unknown_preparation_types = set(policy.allowed_preparation_effect_types) - KNOWN_LLM_PREPARATION_EFFECT_TYPES
    if unknown_preparation_types:
        raise ValueError(
            "exploration challenge "
            f"{challenge.id}.llm_policy.allowed_preparation_effect_types contains unknown values: "
            f"{', '.join(sorted(unknown_preparation_types))}."
        )
    unknown_grant_resources = set(policy.allowed_grant_resource_ids) - resource_ids
    if unknown_grant_resources:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.allowed_grant_resource_ids references unknown resources: "
            f"{', '.join(sorted(unknown_grant_resources))}."
        )
    tier_ids = [tier.id for tier in policy.dc_tiers]
    if len(tier_ids) != len(set(tier_ids)):
        raise ValueError(f"exploration challenge {challenge.id}.llm_policy.dc_policy.tiers contains duplicate ids.")
    tier_id_set = set(tier_ids)
    unknown_allowed_tiers = set(policy.allowed_difficulty_tiers) - tier_id_set
    if unknown_allowed_tiers:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.dc_policy.allowed_tiers references unknown tiers: "
            f"{', '.join(sorted(unknown_allowed_tiers))}."
        )
    if policy.default_difficulty_tier is not None and policy.default_difficulty_tier not in tier_id_set:
        raise ValueError(
            f"exploration challenge {challenge.id}.llm_policy.dc_policy.default_tier references unknown tier."
        )
    for tier in policy.dc_tiers:
        if tier.dc < policy.dc_min or tier.dc > policy.dc_max:
            raise ValueError(
                f"exploration challenge {challenge.id}.llm_policy.dc_policy.tiers.{tier.id}.dc "
                f"is outside dc_range {policy.dc_min}-{policy.dc_max}."
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
        "purple": LedColor.MENU_PURPLE,
        "success": LedColor.INTERACTION_SUCCESS,
        "warning": LedColor.ENEMY_MOVEMENT_DESTINATION,
        "danger": LedColor.ATTACK_MISS,
    }
    if str(value) in named:
        return named[str(value)]
    raise ValueError(f"Unknown color for {field}: {value}.")


def _load_scenario_data(path: Path) -> tuple[dict[str, Any], Path]:
    scenario_path = path / "scenario.json" if path.is_dir() else path
    data = _read_json(scenario_path)
    data, source_path = _resolve_scenario_include(data, scenario_path)
    return _expand_scenario_parts(data, source_path), source_path


def _resolve_scenario_include(data: dict[str, Any], scenario_path: Path) -> tuple[dict[str, Any], Path]:
    include = data.get("$include")
    if include is None:
        return data, scenario_path
    if not isinstance(include, str):
        raise ValueError(f"{scenario_path}.$include must be a string.")
    include_path = _relative_content_path(scenario_path, include)
    included = _read_json(include_path)
    included, source_path = _resolve_scenario_include(included, include_path)
    overlay = {key: value for key, value in data.items() if key != "$include"}
    if overlay:
        included = _deep_merge(included, overlay)
    return included, source_path


def _expand_scenario_parts(data: dict[str, Any], scenario_path: Path) -> dict[str, Any]:
    parts = data.get("parts")
    if parts is None:
        return data
    if not isinstance(parts, dict):
        raise ValueError(f"{scenario_path}.parts must be an object.")
    expanded = {key: value for key, value in data.items() if key != "parts"}
    for field in ("actors", "environment", "objectives", "player_start_zones", "llm_context"):
        if field in parts:
            expanded[field] = _load_named_part(scenario_path, parts[field], field)
    if "exploration" in parts:
        existing = expanded.get("exploration", {})
        if existing is None:
            existing = {}
        if not isinstance(existing, dict):
            raise ValueError(f"{scenario_path}.exploration must be an object when parts.exploration is used.")
        expanded["exploration"] = _deep_merge(existing, _load_exploration_parts(scenario_path, parts["exploration"]))
    return expanded


def _load_exploration_parts(scenario_path: Path, part: Any) -> dict[str, Any]:
    if isinstance(part, str):
        loaded = _load_json_value(_relative_content_path(scenario_path, part))
        if not isinstance(loaded, dict):
            raise ValueError(f"{scenario_path}.parts.exploration must point to an object.")
        return _extract_part_value(loaded, "exploration")
    if not isinstance(part, dict):
        raise ValueError(f"{scenario_path}.parts.exploration must be a string or object.")
    result: dict[str, Any] = {}
    for field, ref in part.items():
        result[field] = _load_named_part(scenario_path, ref, field)
    return result


def _load_named_part(scenario_path: Path, ref: Any, field: str) -> Any:
    if isinstance(ref, str):
        return _extract_part_value(_load_json_value(_relative_content_path(scenario_path, ref)), field)
    return ref


def _extract_part_value(value: Any, field: str) -> Any:
    if isinstance(value, dict) and field in value:
        return value[field]
    return value


def _relative_content_path(source_path: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return source_path.parent / path


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_json(path: Path) -> dict[str, Any]:
    data = _load_json_value(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _load_json_value(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _content_ref_path(scenario_path: Path, category: str, ref: str) -> Path:
    root = _content_root_path(scenario_path)
    filename = ref if ref.endswith(".json") else f"{ref}.json"
    return root / category / filename


def _content_root_path(scenario_path: Path) -> Path:
    for parent in (scenario_path.parent, *scenario_path.parents):
        if parent.name == "content":
            return parent
    return scenario_path.parent.parent


def _parse_ability_scores(data: dict[str, Any]) -> AbilityScores:
    return AbilityScores(
        strength=int(data.get("strength", 10)),
        dexterity=int(data.get("dexterity", 10)),
        constitution=int(data.get("constitution", 10)),
        intelligence=int(data.get("intelligence", 10)),
        wisdom=int(data.get("wisdom", 10)),
        charisma=int(data.get("charisma", 10)),
    )


def _parse_spell_slots(data: Any, actor_id: str) -> tuple[SpellSlotState, ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.spell_slots must be an object.")
    slots: list[SpellSlotState] = []
    for level, value in data.items():
        maximum = int(value)
        slots.append(SpellSlotState(level=int(level), remaining=maximum, maximum=maximum))
    return tuple(sorted(slots, key=lambda slot: slot.level))


def _parse_spell_casting_kind(
    data: Any,
    source_type,
    spell_level: int,
    field: str,
) -> SpellCastingKind:
    source_type_value = getattr(source_type, "value", str(source_type))
    if data is None:
        if source_type_value != "spell":
            return SpellCastingKind.NONE
        return SpellCastingKind.LEVELED if int(spell_level) > 0 else SpellCastingKind.CANTRIP
    kind = _enum_value(SpellCastingKind, str(data), field)
    if source_type_value != "spell" and kind != SpellCastingKind.NONE:
        raise ValueError(f"{field} can only be set for spell sources.")
    if kind == SpellCastingKind.LEVELED and int(spell_level) <= 0:
        raise ValueError(f"{field} leveled requires spell_level greater than 0.")
    if kind == SpellCastingKind.CANTRIP and int(spell_level) != 0:
        raise ValueError(f"{field} cantrip requires spell_level 0.")
    return kind


def _parse_spell_area(data: Any, field: str) -> SpellArea | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    shape = _enum_value(SpellAreaShape, str(_required(data, "shape", field)), f"{field}.shape")
    return SpellArea(
        shape=shape,
        radius_feet=int(data.get("radius_feet", 0)),
        length_feet=int(data.get("length_feet", 0)),
        width_feet=int(data.get("width_feet", 5)),
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


def _healing_hint(definition: ScenarioHealingDefinition) -> str:
    if definition.healing_fixed is not None:
        base = str(definition.healing_fixed)
    elif definition.healing_die_sides is None:
        base = "leczenie"
    else:
        base = f"1d{definition.healing_die_sides}"
    if definition.healing_modifier:
        sign = "+" if definition.healing_modifier > 0 else "-"
        base = f"{base} {sign} {abs(definition.healing_modifier)}"
    return base


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
