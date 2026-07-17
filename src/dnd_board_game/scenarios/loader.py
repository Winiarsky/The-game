from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd_board_game.actors import (
    ABILITY_NAMES,
    AbilityScores,
    Actor,
    ActorAura,
    ActorTrigger,
    ActorId,
    AuraEffectKind,
    AuraTarget,
    TriggerEffectKind,
    TriggerEventType,
    CreatureSize,
    DamageAffinityProfile,
    Faction,
    FeatureDefinition,
    FeatureGrant,
    FeatureSourceKind,
    PreparableSpell,
    ActorResourcePool,
    HitDicePool,
    ProficiencyProfile,
    RecoveryPeriod,
    ResourceRechargeRule,
    SpellPreparationProfile,
    attack_roll_modifiers,
)
from dnd_board_game.combat import (
    ActionEconomyCost,
    AttackSource,
    AttackKind,
    AttackSourceType,
    CombatCondition,
    ConditionSaveTiming,
    DamageType,
    HealingSource,
    HealingSourceType,
    SpellCastingKind,
    SpellArea,
    SpellAreaShape,
    SpellAreaTargetMode,
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
    SceneFlags,
)
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationEncounterTrigger,
    ExplorationHazard,
    ExplorationHazardDamage,
    ExplorationHazardTrigger,
    ExplorationTrap,
    ExplorationObservation,
    ExplorationOptionBonus,
    ExplorationSituationalModifier,
    ExplorationSituationalModifierSource,
    EncounterOutcome,
    EncounterOpeningOutcome,
    EncounterOpeningPolicy,
    EncounterOpeningRule,
    EncounterEdgeType,
    CraftingPolicy,
    CraftingPropertyRequirement,
    CraftingPurpose,
    ExplorationOption,
    ExplorationOptionKind,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    ImprovisedToolUse,
    ItemBreakageRisk,
    LlmChallengePolicy,
    LlmContext,
    LlmGuidanceFact,
    LlmGuidanceFactKind,
    LlmGuidanceFactVisibility,
    LlmDcTier,
    NpcInteraction,
    NpcAttitude,
    NpcAttemptPolicy,
    NpcIntentTarget,
    NpcIntentPermission,
    NpcInteractionPolicy,
    NpcLockedInformation,
    NpcOutcomeBranch,
    NpcOutcomeTier,
    NpcInteractionStatus,
    NpcSceneTransition,
    NpcTransitionReaction,
    NpcTransitionResultType,
    NpcTransitionVariant,
    NpcStateUpdate,
    ObservationFact,
    ObservationEncounterEdge,
    PartyPosition,
    SceneMode,
    SceneFixture,
    FixtureActionPolicy,
    FixtureOperation,
    RestSafety,
    ShortRestPolicy,
    TemporaryItemTemplate,
    EncounterTriggerCondition,
    mechanic_tool,
    validate_policy_exploration_effect,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.rules import EffectDuration, SaveDamageOnSuccess, SavingThrowRequest
from dnd_board_game.inventory import (
    InventoryItem,
    HandSlot,
    ItemCollectionDestination,
    ItemDefinition,
    ItemInstance,
    ItemPropertyCatalog,
    ItemPropertyDefinition,
    normalize_hand_equipment,
)
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
        "create_temporary_item",
    }
)


@dataclass(frozen=True, slots=True)
class ScenarioAttackDefinition:
    id: str
    name: str
    source_type: AttackSourceType
    range_feet: int
    reach_feet: int | None
    attack_modifier: int | None
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
    resource_pool_id: str | None = None
    resource_cost: int = 1
    source_item_id: str | None = None
    attack_kind: AttackKind = AttackKind.MELEE
    proficiency_id: str | None = None


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
    range_feet: int = 0
    effect_kind: str | None = None
    action_cost: ActionEconomyCost = ActionEconomyCost.ACTION
    condition: CombatCondition | None = None
    save_ability: str | None = None
    save_dc: int | None = None
    save_timing: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioActorDefinition:
    id: str
    name: str
    kind: str
    faction: Faction
    size: CreatureSize
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
    hit_dice: tuple[HitDicePool, ...]
    resource_pools: tuple[ActorResourcePool, ...]
    proficiency_bonus: int
    proficiencies: ProficiencyProfile
    uses_death_saves: bool
    damage_affinities: DamageAffinityProfile
    attacks: tuple[ScenarioAttackDefinition, ...]
    attacks_per_action: int = 1
    multiattack: tuple[str, ...] = ()
    condition_immunities: tuple[str, ...] = ()
    auras: tuple[ActorAura, ...] = ()
    triggers: tuple[ActorTrigger, ...] = ()
    features: tuple[FeatureGrant, ...] = ()
    healing_sources: tuple[ScenarioHealingDefinition, ...] = ()
    combat_actions: tuple[ScenarioCombatActionDefinition, ...] = ()
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioFeatureDefinition:
    definition: FeatureDefinition
    resource_pools: tuple[ActorResourcePool, ...] = ()
    attacks: tuple[ScenarioAttackDefinition, ...] = ()
    healing_sources: tuple[ScenarioHealingDefinition, ...] = ()
    combat_actions: tuple[ScenarioCombatActionDefinition, ...] = ()
    auras: tuple[ActorAura, ...] = ()
    triggers: tuple[ActorTrigger, ...] = ()


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
    projectile_cover_bonus: int = 0


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
    exploration_npc_transitions: tuple[NpcSceneTransition, ...] = ()
    exploration_observations: tuple[ExplorationObservation, ...] = ()
    exploration_traps: tuple[ExplorationTrap, ...] = ()
    party_start_zone_id: str | None = None
    llm_context: LlmContext = LlmContext()
    crafting_policy: CraftingPolicy = CraftingPolicy()


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
    multiattack_sources_by_actor: dict[ActorId, tuple[AttackSource, ...]]
    weapon_attack_sources_by_item_id: dict[str, tuple[AttackSource, ...]]
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
    npc_transitions: tuple[NpcSceneTransition, ...] = ()
    observations: tuple[ExplorationObservation, ...] = ()
    traps: tuple[ExplorationTrap, ...] = ()
    environment: tuple[EnvironmentSetupEntry, ...] = ()
    llm_context: LlmContext = LlmContext()
    objectives: tuple[SceneObjective, ...] = ()
    crafting_policy: CraftingPolicy = CraftingPolicy()


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
    actors_by_id = {str(actor.id): actor for actor in actors}
    attack_source_options_by_actor = {
        ActorId(actor.id): tuple(
            sorted(
                (
                    _attack_source_from_definition(
                        attack,
                        f"attack_{actor.id}:{attack.id}",
                        actors_by_id[actor.id],
                    )
                    for attack in actor.attacks
                ),
                key=lambda source: source.resource_pool_id is not None,
            )
        )
        for actor in definition.actors
    }
    attack_sources_by_actor = {actor_id: sources[0] for actor_id, sources in attack_source_options_by_actor.items() if sources}
    multiattack_sources_by_actor: dict[ActorId, tuple[AttackSource, ...]] = {}
    for actor in definition.actors:
        if not actor.multiattack:
            continue
        sources_by_id = {
            source.id: source
            for source in attack_source_options_by_actor[ActorId(actor.id)]
        }
        missing = tuple(source_id for source_id in actor.multiattack if source_id not in sources_by_id)
        if missing:
            raise ValueError(
                f"actor {actor.id}.multiattack references unknown attacks: {', '.join(missing)}."
            )
        multiattack_sources_by_actor[ActorId(actor.id)] = tuple(
            sources_by_id[source_id] for source_id in actor.multiattack
        )
    weapon_attack_sources: dict[str, list[AttackSource]] = {}
    for sources in attack_source_options_by_actor.values():
        for source in sources:
            if source.source_item_id is None:
                continue
            by_id = weapon_attack_sources.setdefault(source.source_item_id, [])
            if all(candidate.id != source.id for candidate in by_id):
                by_id.append(source)
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
            projectile_cover_bonus=entry.projectile_cover_bonus,
        )
        for entry in definition.environment
        if entry.interaction_label is not None or entry.projectile_cover_bonus > 0
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
        multiattack_sources_by_actor=multiattack_sources_by_actor,
        weapon_attack_sources_by_item_id={
            item_id: tuple(sources) for item_id, sources in weapon_attack_sources.items()
        },
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
        npc_transitions=definition.exploration_npc_transitions,
        observations=definition.exploration_observations,
        traps=definition.exploration_traps,
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
        crafting_policy=definition.crafting_policy,
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
    property_catalog = _load_item_property_catalog(scenario_path)
    crafting_policy = _load_crafting_policy(scenario_path, property_catalog)
    scene_mode = _enum_value(SceneMode, str(data.get("scene_mode", SceneMode.ENCOUNTER.value)), "scenario.scene_mode")
    return ScenarioDefinition(
        id=str(_required(data, "id", "scenario")),
        name=str(_required(data, "name", "scenario")),
        board_dimensions=BoardDimensions(cols=cols, rows=rows),
        scene_mode=scene_mode,
        actors=tuple(_parse_actor(actor_data, scenario_path, property_catalog) for actor_data in actors_data),
        environment=tuple(_parse_environment(entry) for entry in environment_data),
        player_start_zones=tuple(_parse_start_zone(zone, "scenario.player_start_zones") for zone in start_zones_data),
        objectives=tuple(_parse_objective(entry) for entry in objectives_data),
        exploration_zones=tuple(
            _parse_exploration_zone(entry, scenario_path, property_catalog)
            for entry in exploration_data.get("zones", [])
        ),
        exploration_points=tuple(_parse_exploration_point(entry) for entry in exploration_data.get("points", [])),
        exploration_challenges=tuple(_parse_exploration_challenge(entry) for entry in exploration_data.get("challenges", [])),
        exploration_resources=tuple(
            _parse_exploration_resource(entry, property_catalog)
            for entry in exploration_data.get("resources", [])
        ),
        exploration_initial_resources=tuple(str(item) for item in exploration_data.get("initial_resources", [])),
        exploration_encounter_triggers=tuple(_parse_exploration_encounter_trigger(entry) for entry in exploration_data.get("encounter_triggers", [])),
        exploration_npc_transitions=tuple(
            _parse_npc_scene_transition(entry)
            for entry in exploration_data.get("npc_transitions", [])
        ),
        exploration_observations=tuple(
            _parse_exploration_observation(entry)
            for entry in exploration_data.get("observations", [])
        ),
        exploration_traps=tuple(
            _parse_exploration_trap(entry)
            for entry in exploration_data.get("traps", [])
        ),
        party_start_zone_id=str(exploration_data["party_start_zone"]) if "party_start_zone" in exploration_data else None,
        llm_context=_parse_llm_context(data.get("llm_context", {}), "scenario.llm_context"),
        crafting_policy=crafting_policy,
    )


def _parse_actor(
    data: dict[str, Any],
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog,
) -> ScenarioActorDefinition:
    if not isinstance(data, dict):
        raise ValueError("scenario.actors entries must be objects.")
    source_ref = data.get("source_ref")
    merged: dict[str, Any] = {}
    if source_ref is not None:
        merged.update(_read_json(_content_ref_path(scenario_path, "monsters", str(source_ref))))
    merged.update(data)

    actor_id = str(_required(merged, "id", "actor"))
    feature_refs = merged.get("feature_refs", [])
    if not isinstance(feature_refs, list) or not all(
        isinstance(feature_ref, str) and feature_ref.strip()
        for feature_ref in feature_refs
    ):
        raise ValueError(f"actor {actor_id}.feature_refs must be a list of non-empty ids.")
    feature_definitions = tuple(
        _parse_feature_definition(
            _read_json(_content_ref_path(scenario_path, "features", feature_ref)),
            actor_id,
        )
        for feature_ref in feature_refs
    )
    if len({feature.definition.id for feature in feature_definitions}) != len(feature_definitions):
        raise ValueError(f"actor {actor_id}.feature_refs cannot contain duplicate features.")

    attacks_data = merged.get("attacks")
    if attacks_data is None:
        attacks_data = []
    if not isinstance(attacks_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.attacks must be a list.")
    attacks_data = list(attacks_data)
    healing_data = merged.get("healing_sources", [])
    if not isinstance(healing_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.healing_sources must be a list.")
    healing_data = list(healing_data)
    combat_actions_data = merged.get("combat_actions", [])
    if not isinstance(combat_actions_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.combat_actions must be a list.")
    combat_actions_data = list(combat_actions_data)
    item_refs = merged.get("item_refs", [])
    if not isinstance(item_refs, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.item_refs must be a list.")
    inventory_data = merged.get("inventory", [])
    if not isinstance(inventory_data, list):
        raise ValueError(f"actor {merged.get('id', '<unknown>')}.inventory must be a list.")
    inventory_items: list[InventoryItem] = []
    for item_ref in item_refs:
        item = _read_json(_content_ref_path(scenario_path, "items", str(item_ref)))
        inventory_item = _inventory_item_from_item_data(
            item,
            quantity=1,
            equipped=True,
            source_ref=str(item_ref),
            property_catalog=property_catalog,
        )
        inventory_items.append(inventory_item)
        attacks_data.extend(
            _attacks_with_item_source(
                item.get("attacks", []),
                inventory_item.id,
                proficiency_id=str(item.get("id", inventory_item.id)),
            )
        )
        healing_data.extend(item.get("healing_sources", []))
        combat_actions_data.extend(_combat_actions_with_item_source(item.get("combat_actions", []), str(item_ref)))
    for item_entry in inventory_data:
        item, inventory_item = _parse_inventory_entry(
            item_entry,
            scenario_path,
            actor_id=str(merged.get("id", "<unknown>")),
            property_catalog=property_catalog,
        )
        inventory_items.append(inventory_item)
        attacks_data.extend(
            _attacks_with_item_source(
                item.get("attacks", []),
                inventory_item.id,
                proficiency_id=str(item.get("id", inventory_item.id)),
            )
        )
        if inventory_item.equipped:
            healing_data.extend(item.get("healing_sources", []))
        combat_actions_data.extend(_combat_actions_with_item_source(item.get("combat_actions", []), inventory_item.id))

    attacks = tuple(_parse_attack(attack, actor_id) for attack in attacks_data) + tuple(
        attack
        for feature in feature_definitions
        for attack in feature.attacks
    )
    if not attacks:
        raise ValueError(f"actor {actor_id}.attacks must contain at least one attack.")
    healing_sources = tuple(_parse_healing_source(source, actor_id) for source in healing_data) + tuple(
        source
        for feature in feature_definitions
        for source in feature.healing_sources
    )
    combat_actions = tuple(_parse_combat_action(action, actor_id) for action in combat_actions_data) + tuple(
        action
        for feature in feature_definitions
        for action in feature.combat_actions
    )
    _validate_unique_ids(attacks, f"actor {actor_id}.attacks")
    _validate_unique_ids(healing_sources, f"actor {actor_id}.healing_sources")
    _validate_unique_ids(combat_actions, f"actor {actor_id}.combat_actions")
    spell_slots = _parse_spell_slots(merged.get("spell_slots", {}), actor_id)
    actor_kind = str(_required(merged, "kind", f"actor {actor_id}"))
    attacks_per_action = int(merged.get("attacks_per_action", 1))
    if attacks_per_action < 1:
        raise ValueError(f"actor {actor_id}.attacks_per_action must be at least 1.")
    multiattack_data = merged.get("multiattack", [])
    if not isinstance(multiattack_data, list) or not all(
        isinstance(source_id, str) and source_id for source_id in multiattack_data
    ):
        raise ValueError(f"actor {actor_id}.multiattack must be a list of attack ids.")
    multiattack = tuple(multiattack_data)
    known_attack_ids = {attack.id for attack in attacks}
    unknown_multiattack_ids = tuple(source_id for source_id in multiattack if source_id not in known_attack_ids)
    if unknown_multiattack_ids:
        raise ValueError(
            f"actor {actor_id}.multiattack references unknown attacks: "
            f"{', '.join(unknown_multiattack_ids)}."
        )
    if multiattack and actor_kind != "monster":
        raise ValueError(f"actor {actor_id}.multiattack is only supported for monsters.")
    proficiencies = _parse_proficiency_profile(merged, actor_id)
    damage_affinities = _parse_damage_affinities(merged, actor_id)
    condition_immunities_data = merged.get("condition_immunities", [])
    if not isinstance(condition_immunities_data, list | tuple):
        raise ValueError(f"actor {actor_id}.condition_immunities must be a list.")
    condition_immunities = tuple(
        _enum_value(
            CombatCondition,
            str(value),
            f"actor {actor_id}.condition_immunities",
        ).value
        for value in condition_immunities_data
    )
    if len(condition_immunities) != len(set(condition_immunities)):
        raise ValueError(f"actor {actor_id}.condition_immunities cannot contain duplicates.")
    auras = _parse_actor_auras(merged.get("auras", []), actor_id) + tuple(
        aura for feature in feature_definitions for aura in feature.auras
    )
    triggers = _parse_actor_triggers(merged.get("triggers", []), actor_id) + tuple(
        trigger for feature in feature_definitions for trigger in feature.triggers
    )
    resource_pools = _parse_actor_resources(merged.get("resource_pools", []), actor_id) + tuple(
        pool for feature in feature_definitions for pool in feature.resource_pools
    )
    _validate_unique_ids(auras, f"actor {actor_id}.auras")
    _validate_unique_ids(triggers, f"actor {actor_id}.triggers")
    _validate_unique_ids(resource_pools, f"actor {actor_id}.resource_pools")
    resource_ids = {pool.id for pool in resource_pools}
    for attack in attacks:
        if attack.resource_cost < 1:
            raise ValueError(f"attack {attack.id}.resource_cost must be positive.")
        if attack.resource_pool_id is not None and attack.resource_pool_id not in resource_ids:
            raise ValueError(
                f"attack {attack.id}.resource_pool_id references unknown actor resource: "
                f"{attack.resource_pool_id}."
            )
    return ScenarioActorDefinition(
        id=actor_id,
        name=str(_required(merged, "name", f"actor {actor_id}")),
        kind=actor_kind,
        faction=_enum_value(Faction, str(_required(merged, "faction", f"actor {actor_id}")), f"actor {actor_id}.faction"),
        size=_enum_value(
            CreatureSize,
            str(merged.get("size", CreatureSize.MEDIUM.value)),
            f"actor {actor_id}.size",
        ),
        ac=int(_required(merged, "ac", f"actor {actor_id}")),
        hp=int(_required(merged, "hp", f"actor {actor_id}")),
        temp_hp=int(merged.get("temp_hp", 0)),
        speed_feet=int(_required(merged, "speed_feet", f"actor {actor_id}")),
        position=_parse_coordinate(_required(merged, "position", f"actor {actor_id}"), f"actor {actor_id}.position"),
        ability_scores=_parse_ability_scores(_required_mapping(merged, "ability_scores", f"actor {actor_id}")),
        spell_slots=spell_slots,
        spell_save_dc=int(merged.get("spell_save_dc", 0)),
        inventory=normalize_hand_equipment(inventory_items),
        spell_ids=_spell_ids_for_actor(attacks, healing_sources, combat_actions),
        spell_preparation=_parse_spell_preparation(
            merged.get("spell_preparation"),
            actor_id=actor_id,
            attacks=attacks,
            healing_sources=healing_sources,
            combat_actions=combat_actions,
            spell_slots=spell_slots,
        ),
        hit_dice=_parse_hit_dice(merged.get("hit_dice", {}), actor_id),
        resource_pools=resource_pools,
        proficiency_bonus=int(merged.get("proficiency_bonus", 2)),
        proficiencies=proficiencies,
        uses_death_saves=bool(merged.get("uses_death_saves", actor_kind == "player_character")),
        damage_affinities=damage_affinities,
        attacks=attacks,
        attacks_per_action=attacks_per_action,
        multiattack=multiattack,
        condition_immunities=condition_immunities,
        auras=auras,
        triggers=triggers,
        features=tuple(feature.definition.grant() for feature in feature_definitions),
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


def _parse_proficiency_profile(data: dict[str, Any], actor_id: str) -> ProficiencyProfile:
    raw = data.get("proficiencies", {})
    if not isinstance(raw, dict):
        raise ValueError(f"actor {actor_id}.proficiencies must be an object.")

    def values(field: str, legacy_field: str | None = None) -> tuple[str, ...]:
        source = raw.get(field, data.get(legacy_field, ())) if legacy_field else raw.get(field, ())
        if not isinstance(source, list | tuple):
            raise ValueError(f"actor {actor_id}.proficiencies.{field} must be a list.")
        return tuple(str(value) for value in source)

    return ProficiencyProfile(
        saving_throws=values("saving_throws"),
        skills=values("skills", "skill_proficiencies"),
        expertise=values("expertise", "skill_expertise"),
        weapons=values("weapons"),
        armor=values("armor"),
        tools=values("tools"),
    )


def _parse_damage_affinities(data: dict[str, Any], actor_id: str) -> DamageAffinityProfile:
    def values(field: str) -> tuple[DamageType, ...]:
        raw = data.get(field, [])
        if not isinstance(raw, list | tuple):
            raise ValueError(f"actor {actor_id}.{field} must be a list.")
        return tuple(
            _enum_value(DamageType, str(value), f"actor {actor_id}.{field}")
            for value in raw
        )

    return DamageAffinityProfile(
        resistances=values("damage_resistances"),
        immunities=values("damage_immunities"),
        vulnerabilities=values("damage_vulnerabilities"),
    )


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


def _attacks_with_item_source(
    attacks: Any,
    item_id: str,
    *,
    proficiency_id: str | None = None,
) -> list[dict[str, Any]]:
    if attacks is None:
        return []
    if not isinstance(attacks, list):
        raise ValueError(f"item {item_id}.attacks must be a list.")
    result: list[dict[str, Any]] = []
    for attack in attacks:
        if not isinstance(attack, dict):
            raise ValueError(f"item {item_id}.attacks entries must be objects.")
        item_attack = dict(attack)
        item_attack.setdefault("source_item_id", item_id)
        item_attack.setdefault("proficiency_id", proficiency_id or item_id)
        result.append(item_attack)
    return result


def _parse_inventory_entry(
    item_entry: Any,
    scenario_path: Path,
    actor_id: str,
    property_catalog: ItemPropertyCatalog,
) -> tuple[dict[str, Any], InventoryItem]:
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
    base_properties = _parse_string_tuple(
        item_data.get("properties", []),
        f"actor {actor_id}.inventory {item_id}.properties",
    )
    added_properties = _parse_string_tuple(
        item_entry.get("added_properties", []),
        f"actor {actor_id}.inventory {item_id}.added_properties",
    )
    removed_properties = _parse_string_tuple(
        item_entry.get("removed_properties", []),
        f"actor {actor_id}.inventory {item_id}.removed_properties",
    )
    property_catalog.validate(base_properties, f"actor {actor_id}.inventory {item_id}.properties")
    property_catalog.validate(added_properties, f"actor {actor_id}.inventory {item_id}.added_properties")
    property_catalog.validate(removed_properties, f"actor {actor_id}.inventory {item_id}.removed_properties")
    properties = tuple(sorted((set(base_properties) | set(added_properties)) - set(removed_properties)))
    inventory_item = InventoryItem(
        id=item_id,
        name=str(item_entry.get("name", name)),
        kind=str(item_entry.get("kind", kind)),
        quantity=quantity,
        equipped=bool(item_entry.get("equipped", True)),
        source_ref=source_ref,
        broken=bool(item_entry.get("broken", False)),
        description=str(item_entry.get("description", item_data.get("description", ""))),
        properties=properties,
        portable=bool(item_entry.get("portable", item_data.get("portable", True))),
        hands_required=int(item_entry.get("hands_required", item_data.get("hands_required", 0))),
        held_in=tuple(
            _enum_value(
                HandSlot,
                value,
                f"actor {actor_id}.inventory {item_id}.held_in",
            )
            for value in item_entry.get("held_in", [])
        ),
        light_weapon=bool(item_entry.get("light_weapon", item_data.get("light_weapon", False))),
        versatile_damage_dice=(
            str(item_entry.get("versatile_damage_dice", item_data.get("versatile_damage_dice")))
            if item_entry.get("versatile_damage_dice", item_data.get("versatile_damage_dice")) is not None
            else None
        ),
        armor_class_bonus=int(
            item_entry.get("armor_class_bonus", item_data.get("armor_class_bonus", 0))
        ),
        armor_proficiency=(
            str(item_entry.get("armor_proficiency", item_data.get("armor_proficiency")))
            if item_entry.get("armor_proficiency", item_data.get("armor_proficiency")) is not None
            else None
        ),
    )
    return item_data, inventory_item


def _inventory_item_from_item_data(
    item: dict[str, Any],
    *,
    quantity: int,
    equipped: bool,
    source_ref: str | None,
    property_catalog: ItemPropertyCatalog,
) -> InventoryItem:
    item_id = str(_required(item, "id", f"item {source_ref or '<inline>'}"))
    properties = _parse_string_tuple(item.get("properties", []), f"item {item_id}.properties")
    property_catalog.validate(properties, f"item {item_id}.properties")
    return InventoryItem(
        id=item_id,
        name=str(item.get("name", item_id)),
        kind=str(item.get("kind", "item")),
        quantity=quantity,
        equipped=equipped,
        source_ref=source_ref,
        broken=bool(item.get("broken", False)),
        description=str(item.get("description", "")),
        properties=properties,
        portable=bool(item.get("portable", True)),
        hands_required=int(item.get("hands_required", 0)),
        light_weapon=bool(item.get("light_weapon", False)),
        versatile_damage_dice=(
            str(item["versatile_damage_dice"])
            if item.get("versatile_damage_dice") is not None
            else None
        ),
        armor_class_bonus=int(item.get("armor_class_bonus", 0)),
        armor_proficiency=(
            str(item["armor_proficiency"])
            if item.get("armor_proficiency") is not None
            else None
        ),
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
    save_ability = str(data["save_ability"]) if "save_ability" in data else None
    if save_ability is not None and save_ability not in ABILITY_NAMES:
        raise ValueError(
            f"attack {attack_id}.save_ability must be a D&D ability, got {save_ability!r}."
        )
    try:
        save_damage_on_success = SaveDamageOnSuccess(
            str(data.get("save_damage_on_success", "none"))
        ).value
    except ValueError as exc:
        raise ValueError(
            f"attack {attack_id}.save_damage_on_success must be none or half."
        ) from exc
    range_feet = int(_required(data, "range_feet", f"attack {attack_id}"))
    if range_feet <= 0:
        raise ValueError(f"attack {attack_id}.range_feet must be positive.")
    attack_kind = _enum_value(
        AttackKind,
        str(data.get("attack_kind", "ranged" if range_feet > 10 else "melee")),
        f"attack {attack_id}.attack_kind",
    )
    reach_feet = int(data.get("reach_feet", range_feet)) if attack_kind == AttackKind.MELEE else None
    if attack_kind == AttackKind.RANGED and "reach_feet" in data:
        raise ValueError(f"attack {attack_id}.reach_feet is only valid for melee attacks.")
    if reach_feet is not None and (reach_feet <= 0 or reach_feet % 5 != 0):
        raise ValueError(f"attack {attack_id}.reach_feet must be a positive multiple of 5.")
    return ScenarioAttackDefinition(
        id=attack_id,
        name=str(_required(data, "name", f"attack {attack_id}")),
        source_type=source_type,
        range_feet=range_feet,
        reach_feet=reach_feet,
        attack_modifier=(int(data["attack_modifier"]) if "attack_modifier" in data else None),
        damage_fixed=_parse_damage_fixed(damage),
        damage_die_sides=_parse_damage_die(damage),
        damage_modifier=int(damage.get("modifier", 0)),
        damage_type=str(_required(damage, "damage_type", f"attack {attack_id}.damage")),
        ability=str(data["ability"]) if "ability" in data else None,
        spell_level=spell_level,
        area=_parse_spell_area(data.get("area"), f"attack {attack_id}.area"),
        save_ability=save_ability,
        save_dc=int(data.get("save_dc", 0)),
        save_damage_on_success=save_damage_on_success,
        casting_kind=_parse_spell_casting_kind(data.get("casting_kind"), source_type, spell_level, f"attack {attack_id}.casting_kind"),
        prepared=bool(data.get("prepared", True)),
        source_item_id=str(data["source_item_id"]) if "source_item_id" in data else None,
        attack_kind=attack_kind,
        proficiency_id=str(data["proficiency_id"]) if "proficiency_id" in data else None,
        resource_pool_id=str(data["resource_pool_id"]) if "resource_pool_id" in data else None,
        resource_cost=int(data.get("resource_cost", 1)),
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
    range_feet = int(data.get("range_feet", 0))
    if range_feet < 0:
        raise ValueError(f"combat action {action_id}.range_feet must be non-negative.")
    effect_kind = str(data["effect_kind"]) if "effect_kind" in data else None
    duration = str(data.get("duration", "next_turn_start"))
    if action_type == "targeted_item_effect":
        if not data.get("source_item_id"):
            raise ValueError(f"combat action {action_id} requires source_item_id.")
        if effect_kind not in {"grant_next_attack_penalty", "apply_condition"}:
            raise ValueError(f"combat action {action_id} has unsupported effect_kind.")
        EffectDuration(duration)
    condition = (
        _enum_value(CombatCondition, str(data["condition"]), f"combat action {action_id}.condition")
        if "condition" in data
        else None
    )
    save_ability = str(data["save_ability"]) if "save_ability" in data else None
    save_dc = int(data["save_dc"]) if "save_dc" in data else None
    save_timing = str(data["save_timing"]) if "save_timing" in data else None
    if effect_kind == "apply_condition":
        if condition is None:
            raise ValueError(f"combat action {action_id} requires condition.")
        save_fields = (save_ability, save_dc, save_timing)
        if any(value is not None for value in save_fields) and not all(
            value is not None for value in save_fields
        ):
            raise ValueError(
                f"combat action {action_id} condition requires all save fields or none."
            )
        if save_timing is not None:
            ConditionSaveTiming(save_timing)
    source_type = AttackSourceType.SPELL if action_type.startswith("concentration_") else AttackSourceType.CUSTOM
    return ScenarioCombatActionDefinition(
        id=action_id,
        name=str(_required(data, "name", f"combat action {action_id}")),
        action_type=action_type,
        label=str(data.get("label", data.get("name", action_id))),
        value=int(data.get("value", 0)),
        ability=str(data["ability"]) if "ability" in data else None,
        duration=duration,
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
        range_feet=range_feet,
        effect_kind=effect_kind,
        action_cost=ActionEconomyCost(str(data.get("action_cost", "action"))),
        condition=condition,
        save_ability=save_ability,
        save_dc=save_dc,
        save_timing=save_timing,
    )


def _parse_environment(data: dict[str, Any]) -> ScenarioEnvironmentDefinition:
    if not isinstance(data, dict):
        raise ValueError("scenario.environment entries must be objects.")
    entry_id = str(_required(data, "id", "environment"))
    positions_data = _required_list(data, "positions", f"environment {entry_id}")
    projectile_cover_bonus = int(data.get("projectile_cover_bonus", 0))
    if projectile_cover_bonus not in {0, 2, 5}:
        raise ValueError(
            f"environment {entry_id}.projectile_cover_bonus must be 0, 2, or 5."
        )
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
        projectile_cover_bonus=projectile_cover_bonus,
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


def _parse_exploration_zone(
    data: Any,
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog | None,
) -> ExplorationZone:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.zones entries must be objects.")
    zone_id = str(_required(data, "id", "exploration zone"))
    positions_data = _required_list(data, "positions", f"exploration zone {zone_id}")
    search_data = data.get("search", {})
    if search_data is None:
        search_data = {}
    if not isinstance(search_data, dict):
        raise ValueError(f"exploration zone {zone_id}.search must be an object.")
    item_instances = _parse_scene_item_instances(
        data.get("available_items", []),
        scenario_path,
        property_catalog,
        f"exploration zone {zone_id}.available_items",
    )
    fixtures = _parse_scene_fixtures(
        data.get("fixtures", []),
        scenario_path,
        property_catalog,
        f"exploration zone {zone_id}.fixtures",
    )
    source_ids = tuple(item.id for item in item_instances) + tuple(fixture.id for fixture in fixtures)
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f"exploration zone {zone_id} contains duplicate item or fixture ids.")
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
        short_rest_policy=_parse_short_rest_policy(data.get("short_rest"), zone_id),
        item_instances=item_instances,
        fixtures=fixtures,
    )


def _load_item_property_catalog(scenario_path: Path) -> ItemPropertyCatalog:
    path = _content_ref_path(scenario_path, "items", "properties")
    data = _read_json(path)
    schema_version = int(data.get("schema_version", 0))
    if schema_version != 1:
        raise ValueError(f"{path}.schema_version must be 1.")
    raw_properties = data.get("properties")
    if not isinstance(raw_properties, list):
        raise ValueError(f"{path}.properties must be a list.")
    properties: list[ItemPropertyDefinition] = []
    for index, raw_property in enumerate(raw_properties):
        field = f"{path}.properties[{index}]"
        if not isinstance(raw_property, dict):
            raise ValueError(f"{field} must be an object.")
        properties.append(
            ItemPropertyDefinition(
                id=str(_required(raw_property, "id", field)),
                label=str(_required(raw_property, "label", field)),
                description=str(raw_property.get("description", "")),
            )
        )
    return ItemPropertyCatalog(schema_version=schema_version, properties=tuple(properties))


def _load_crafting_policy(
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog,
) -> CraftingPolicy:
    path = _content_ref_path(scenario_path, "items", "crafting_purposes")
    data = _read_json(path)
    schema_version = int(data.get("schema_version", 0))
    raw_purposes = data.get("purposes")
    if not isinstance(raw_purposes, list):
        raise ValueError(f"{path}.purposes must be a list.")
    purposes: list[CraftingPurpose] = []
    for purpose_index, raw_purpose in enumerate(raw_purposes):
        purpose_field = f"{path}.purposes[{purpose_index}]"
        if not isinstance(raw_purpose, dict):
            raise ValueError(f"{purpose_field} must be an object.")
        raw_requirements = raw_purpose.get("requirements")
        if not isinstance(raw_requirements, list):
            raise ValueError(f"{purpose_field}.requirements must be a list.")
        requirements: list[CraftingPropertyRequirement] = []
        for requirement_index, raw_requirement in enumerate(raw_requirements):
            requirement_field = f"{purpose_field}.requirements[{requirement_index}]"
            if not isinstance(raw_requirement, dict):
                raise ValueError(f"{requirement_field} must be an object.")
            properties = _parse_string_tuple(
                raw_requirement.get("properties", []),
                f"{requirement_field}.properties",
            )
            property_catalog.validate(properties, f"{requirement_field}.properties")
            requirements.append(
                CraftingPropertyRequirement(
                    properties=properties,
                    minimum_quantity=int(raw_requirement.get("minimum_quantity", 1)),
                )
            )
        purposes.append(
            CraftingPurpose(
                id=str(_required(raw_purpose, "id", purpose_field)),
                label=str(_required(raw_purpose, "label", purpose_field)),
                requirements=tuple(requirements),
                bonus_tags=_parse_string_tuple(raw_purpose.get("bonus_tags", []), f"{purpose_field}.bonus_tags"),
                modifier=int(raw_purpose.get("modifier", 0)),
                uses=int(raw_purpose.get("uses", 1)),
                time_cost_minutes=int(raw_purpose.get("time_cost_minutes", 0)),
                risk=str(raw_purpose.get("risk", "")),
            )
        )
    return CraftingPolicy(
        schema_version=schema_version,
        purposes=tuple(purposes),
        max_active_items=int(data.get("max_active_items", 3)),
        property_ids=tuple(sorted(property_catalog.known_ids)),
        property_labels=tuple(sorted((item.id, item.label) for item in property_catalog.properties)),
    )


def _parse_scene_item_instances(
    data: Any,
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog | None,
    field: str,
) -> tuple[ItemInstance, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{field} must be a list.")
    if data and property_catalog is None:
        raise ValueError(f"{field} requires the item property catalog.")
    instances = tuple(
        _parse_scene_item_instance(entry, scenario_path, property_catalog, f"{field}[{index}]")
        for index, entry in enumerate(data)
    )
    ids = tuple(item.id for item in instances)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{field} contains duplicate ids.")
    return instances


def _parse_scene_item_instance(
    data: Any,
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog | None,
    field: str,
) -> ItemInstance:
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    if property_catalog is None:
        raise ValueError(f"{field} requires the item property catalog.")
    definition_ref = data.get("definition_id", data.get("item_ref"))
    if definition_ref is None:
        raise ValueError(f"{field}.definition_id is required.")
    definition_data = _read_json(_content_ref_path(scenario_path, "items", str(definition_ref)))
    definition = _parse_item_definition(definition_data, property_catalog, f"item definition {definition_ref}")
    added_properties = _parse_string_tuple(data.get("added_properties", []), f"{field}.added_properties")
    removed_properties = _parse_string_tuple(data.get("removed_properties", []), f"{field}.removed_properties")
    property_catalog.validate(added_properties, f"{field}.added_properties")
    property_catalog.validate(removed_properties, f"{field}.removed_properties")
    return ItemInstance(
        id=str(_required(data, "id", field)),
        definition=definition,
        quantity=int(data.get("quantity", 1)),
        condition=str(data.get("condition", "normal")),
        added_properties=added_properties,
        removed_properties=removed_properties,
        owner_id=str(data["owner_id"]) if "owner_id" in data else None,
        visible=bool(data.get("visible", True)),
        available=bool(data.get("available", True)),
    )


def _parse_item_definition(
    data: dict[str, Any],
    property_catalog: ItemPropertyCatalog,
    field: str,
) -> ItemDefinition:
    properties = _parse_string_tuple(data.get("properties", []), f"{field}.properties")
    property_catalog.validate(properties, f"{field}.properties")
    weight = data.get("default_weight_lb")
    return ItemDefinition(
        id=str(_required(data, "id", field)),
        name=str(_required(data, "name", field)),
        kind=str(data.get("kind", "item")),
        description=str(data.get("description", "")),
        properties=properties,
        portable=bool(data.get("portable", True)),
        default_weight_lb=float(weight) if weight is not None else None,
        collection_destination=_enum_value(
            ItemCollectionDestination,
            data.get("collection_destination", ItemCollectionDestination.ACTOR_INVENTORY.value),
            f"{field}.collection_destination",
        ),
        hands_required=int(data.get("hands_required", 0)),
        light_weapon=bool(data.get("light_weapon", False)),
        versatile_damage_dice=(
            str(data["versatile_damage_dice"])
            if data.get("versatile_damage_dice") is not None
            else None
        ),
        armor_class_bonus=int(data.get("armor_class_bonus", 0)),
        armor_proficiency=(
            str(data["armor_proficiency"])
            if data.get("armor_proficiency") is not None
            else None
        ),
    )


def _parse_scene_fixtures(
    data: Any,
    scenario_path: Path,
    property_catalog: ItemPropertyCatalog | None,
    field: str,
) -> tuple[SceneFixture, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{field} must be a list.")
    if data and property_catalog is None:
        raise ValueError(f"{field} requires the item property catalog.")
    fixtures: list[SceneFixture] = []
    for index, raw_fixture in enumerate(data):
        fixture_field = f"{field}[{index}]"
        if not isinstance(raw_fixture, dict):
            raise ValueError(f"{fixture_field} must be an object.")
        if property_catalog is None:
            raise ValueError(f"{fixture_field} requires the item property catalog.")
        properties = _parse_string_tuple(raw_fixture.get("properties", []), f"{fixture_field}.properties")
        property_catalog.validate(properties, f"{fixture_field}.properties")
        fixtures.append(
            SceneFixture(
                id=str(_required(raw_fixture, "id", fixture_field)),
                name=str(_required(raw_fixture, "name", fixture_field)),
                description=str(raw_fixture.get("description", "")),
                properties=properties,
                condition=str(raw_fixture.get("condition", "normal")),
                visible=bool(raw_fixture.get("visible", True)),
                portable=bool(raw_fixture.get("portable", False)),
                detachable=bool(raw_fixture.get("detachable", False)),
                destructible=bool(raw_fixture.get("destructible", False)),
                yield_items=_parse_scene_item_instances(
                    raw_fixture.get("yield_items", []),
                    scenario_path,
                    property_catalog,
                    f"{fixture_field}.yield_items",
                ),
                action_policies=_parse_fixture_action_policies(
                    raw_fixture.get("action_policies", []),
                    fixture_field,
                ),
            )
        )
    ids = tuple(fixture.id for fixture in fixtures)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{field} contains duplicate ids.")
    return tuple(fixtures)


def _parse_fixture_action_policies(data: Any, fixture_field: str) -> tuple[FixtureActionPolicy, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{fixture_field}.action_policies must be a list.")
    policies: list[FixtureActionPolicy] = []
    for index, raw_policy in enumerate(data):
        field = f"{fixture_field}.action_policies[{index}]"
        if not isinstance(raw_policy, dict):
            raise ValueError(f"{field} must be an object.")
        policies.append(
            FixtureActionPolicy(
                operation=_enum_value(FixtureOperation, _required(raw_policy, "operation", field), f"{field}.operation"),
                result_condition=str(_required(raw_policy, "result_condition", field)),
                ability=str(_required(raw_policy, "ability", field)).strip().lower(),
                skill=(
                    str(raw_policy["skill"]).strip().lower()
                    if raw_policy.get("skill") is not None
                    else None
                ),
                difficulty_tier=str(_required(raw_policy, "difficulty_tier", field)).strip().lower(),
                allowed_conditions=_parse_string_tuple(
                    raw_policy.get("allowed_conditions", []),
                    f"{field}.allowed_conditions",
                ),
                progress_on_success=int(raw_policy.get("progress_on_success", 1)),
                progress_on_failure=int(raw_policy.get("progress_on_failure", 0)),
                success_noise=int(raw_policy.get("success_noise", 0)),
                failure_noise=int(raw_policy.get("failure_noise", 0)),
                failure_complication=(
                    str(raw_policy["failure_complication"])
                    if raw_policy.get("failure_complication") is not None
                    else None
                ),
                makes_fixture_unavailable=bool(raw_policy.get("makes_fixture_unavailable", False)),
                release_yield_items=bool(raw_policy.get("release_yield_items", False)),
            )
        )
    return tuple(policies)


def _parse_short_rest_policy(data: Any, zone_id: str) -> ShortRestPolicy | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"exploration zone {zone_id}.short_rest must be an object.")
    effects = data.get("completion_effects", [])
    if not isinstance(effects, list) or any(not isinstance(effect, dict) for effect in effects):
        raise ValueError(
            f"exploration zone {zone_id}.short_rest.completion_effects must be a list of objects."
        )
    return ShortRestPolicy(
        id=str(data.get("id") or f"short_rest:{zone_id}"),
        safety=_enum_value(
            RestSafety,
            str(data.get("safety", RestSafety.SAFE.value)),
            f"exploration zone {zone_id}.short_rest.safety",
        ),
        risk_summary=str(data.get("risk_summary", "")),
        duration_minutes=int(data.get("duration_minutes", 60)),
        max_completions=int(data.get("max_completions", 0)),
        completion_effects=tuple(effects),
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
        id=str(data.get("id", point_id)),
        name=str(data.get("name", data.get("public_name", point_id))),
        public_description=str(_required(data, "public_description", f"npc interaction {point_id}")),
        gm_context=str(data.get("gm_context", "")),
        personality=str(data.get("personality", "")),
        current_state=str(data.get("current_state", "")),
        initial_attitude=_enum_value(
            NpcAttitude,
            str(data.get("initial_attitude", NpcAttitude.INDIFFERENT.value)),
            f"npc interaction {point_id}.initial_attitude",
        ),
        initial_physical_state=str(data.get("initial_physical_state", "")),
        initial_emotional_state=str(data.get("initial_emotional_state", "")),
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
            allowed_effect_types=tuple(
                str(item).strip().lower()
                for item in policy_data.get("allowed_effect_types", ["set_flag"])
                if str(item).strip()
            ),
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
                state_on_success=_parse_npc_state_update(
                    permission_data.get("state_on_success"),
                    f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.state_on_success",
                ),
                state_on_failure=_parse_npc_state_update(
                    permission_data.get("state_on_failure"),
                    f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.state_on_failure",
                ),
                uses_social_reaction=bool(permission_data.get("uses_social_reaction", False)),
                attempt_policy=_parse_npc_attempt_policy(
                    permission_data.get("attempt_policy"),
                    f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.attempt_policy",
                ),
                targets=_parse_npc_intent_targets(
                    permission_data.get("targets"),
                    f"exploration point {point_id}.npc_interaction.policy.intent_permissions.{intent}.targets",
                ),
            )
        )
    return tuple(permissions)


def _parse_npc_attempt_policy(data: Any, field: str) -> NpcAttemptPolicy | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    attempt_id = str(data.get("attempt_id", "")).strip().lower()
    if not attempt_id:
        raise ValueError(f"{field}.attempt_id is required.")
    raw_max_attempts = data.get("max_attempts", 1)
    if not isinstance(raw_max_attempts, int) or isinstance(raw_max_attempts, bool):
        raise ValueError(f"{field}.max_attempts must be an integer.")
    retry_flags = data.get("retry_requires_any_flags", [])
    if not isinstance(retry_flags, list):
        raise ValueError(f"{field}.retry_requires_any_flags must be an array.")
    return NpcAttemptPolicy(
        attempt_id=attempt_id,
        max_attempts=raw_max_attempts,
        retry_requires_any_flags=tuple(
            str(item).strip()
            for item in retry_flags
        ),
        retry_locked_message=str(
            data.get(
                "retry_locked_message",
                "NPC nie zgadza się ponownie rozmawiać o tym bez zmiany sytuacji.",
            )
        ),
        exhausted_message=str(
            data.get("exhausted_message", "To podejście zostało wyczerpane.")
        ),
    )


def _parse_npc_intent_targets(data: Any, field: str) -> tuple[NpcIntentTarget, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"{field} must be an array.")
    targets: list[NpcIntentTarget] = []
    for index, raw_target in enumerate(data):
        target_field = f"{field}[{index}]"
        if not isinstance(raw_target, dict):
            raise ValueError(f"{target_field} must be an object.")
        outcomes = raw_target.get("outcomes")
        if not isinstance(outcomes, dict):
            raise ValueError(f"{target_field}.outcomes must be an object.")
        branches: list[NpcOutcomeBranch] = []
        for outcome in NpcOutcomeTier:
            raw_branch = outcomes.get(outcome.value)
            if not isinstance(raw_branch, dict):
                raise ValueError(f"{target_field}.outcomes.{outcome.value} must be an object.")
            raw_effects = raw_branch.get("effects", [])
            if not isinstance(raw_effects, list) or any(not isinstance(item, dict) for item in raw_effects):
                raise ValueError(f"{target_field}.outcomes.{outcome.value}.effects must be an array of objects.")
            raw_revealed = raw_branch.get("revealed_information_ids", [])
            if not isinstance(raw_revealed, list):
                raise ValueError(
                    f"{target_field}.outcomes.{outcome.value}.revealed_information_ids must be an array."
                )
            branches.append(
                NpcOutcomeBranch(
                    outcome=outcome,
                    message=str(raw_branch.get("message", "")),
                    preview=str(raw_branch.get("preview", "")),
                    effects=tuple(dict(item) for item in raw_effects),
                    state_update=_parse_npc_state_update(
                        raw_branch.get("state_update"),
                        f"{target_field}.outcomes.{outcome.value}.state_update",
                    ),
                    revealed_information_ids=tuple(
                        str(item).strip()
                        for item in raw_revealed
                    ),
                    transition_id=(
                        str(raw_branch["transition_id"]).strip().lower()
                        if raw_branch.get("transition_id")
                        else None
                    ),
                )
            )
        raw_max_quantity = raw_target.get("max_quantity", 1)
        if not isinstance(raw_max_quantity, int) or isinstance(raw_max_quantity, bool):
            raise ValueError(f"{target_field}.max_quantity must be an integer.")
        raw_dc = raw_target.get("dc")
        if raw_dc is not None and (not isinstance(raw_dc, int) or isinstance(raw_dc, bool)):
            raise ValueError(f"{target_field}.dc must be an integer.")
        raw_requires_flags = raw_target.get("requires_flags", [])
        if not isinstance(raw_requires_flags, list):
            raise ValueError(f"{target_field}.requires_flags must be an array.")
        targets.append(
            NpcIntentTarget(
                id=str(raw_target.get("id", "")).strip().lower(),
                label=str(raw_target.get("label", "")),
                description=str(raw_target.get("description", "")),
                reward_label=str(raw_target.get("reward_label", "")),
                risk_summary=str(raw_target.get("risk_summary", "")),
                max_quantity=raw_max_quantity,
                requires_flags=tuple(str(item).strip() for item in raw_requires_flags),
                ability=(str(raw_target["ability"]).strip().lower() if raw_target.get("ability") else None),
                skill=(str(raw_target["skill"]).strip().lower() if raw_target.get("skill") else None),
                dc=raw_dc,
                outcome_branches=tuple(branches),
            )
        )
    return tuple(targets)


def _parse_npc_scene_transition(data: Any) -> NpcSceneTransition:
    if not isinstance(data, dict):
        raise ValueError("exploration.npc_transitions entries must be objects.")
    transition_id = str(_required(data, "id", "NPC scene transition")).strip().lower()
    raw_variants = data.get("variants")
    if not isinstance(raw_variants, list):
        raise ValueError(f"NPC scene transition {transition_id}.variants must be an array.")
    variants: list[NpcTransitionVariant] = []
    for variant_index, raw_variant in enumerate(raw_variants):
        field = f"NPC scene transition {transition_id}.variants[{variant_index}]"
        if not isinstance(raw_variant, dict):
            raise ValueError(f"{field} must be an object.")
        raw_reactions = raw_variant.get("reactions")
        if not isinstance(raw_reactions, list):
            raise ValueError(f"{field}.reactions must be an array.")
        reactions: list[NpcTransitionReaction] = []
        for reaction_index, raw_reaction in enumerate(raw_reactions):
            reaction_field = f"{field}.reactions[{reaction_index}]"
            if not isinstance(raw_reaction, dict):
                raise ValueError(f"{reaction_field} must be an object.")
            raw_effects = raw_reaction.get("effects", [])
            if not isinstance(raw_effects, list) or any(not isinstance(item, dict) for item in raw_effects):
                raise ValueError(f"{reaction_field}.effects must be an array of objects.")
            for array_field in ("suppress_encounter_trigger_ids",):
                if not isinstance(raw_reaction.get(array_field, []), list):
                    raise ValueError(f"{reaction_field}.{array_field} must be an array.")
            reactions.append(
                NpcTransitionReaction(
                    id=str(_required(raw_reaction, "id", reaction_field)).strip().lower(),
                    label=str(_required(raw_reaction, "label", reaction_field)),
                    description=str(_required(raw_reaction, "description", reaction_field)),
                    result_type=NpcTransitionResultType(
                        str(_required(raw_reaction, "result_type", reaction_field))
                    ),
                    narration=str(_required(raw_reaction, "narration", reaction_field)),
                    effects=tuple(dict(item) for item in raw_effects),
                    suppress_encounter_trigger_ids=tuple(
                        str(item).strip()
                        for item in raw_reaction.get("suppress_encounter_trigger_ids", [])
                    ),
                    encounter_trigger_id=(
                        str(raw_reaction["encounter_trigger_id"]).strip()
                        if raw_reaction.get("encounter_trigger_id")
                        else None
                    ),
                    npc_status=(
                        NpcInteractionStatus(str(raw_reaction["npc_status"]))
                        if raw_reaction.get("npc_status")
                        else None
                    ),
                )
            )
        for array_field in (
            "required_flags",
            "forbidden_flags",
            "required_resolved_encounter_trigger_ids",
            "forbidden_resolved_encounter_trigger_ids",
        ):
            if not isinstance(raw_variant.get(array_field, []), list):
                raise ValueError(f"{field}.{array_field} must be an array.")
        variants.append(
            NpcTransitionVariant(
                id=str(_required(raw_variant, "id", field)).strip().lower(),
                title=str(_required(raw_variant, "title", field)),
                narration=str(_required(raw_variant, "narration", field)),
                reactions=tuple(reactions),
                required_flags=tuple(str(item).strip() for item in raw_variant.get("required_flags", [])),
                forbidden_flags=tuple(str(item).strip() for item in raw_variant.get("forbidden_flags", [])),
                required_resolved_encounter_trigger_ids=tuple(
                    str(item).strip()
                    for item in raw_variant.get("required_resolved_encounter_trigger_ids", [])
                ),
                forbidden_resolved_encounter_trigger_ids=tuple(
                    str(item).strip()
                    for item in raw_variant.get("forbidden_resolved_encounter_trigger_ids", [])
                ),
            )
        )
    return NpcSceneTransition(
        transition_id,
        str(_required(data, "npc_id", f"NPC scene transition {transition_id}")),
        tuple(variants),
    )


def _parse_npc_state_update(data: Any, field: str) -> NpcStateUpdate | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    attitude = data.get("attitude")
    return NpcStateUpdate(
        attitude=(
            _enum_value(NpcAttitude, str(attitude), f"{field}.attitude")
            if attitude is not None
            else None
        ),
        physical_state=(
            str(data["physical_state"])
            if data.get("physical_state") is not None
            else None
        ),
        emotional_state=(
            str(data["emotional_state"])
            if data.get("emotional_state") is not None
            else None
        ),
    )


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
        hazards=_parse_exploration_hazards(data.get("hazards", []), option_id),
    )


def _parse_exploration_hazards(data: Any, option_id: str) -> tuple[ExplorationHazard, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"exploration challenge option {option_id}.hazards must be a list.")
    hazards: list[ExplorationHazard] = []
    triggers: set[ExplorationHazardTrigger] = set()
    for index, entry in enumerate(data):
        context = f"exploration challenge option {option_id}.hazards[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{context} must be an object.")
        hazard_id = str(_required(entry, "id", context))
        trigger = _enum_value(
            ExplorationHazardTrigger,
            str(entry.get("trigger", "critical_failure")),
            f"{context}.trigger",
        )
        if trigger in triggers:
            raise ValueError(f"{context}.trigger duplicates {trigger.value!r} for one option.")
        triggers.add(trigger)
        save = _required_mapping(entry, "saving_throw", context)
        ability = str(_required(save, "ability", f"{context}.saving_throw"))
        if ability not in ABILITY_NAMES:
            raise ValueError(f"{context}.saving_throw.ability must be a D&D ability.")
        damage_on_success = _enum_value(
            SaveDamageOnSuccess,
            str(save.get("damage_on_success", "none")),
            f"{context}.saving_throw.damage_on_success",
        )
        damage = _required_mapping(entry, "damage", context)
        damage_type = _enum_value(
            DamageType,
            str(_required(damage, "damage_type", f"{context}.damage")),
            f"{context}.damage.damage_type",
        )
        label = str(_required(entry, "label", context))
        save_dc = int(_required(save, "dc", f"{context}.saving_throw"))
        if save_dc <= 0:
            raise ValueError(f"{context}.saving_throw.dc must be positive.")
        hazards.append(
            ExplorationHazard(
                id=hazard_id,
                label=label,
                trigger=trigger,
                saving_throw=SavingThrowRequest(
                    ability=ability,
                    dc=save_dc,
                    source_label=label,
                    dc_source_label=str(save.get("dc_source_label", f"ST zagrożenia: {label}")),
                    damage_on_success=damage_on_success,
                    success_effect_label=str(save.get("success_effect_label", "")),
                    failure_effect_label=str(save.get("failure_effect_label", "pełny efekt")),
                ),
                damage=ExplorationHazardDamage(
                    damage_type=damage_type.value,
                    fixed=_parse_damage_fixed(damage),
                    die_sides=_parse_damage_die(damage),
                    modifier=int(damage.get("modifier", 0)),
                ),
                narration=str(entry.get("narration", "")),
                success_message=str(entry.get("success_message", "")),
                failure_message=str(entry.get("failure_message", "")),
                success_effects=_parse_exploration_hazard_effects(
                    entry.get("success_effects", []),
                    f"{context}.success_effects",
                ),
                failure_effects=_parse_exploration_hazard_effects(
                    entry.get("failure_effects", []),
                    f"{context}.failure_effects",
                ),
            )
        )
    return tuple(hazards)


def _parse_exploration_trap(data: Any) -> ExplorationTrap:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.traps entries must be objects.")
    trap_id = str(_required(data, "id", "exploration trap"))
    field = f"exploration trap {trap_id}"
    hazard_data = _required_mapping(data, "hazard", field)
    hazards = _parse_exploration_hazards([hazard_data], f"trap:{trap_id}")
    disarm_data = data.get("disarm_check")
    bypass_data = data.get("bypass_check")
    return ExplorationTrap(
        id=trap_id,
        zone_id=str(_required(data, "zone_id", field)),
        name=str(_required(data, "name", field)),
        revealed_description=str(_required(data, "revealed_description", field)),
        detection_observation_id=str(_required(data, "detection_observation_id", field)),
        hazard=hazards[0],
        activation_challenge_id=(
            str(data["activation_challenge_id"])
            if data.get("activation_challenge_id")
            else None
        ),
        disarm_check=(
            _parse_scene_ability_check(disarm_data, f"trap:{trap_id}:disarm")
            if disarm_data is not None
            else None
        ),
        bypass_check=(
            _parse_scene_ability_check(bypass_data, f"trap:{trap_id}:bypass")
            if bypass_data is not None
            else None
        ),
        required_item_id=str(data["required_item_id"]) if data.get("required_item_id") else None,
        disarm_intent_examples=_parse_string_tuple(
            data.get("disarm_intent_examples", []),
            f"{field}.disarm_intent_examples",
        ),
        bypass_intent_examples=_parse_string_tuple(
            data.get("bypass_intent_examples", []),
            f"{field}.bypass_intent_examples",
        ),
        trigger_intent_examples=_parse_string_tuple(
            data.get("trigger_intent_examples", []),
            f"{field}.trigger_intent_examples",
        ),
        disarm_success_message=str(data.get("disarm_success_message", "Pułapka została rozbrojona.")),
        bypass_success_message=str(data.get("bypass_success_message", "Drużyna bezpiecznie omija pułapkę.")),
    )


def _parse_exploration_hazard_effects(
    data: Any,
    context: str,
) -> tuple[dict[str, object], ...]:
    if not isinstance(data, list):
        raise ValueError(f"{context} must be a list.")
    supported = {
        "set_flag",
        "add_noise",
        "add_complication",
        "move_party",
        "apply_condition",
    }
    effects: list[dict[str, object]] = []
    for index, raw_effect in enumerate(data):
        effect_context = f"{context}[{index}]"
        if not isinstance(raw_effect, dict):
            raise ValueError(f"{effect_context} must be an object.")
        effect_type = str(_required(raw_effect, "type", effect_context)).strip().lower()
        if effect_type not in supported:
            raise ValueError(f"{effect_context}.type is unsupported: {effect_type}.")
        raw_parameters = raw_effect.get("parameters", {})
        if not isinstance(raw_parameters, dict):
            raise ValueError(f"{effect_context}.parameters must be an object.")
        parameters = dict(raw_parameters)
        if effect_type == "apply_condition":
            condition = str(_required(parameters, "condition", effect_context)).strip().lower()
            if condition != CombatCondition.PRONE.value:
                raise ValueError(
                    f"{effect_context}.condition must be a persistent exploration condition."
                )
            parameters["condition"] = condition
        effects.append({"type": effect_type, "parameters": parameters})
    return tuple(effects)


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
        source_id=str(data["source_id"]) if data.get("source_id") else None,
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


def _parse_exploration_resource(
    data: Any,
    property_catalog: ItemPropertyCatalog,
) -> ExplorationResource:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.resources entries must be objects.")
    resource_id = str(_required(data, "id", "exploration resource"))
    properties = _parse_string_tuple(data.get("properties", []), f"exploration resource {resource_id}.properties")
    property_catalog.validate(properties, f"exploration resource {resource_id}.properties")
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
        properties=properties,
        portable=bool(data.get("portable", True)),
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
        opening_policy=_parse_encounter_opening_policy(
            data.get("opening_policy"),
            f"exploration encounter trigger {trigger_id}.opening_policy",
        ),
        outcome_on_victory=_parse_encounter_outcome(
            data.get("outcome_on_victory"),
            f"exploration encounter trigger {trigger_id}.outcome_on_victory",
        ),
        outcome_on_defeat=_parse_encounter_outcome(
            data.get("outcome_on_defeat"),
            f"exploration encounter trigger {trigger_id}.outcome_on_defeat",
        ),
    )


def _parse_encounter_opening_policy(data: Any, field: str) -> EncounterOpeningPolicy | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    rules_data = data.get("rules", [])
    if not isinstance(rules_data, list):
        raise ValueError(f"{field}.rules must be a list.")
    rules: list[EncounterOpeningRule] = []
    for index, raw_rule in enumerate(rules_data):
        rule_field = f"{field}.rules[{index}]"
        if not isinstance(raw_rule, dict):
            raise ValueError(f"{rule_field} must be an object.")
        rules.append(
            EncounterOpeningRule(
                id=str(_required(raw_rule, "id", rule_field)),
                outcome=_enum_value(
                    EncounterOpeningOutcome,
                    str(_required(raw_rule, "outcome", rule_field)),
                    f"{rule_field}.outcome",
                ),
                title=str(_required(raw_rule, "title", rule_field)),
                narration=str(_required(raw_rule, "narration", rule_field)),
                min_noise=int(raw_rule["min_noise"]) if "min_noise" in raw_rule else None,
                max_noise=int(raw_rule["max_noise"]) if "max_noise" in raw_rule else None,
                required_flags=_parse_string_tuple(raw_rule.get("required_flags", []), f"{rule_field}.required_flags"),
                forbidden_flags=_parse_string_tuple(raw_rule.get("forbidden_flags", []), f"{rule_field}.forbidden_flags"),
                completion_any_tags=_parse_string_tuple(
                    raw_rule.get("completion_any_tags", []),
                    f"{rule_field}.completion_any_tags",
                ),
            )
        )
    return EncounterOpeningPolicy(
        challenge_id=str(_required(data, "challenge_id", field)),
        default_outcome=_enum_value(
            EncounterOpeningOutcome,
            str(_required(data, "default_outcome", field)),
            f"{field}.default_outcome",
        ),
        default_title=str(_required(data, "default_title", field)),
        default_narration=str(_required(data, "default_narration", field)),
        rules=tuple(rules),
    )


def _parse_exploration_observation(data: Any) -> ExplorationObservation:
    if not isinstance(data, dict):
        raise ValueError("scenario.exploration.observations entries must be objects.")
    observation_id = str(_required(data, "id", "exploration observation"))
    facts_data = data.get("facts", [])
    if not isinstance(facts_data, list):
        raise ValueError(f"exploration observation {observation_id}.facts must be a list.")
    return ExplorationObservation(
        id=observation_id,
        zone_id=str(_required(data, "zone_id", f"exploration observation {observation_id}")),
        challenge_id=str(data["challenge_id"]) if "challenge_id" in data else None,
        label=str(_required(data, "label", f"exploration observation {observation_id}")),
        description=str(_required(data, "description", f"exploration observation {observation_id}")),
        ability=str(_required(data, "ability", f"exploration observation {observation_id}")),
        skill=str(data["skill"]) if data.get("skill") else None,
        failure_message=str(_required(data, "failure_message", f"exploration observation {observation_id}")),
        participants=CheckParticipants(str(data.get("participants", CheckParticipants.SINGLE_ACTOR.value))),
        aggregation=CheckAggregation(str(data.get("aggregation", CheckAggregation.LEAD_RESULT.value))),
        roll_mode=RollMode(str(data.get("roll_mode", RollMode.NORMAL.value))),
        intent_examples=_parse_string_tuple(
            data.get("intent_examples", []),
            f"exploration observation {observation_id}.intent_examples",
        ),
        facts=tuple(
            _parse_observation_fact(entry, observation_id, index)
            for index, entry in enumerate(facts_data)
        ),
    )


def _parse_observation_fact(data: Any, observation_id: str, index: int) -> ObservationFact:
    field = f"exploration observation {observation_id}.facts[{index}]"
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    edge_data = data.get("encounter_edge")
    encounter_edge = None
    if edge_data is not None:
        if not isinstance(edge_data, dict):
            raise ValueError(f"{field}.encounter_edge must be an object.")
        encounter_edge = ObservationEncounterEdge(
            edge_type=EncounterEdgeType(str(_required(edge_data, "type", f"{field}.encounter_edge"))),
            encounter_trigger_id=str(
                _required(edge_data, "encounter_trigger_id", f"{field}.encounter_edge")
            ),
            label=str(_required(edge_data, "label", f"{field}.encounter_edge")),
        )
    return ObservationFact(
        id=str(_required(data, "id", field)),
        minimum_total=int(_required(data, "minimum_total", field)),
        narration=str(_required(data, "narration", field)),
        reveal_flag=str(_required(data, "reveal_flag", field)),
        effects=_parse_effects(data.get("effects", []), f"{field}.effects"),
        encounter_edge=encounter_edge,
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
    guidance_facts_data = data.get("guidance_facts", [])
    if not isinstance(guidance_facts_data, list):
        raise ValueError(f"{field}.guidance_facts must be a list.")
    guidance_facts = tuple(
        _parse_llm_guidance_fact(item, f"{field}.guidance_facts[{index}]")
        for index, item in enumerate(guidance_facts_data)
    )
    fact_ids = tuple(fact.id for fact in guidance_facts)
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError(f"{field}.guidance_facts contains duplicate ids.")
    return LlmContext(
        summary=str(data.get("summary", "")),
        available_materials=_parse_string_tuple(data.get("available_materials", []), f"{field}.available_materials"),
        forbidden_assumptions=_parse_string_tuple(data.get("forbidden_assumptions", []), f"{field}.forbidden_assumptions"),
        reasonable_approaches=_parse_string_tuple(data.get("reasonable_approaches", []), f"{field}.reasonable_approaches"),
        impossible_approaches=_parse_string_tuple(data.get("impossible_approaches", []), f"{field}.impossible_approaches"),
        risk_notes=_parse_string_tuple(data.get("risk_notes", []), f"{field}.risk_notes"),
        guidance_facts=guidance_facts,
    )


def _parse_llm_guidance_fact(data: Any, field: str) -> LlmGuidanceFact:
    if not isinstance(data, dict):
        raise ValueError(f"{field} must be an object.")
    return LlmGuidanceFact(
        id=str(_required(data, "id", field)),
        text=str(_required(data, "text", field)),
        kind=LlmGuidanceFactKind(str(_required(data, "kind", field))),
        visibility=LlmGuidanceFactVisibility(str(_required(data, "visibility", field))),
        minimum_hint_level=int(data.get("minimum_hint_level", 0)),
        reveal_if_flags=_parse_string_tuple(data.get("reveal_if_flags", []), f"{field}.reveal_if_flags"),
        match_phrases=_parse_string_tuple(data.get("match_phrases", []), f"{field}.match_phrases"),
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
        temporary_item_templates=_parse_temporary_item_templates(
            data.get("temporary_item_templates", []),
            f"{field}.temporary_item_templates",
        ),
    )


def _parse_temporary_item_templates(data: Any, field: str) -> tuple[TemporaryItemTemplate, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{field} must be a list.")
    templates: list[TemporaryItemTemplate] = []
    for index, raw_template in enumerate(data):
        item_field = f"{field}[{index}]"
        if not isinstance(raw_template, dict):
            raise ValueError(f"{item_field} must be an object.")
        uses = int(raw_template.get("uses", 1))
        modifier = int(raw_template.get("modifier", 0))
        if uses < 1:
            raise ValueError(f"{item_field}.uses must be positive.")
        if not -2 <= modifier <= 2:
            raise ValueError(f"{item_field}.modifier must be between -2 and 2.")
        templates.append(
            TemporaryItemTemplate(
                id=str(raw_template.get("id", "")).strip(),
                label=str(raw_template.get("label", "")).strip(),
                description=str(raw_template.get("description", "")).strip(),
                bonus_tags=_parse_string_tuple(raw_template.get("bonus_tags", []), f"{item_field}.bonus_tags"),
                modifier=modifier,
                advantage=bool(raw_template.get("advantage", False)),
                uses=uses,
                risk=str(raw_template.get("risk", "")).strip(),
                allowed_materials=_parse_string_tuple(
                    raw_template.get("allowed_materials", []),
                    f"{item_field}.allowed_materials",
                ),
            )
        )
    ids = [template.id for template in templates]
    if any(not template.id or not template.label or not template.bonus_tags for template in templates):
        raise ValueError(f"{field} entries require id, label and bonus_tags.")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{field} contains duplicate ids.")
    return tuple(templates)


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
        action_cost=ActionEconomyCost(str(data.get("action_cost", "action"))),
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
        tool=str(data["tool"]) if "tool" in data else None,
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
        size=definition.size,
        max_hp=definition.hp,
        ability_scores=definition.ability_scores,
        spell_slots=definition.spell_slots,
        spell_save_dc=definition.spell_save_dc,
        inventory=definition.inventory,
        spell_ids=definition.spell_ids,
        spell_preparation=definition.spell_preparation,
        hit_dice=definition.hit_dice,
        resource_pools=definition.resource_pools,
        proficiency_bonus=definition.proficiency_bonus,
        proficiencies=definition.proficiencies,
        uses_death_saves=definition.uses_death_saves,
        damage_affinities=definition.damage_affinities,
        attacks_per_action=definition.attacks_per_action,
        condition_immunities=definition.condition_immunities,
        auras=definition.auras,
        triggers=definition.triggers,
        features=definition.features,
    )


def _attack_source_from_definition(
    definition: ScenarioAttackDefinition,
    stacking_key: str,
    actor: Actor,
) -> AttackSource:
    proficiency_id = definition.proficiency_id or definition.source_item_id or definition.id
    if definition.ability is not None:
        modifiers = attack_roll_modifiers(
            actor,
            definition.ability,
            proficient=(
                definition.source_type == AttackSourceType.WEAPON
                and actor.proficiencies.is_weapon_proficient(proficiency_id)
            ),
        )
    else:
        if definition.attack_modifier is None:
            raise ValueError(
                f"Attack {definition.id} requires either ability or legacy attack_modifier."
            )
        modifiers = (
            RollModifier(
                f"Premia ataku: {definition.name}",
                definition.attack_modifier,
                RollModifierType.CUSTOM,
                stacking_key=stacking_key,
            ),
        )
    return AttackSource(
        name=definition.name,
        source_type=definition.source_type,
        range_feet=definition.range_feet,
        attack_roll_request=D20RollRequest(modifiers=modifiers),
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
        source_item_id=definition.source_item_id,
        attack_kind=definition.attack_kind,
        proficiency_id=proficiency_id,
        reach_feet=definition.reach_feet,
        resource_pool_id=definition.resource_pool_id,
        resource_cost=definition.resource_cost,
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
    challenges_by_zone = {
        challenge.zone_id: challenge
        for challenge in definition.exploration_challenges
    }
    for zone in definition.exploration_zones:
        challenge = challenges_by_zone.get(zone.id)
        for fixture in zone.fixtures:
            for action in fixture.action_policies:
                if challenge is None:
                    raise ValueError(
                        f"exploration fixture {fixture.id}.action_policies requires a challenge in zone {zone.id}."
                    )
                policy = challenge.llm_policy
                if policy.dc_for_tier(action.difficulty_tier) is None:
                    raise ValueError(
                        f"exploration fixture {fixture.id} action {action.operation.value} references unknown "
                        f"difficulty tier: {action.difficulty_tier}."
                    )
                if not policy.progress_success_min <= action.progress_on_success <= policy.progress_success_max:
                    raise ValueError(
                        f"exploration fixture {fixture.id} action {action.operation.value} success progress "
                        "is outside challenge policy."
                    )
                if not policy.progress_failure_min <= action.progress_on_failure <= policy.progress_failure_max:
                    raise ValueError(
                        f"exploration fixture {fixture.id} action {action.operation.value} failure progress "
                        "is outside challenge policy."
                    )
                if (
                    action.failure_complication is not None
                    and action.failure_complication not in policy.allowed_complications
                ):
                    raise ValueError(
                        f"exploration fixture {fixture.id} action {action.operation.value} references disallowed "
                        f"complication: {action.failure_complication}."
                    )
                if action.release_yield_items and not fixture.yield_items:
                    raise ValueError(
                        f"exploration fixture {fixture.id} releases yield items but defines none."
                    )
    challenge_ids = {challenge.id for challenge in definition.exploration_challenges}
    observation_ids = tuple(observation.id for observation in definition.exploration_observations)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("exploration.observations contains duplicate ids.")
    encounter_trigger_ids = {trigger.id for trigger in definition.exploration_encounter_triggers}
    for observation in definition.exploration_observations:
        if observation.zone_id not in zone_ids:
            raise ValueError(f"exploration observation {observation.id}.zone_id references unknown zone.")
        if observation.challenge_id is not None and observation.challenge_id not in challenge_ids:
            raise ValueError(f"exploration observation {observation.id}.challenge_id references unknown challenge.")
        if observation.challenge_id is not None:
            challenge = next(item for item in definition.exploration_challenges if item.id == observation.challenge_id)
            if challenge.zone_id != observation.zone_id:
                raise ValueError(f"exploration observation {observation.id} must share its challenge zone.")
        for fact in observation.facts:
            if (
                fact.encounter_edge is not None
                and fact.encounter_edge.encounter_trigger_id not in encounter_trigger_ids
            ):
                raise ValueError(
                    f"exploration observation {observation.id} fact {fact.id}.encounter_edge "
                    "references unknown encounter trigger."
                )
    trap_ids = tuple(trap.id for trap in definition.exploration_traps)
    if len(trap_ids) != len(set(trap_ids)):
        raise ValueError("exploration.traps contains duplicate ids.")
    observations_by_id = {item.id: item for item in definition.exploration_observations}
    for trap in definition.exploration_traps:
        if trap.zone_id not in zone_ids:
            raise ValueError(f"exploration trap {trap.id}.zone_id references unknown zone.")
        observation = observations_by_id.get(trap.detection_observation_id)
        if observation is None:
            raise ValueError(f"exploration trap {trap.id} references unknown detection observation.")
        if observation.zone_id != trap.zone_id:
            raise ValueError(f"exploration trap {trap.id} must share its detection observation zone.")
        reveals_trap = any(
            effect.get("type") == "reveal_trap"
            and isinstance(effect.get("parameters"), dict)
            and effect["parameters"].get("trap_id") == trap.id
            for fact in observation.facts
            for effect in fact.effects
        )
        if not reveals_trap:
            raise ValueError(f"exploration trap {trap.id} detection observation must reveal that trap.")
        if trap.required_item_id is not None and trap.required_item_id not in actor_item_ids:
            raise ValueError(f"exploration trap {trap.id} requires unknown actor inventory item.")
        if (
            trap.activation_challenge_id is not None
            and trap.activation_challenge_id not in challenge_ids
        ):
            raise ValueError(f"exploration trap {trap.id} references unknown activation challenge.")
    for trigger in definition.exploration_encounter_triggers:
        if trigger.opening_policy is not None:
            policy = trigger.opening_policy
            if policy.challenge_id not in challenge_ids:
                raise ValueError(
                    f"exploration encounter trigger {trigger.id}.opening_policy.challenge_id references unknown challenge."
                )
            rule_ids = tuple(rule.id for rule in policy.rules)
            if len(rule_ids) != len(set(rule_ids)):
                raise ValueError(f"exploration encounter trigger {trigger.id}.opening_policy contains duplicate rule ids.")
            for rule in policy.rules:
                if rule.min_noise is not None and rule.min_noise < 0:
                    raise ValueError(f"encounter opening rule {rule.id}.min_noise must be non-negative.")
                if rule.max_noise is not None and rule.max_noise < 0:
                    raise ValueError(f"encounter opening rule {rule.id}.max_noise must be non-negative.")
                if rule.min_noise is not None and rule.max_noise is not None and rule.min_noise > rule.max_noise:
                    raise ValueError(f"encounter opening rule {rule.id} has an invalid noise range.")
                if set(rule.required_flags).intersection(rule.forbidden_flags):
                    raise ValueError(f"encounter opening rule {rule.id} requires and forbids the same flag.")
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
    transition_ids = tuple(item.id for item in definition.exploration_npc_transitions)
    if len(transition_ids) != len(set(transition_ids)):
        raise ValueError("exploration.npc_transitions contains duplicate ids.")
    transition_id_set = set(transition_ids)
    npc_ids = {
        point.npc_interaction.id
        for point in definition.exploration_points
        if point.npc_interaction is not None
    }
    for transition in definition.exploration_npc_transitions:
        if transition.npc_id not in npc_ids:
            raise ValueError(
                f"exploration NPC transition {transition.id}.npc_id references unknown NPC."
            )
        if not _npc_transition_variant_is_fallback(transition.variants[-1]):
            raise ValueError(
                f"exploration NPC transition {transition.id} must end with an unconditional fallback variant."
            )
        for variant in transition.variants:
            for reaction in variant.reactions:
                referenced_triggers = set(reaction.suppress_encounter_trigger_ids)
                if reaction.encounter_trigger_id is not None:
                    referenced_triggers.add(reaction.encounter_trigger_id)
                unknown = referenced_triggers - encounter_trigger_ids
                if unknown:
                    raise ValueError(
                        f"exploration NPC transition {transition.id} references unknown encounter trigger: "
                        + ", ".join(sorted(unknown))
                        + "."
                    )
    _validate_npc_content_effects(definition)
    for point in definition.exploration_points:
        if point.npc_interaction is None:
            continue
        for permission in point.npc_interaction.policy.intent_permissions:
            for target in permission.targets:
                for branch in target.outcome_branches:
                    if branch.transition_id is not None and branch.transition_id not in transition_id_set:
                        raise ValueError(
                            f"NPC target {target.id} references unknown scene transition: {branch.transition_id}."
                        )


def _validate_npc_content_effects(definition: ScenarioDefinition) -> None:
    state = ExplorationState(
        zones=definition.exploration_zones,
        points=definition.exploration_points,
        party_position=PartyPosition(str(definition.party_start_zone_id)),
        flags=SceneFlags(),
        challenges=definition.exploration_challenges,
        resources=definition.exploration_resources,
        traps=definition.exploration_traps,
    )
    npc_by_id: dict[str, NpcInteraction] = {}
    for point in definition.exploration_points:
        npc = point.npc_interaction
        if npc is None:
            continue
        if npc.id in npc_by_id:
            raise ValueError(f"exploration NPC id is duplicated: {npc.id}.")
        npc_by_id[npc.id] = npc
        policy = npc.policy
        if len(policy.allowed_flags) != len(set(policy.allowed_flags)):
            raise ValueError(f"NPC {npc.id}.policy.allowed_flags contains duplicates.")
        if len(policy.allowed_effect_types) != len(set(policy.allowed_effect_types)):
            raise ValueError(f"NPC {npc.id}.policy.allowed_effect_types contains duplicates.")
        information_ids = tuple(item.id for item in npc.locked_information)
        if len(information_ids) != len(set(information_ids)):
            raise ValueError(f"NPC {npc.id}.locked_information contains duplicate ids.")
        known_information_ids = set(information_ids)
        allowed_flags = set(policy.allowed_flags)
        for info in npc.locked_information:
            unknown_set_flags = set(info.sets_flags) - allowed_flags if allowed_flags else set()
            if unknown_set_flags:
                raise ValueError(
                    f"NPC {npc.id}.locked_information.{info.id}.sets_flags contains disallowed flags: "
                    + ", ".join(sorted(unknown_set_flags))
                    + "."
                )
            _validate_npc_effect_sequence(
                info.effects_on_reveal,
                state=state,
                npc=npc,
                field=f"NPC {npc.id}.locked_information.{info.id}.effects_on_reveal",
            )
        for permission in policy.intent_permissions:
            unknown_permission_information = set(permission.reveals) - known_information_ids
            if unknown_permission_information:
                raise ValueError(
                    f"NPC {npc.id}.intent_permissions.{permission.intent}.reveals references unknown information: "
                    + ", ".join(sorted(unknown_permission_information))
                    + "."
                )
            for target in permission.targets:
                for branch in target.outcome_branches:
                    unknown_branch_information = (
                        set(branch.revealed_information_ids) - known_information_ids
                    )
                    if unknown_branch_information:
                        raise ValueError(
                            f"NPC {npc.id}.intent_permissions.{permission.intent}.targets.{target.id}."
                            f"outcomes.{branch.outcome.value}.revealed_information_ids references unknown information: "
                            + ", ".join(sorted(unknown_branch_information))
                            + "."
                        )
                    _validate_npc_effect_sequence(
                        branch.effects,
                        state=state,
                        npc=npc,
                        field=(
                            f"NPC {npc.id}.intent_permissions.{permission.intent}.targets.{target.id}."
                            f"outcomes.{branch.outcome.value}.effects"
                        ),
                    )
    for transition in definition.exploration_npc_transitions:
        npc = npc_by_id[transition.npc_id]
        for variant in transition.variants:
            for reaction in variant.reactions:
                _validate_npc_effect_sequence(
                    reaction.effects,
                    state=state,
                    npc=npc,
                    field=(
                        f"NPC transition {transition.id}.variants.{variant.id}."
                        f"reactions.{reaction.id}.effects"
                    ),
                )


def _validate_npc_effect_sequence(
    effects: tuple[dict[str, object], ...],
    *,
    state: ExplorationState,
    npc: NpcInteraction,
    field: str,
) -> None:
    for index, effect in enumerate(effects):
        validate_policy_exploration_effect(
            effect,
            state,
            allowed_effect_types=npc.policy.allowed_effect_types,
            allowed_flags=npc.policy.allowed_flags,
            field=f"{field}[{index}]",
        )


def _npc_transition_variant_is_fallback(variant: NpcTransitionVariant) -> bool:
    return not (
        variant.required_flags
        or variant.forbidden_flags
        or variant.required_resolved_encounter_trigger_ids
        or variant.forbidden_resolved_encounter_trigger_ids
    )


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
    local_path = root / category / filename
    if local_path.exists():
        return local_path
    bundled_path = Path(__file__).resolve().parents[3] / "content" / category / filename
    if bundled_path.exists():
        return bundled_path
    return local_path


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


def _parse_hit_dice(data: Any, actor_id: str) -> tuple[HitDicePool, ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ValueError(f"actor {actor_id}.hit_dice must be an object.")
    pools = []
    for raw_die, raw_maximum in data.items():
        die = str(raw_die).strip().lower()
        if not die.startswith("d") or not die[1:].isdigit():
            raise ValueError(f"actor {actor_id}.hit_dice key must look like d8 or d10.")
        maximum = int(raw_maximum)
        pools.append(HitDicePool(int(die[1:]), maximum, maximum))
    return tuple(sorted(pools, key=lambda pool: pool.die_sides))


def _parse_actor_resources(data: Any, actor_id: str) -> tuple[ActorResourcePool, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError(f"actor {actor_id}.resource_pools must be a list.")
    pools = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError(f"actor {actor_id}.resource_pools entries must be objects.")
        resource_id = str(_required(entry, "id", f"actor {actor_id}.resource_pool"))
        maximum = int(_required(entry, "maximum", f"actor resource {resource_id}"))
        recharge_data = entry.get("recharge")
        recharge = None
        if recharge_data is not None:
            if not isinstance(recharge_data, dict):
                raise ValueError(f"actor resource {resource_id}.recharge must be an object.")
            recharge = ResourceRechargeRule(
                die_sides=int(recharge_data.get("die_sides", 6)),
                minimum_roll=int(_required(
                    recharge_data,
                    "minimum_roll",
                    f"actor resource {resource_id}.recharge",
                )),
            )
        pools.append(
            ActorResourcePool(
                id=resource_id,
                label=str(entry.get("label") or resource_id),
                current=int(entry.get("current", maximum)),
                maximum=maximum,
                recovery=_enum_value(
                    RecoveryPeriod,
                    str(entry.get("recovery", RecoveryPeriod.NEVER.value)),
                    f"actor resource {resource_id}.recovery",
                ),
                recharge=recharge,
            )
        )
    if len({pool.id for pool in pools}) != len(pools):
        raise ValueError(f"actor {actor_id}.resource_pools ids must be unique.")
    return tuple(pools)


def _parse_feature_definition(
    data: dict[str, Any],
    actor_id: str,
) -> ScenarioFeatureDefinition:
    feature_id = str(_required(data, "id", f"actor {actor_id}.feature"))
    schema_version = int(data.get("schema_version", 1))
    if schema_version != 1:
        raise ValueError(
            f"feature {feature_id}.schema_version must be 1, got {schema_version}."
        )
    grants = data.get("grants", {})
    if not isinstance(grants, dict):
        raise ValueError(f"feature {feature_id}.grants must be an object.")
    resource_pools = _parse_actor_resources(
        grants.get("resource_pools", []),
        f"{actor_id}.feature.{feature_id}",
    )
    attacks_data = grants.get("attacks", [])
    healing_data = grants.get("healing_sources", [])
    combat_actions_data = grants.get("combat_actions", [])
    for field_name, values in (
        ("attacks", attacks_data),
        ("healing_sources", healing_data),
        ("combat_actions", combat_actions_data),
    ):
        if not isinstance(values, list):
            raise ValueError(f"feature {feature_id}.grants.{field_name} must be a list.")
    attacks = tuple(_parse_attack(value, actor_id) for value in attacks_data)
    healing_sources = tuple(_parse_healing_source(value, actor_id) for value in healing_data)
    combat_actions = tuple(_parse_combat_action(value, actor_id) for value in combat_actions_data)
    auras = _parse_actor_auras(
        grants.get("auras", []),
        f"{actor_id}.feature.{feature_id}",
    )
    triggers = _parse_actor_triggers(
        grants.get("triggers", []),
        f"{actor_id}.feature.{feature_id}",
    )
    action_ids = (
        tuple(attack.id for attack in attacks)
        + tuple(source.id for source in healing_sources)
        + tuple(action.id for action in combat_actions)
    )
    definition = FeatureDefinition(
        id=feature_id,
        label=str(_required(data, "label", f"feature {feature_id}")),
        description=str(data.get("description", "")),
        source_kind=_enum_value(
            FeatureSourceKind,
            str(_required(data, "source_kind", f"feature {feature_id}")),
            f"feature {feature_id}.source_kind",
        ),
        source_ref=str(data.get("source_ref", feature_id)),
        resource_ids=tuple(pool.id for pool in resource_pools),
        action_ids=action_ids,
        trigger_ids=tuple(trigger.id for trigger in triggers),
        aura_ids=tuple(aura.id for aura in auras),
    )
    if not (
        definition.resource_ids
        or definition.action_ids
        or definition.trigger_ids
        or definition.aura_ids
    ):
        raise ValueError(f"feature {feature_id} must grant at least one mechanic.")
    return ScenarioFeatureDefinition(
        definition=definition,
        resource_pools=resource_pools,
        attacks=attacks,
        healing_sources=healing_sources,
        combat_actions=combat_actions,
        auras=auras,
        triggers=triggers,
    )


def _validate_unique_ids(values: tuple[Any, ...], field: str) -> None:
    ids = tuple(str(value.id) for value in values)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{field} ids must be unique.")


def _parse_actor_auras(data: Any, actor_id: str) -> tuple[ActorAura, ...]:
    if not isinstance(data, list):
        raise ValueError(f"actor {actor_id}.auras must be a list.")
    auras: list[ActorAura] = []
    for raw_aura in data:
        if not isinstance(raw_aura, dict):
            raise ValueError(f"actor {actor_id}.auras entries must be objects.")
        aura_id = str(_required(raw_aura, "id", f"actor {actor_id}.aura"))
        auras.append(
            ActorAura(
                id=aura_id,
                label=str(_required(raw_aura, "label", f"actor aura {aura_id}")),
                radius_feet=int(
                    _required(raw_aura, "radius_feet", f"actor aura {aura_id}")
                ),
                target=_enum_value(
                    AuraTarget,
                    str(_required(raw_aura, "target", f"actor aura {aura_id}")),
                    f"actor aura {aura_id}.target",
                ),
                effect_kind=_enum_value(
                    AuraEffectKind,
                    str(_required(raw_aura, "effect_kind", f"actor aura {aura_id}")),
                    f"actor aura {aura_id}.effect_kind",
                ),
                value=int(_required(raw_aura, "value", f"actor aura {aura_id}")),
            )
        )
    if len({aura.id for aura in auras}) != len(auras):
        raise ValueError(f"actor {actor_id}.auras ids must be unique.")
    return tuple(auras)


def _parse_actor_triggers(data: Any, actor_id: str) -> tuple[ActorTrigger, ...]:
    if not isinstance(data, list):
        raise ValueError(f"actor {actor_id}.triggers must be a list.")
    triggers: list[ActorTrigger] = []
    for raw_trigger in data:
        if not isinstance(raw_trigger, dict):
            raise ValueError(f"actor {actor_id}.triggers entries must be objects.")
        trigger_id = str(_required(raw_trigger, "id", f"actor {actor_id}.trigger"))
        triggers.append(
            ActorTrigger(
                id=trigger_id,
                label=str(
                    _required(raw_trigger, "label", f"actor trigger {trigger_id}")
                ),
                event_type=_enum_value(
                    TriggerEventType,
                    str(_required(raw_trigger, "event_type", f"actor trigger {trigger_id}")),
                    f"actor trigger {trigger_id}.event_type",
                ),
                effect_kind=_enum_value(
                    TriggerEffectKind,
                    str(_required(raw_trigger, "effect_kind", f"actor trigger {trigger_id}")),
                    f"actor trigger {trigger_id}.effect_kind",
                ),
                value=int(_required(raw_trigger, "value", f"actor trigger {trigger_id}")),
            )
        )
    if len({trigger.id for trigger in triggers}) != len(triggers):
        raise ValueError(f"actor {actor_id}.triggers ids must be unique.")
    return tuple(triggers)


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
        target_mode=_enum_value(
            SpellAreaTargetMode,
            str(data.get("target_mode", SpellAreaTargetMode.ALL_CREATURES.value)),
            f"{field}.target_mode",
        ),
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
