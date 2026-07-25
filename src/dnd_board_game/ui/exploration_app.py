from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, fields, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from dnd_board_game.actions import (
    PlayerIntentHint,
    action_mechanic_payload,
    attack_mechanic_from_source,
    combat_action_mechanic_from_definition,
    healing_mechanic_from_source,
    parse_player_input,
    slash_help_message,
)
from dnd_board_game.application import (
    CombatApproachInteractionPlan,
    CombatMovementFlowService,
    CombatReactionFlowService,
    CombatSceneInteractionFlowService,
    CombatSceneInteractionTransition,
    CombatGrappleFlowService,
    CombatShoveFlowService,
    StabilizationMethod,
    CombatTurnActionFlowService,
    CombatTurnFinalizationService,
    CombatResourceTransition,
    EnemyTurnFlowService,
    EnemyTurnTransitionKind,
    ExpiredCombatEffects,
    ExplorationFlowService,
    ExplorationFlowStage,
    ExplorationInteractionFlowService,
    PendingAreaSpell,
    PendingCombatInteraction,
    PendingCombatSkillCheck,
    PendingGrapple,
    PendingShove,
    PendingConcentrationAction,
    PendingConcentrationCheck,
    PendingEnemySavingThrow,
    PendingPlayerAttack,
    PendingPlayerHealing,
    PendingShortRest,
    PlayerAreaHealingFlowService,
    PlayerAreaSpellTransition,
    PlayerReactionFlowService,
    PlayerAttackTransition,
    PlayerCombatActionFlowService,
    PlayerCombatResourceFlowService,
    SpellPreparationFlowService,
    ShortRestFlowService,
    short_rest_count,
    legal_stabilization_targets,
    resolve_combat_stabilization,
    resolve_encounter_opening,
    apply_exploration_hazard_outcome,
    resolve_exploration_hazard,
    hidden_states_from_precombat_attempts,
    precombat_stealth_is_available,
    precombat_stealth_modifier,
    resolve_precombat_stealth,
    resolve_targeted_item_action,
    targeted_item_action_is_legal,
    ShoveMode,
    GrappleMode,
    automatic_grapple_opponent_roll,
    automatic_defender_roll,
)
from dnd_board_game.application.damage_presentation import (
    applied_damage_message,
    applied_damage_payload,
)
from dnd_board_game.actors import (
    Actor,
    Faction,
    FeatureGrant,
    actor_resource_pool,
    can_spend_actor_resource,
    can_grapple_or_shove_size,
    creature_size_label_pl,
    largest_grapple_or_shove_target,
    ability_check_roll_modifiers,
    passive_skill_score,
    saving_throw_roll_modifiers,
    skill_modifier,
    spell_is_prepared,
)
from dnd_board_game.combat import (
    ActorSetupEntry,
    ActionUse,
    action_economy_cost_label,
    attack_action_remaining,
    ActiveCombatEffect,
    AttackKind,
    AttackPositioning,
    CombatState,
    CombatStatus,
    CombatCondition,
    ConditionState,
    CoverLevel,
    CombatContextMenu,
    CombatMenuAction,
    CombatMenuCategory,
    CombatMenuOption,
    ContextualActionCatalog,
    DeathSaveOutcome,
    CombatInteractionOption,
    EncounterSetup,
    EnemyAutoTurnResult,
    EnemyTurnPlan,
    InitiativeEntry,
    InitiativeOrder,
    HealingSource,
    InitiativePrompt,
    SpellAreaShape,
    TurnActionState,
    EnvironmentSetupEntry,
    EnvironmentSetupType,
    SceneFlags,
    SetupStep,
    SetupStepKind,
    SetupVisibility,
    build_setup_steps,
    build_initiative_order,
    build_player_initiative_prompts,
    current_actor as combat_current_actor,
    expire_turn_end_effects,
    expire_turn_start_effects,
    expire_combat_effects,
    finish_turn,
    active_actor_led_feedback,
    active_auras,
    attack_source_with_combat_effects,
    attack_source_with_hidden_advantage,
    attack_source_for_actor,
    attack_source_with_prone,
    effective_movement_speed,
    effective_attack_kind,
    melee_reach_feet,
    attack_source_with_positioning,
    attack_source_with_target_combat_effects,
    movement_remaining,
    movement_range_with_condition_cost,
    legal_healing_targets,
    legal_area_centers,
    can_consume_spell_resource,
    can_use_attack_action,
    condition_definition,
    condition_label,
    condition_roll_request,
    ConditionSaveTiming,
    pending_condition_saves,
    resolve_condition_save,
    can_use_object_interactions,
    consume_spell_resource,
    direction_anchor_positions,
    evaluate_attack_positioning,
    attack_sources_with_versatile_variants,
    eligible_two_weapon_bonus_sources,
    is_hidden_from,
    hide_eligibility,
    has_condition,
    grappled_by,
    grappled_actor_ids,
    drop_weapon,
    don_shield,
    doff_shield,
    equip_weapon,
    replace_actor,
    resolve_actor_trigger_events,
    resolve_combat_trigger_events,
    pickup_dropped_weapon,
    resolve_death_save,
    roll_enemy_initiative,
    scene_flag,
    saving_throw_aura_modifiers,
    scene_object_by_id,
    setup_led_feedback,
    start_combat,
    start_attack_action,
    standing_movement_cost,
    stow_weapon,
    two_weapon_bonus_attack_source,
)
from dnd_board_game.core.damage_types import damage_type_label_pl
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    CollectionPlan,
    CraftingDraft,
    CraftingPlan,
    CraftingSource,
    CraftingSourceKind,
    EncounterEdge,
    EncounterEdgeType,
    EncounterOutcome,
    EncounterOpeningOutcome,
    ExplorationChallenge,
    ExplorationFlowGraph,
    ExplorationEncounterTrigger,
    ExplorationHazard,
    ExplorationHazardTrigger,
    ExplorationTrap,
    ExplorationTrapAction,
    ExplorationTrapStatus,
    ExplorationChallengeOption,
    ExplorationCheckPlan,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    FixtureActionPlan,
    FixtureOperation,
    ExplorationMechanicId,
    ExplorationObservation,
    ExplorationSituationalModifier,
    ExplorationSituationalModifierSource,
    ImprovisedToolUse,
    InteractionGoal,
    InteractionParticipantMode,
    PartyCheckInput,
    PartyPosition,
    NpcAttemptPlan,
    NpcInteractionStatus,
    NpcIntentActionPlan,
    NpcRuntimeState,
    NpcOutcomeTier,
    NpcTransitionPlan,
    NpcTransitionResultType,
    NpcStateUpdate,
    SocialInteractionPlan,
    PendingEncounter,
    ShortRestPolicy,
    SceneSourceMatch,
    SceneSourceCollection,
    TemporaryItem,
    MECHANIC_TOOLS,
    active_option_bonuses_for_actor,
    apply_goal_resolution_profile,
    available_interaction_goals,
    apply_fixture_action,
    apply_exploration_effect,
    actors_matching_challenge_option,
    available_encounter_edges,
    available_exploration_zones,
    build_crafting_source_registry,
    collect_source,
    challenge_for_zone,
    challenge_state_for,
    exploration_zone_feedback,
    mechanic_payload_for_option,
    matching_resources,
    match_revealed_trap_action,
    match_exploration_observation,
    match_available_sources,
    match_scene_sources_by_properties,
    match_visible_scene_sources,
    interaction_goal,
    match_npc_key_issue,
    is_source_lookup_only,
    describes_direct_source_use,
    create_temporary_item,
    discover_scene_source,
    craft_temporary_item,
    consume_encounter_edge,
    dismantle_crafted_item,
    grant_encounter_edge,
    reveal_exploration_points,
    resolve_challenge_option,
    resolve_exploration_check,
    resolve_observation,
    validate_mechanic_selection,
    validate_policy_exploration_effect,
    validate_source_property_query,
    visible_exploration_points,
    visible_exploration_zones,
    option_roll_modifiers_for_actor,
    npc_runtime_state_for,
    plan_source_collection,
    plan_fixture_action,
    resolve_trap_action,
    resolve_npc_runtime_interaction,
    npc_outcome_for_check,
    resolve_npc_outcome,
    plan_npc_transition,
    resolve_npc_transition_reaction,
    restore_npc_transition_plan,
    set_npc_interaction_status,
    trap_state_for,
    trigger_trap,
    remove_exploration_condition,
    use_temporary_item,
)
from dnd_board_game.llm import (
    GmActionFlow,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    GmDeclarationThreadEntry,
    GmFlowRouteCandidate,
    GmClassifierProposal,
    GmPreparationEffect,
    GmProposalValidationError,
    PreparationEffectType,
    NpcInteractionProposal,
    build_gm_classifier_request,
    build_npc_interaction_request,
    challenge_option_from_validated_proposal,
    validate_gm_declaration_analysis,
    validate_gm_classifier_proposal,
    validate_npc_interaction_proposal,
)
from dnd_board_game.hardware import BoardSessionAdapter, LedColor, LedFeedback, LedFrame, LedRole, led_color_name_pl, movement_led_feedback
from dnd_board_game.inventory import (
    break_inventory_item,
    consume_inventory_item,
    effective_armor_class,
    hand_loadout_payload,
    inventory_item_payload,
    plan_hand_equip,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectEvent,
    EffectEventType,
    EffectDuration,
    RollMode,
    RollModifier,
    RollModifierType,
    ability_modifier,
    complete_long_rest,
    expire_active_effects,
    resolve_d20_roll,
    roll_instruction,
)
from dnd_board_game.save import (
    SNAPSHOT_SCHEMA_VERSION,
    SessionSnapshot,
    read_snapshot,
    write_snapshot,
)
from dnd_board_game.scenarios import (
    LoadedEncounter,
    LoadedExploration,
    build_encounter_from_scenario,
    build_exploration_from_scenario,
    load_scenario,
)
from dnd_board_game.runtime.session_observer import SessionObserver
from dnd_board_game.world import Coordinate, MovementRangeResult, PathResult, movement_range

from .session_state import UiPendingState
from .session_view import UiSessionView
from .conversation import InteractionConversationEntry


class PendingKind(StrEnum):
    CHALLENGE = "challenge"
    CRAFTING = "crafting"
    NPC = "npc"
    OBSERVATION = "observation"
    SOURCE_SELECTION = "source_selection"
    COLLECTION = "collection"
    TRAP = "trap"


class PendingStage(StrEnum):
    DECISION = "decision"
    ROLL = "roll"
    BREAKAGE = "breakage"
    HAZARD_SAVE = "hazard_save"


UiFlowStage = ExplorationFlowStage


EXPLORATION_DECISION_ABILITIES = frozenset(
    {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
)
EXPLORATION_DECISION_DC_MIN = 5
EXPLORATION_DECISION_DC_MAX = 25
EXPLORATION_DECISION_MAX_SITUATIONAL_MODIFIERS = 3
CONVERSATION_GM_TITLES = frozenset(
    {
        "Odpowiedź MG",
        "Podpowiedź MG",
        "MG proponuje sprawdzenie",
        "MG dopytuje",
        "Świat odpowiada",
        "Deklaracja wymaga doprecyzowania",
        "Deklaracja wymaga korekty",
        "Narracja MG",
        "Odpowiedź NPC",
        "Przygotowanie",
        "Poprawiono decyzję MG",
        "Decyzja",
        "Wyjaśnienie",
        "Reinterpretacja",
        "Utworzono przedmiot sceny",
        "Rozmontowano przedmiot sceny",
        "Użyto przedmiotu sceny",
        "Znaleziono w scenie",
        "Wynik podejścia",
        "Wynik rozpoznania",
        "Zagrożenie",
        "Wynik zagrożenia",
        "Pułapka",
        "Wynik pułapki",
        "Zmiana nastawienia",
        "Reakcja NPC",
    }
)


@dataclass(frozen=True, slots=True)
class UiMessage:
    title: str
    body: str

    def as_payload(self) -> dict[str, str]:
        return {"title": self.title, "body": self.body}


@dataclass(frozen=True, slots=True)
class PendingInteraction:
    kind: PendingKind
    stage: PendingStage
    proposal: GmClassifierProposal | GmDeclarationAnalysis | NpcInteractionProposal | None = None
    challenge: ExplorationChallenge | None = None
    option: ExplorationChallengeOption | None = None
    participant_actor_ids: tuple[str, ...] = ()
    resources: tuple[ExplorationResource, ...] = ()
    point: ExplorationPoint | None = None
    check_plan: ExplorationCheckPlan | None = None
    crafting_plan: CraftingPlan | None = None
    crafting_source_labels: tuple[tuple[str, str], ...] = ()
    observation: ExplorationObservation | None = None
    source_matches: tuple[SceneSourceMatch, ...] = ()
    source_search_text: str = ""
    source_property_labels: tuple[tuple[str, str], ...] = ()
    use_source: CraftingSource | None = None
    collection_plan: CollectionPlan | None = None
    fixture_action_plan: FixtureActionPlan | None = None
    breakage_actor_id: str | None = None
    breakage_item_id: str | None = None
    breakage_item_label: str = ""
    breakage_chance_percent: int | None = None
    hazard: ExplorationHazard | None = None
    hazard_actor_id: str | None = None
    trap: ExplorationTrap | None = None
    trap_action: ExplorationTrapAction | None = None
    social_plan: SocialInteractionPlan | None = None
    attempt_plan: NpcAttemptPlan | None = None
    action_plan: NpcIntentActionPlan | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "stage": self.stage.value,
            "proposal": self.proposal.model_dump(mode="json") if self.proposal is not None else {},
        }
        if self.challenge is not None:
            payload["challenge_id"] = self.challenge.id
            payload["challenge_name"] = self.challenge.name
        if self.option is not None:
            payload["option"] = _challenge_option_payload(self.option)
        if self.participant_actor_ids:
            payload["participant_actor_ids"] = list(self.participant_actor_ids)
        if self.resources:
            payload["resources"] = [_resource_payload(resource) for resource in self.resources]
        if self.point is not None:
            payload["point_id"] = self.point.id
            payload["point_name"] = self.point.name
        if self.check_plan is not None:
            payload["check_plan"] = self.check_plan.as_payload()
        if self.social_plan is not None:
            payload["social_plan"] = self.social_plan.as_payload()
        if self.attempt_plan is not None:
            payload["attempt_plan"] = self.attempt_plan.as_payload()
        if self.action_plan is not None:
            payload["npc_action_plan"] = self.action_plan.as_payload()
        if self.hazard is not None:
            payload["hazard"] = self.hazard.as_payload()
            payload["hazard_actor_id"] = self.hazard_actor_id
        if self.trap is not None:
            check = (
                self.trap.disarm_check
                if self.trap_action == ExplorationTrapAction.DISARM
                else self.trap.bypass_check
                if self.trap_action == ExplorationTrapAction.BYPASS
                else None
            )
            payload["trap"] = {
                "id": self.trap.id,
                "name": self.trap.name,
                "description": self.trap.revealed_description,
                "action": self.trap_action.value if self.trap_action is not None else None,
                "ability": check.ability if check is not None else None,
                "skill": check.skill if check is not None else None,
                "tool": check.tool if check is not None else None,
                "dc": check.dc if check is not None else None,
                "required_item_id": self.trap.required_item_id,
            }
        if self.observation is not None:
            payload["observation"] = {
                "id": self.observation.id,
                "label": self.observation.label,
                "description": self.observation.description,
                "ability": self.observation.ability,
                "skill": self.observation.skill,
                "dc": self.observation.dc,
                "thresholds": [fact.minimum_total for fact in self.observation.facts],
            }
        if self.source_matches:
            property_labels = dict(self.source_property_labels)
            source_query = (
                self.proposal.source_query
                if isinstance(self.proposal, GmDeclarationAnalysis)
                else None
            )
            payload["source_selection"] = {
                "requested_name": source_query.requested_name if source_query is not None else None,
                "purpose": source_query.purpose if source_query is not None else "",
                "candidates": [
                    {
                        "id": match.source.id,
                        "label": match.source.label,
                        "quantity": match.source.quantity,
                        "condition": match.source.condition,
                        "properties": [
                            {
                                "id": property_id,
                                "label": property_labels.get(property_id, property_id),
                            }
                            for property_id in match.source.properties
                        ],
                        "matched_property_ids": list(match.matched_preferred_properties),
                        "portable": match.source.portable,
                        "detachable": match.source.detachable,
                        "kind": match.source.kind.value,
                    }
                    for match in self.source_matches
                ],
            }
        if self.use_source is not None:
            property_labels = dict(self.source_property_labels)
            payload["source_use"] = {
                "id": self.use_source.id,
                "label": self.use_source.label,
                "kind": self.use_source.kind.value,
                "quantity": self.use_source.quantity,
                "condition": self.use_source.condition,
                "properties": [
                    {
                        "id": property_id,
                        "label": property_labels.get(property_id, property_id),
                    }
                    for property_id in self.use_source.properties
                ],
                "portable": self.use_source.portable,
                "detachable": self.use_source.detachable,
                "remains_in_scene": self.use_source.kind.value
                in {"scene_item", "scene_fixture"},
            }
        if self.collection_plan is not None:
            property_labels = dict(self.source_property_labels)
            payload["collection"] = {
                **self.collection_plan.as_payload(),
                "properties": [
                    {
                        "id": property_id,
                        "label": property_labels.get(property_id, property_id),
                    }
                    for property_id in self.collection_plan.source.properties
                ],
            }
        if self.fixture_action_plan is not None:
            payload["fixture_action"] = self.fixture_action_plan.as_payload()
        if self.crafting_plan is not None:
            source_labels = dict(self.crafting_source_labels)
            payload["crafting"] = {
                "label": self.crafting_plan.draft.label,
                "description": self.crafting_plan.draft.description,
                "purpose_id": self.crafting_plan.purpose.id,
                "purpose_label": self.crafting_plan.purpose.label,
                "components": [
                    {
                        "source_id": component.source_id,
                        "label": source_labels.get(component.source_id, component.source_id),
                        "quantity": component.quantity,
                        "disposition": component.disposition.value,
                    }
                    for component in self.crafting_plan.component_uses
                ],
                "time_cost_minutes": self.crafting_plan.purpose.time_cost_minutes,
                "modifier": self.crafting_plan.purpose.modifier,
                "bonus_tags": list(self.crafting_plan.purpose.bonus_tags),
                "uses": self.crafting_plan.purpose.uses,
                "risk": self.crafting_plan.purpose.risk,
                "scope": self.crafting_plan.draft.scope.value,
                "auto_selected_components": self.crafting_plan.draft.auto_select_missing_components,
                "requires_build_roll": False,
            }
        if self.stage == PendingStage.BREAKAGE:
            payload["breakage"] = {
                "actor_id": self.breakage_actor_id,
                "item_id": self.breakage_item_id,
                "item_label": self.breakage_item_label,
                "chance_percent": self.breakage_chance_percent,
            }
        return payload


@dataclass(slots=True)
class EncounterSetupFlow:
    encounter: LoadedEncounter
    steps: tuple[SetupStep, ...]
    current_index: int = 0
    completed: bool = False
    player_start_actor_ids: tuple[str, ...] = ()
    player_start_assignments: dict[str, Coordinate] = field(default_factory=dict)

    @property
    def current_step(self) -> SetupStep | None:
        if self.completed or not self.steps:
            return None
        return self.steps[self.current_index]

    def as_payload(self) -> dict[str, object]:
        step = self.current_step
        current_start_actor = self.current_player_start_actor
        step_payload = _setup_step_payload(step) if step is not None else None
        if step_payload is not None and self.is_player_start_step:
            assigned_positions = set(self.player_start_assignments.values())
            step_payload["requires_board_assignment"] = True
            step_payload["assignment_actor_id"] = str(current_start_actor.id) if current_start_actor is not None else None
            step_payload["assignment_actor_name"] = current_start_actor.name if current_start_actor is not None else None
            step_payload["assigned_positions"] = [
                [position.col, position.row] for position in self.player_start_assignments.values()
            ]
            step_payload["available_positions"] = [
                [position.col, position.row] for position in step.positions if position not in assigned_positions
            ]
        return {
            "scenario_id": self.encounter.scenario_id,
            "scenario_name": self.encounter.scenario_name,
            "status": "completed" if self.completed else "active",
            "current_index": self.current_index,
            "step_count": len(self.steps),
            "current_step": step_payload,
        }

    @property
    def is_player_start_step(self) -> bool:
        step = self.current_step
        return step is not None and step.label == "pola startowe bohaterów"

    @property
    def current_player_start_actor(self) -> Actor | None:
        if not self.is_player_start_step:
            return None
        assigned = set(self.player_start_assignments)
        for actor_id in self.player_start_actor_ids:
            if actor_id in assigned:
                continue
            return next((actor for actor in self.encounter.actors if str(actor.id) == actor_id), None)
        return None

    def remaining_player_start_positions(self) -> tuple[Coordinate, ...]:
        step = self.current_step
        if step is None:
            return ()
        assigned = set(self.player_start_assignments.values())
        return tuple(position for position in step.positions if position not in assigned)


@dataclass(slots=True)
class ExplorationSetupFlow:
    steps: tuple[SetupStep, ...]
    current_index: int = 0
    completed: bool = False

    @property
    def current_step(self) -> SetupStep | None:
        if self.completed or not self.steps:
            return None
        return self.steps[self.current_index]

    def as_payload(self) -> dict[str, object]:
        step = self.current_step
        return {
            "status": "completed" if self.completed else "active",
            "current_index": self.current_index,
            "step_count": len(self.steps),
            "current_step": _setup_step_payload(step) if step is not None else None,
        }


@dataclass(slots=True)
class EncounterInitiativeFlow:
    encounter: LoadedEncounter
    prompts: tuple[InitiativePrompt, ...]
    entries: list[InitiativeEntry]
    current_prompt_index: int = 0
    completed: bool = False
    order: InitiativeOrder | None = None
    edges_by_actor_id: dict[str, EncounterEdge] = field(default_factory=dict)

    @property
    def current_prompt(self) -> InitiativePrompt | None:
        if self.completed or self.current_prompt_index >= len(self.prompts):
            return None
        return self.prompts[self.current_prompt_index]

    def as_payload(self) -> dict[str, object]:
        prompt = self.current_prompt
        return {
            "scenario_id": self.encounter.scenario_id,
            "scenario_name": self.encounter.scenario_name,
            "status": "completed" if self.completed else "active",
            "current_prompt_index": self.current_prompt_index,
            "prompt_count": len(self.prompts),
            "current_prompt": (
                _initiative_prompt_payload(prompt, self.edges_by_actor_id.get(str(prompt.actor.id)))
                if prompt is not None
                else None
            ),
            "entries": [_initiative_entry_payload(entry) for entry in self.entries],
            "order": [_initiative_entry_payload(entry) for entry in self.order.entries] if self.order is not None else [],
        }


@dataclass(frozen=True, slots=True)
class BoardScanTarget:
    positions: tuple[Coordinate, ...]
    feedback: LedFeedback
    empty_message: str


@dataclass(frozen=True, slots=True)
class PendingCombatHelp:
    helper_id: str
    ally_ids: tuple[str, ...]
    target_ids: tuple[str, ...]

    def as_payload(self, state: CombatState, active_effects: tuple[ActiveCombatEffect, ...]) -> dict[str, object]:
        return {
            "helper": _combat_actor_payload(_actor_by_string_id_from_state(state, self.helper_id), active_effects),
            "allies": [
                _combat_actor_payload(actor, active_effects)
                for actor in state.actors
                if str(actor.id) in self.ally_ids
            ],
            "targets": [
                _combat_actor_payload(actor, active_effects)
                for actor in state.actors
                if str(actor.id) in self.target_ids
            ],
        }


@dataclass(frozen=True, slots=True)
class PendingCombatReady:
    actor_id: str
    triggers: tuple[str, ...] = ("enemy_moves", "enemy_attacks")

    def as_payload(self, state: CombatState, active_effects: tuple[ActiveCombatEffect, ...]) -> dict[str, object]:
        return {
            "actor": _combat_actor_payload(_actor_by_string_id_from_state(state, self.actor_id), active_effects),
            "triggers": [{"id": trigger, "label": _ready_trigger_label(trigger)} for trigger in self.triggers],
        }


@dataclass(frozen=True, slots=True)
class PendingOpportunityMovement:
    actor_id: str
    destination: Coordinate
    path: PathResult
    threat_actor_ids: tuple[str, ...]

    def as_payload(self, state: CombatState, active_effects: tuple[ActiveCombatEffect, ...]) -> dict[str, object]:
        threats = [
            _combat_actor_payload(actor, active_effects)
            for actor in state.actors
            if str(actor.id) in self.threat_actor_ids
        ]
        return {
            "actor_id": self.actor_id,
            "destination": [self.destination.col, self.destination.row],
            "path": [[position.col, position.row] for position in self.path.path],
            "cost_feet": self.path.cost_feet,
            "threats": threats,
        }


@dataclass(frozen=True, slots=True)
class PendingApproachPickup:
    actor_id: str
    dropped_weapon_id: str
    destination: Coordinate


@dataclass(frozen=True, slots=True)
class PendingEnemyOpportunityAttack:
    target_id: str
    threat_actor_ids: tuple[str, ...]
    current_index: int = 0
    stage: str = "choice"
    natural_roll: int | None = None
    natural_rolls: tuple[int, ...] = ()
    total: int | None = None
    hit: bool | None = None
    critical: bool = False

    @property
    def attacker_id(self) -> str:
        return self.threat_actor_ids[self.current_index]


@dataclass(frozen=True, slots=True)
class PendingReadyAttack:
    readied_actor_id: str
    target_id: str
    effect_id: str
    trigger: str
    stage: str = "choice"
    natural_roll: int | None = None
    natural_rolls: tuple[int, ...] = ()
    total: int | None = None
    hit: bool | None = None
    critical: bool = False


class ExplorationUiSession:
    def __init__(
        self,
        scenario_path: str | Path,
        *,
        gm_client: object | None = None,
        npc_client: object | None = None,
        debug_point_id: str | None = None,
        debug_challenge_id: str | None = None,
        session_id: str | None = None,
        observation_dir: str | Path = "data/session_observations",
        save_dir: str | Path = "data/saves",
    ) -> None:
        self.scenario_path = Path(scenario_path)
        self.gm_client = gm_client
        self.npc_client = npc_client
        self.debug_point_id = debug_point_id or ""
        self.debug_challenge_id = debug_challenge_id or ""
        if self.debug_point_id and self.debug_challenge_id:
            raise ValueError("Wybierz debug point albo debug challenge, nie oba jednocześnie.")
        self._fixed_session_id = session_id
        self.observation_dir = Path(observation_dir)
        self.save_dir = Path(save_dir)
        self.observer = SessionObserver(session_id or _ui_session_id(), self.observation_dir)
        self.combat_movement_flow = CombatMovementFlowService()
        self.combat_reaction_flow = CombatReactionFlowService()
        self.combat_scene_interaction_flow = CombatSceneInteractionFlowService()
        self.combat_turn_action_flow = CombatTurnActionFlowService()
        self.combat_grapple_flow = CombatGrappleFlowService()
        self.combat_shove_flow = CombatShoveFlowService()
        self.combat_turn_finalization = CombatTurnFinalizationService()
        self.enemy_turn_flow = EnemyTurnFlowService()
        self.player_area_healing_flow = PlayerAreaHealingFlowService()
        self.player_combat_action_flow = PlayerCombatActionFlowService()
        self.player_combat_resource_flow = PlayerCombatResourceFlowService()
        self.player_reaction_flow = PlayerReactionFlowService()
        self.spell_preparation_flow = SpellPreparationFlowService()
        self.short_rest_flow = ShortRestFlowService()
        self.exploration_flow = ExplorationFlowService()
        self.exploration_interaction_flow = ExplorationInteractionFlowService()
        self.reset()

    def reset(self) -> None:
        if self._fixed_session_id is None:
            self.observer = SessionObserver(_ui_session_id(), self.observation_dir)
        self.exploration = build_exploration_from_scenario(load_scenario(self.scenario_path))
        long_rest_results = tuple(
            complete_long_rest(actor)
            for actor in self.exploration.actors
            if actor.faction == Faction.ALLY
        )
        rested_actors = {result.actor_after.id: result.actor_after for result in long_rest_results}
        rested_actor_values = tuple(
            rested_actors.get(actor.id, actor) for actor in self.exploration.actors
        )
        long_rest_triggers = resolve_actor_trigger_events(
            rested_actor_values,
            (
                EffectEvent(EffectEventType.LONG_REST_COMPLETED, actor_id=str(actor.id))
                for actor in rested_actor_values
                if actor.faction == Faction.ALLY
            ),
        )
        self.exploration = replace(
            self.exploration,
            actors=long_rest_triggers.actors,
        )
        self.state = ExplorationState(
            self.exploration.zones,
            self.exploration.points,
            self.exploration.party_position,
            SceneFlags(),
            challenges=self.exploration.challenges,
            resources=self.exploration.resources,
            inventory_resource_ids=self.exploration.initial_resource_ids,
            traps=self.exploration.traps,
        )
        if self.debug_point_id:
            self.state, _revealed = reveal_exploration_points(self.state, (self.debug_point_id,))
        if self.debug_challenge_id:
            debug_challenge = next(
                (
                    challenge
                    for challenge in self.state.challenges
                    if challenge.id == self.debug_challenge_id
                ),
                None,
            )
            if debug_challenge is None:
                raise ValueError(f"Unknown exploration challenge: {self.debug_challenge_id}.")
            self.state = replace(
                self.state,
                party_position=PartyPosition(debug_challenge.zone_id),
            )
        self.messages: list[UiMessage] = []
        self.conversation_entries: list[InteractionConversationEntry] = []
        self.pending_state = UiPendingState()
        self.declaration_thread: list[GmDeclarationThreadEntry] = []
        self.active_preparation_effects: list[GmPreparationEffect] = []
        self.selected_lead_actor_id = str(self.exploration.actors[0].id)
        self.selected_helper_actor_id: str | None = None
        self.active_point_id = self.debug_point_id
        self.exploration_board_selection_active = False
        self.exploration_setup_flow: ExplorationSetupFlow | None = None
        self.exploration_setup_is_initial = False
        self.post_interaction_setup_steps: tuple[SetupStep, ...] = ()
        self.selected_combat_movement_path = None
        self.encounter_setup_flow: EncounterSetupFlow | None = None
        self.encounter_initiative_flow: EncounterInitiativeFlow | None = None
        self.combat_state: CombatState | None = None
        self.resolved_encounter_trigger_ids: set[str] = set()
        self.selected_attack_source_ids: dict[str, str] = {}
        self.combat_targeting_attack_source_id: str | None = None
        self.selected_healing_source_ids: dict[str, str] = {}
        self.active_combat_effects: tuple[ActiveCombatEffect, ...] = ()
        self.encounter_rng = random.Random(7)
        board_defaults = _load_board_defaults()
        self.board_backend = "none"
        self.configured_board_backend = board_defaults["backend"]
        self.board_url = board_defaults["board_url"]
        self.board_serial_port = board_defaults["serial_port"]
        self.wled_url = board_defaults["wled_url"]
        self.scan_timeout_s = 30.0
        self.board_adapter: BoardSessionAdapter | None = None
        self.board_message = (
            "Plansza niepodłączona. Domyślne ustawienia wczytane z board/config.json "
            f"({self.configured_board_backend})."
        )
        if self.debug_point_id or self.debug_challenge_id:
            self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        else:
            self.ui_flow_stage = UiFlowStage.WAITING_FOR_BOARD
        self.preview_zone_id = ""
        self.interaction_result: dict[str, object] | None = None
        self._record(
            "ui_session_started",
            {
                "scenario_path": str(self.scenario_path),
                "scenario_id": self.exploration.scenario_id,
                "scenario_name": self.exploration.scenario_name,
                "debug_point_id": self.debug_point_id,
                "debug_challenge_id": self.debug_challenge_id,
                "initial_zone_id": self.state.party_position.zone_id,
                "initial_resource_ids": list(self.state.inventory_resource_ids),
                "automatic_long_rest": [
                    {
                        "actor_id": str(result.actor_after.id),
                        "hp_recovered": result.hp_recovered,
                        "hit_dice_recovered": result.hit_dice_recovered,
                        "recovered_resource_ids": list(result.recovered_resource_ids),
                    }
                    for result in long_rest_results
                ],
            },
        )
        self._record(
            "ui_automatic_long_rest_completed",
            {
                "actor_ids": [str(result.actor_after.id) for result in long_rest_results],
                "next_stage": self.ui_flow_stage.value,
            },
        )
        self._add_message(
            "Długi odpoczynek ukończony",
            "Drużyna rozpoczyna scenariusz po long reście. Odnowiono HP, sloty i zasoby; teraz można przygotować czary.",
        )
        self._add_trigger_activation_notices(long_rest_triggers.activations)

    @property
    def pending(self) -> PendingInteraction | None:
        return self.pending_state.interaction

    @pending.setter
    def pending(self, value: PendingInteraction | None) -> None:
        self.pending_state.interaction = value

    @property
    def pending_encounter(self) -> PendingEncounter | None:
        return self.pending_state.encounter

    @pending_encounter.setter
    def pending_encounter(self, value: PendingEncounter | None) -> None:
        self.pending_state.encounter = value

    @property
    def pending_npc_transition(self) -> NpcTransitionPlan | None:
        return self.pending_state.npc_transition

    @pending_npc_transition.setter
    def pending_npc_transition(self, value: NpcTransitionPlan | None) -> None:
        self.pending_state.npc_transition = value

    @property
    def pending_enemy_turn_intent(self) -> EnemyTurnPlan | None:
        return self.pending_state.enemy_turn_intent

    @pending_enemy_turn_intent.setter
    def pending_enemy_turn_intent(self, value: EnemyTurnPlan | None) -> None:
        self.pending_state.enemy_turn_intent = value

    @property
    def pending_enemy_turn_result(self) -> EnemyAutoTurnResult | None:
        return self.pending_state.enemy_turn_result

    @pending_enemy_turn_result.setter
    def pending_enemy_turn_result(self, value: EnemyAutoTurnResult | None) -> None:
        self.pending_state.enemy_turn_result = value

    @property
    def pending_enemy_turn_ack_result(self) -> EnemyAutoTurnResult | None:
        return self.pending_state.enemy_turn_ack_result

    @pending_enemy_turn_ack_result.setter
    def pending_enemy_turn_ack_result(self, value: EnemyAutoTurnResult | None) -> None:
        self.pending_state.enemy_turn_ack_result = value

    @property
    def pending_enemy_saving_throw(self) -> PendingEnemySavingThrow | None:
        return self.pending_state.enemy_saving_throw

    @pending_enemy_saving_throw.setter
    def pending_enemy_saving_throw(self, value: PendingEnemySavingThrow | None) -> None:
        self.pending_state.enemy_saving_throw = value

    @property
    def pending_player_attack(self) -> PendingPlayerAttack | None:
        return self.pending_state.player_attack

    @pending_player_attack.setter
    def pending_player_attack(self, value: PendingPlayerAttack | None) -> None:
        self.pending_state.player_attack = value

    @property
    def pending_player_healing(self) -> PendingPlayerHealing | None:
        return self.pending_state.player_healing

    @pending_player_healing.setter
    def pending_player_healing(self, value: PendingPlayerHealing | None) -> None:
        self.pending_state.player_healing = value

    @property
    def pending_area_spell(self) -> PendingAreaSpell | None:
        return self.pending_state.area_spell

    @pending_area_spell.setter
    def pending_area_spell(self, value: PendingAreaSpell | None) -> None:
        self.pending_state.area_spell = value

    @property
    def pending_combat_interaction(self) -> PendingCombatInteraction | None:
        return self.pending_state.combat_interaction

    @pending_combat_interaction.setter
    def pending_combat_interaction(self, value: PendingCombatInteraction | None) -> None:
        self.pending_state.combat_interaction = value

    @property
    def pending_combat_context_menu(self) -> CombatContextMenu | None:
        return self.pending_state.combat_context_menu

    @pending_combat_context_menu.setter
    def pending_combat_context_menu(self, value: CombatContextMenu | None) -> None:
        self.pending_state.combat_context_menu = value

    @property
    def pending_approach_interaction(self) -> CombatApproachInteractionPlan | None:
        return self.pending_state.approach_interaction

    @pending_approach_interaction.setter
    def pending_approach_interaction(self, value: CombatApproachInteractionPlan | None) -> None:
        self.pending_state.approach_interaction = value

    @property
    def pending_approach_pickup(self) -> PendingApproachPickup | None:
        return self.pending_state.approach_pickup

    @pending_approach_pickup.setter
    def pending_approach_pickup(self, value: PendingApproachPickup | None) -> None:
        self.pending_state.approach_pickup = value

    @property
    def pending_combat_help(self) -> PendingCombatHelp | None:
        return self.pending_state.combat_help

    @pending_combat_help.setter
    def pending_combat_help(self, value: PendingCombatHelp | None) -> None:
        self.pending_state.combat_help = value

    @property
    def pending_combat_skill_check(self) -> PendingCombatSkillCheck | None:
        return self.pending_state.combat_skill_check

    @pending_combat_skill_check.setter
    def pending_combat_skill_check(self, value: PendingCombatSkillCheck | None) -> None:
        self.pending_state.combat_skill_check = value

    @property
    def pending_combat_shove(self) -> PendingShove | None:
        return self.pending_state.combat_shove

    @pending_combat_shove.setter
    def pending_combat_shove(self, value: PendingShove | None) -> None:
        self.pending_state.combat_shove = value

    @property
    def pending_combat_grapple(self) -> PendingGrapple | None:
        return self.pending_state.combat_grapple

    @pending_combat_grapple.setter
    def pending_combat_grapple(self, value: PendingGrapple | None) -> None:
        self.pending_state.combat_grapple = value

    @property
    def pending_concentration_action(self) -> PendingConcentrationAction | None:
        return self.pending_state.concentration_action

    @pending_concentration_action.setter
    def pending_concentration_action(self, value: PendingConcentrationAction | None) -> None:
        self.pending_state.concentration_action = value

    @property
    def pending_concentration_check(self) -> PendingConcentrationCheck | None:
        return self.pending_state.concentration_check

    @pending_concentration_check.setter
    def pending_concentration_check(self, value: PendingConcentrationCheck | None) -> None:
        self.pending_state.concentration_check = value

    @property
    def pending_combat_ready(self) -> PendingCombatReady | None:
        return self.pending_state.combat_ready

    @pending_combat_ready.setter
    def pending_combat_ready(self, value: PendingCombatReady | None) -> None:
        self.pending_state.combat_ready = value

    @property
    def pending_opportunity_movement(self) -> PendingOpportunityMovement | None:
        return self.pending_state.opportunity_movement

    @pending_opportunity_movement.setter
    def pending_opportunity_movement(self, value: PendingOpportunityMovement | None) -> None:
        self.pending_state.opportunity_movement = value

    @property
    def pending_enemy_opportunity_attack(self) -> PendingEnemyOpportunityAttack | None:
        return self.pending_state.enemy_opportunity_attack

    @pending_enemy_opportunity_attack.setter
    def pending_enemy_opportunity_attack(self, value: PendingEnemyOpportunityAttack | None) -> None:
        self.pending_state.enemy_opportunity_attack = value

    @property
    def pending_ready_attack(self) -> PendingReadyAttack | None:
        return self.pending_state.ready_attack

    @pending_ready_attack.setter
    def pending_ready_attack(self, value: PendingReadyAttack | None) -> None:
        self.pending_state.ready_attack = value

    @property
    def pending_short_rest(self) -> PendingShortRest | None:
        return self.pending_state.short_rest

    @pending_short_rest.setter
    def pending_short_rest(self, value: PendingShortRest | None) -> None:
        self.pending_state.short_rest = value

    @property
    def current_zone(self) -> ExplorationZone:
        return next(zone for zone in self.state.zones if zone.id == self.state.party_position.zone_id)

    @property
    def active_point(self) -> ExplorationPoint | None:
        if not self.active_point_id:
            return None
        return next((point for point in self.state.points if point.id == self.active_point_id), None)

    def state_payload(self) -> dict[str, object]:
        if self.ui_flow_stage not in {
            UiFlowStage.SHORT_REST,
            UiFlowStage.SCENARIO_COMPLETE,
        }:
            if self.pending_npc_transition is None:
                self._refresh_pending_encounter()
        self._expire_invalid_combat_effects()
        active_challenge = self.active_challenge if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else None
        current_zone_points = self.current_zone_points() if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else ()
        scene_status = _scene_status_payload(self.state)
        scene_status.append({"label": "Czas scenariusza", "value": _duration_minutes_label(self.state.elapsed_minutes)})
        fixture_names = {
            (zone.id, fixture.id): fixture.name
            for zone in self.state.zones
            for fixture in zone.fixtures
        }
        for fixture_state in self.state.fixture_states:
            scene_status.append(
                {
                    "label": fixture_names.get(
                        (fixture_state.zone_id, fixture_state.fixture_id),
                        fixture_state.fixture_id,
                    ),
                    "value": fixture_state.condition,
                }
            )
        actor_names = {str(actor.id): actor.name for actor in self.exploration.actors}
        for condition in self.state.condition_states:
            condition_label = (
                "Powalony"
                if condition.condition == CombatCondition.PRONE
                else condition.condition.value
            )
            scene_status.append(
                {
                    "label": f"Stan: {actor_names.get(condition.actor_id, condition.actor_id)}",
                    "value": condition_label,
                }
            )
        trap_status_labels = {
            ExplorationTrapStatus.REVEALED: "wykryta — aktywna",
            ExplorationTrapStatus.DISARMED: "rozbrojona",
            ExplorationTrapStatus.BYPASSED: "bezpiecznie ominięta",
            ExplorationTrapStatus.TRIGGERED: "uruchomiona",
        }
        for trap in self.state.traps:
            trap_state = trap_state_for(self.state, trap.id)
            if trap_state.status == ExplorationTrapStatus.HIDDEN:
                continue
            scene_status.append(
                {
                    "label": f"Pułapka: {trap.name}",
                    "value": trap_status_labels[trap_state.status],
                }
            )
        for edge in self.state.encounter_edges:
            if edge.consumed:
                continue
            scene_status.append(
                {
                    "label": "Przewaga na inicjatywę",
                    "value": f"{actor_names.get(edge.beneficiary_actor_id, edge.beneficiary_actor_id)} — {edge.label}",
                }
            )
        if self.pending_encounter is not None:
            scene_status.append({"label": "Encounter", "value": self.pending_encounter.name})
        preview_zone = self._preview_zone()
        collected_source_ids = {item.source_id for item in self.state.source_collections}
        return UiSessionView(
            scenario={"id": self.exploration.scenario_id, "name": self.exploration.scenario_name},
            session_log={
                "session_id": self.observer.session_id,
                "path": str(self.observer.path),
            },
            snapshot=self._snapshot_payload(),
            flow={
                "stage": self.ui_flow_stage.value,
                "can_start": self.ui_flow_stage == UiFlowStage.READY_TO_START,
                "preview_zone": _zone_payload(preview_zone, self._scenario_asset_root(), self.state) if preview_zone else None,
                "available_locations": [_zone_payload(zone, self._scenario_asset_root(), self.state) for zone in self._scene_location_zones()],
                "interaction_result": self.interaction_result,
            },
            spell_preparation=self._spell_preparation_payload(),
            short_rest=self._short_rest_payload(),
            current_zone=_zone_payload(self.current_zone, self._scenario_asset_root()),
            available_zones=[_zone_payload(zone, self._scenario_asset_root()) for zone in visible_exploration_zones(self.state.zones) if zone_is_ui_available(self.state, zone)],
            visible_environment=[_environment_entry_payload(entry) for entry in self.exploration.environment if entry.visibility == SetupVisibility.VISIBLE],
            travel_options=[_zone_payload(zone, self._scenario_asset_root()) for zone in self.travel_options()],
            visible_points=[_point_payload(point, _npc_state_for_point(self.state, point), self.state.flags) for point in visible_exploration_points(self.state.points)],
            current_zone_points=[_point_payload(point, _npc_state_for_point(self.state, point), self.state.flags) for point in current_zone_points],
            active_challenge=(
                _challenge_payload(
                    self.state,
                    active_challenge,
                    self.exploration.actors,
                    self.exploration.flows,
                    self.exploration_interaction_flow,
                )
                if active_challenge
                else None
            ),
            active_point=(
                _point_payload(self.active_point, _npc_state_for_point(self.state, self.active_point), self.state.flags)
                if self.active_point
                else None
            ),
            resources=[
                *[_resource_payload(resource) for resource in self.state.resources if resource.id in self.state.inventory_resource_ids],
                *[
                    _temporary_item_payload(item)
                    for item in self.state.temporary_items
                    if item.available
                    and f"temporary:{item.id}" not in collected_source_ids
                ],
            ],
            discovered_sources=self._discovered_sources_payload(),
            actors=[
                _exploration_actor_payload(actor, self.state.condition_states)
                for actor in self.exploration.actors
            ],
            active_effects=[effect.as_payload() for effect in self.active_combat_effects],
            scene_status=scene_status,
            flags=[{"key": key, "value": value} for key, value in self.state.flags.values],
            messages=[message.as_payload() for message in self.messages],
            conversation=self._conversation_payload(),
            pending=self.pending.as_payload() if self.pending else None,
            pending_npc_transition=(
                self.pending_npc_transition.as_payload()
                if self.pending_npc_transition is not None
                else None
            ),
            selected_lead_actor_id=self.selected_lead_actor_id,
            selected_helper_actor_id=self.selected_helper_actor_id,
            allowed_mechanics=[tool.as_payload() for tool in MECHANIC_TOOLS.values()],
            pending_encounter=self._pending_encounter_payload(),
            exploration_setup=self.exploration_setup_flow.as_payload() if self.exploration_setup_flow else None,
            encounter_setup=self.encounter_setup_flow.as_payload() if self.encounter_setup_flow else None,
            encounter_stealth=self._precombat_stealth_payload(),
            encounter_initiative=(
                self.encounter_initiative_flow.as_payload() if self.encounter_initiative_flow else None
            ),
            combat=_combat_payload(
                self.combat_state,
                self._active_encounter(),
                self.selected_combat_movement_path,
                self.pending_enemy_turn_intent,
                self.pending_enemy_turn_result,
                self.pending_enemy_turn_ack_result,
                self.pending_enemy_saving_throw,
                self.pending_player_attack,
                self.pending_player_healing,
                self.pending_area_spell,
                self.pending_combat_context_menu,
                self.pending_combat_interaction,
                self.pending_combat_help,
                self.pending_combat_skill_check,
                self.pending_combat_shove,
                self.pending_combat_grapple,
                self.pending_concentration_action,
                self.pending_concentration_check,
                self.pending_combat_ready,
                self.pending_opportunity_movement,
                self.pending_enemy_opportunity_attack,
                self.pending_ready_attack,
                self.active_combat_effects,
                self.selected_attack_source_ids,
                self.selected_healing_source_ids,
                self.combat_targeting_attack_source_id,
            )
            if self.combat_state
            else None,
            board=self._board_payload(),
            required_rolls=self.required_rolls_payload(),
        ).as_payload()

    def _discovered_sources_payload(self) -> list[dict[str, object]]:
        registry = build_crafting_source_registry(self.state, self.exploration.actors)
        property_label = self.exploration.crafting_policy.property_label
        collections_by_source: dict[str, list[SceneSourceCollection]] = {}
        for collection in self.state.source_collections:
            collections_by_source.setdefault(collection.source_id, []).append(collection)
        result: list[dict[str, object]] = []
        for discovery in self.state.source_discoveries:
            if discovery.zone_id != self.current_zone.id:
                continue
            source = registry.source_by_id(discovery.source_id)
            if source is None:
                continue
            collections = collections_by_source.get(source.id, [])
            result.append(
                {
                    "id": source.id,
                    "label": source.label,
                    "kind": source.kind.value,
                    "quantity": source.quantity,
                    "condition": source.condition,
                    "properties": [
                        {"id": item, "label": property_label(item)}
                        for item in source.properties
                    ],
                    "matched_properties": [
                        {"id": item, "label": property_label(item)}
                        for item in discovery.matched_properties
                    ],
                    "purpose": discovery.purpose,
                    "requested_as": discovery.requested_as,
                    "semantic_substitution": discovery.semantic_substitution,
                    "available": source.usable,
                    "portable": source.portable,
                    "inventory": False,
                    "collections": [
                        {
                            "quantity": item.quantity,
                            "destination": item.destination,
                            "owner_actor_id": item.owner_actor_id,
                        }
                        for item in collections
                    ],
                }
            )
        return result

    @property
    def snapshot_path(self) -> Path:
        return self.save_dir / f"{self.exploration.scenario_id}.snapshot.json"

    def create_snapshot(self) -> SessionSnapshot:
        blocker = self._snapshot_blocker()
        if blocker is not None:
            raise ValueError(blocker)
        return SessionSnapshot(
            scenario_id=self.exploration.scenario_id,
            ui_stage=self.ui_flow_stage.value,
            actors=self.exploration.actors,
            exploration_state=self.state,
            active_effects=self.active_combat_effects,
            pending_encounter=self.pending_encounter,
            pending_npc_transition=(
                self.pending_npc_transition.pending
                if self.pending_npc_transition is not None
                else None
            ),
            combat_state=self.combat_state,
            resolved_encounter_trigger_ids=tuple(sorted(self.resolved_encounter_trigger_ids)),
            selected_attack_source_ids=tuple(sorted(self.selected_attack_source_ids.items())),
            selected_healing_source_ids=tuple(sorted(self.selected_healing_source_ids.items())),
            selected_lead_actor_id=self.selected_lead_actor_id,
            selected_helper_actor_id=self.selected_helper_actor_id,
            active_point_id=self.active_point_id,
            preview_zone_id=self.preview_zone_id,
            interaction_result=self.interaction_result,
            conversation_entries=tuple(self.conversation_entries),
        )

    def save_snapshot(self) -> dict[str, object]:
        snapshot = self.create_snapshot()
        write_snapshot(self.snapshot_path, snapshot)
        self._record(
            "ui_snapshot_saved",
            {"path": str(self.snapshot_path), "schema_version": SNAPSHOT_SCHEMA_VERSION},
        )
        self._add_message("Gra zapisana", f"Zapisano stan scenariusza w wersji {SNAPSHOT_SCHEMA_VERSION}.")
        return self.state_payload()

    def load_snapshot(self) -> dict[str, object]:
        base_exploration = build_exploration_from_scenario(load_scenario(self.scenario_path))
        base_state = ExplorationState(
            base_exploration.zones,
            base_exploration.points,
            base_exploration.party_position,
            SceneFlags(),
            challenges=base_exploration.challenges,
            resources=base_exploration.resources,
            inventory_resource_ids=base_exploration.initial_resource_ids,
            traps=base_exploration.traps,
        )
        snapshot = read_snapshot(self.snapshot_path, base_state=base_state)
        if snapshot.scenario_id != base_exploration.scenario_id:
            raise ValueError(
                f"Zapis dotyczy scenariusza {snapshot.scenario_id}, a nie {base_exploration.scenario_id}."
            )
        expected_actor_ids = {str(actor.id) for actor in base_exploration.actors}
        restored_actor_ids = {str(actor.id) for actor in snapshot.actors}
        if expected_actor_ids != restored_actor_ids:
            raise ValueError("Lista bohaterów zapisu nie odpowiada aktualnej wersji scenariusza.")
        stage = UiFlowStage(snapshot.ui_stage)
        known_trigger_by_id = {trigger.id: trigger for trigger in base_exploration.encounter_triggers}
        if set(snapshot.resolved_encounter_trigger_ids) - set(known_trigger_by_id):
            raise ValueError("Zapis zawiera nieznany trigger rozstrzygniętego encountera.")
        if snapshot.pending_encounter is not None:
            trigger = known_trigger_by_id.get(snapshot.pending_encounter.trigger_id)
            if trigger is None or trigger.encounter_scenario != snapshot.pending_encounter.encounter_scenario:
                raise ValueError("Oczekujący encounter nie odpowiada aktualnej wersji scenariusza.")
        point_ids = {point.id for point in base_exploration.points}
        zone_ids = {zone.id for zone in base_exploration.zones}
        if snapshot.active_point_id and snapshot.active_point_id not in point_ids:
            raise ValueError("Zapis odwołuje się do nieznanego aktywnego punktu.")
        if snapshot.preview_zone_id and snapshot.preview_zone_id not in zone_ids:
            raise ValueError("Zapis odwołuje się do nieznanej lokacji podglądu.")
        selection_actor_ids = restored_actor_ids | (
            {str(actor.id) for actor in snapshot.combat_state.actors} if snapshot.combat_state is not None else set()
        )
        selected_actor_ids = {
            snapshot.selected_lead_actor_id,
            snapshot.selected_helper_actor_id or "",
            *(actor_id for actor_id, _source_id in snapshot.selected_attack_source_ids),
            *(actor_id for actor_id, _source_id in snapshot.selected_healing_source_ids),
        } - {""}
        if selected_actor_ids - selection_actor_ids:
            raise ValueError("Zapis zawiera wybór dla nieznanego aktora.")
        effect_actor_ids = {
            actor_id
            for effect in snapshot.active_effects
            for actor_id in (effect.actor_id, effect.source_actor_id, effect.target_actor_id)
            if actor_id
        }
        if effect_actor_ids - selection_actor_ids:
            raise ValueError("Aktywny efekt zapisu odwołuje się do nieznanego aktora.")
        exploration_condition_actor_ids = {
            condition.actor_id for condition in snapshot.exploration_state.condition_states
        }
        if exploration_condition_actor_ids - restored_actor_ids:
            raise ValueError("Stan eksploracyjny zapisu odwołuje się do nieznanego aktora.")
        restored_initiative_flow = None
        if snapshot.combat_state is not None:
            if snapshot.pending_encounter is None:
                raise ValueError("Zapis aktywnej walki nie zawiera identyfikatora encountera.")
            encounter = build_encounter_from_scenario(load_scenario(snapshot.pending_encounter.encounter_scenario))
            combat_by_id = {actor.id: actor for actor in snapshot.combat_state.actors}
            encounter = replace(
                encounter,
                actors=tuple(combat_by_id.get(actor.id, actor) for actor in encounter.actors),
            )
            combat_ids = {str(actor.id) for actor in snapshot.combat_state.actors}
            encounter_ids = {str(actor.id) for actor in encounter.actors}
            if combat_ids != encounter_ids:
                raise ValueError("Lista aktorów walki nie odpowiada aktualnej wersji encountera.")
            restored_initiative_flow = EncounterInitiativeFlow(
                encounter=encounter,
                prompts=(),
                entries=list(snapshot.combat_state.initiative_order.entries),
                completed=True,
                order=snapshot.combat_state.initiative_order,
            )
        self.exploration = replace(base_exploration, actors=snapshot.actors)
        self.state = snapshot.exploration_state
        self.active_combat_effects = snapshot.active_effects
        self.combat_state = snapshot.combat_state
        self.resolved_encounter_trigger_ids = set(snapshot.resolved_encounter_trigger_ids)
        self.selected_attack_source_ids = dict(snapshot.selected_attack_source_ids)
        self.selected_healing_source_ids = dict(snapshot.selected_healing_source_ids)
        self.selected_lead_actor_id = snapshot.selected_lead_actor_id
        self.selected_helper_actor_id = snapshot.selected_helper_actor_id
        self.active_point_id = snapshot.active_point_id
        self.preview_zone_id = snapshot.preview_zone_id
        self.interaction_result = dict(snapshot.interaction_result) if snapshot.interaction_result is not None else None
        self.ui_flow_stage = stage
        restored_npc_transition = (
            restore_npc_transition_plan(base_exploration.npc_transitions, snapshot.pending_npc_transition)
            if snapshot.pending_npc_transition is not None
            else None
        )
        self.pending_state = UiPendingState(
            encounter=snapshot.pending_encounter,
            npc_transition=restored_npc_transition,
        )
        self.declaration_thread = []
        self.active_preparation_effects = []
        self.exploration_setup_flow = None
        self.post_interaction_setup_steps = ()
        self.selected_combat_movement_path = None
        self.encounter_setup_flow = None
        self.encounter_initiative_flow = restored_initiative_flow
        self.messages = []
        self.conversation_entries = list(snapshot.conversation_entries)
        self._record(
            "ui_snapshot_loaded",
            {"path": str(self.snapshot_path), "schema_version": SNAPSHOT_SCHEMA_VERSION},
        )
        self._add_message("Gra wczytana", "Przywrócono zapisany stan scenariusza.")
        self.board_message = "Przywrócono zapis gry. Stan planszy zsynchronizowano z sesją."
        self._sync_board_leds()
        return self.state_payload()

    def _snapshot_blocker(self) -> str | None:
        pending_fields = tuple(
            item.name
            for item in fields(self.pending_state)
            if item.name not in {"encounter", "npc_transition"}
            and getattr(self.pending_state, item.name) is not None
        )
        if pending_fields:
            return "Najpierw dokończ albo anuluj rozpoczęty wybór, rzut lub odpoczynek."
        if self.active_preparation_effects:
            return "Najpierw rozstrzygnij aktywne przygotowanie do testu."
        if self.selected_combat_movement_path is not None:
            return "Najpierw potwierdź albo anuluj podgląd ruchu."
        if self.exploration_setup_flow is not None and not self.exploration_setup_flow.completed:
            return "Najpierw zakończ setup eksploracji."
        if self.encounter_setup_flow is not None and self.combat_state is None:
            return "Najpierw zakończ setup i inicjatywę encountera."
        if self.encounter_initiative_flow is not None and self.combat_state is None:
            return "Najpierw zakończ inicjatywę encountera."
        return None

    def _snapshot_payload(self) -> dict[str, object]:
        blocker = self._snapshot_blocker()
        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "path": str(self.snapshot_path),
            "exists": self.snapshot_path.exists(),
            "can_save": blocker is None,
            "blocker": blocker,
        }

    def configure_board(
        self,
        *,
        backend: str,
        board_url: str = "",
        board_serial_port: str = "",
        wled_url: str = "",
        scan_timeout_s: float | None = None,
    ) -> dict[str, object]:
        backend = str(backend or "none").strip().lower()
        if backend not in {"none", "simulator", "hardware"}:
            raise ValueError("Backend planszy musi mieć wartość none, simulator albo hardware.")
        self.board_backend = backend
        self.board_url = board_url.strip() or self.board_url
        self.board_serial_port = board_serial_port.strip()
        self.wled_url = wled_url.strip()
        if scan_timeout_s is not None:
            self.scan_timeout_s = max(0.1, float(scan_timeout_s))
        if backend == "none":
            self.board_adapter = None
            self.board_message = "Plansza niepodłączona."
            if (
                not self.debug_point_id
                and not self.debug_challenge_id
                and self.ui_flow_stage != UiFlowStage.SPELL_PREPARATION
            ):
                self.ui_flow_stage = UiFlowStage.WAITING_FOR_BOARD
            self._record("ui_board_configured", {"backend": backend, "connected": False})
            return self.state_payload()
        self.board_adapter = BoardSessionAdapter.connect(
            backend=backend,
            board_url=self.board_url,
            serial_port=self.board_serial_port,
            wled_url=self.wled_url,
        )
        self.board_message = f"Plansza podłączona: {backend}."
        if self.ui_flow_stage == UiFlowStage.WAITING_FOR_BOARD:
            self.ui_flow_stage = UiFlowStage.READY_TO_START
        self._sync_board_leds()
        self._record(
            "ui_board_configured",
            {
                "backend": backend,
                "connected": True,
                "board_url": self.board_url,
                "serial_port": self.board_serial_port,
                "wled_url": self.wled_url,
            },
        )
        return self.state_payload()

    def attach_board_connection(self, connection: object, *, backend: str = "simulator") -> None:
        self.board_backend = backend
        self.board_adapter = BoardSessionAdapter(connection)
        self.board_message = f"Plansza podłączona: {backend}."
        if backend in {"simulator", "hardware"} and self.ui_flow_stage == UiFlowStage.WAITING_FOR_BOARD:
            self.ui_flow_stage = UiFlowStage.READY_TO_START

    def confirm_spell_preparation(
        self,
        *,
        actor_id: str,
        spell_ids: tuple[str, ...],
    ) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.SPELL_PREPARATION:
            raise ValueError("Przygotowanie czarów nie jest teraz aktywne.")
        transition = self.spell_preparation_flow.confirm(
            actors=self.exploration.actors,
            actor_id=actor_id,
            spell_ids=spell_ids,
        )
        self.exploration = replace(self.exploration, actors=transition.actors)
        actor = next(candidate for candidate in transition.actors if str(candidate.id) == actor_id)
        self._record(
            "ui_spell_preparation_confirmed",
            {
                "actor_id": actor_id,
                "prepared_spell_ids": list(transition.prepared_spell_ids),
                "complete": transition.complete,
            },
        )
        self._add_message(
            "Przygotowanie czarów",
            f"{actor.name} potwierdza przygotowane czary.",
        )
        if transition.complete:
            self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
            self.preview_zone_id = ""
            self.board_message = "Przygotowanie zakończone. Wybierz pierwszą lokację na planszy."
        self._sync_board_leds()
        return self.state_payload()

    def start_short_rest(self) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE:
            raise ValueError("Krótki odpoczynek można rozpocząć tylko podczas eksploracji.")
        if self.pending is not None or self.active_point is not None:
            raise ValueError("Najpierw zakończ aktywną interakcję.")
        self._refresh_pending_encounter()
        pending = self.short_rest_flow.start(
            state=self.state,
            zone=self.current_zone,
            encounter_pending=self.pending_encounter is not None,
        )
        self.pending_short_rest = pending
        self.ui_flow_stage = UiFlowStage.SHORT_REST
        self.board_message = "Podgląd krótkiego odpoczynku. Potwierdź koszt i ryzyko."
        self._record(
            "ui_short_rest_started",
            {
                "policy_id": pending.policy.id,
                "zone_id": pending.zone_id,
                "duration_minutes": pending.policy.duration_minutes,
                "safety": pending.policy.safety.value,
            },
        )
        return self.state_payload()

    def confirm_short_rest(self) -> dict[str, object]:
        pending = self.pending_short_rest
        if self.ui_flow_stage != UiFlowStage.SHORT_REST or pending is None:
            raise ValueError("Brak krótkiego odpoczynku do potwierdzenia.")
        transition = self.short_rest_flow.complete(
            state=self.state,
            actors=self.exploration.actors,
            pending=pending,
            active_effects=self.active_combat_effects,
        )
        self.state = transition.state
        self.exploration = replace(self.exploration, actors=transition.actors)
        self.pending_short_rest = transition.pending
        self.active_combat_effects = transition.active_effects
        self._add_trigger_activation_notices(transition.trigger_activations)
        for effect, raw_effect in zip(transition.effects, pending.policy.completion_effects, strict=True):
            self._record_effect_result(
                effect,
                source="short_rest_completion",
                raw_effect=raw_effect,
            )
        recovered = {
            str(result.actor_after.id): list(result.recovered_resource_ids)
            for result in transition.rest_results
            if result.recovered_resource_ids
        }
        self._record(
            "ui_short_rest_completed",
            {
                "policy_id": pending.policy.id,
                "zone_id": pending.zone_id,
                "elapsed_minutes": self.state.elapsed_minutes,
                "recovered_resources": recovered,
                "effect_types": [effect.effect_type for effect in transition.effects],
                "expired_effect_ids": [effect.id for effect in transition.expired_effects],
            },
        )
        self._add_message(
            "Krótki odpoczynek ukończony",
            "Minęła godzina. Gracze mogą teraz wydawać Hit Dice pojedynczo.",
        )
        self.board_message = "Odpoczynek ukończony. Wydaj Hit Dice albo zakończ odpoczynek."
        return self.state_payload()

    def finish_scenario(self) -> dict[str, object]:
        if self.combat_state is not None:
            raise ValueError("Najpierw zakończ aktywną walkę.")
        if self.pending_short_rest is not None or self.pending is not None:
            raise ValueError("Najpierw zakończ aktywną decyzję albo odpoczynek.")
        if self.ui_flow_stage == UiFlowStage.SCENARIO_COMPLETE:
            return self.state_payload()
        if self.ui_flow_stage not in {
            UiFlowStage.LOCATION_ACTIVE,
            UiFlowStage.INTERACTION_RESULT,
        }:
            raise ValueError("Scenariusz można zakończyć dopiero podczas aktywnej eksploracji.")
        expiration = expire_active_effects(
            self.active_combat_effects,
            EffectEvent(EffectEventType.SCENARIO_ENDED),
        )
        self.active_combat_effects = expiration.active_effects
        self.active_preparation_effects.clear()
        expired_temporary_items = tuple(item.id for item in self.state.temporary_items if item.available)
        self.state = replace(self.state, temporary_items=())
        self.pending_encounter = None
        self.ui_flow_stage = UiFlowStage.SCENARIO_COMPLETE
        self.board_message = "Scenariusz zakończony. Efekty dzienne wygasły."
        self._record(
            "ui_scenario_completed",
            {
                "elapsed_minutes": self.state.elapsed_minutes,
                "expired_effect_ids": [effect.id for effect in expiration.expired_effects],
                "expired_temporary_item_ids": list(expired_temporary_items),
            },
        )
        self._add_message(
            "Scenariusz zakończony",
            "Efekty trwające do końca scenariusza wygasły. Reset rozpocznie kolejny scenariusz automatycznym long restem.",
        )
        self._sync_board_leds()
        return self.state_payload()

    def spend_short_rest_hit_die(
        self,
        *,
        actor_id: str,
        die_sides: int,
        natural_roll: int,
    ) -> dict[str, object]:
        pending = self.pending_short_rest
        if (
            self.ui_flow_stage != UiFlowStage.SHORT_REST
            or pending is None
            or not pending.completed
        ):
            raise ValueError("Hit Dice można wydawać dopiero po ukończeniu short resta.")
        transition = self.short_rest_flow.spend_hit_die(
            actors=self.exploration.actors,
            actor_id=actor_id,
            die_sides=die_sides,
            natural_roll=natural_roll,
        )
        self.exploration = replace(self.exploration, actors=transition.actors)
        result = transition.result
        self._record(
            "ui_short_rest_hit_die_spent",
            {
                "actor_id": actor_id,
                "die_sides": die_sides,
                "natural_roll": natural_roll,
                "constitution_modifier": result.constitution_modifier,
                "effective_healing": result.effective_healing,
            },
        )
        self._add_message(
            "Wydana Hit Die",
            (
                f"{result.actor_after.name}: d{die_sides} {natural_roll}, "
                f"CON {_format_signed(result.constitution_modifier)}, "
                f"odzyskano {result.effective_healing} HP."
            ),
        )
        return self.state_payload()

    def cancel_short_rest(self) -> dict[str, object]:
        pending = self.pending_short_rest
        if self.ui_flow_stage != UiFlowStage.SHORT_REST or pending is None:
            raise ValueError("Brak krótkiego odpoczynku do anulowania.")
        if pending.completed:
            raise ValueError("Ukończonego odpoczynku nie można anulować.")
        self.pending_short_rest = None
        self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        self.board_message = "Krótki odpoczynek anulowany bez upływu czasu."
        self._record("ui_short_rest_cancelled", {"policy_id": pending.policy.id})
        return self.state_payload()

    def finish_short_rest(self) -> dict[str, object]:
        pending = self.pending_short_rest
        if (
            self.ui_flow_stage != UiFlowStage.SHORT_REST
            or pending is None
            or not pending.completed
        ):
            raise ValueError("Najpierw ukończ krótki odpoczynek.")
        self.pending_short_rest = None
        self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        self.board_message = "Krótki odpoczynek zakończony. Drużyna wraca do eksploracji."
        self._record("ui_short_rest_finished", {"policy_id": pending.policy.id})
        return self.state_payload()

    def start_session(self) -> dict[str, object]:
        setup_steps = _build_exploration_setup_steps(self.exploration.environment)
        transition = self.exploration_flow.start_session(
            board_connected=self.board_adapter is not None,
            board_backend=self.board_backend,
            current_stage=self.ui_flow_stage,
            setup_steps=setup_steps,
            spell_preparation_pending=bool(
                self.spell_preparation_flow.pending_actors(self.exploration.actors)
            ),
        )
        if transition is None:
            return self.state_payload()
        self.exploration_setup_flow = (
            ExplorationSetupFlow(transition.setup_steps) if transition.setup_steps else None
        )
        self.exploration_setup_is_initial = bool(transition.setup_steps)
        self.ui_flow_stage = transition.stage
        self.board_message = transition.board_message
        self.preview_zone_id = ""
        self.pending = None
        self.active_point_id = ""
        self._sync_board_leds()
        self._record("ui_play_session_started", {"stage": self.ui_flow_stage.value, "board_backend": self.board_backend})
        return self.state_payload()

    def finish_interaction_result(self) -> dict[str, object]:
        transition = self.exploration_flow.finish_interaction(
            current_stage=self.ui_flow_stage,
            post_interaction_setup_steps=self.post_interaction_setup_steps,
        )
        if transition is None:
            return self.state_payload()
        self.interaction_result = None
        self.preview_zone_id = ""
        self.exploration_setup_flow = (
            ExplorationSetupFlow(transition.setup_steps) if transition.setup_steps else None
        )
        self.exploration_setup_is_initial = False
        self.post_interaction_setup_steps = ()
        self.ui_flow_stage = transition.stage
        self.exploration_board_selection_active = False
        self.board_message = transition.board_message
        self._sync_board_leds()
        return self.state_payload()

    def cancel_location_preview(self) -> dict[str, object]:
        transition = self.exploration_flow.cancel_location_preview(current_stage=self.ui_flow_stage)
        if transition is None:
            return self.state_payload()
        self.preview_zone_id = transition.preview_zone_id
        self.board_message = transition.board_message
        self._sync_board_leds()
        return self.state_payload()

    def confirm_location_preview(self) -> dict[str, object]:
        transition = self.exploration_flow.confirm_location_preview(
            current_stage=self.ui_flow_stage,
            state=self.state,
            current_zone=self.current_zone,
            preview_zone=self._preview_zone(),
            active_point_id=self.active_point_id,
        )
        if transition is None:
            return self.state_payload()
        self.state = transition.state
        self.ui_flow_stage = transition.stage
        self.preview_zone_id = transition.preview_zone_id
        self.active_point_id = transition.active_point_id
        self.exploration_board_selection_active = False
        self.board_message = transition.board_message
        if transition.event_type:
            self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def confirm_exploration_setup_step(self) -> dict[str, object]:
        if self.exploration_setup_flow is None:
            return self.state_payload()
        flow = self.exploration_setup_flow
        transition = self.exploration_flow.advance_setup_step(
            steps=flow.steps,
            current_index=flow.current_index,
            spell_preparation_pending=bool(
                self.exploration_setup_is_initial
                and self.spell_preparation_flow.pending_actors(self.exploration.actors)
            ),
        )
        if transition is None:
            return self.state_payload()
        self._add_message("Setup mapy", f"Potwierdzono: {transition.confirmed_label}.")
        if transition.completed:
            flow.completed = True
            self.exploration_setup_flow = None
            self.exploration_setup_is_initial = False
            self.ui_flow_stage = transition.stage
            self.preview_zone_id = ""
            self.board_message = transition.board_message
            self._refresh_pending_encounter()
            if self.pending_encounter is not None:
                trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
                self.board_message = (
                    "Encounter gotowy. Rozstrzygnij rozpoczęcie starcia w UI albo Enterem."
                    if trigger is not None and trigger.opening_policy is not None
                    else "Encounter gotowy. Potwierdź rozpoczęcie setupu w UI albo Enterem."
                )
        else:
            flow.current_index = transition.current_index
            self.ui_flow_stage = transition.stage
            self.board_message = transition.board_message
        self._sync_board_leds()
        return self.state_payload()

    def scan_board_selection(self) -> dict[str, object]:
        if self.board_adapter is None:
            raise ValueError("Najpierw podłącz backend planszy.")
        target = self._current_board_scan_target()
        if not target.positions:
            raise ValueError(target.empty_message)
        self.board_adapter.show_scan_feedback(target.feedback)
        try:
            selected_raw = self.board_adapter.scan(
                target.positions,
                timeout_s=self.scan_timeout_s,
            )
        finally:
            self.board_adapter.restore_feedback(target.feedback)
        if selected_raw is None:
            self.board_message = "Nie wybrano pola na planszy."
            self._record("ui_board_scan_timeout", {"stage": self.ui_flow_stage.value})
            return self.state_payload()
        selected = _coordinate_from_scan(selected_raw)
        self._record("ui_board_scan_received", {"stage": self.ui_flow_stage.value, "position": [selected.col, selected.row]})
        return self._handle_board_position(selected)

    def set_exploration_board_selection(self, enabled: bool) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE or self.combat_state is not None:
            raise ValueError("Wybór elementów eksploracji nie jest teraz dostępny.")
        self.exploration_board_selection_active = bool(enabled)
        self.board_message = (
            "Wybór z planszy aktywny. Uruchom skan i kliknij podświetloną lokację albo punkt."
            if self.exploration_board_selection_active
            else "Interakcja aktywna. Plansza nie czeka teraz na kliknięcie."
        )
        self._sync_board_leds()
        return self.state_payload()

    def select_board_position(self, selected: Coordinate) -> dict[str, object]:
        target = self._current_board_scan_target()
        if target.positions and selected not in target.positions:
            raise ValueError("Wybrane pole nie jest teraz aktywnym polem planszy.")
        self._record("ui_board_position_selected", {"stage": self.ui_flow_stage.value, "position": [selected.col, selected.row]})
        return self._handle_board_position(selected)

    def submit_action(
        self,
        text: str,
        *,
        selected_goal_id: str | None = None,
        selected_check_participants: str | None = None,
        participant_actor_ids: tuple[str, ...] = (),
        conversation_only: bool = False,
        infer_flow_route: bool = False,
    ) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE:
            raise ValueError("Najpierw rozpocznij sesję i potwierdź wejście do lokacji na planszy.")
        raw_text = text.strip()
        if not raw_text:
            raise ValueError("Deklaracja nie może być pusta.")
        parsed_input = parse_player_input(raw_text)
        if conversation_only and (
            selected_goal_id is not None
            or selected_check_participants is not None
            or participant_actor_ids
            or infer_flow_route
        ):
            raise ValueError("Swobodna wiadomość do MG nie może jednocześnie deklarować akcji.")
        point = self.active_point
        available_goals = (
            point.npc_interaction.goals
            if point is not None and point.npc_interaction is not None
            else self.active_challenge.goals
            if self.active_challenge is not None
            else ()
        )
        selected_goal_route = (
            self.exploration_interaction_flow.route_for_goal(
                challenge=self.active_challenge,
                flows=self.exploration.flows,
                goal_id=selected_goal_id,
                flags=self.state.flags,
            )
            if self.active_challenge is not None
            and (point is None or point.npc_interaction is None)
            else None
        )
        if self.active_challenge is not None and (
            point is None or point.npc_interaction is None
        ):
            selected_goal = (
                selected_goal_route.goal
                if selected_goal_route is not None
                else None
            )
        else:
            selected_goal = interaction_goal(
                available_goals,
                selected_goal_id,
                self.state.flags,
            )
        if selected_goal_id and selected_goal is None:
            raise ValueError("Wybrany cel nie jest dostępny w tej interakcji.")
        selected_participant_ids: tuple[str, ...] = ()
        resolved_check_participants: CheckParticipants | None = None
        if (
            self.active_challenge is not None
            and selected_goal is not None
            and (point is None or point.npc_interaction is None)
        ):
            resolved_check_participants = _resolve_goal_check_participants(
                selected_goal,
                selected_check_participants,
            )
            selected_participant_ids = _validate_goal_participants(
                selected_goal,
                self.active_challenge,
                self.exploration.actors,
                participant_actor_ids,
                check_participants=resolved_check_participants,
                resolution_option_id=(
                    selected_goal_route.resolution_option_id
                    if selected_goal_route is not None
                    else None
                ),
            )
        elif participant_actor_ids and not infer_flow_route:
            raise ValueError("Postacie można wskazać dopiero po wybraniu celu wyzwania.")
        elif infer_flow_route and selected_check_participants is not None:
            resolved_check_participants = CheckParticipants(selected_check_participants)
        self._record(
            "ui_action_submitted",
            {
                "text": raw_text,
                "slash_command": parsed_input.command.name if parsed_input.command is not None else None,
                "intent_hint": (
                    PlayerIntentHint.QUESTION.value
                    if conversation_only
                    else parsed_input.intent_hint.value
                    if parsed_input.intent_hint is not None
                    else None
                ),
                "conversation_only": conversation_only,
                "zone_id": self.current_zone.id,
                "active_point_id": self.active_point.id if self.active_point else None,
                "active_challenge_id": self.active_challenge.id if self.active_challenge else None,
                "selected_goal_id": selected_goal.id if selected_goal is not None else None,
                "flow_transition_id": (
                    selected_goal_route.transition.id
                    if selected_goal_route is not None
                    and selected_goal_route.transition is not None
                    else None
                ),
                "flow_route_kind": (
                    selected_goal_route.route_kind.value
                    if selected_goal_route is not None
                    else None
                ),
                "participant_actor_ids": list(
                    participant_actor_ids
                    if infer_flow_route
                    else selected_participant_ids
                ),
                "check_participants": (
                    resolved_check_participants.value
                    if resolved_check_participants is not None
                    else None
                ),
            },
        )
        self._add_message("Gracze", raw_text)
        if parsed_input.intent_hint == PlayerIntentHint.HELP:
            self._add_message("Dostępne komendy", slash_help_message())
            return self.state_payload()
        action_text = parsed_input.content
        if parsed_input.intent_hint == PlayerIntentHint.TAKE:
            return self._submit_collection_action(action_text, player_display_text=raw_text)
        if point is not None and point.npc_interaction is not None:
            return self._submit_npc_action(
                point,
                action_text,
                selected_goal_id=selected_goal.id if selected_goal is not None else None,
                conversation_only=conversation_only,
            )
        referenced_point = self._referenced_current_zone_point(action_text)
        if referenced_point is not None:
            positions = ", ".join(f"({position.col},{position.row})" for position in referenced_point.positions)
            self._add_message(
                "Punkt eksploracji",
                (
                    f"{referenced_point.name} jest osobnym punktem interakcji. "
                    f"Najpierw przestaw pionek drużyny na podświetlone na {led_color_name_pl(referenced_point.color)} "
                    f"pole {positions}, żeby wejść w interakcję z tym punktem."
                ),
            )
            return self.state_payload()
        challenge = self.active_challenge
        if challenge is None:
            raise ValueError("W aktualnej lokacji nie ma aktywnego wyzwania ani punktu NPC.")
        trap_action = match_revealed_trap_action(
            self.state,
            action_text,
            zone_id=self.current_zone.id,
        )
        if trap_action is not None:
            trap, action = trap_action
            return self._submit_trap_action(trap, action)
        return self._submit_challenge_action(
            challenge,
            action_text,
            player_intent_hint=(
                PlayerIntentHint.QUESTION
                if conversation_only
                else parsed_input.intent_hint
            ),
            player_display_text=raw_text,
            selected_goal_id=selected_goal.id if selected_goal is not None else None,
            selected_check_participants=resolved_check_participants,
            participant_actor_ids=(
                participant_actor_ids if infer_flow_route else selected_participant_ids
            ),
            conversation_only=conversation_only,
            infer_flow_route=infer_flow_route,
        )

    def _submit_trap_action(
        self,
        trap: ExplorationTrap,
        action: ExplorationTrapAction,
    ) -> dict[str, object]:
        if trap_state_for(self.state, trap.id).status != ExplorationTrapStatus.REVEALED:
            raise ValueError("Najpierw trzeba wykryć pułapkę.")
        if action == ExplorationTrapAction.DISARM and trap.required_item_id is not None:
            owner = next(
                (
                    actor
                    for actor in self.exploration.actors
                    if any(
                        item.id == trap.required_item_id and item.available
                        for item in actor.inventory
                    )
                ),
                None,
            )
            if owner is not None:
                self.selected_lead_actor_id = str(owner.id)
        action_label = {
            ExplorationTrapAction.DISARM: "rozbroić",
            ExplorationTrapAction.BYPASS: "bezpiecznie ominąć",
            ExplorationTrapAction.TRIGGER: "celowo uruchomić",
        }[action]
        self.pending = PendingInteraction(
            kind=PendingKind.TRAP,
            stage=PendingStage.DECISION,
            challenge=self.active_challenge,
            trap=trap,
            trap_action=action,
        )
        self._add_message(
            "Pułapka",
            f"Chcecie {action_label} pułapkę: {trap.name}. Potwierdźcie sposób działania.",
        )
        self._record(
            "ui_exploration_trap_action_proposed",
            {"trap_id": trap.id, "action": action.value},
        )
        return self.state_payload()

    def _submit_collection_action(
        self,
        text: str,
        *,
        player_display_text: str,
    ) -> dict[str, object]:
        registry = build_crafting_source_registry(self.state, self.exploration.actors)
        allowed_kinds = frozenset(
            {
                CraftingSourceKind.SCENE_ITEM,
                CraftingSourceKind.SCENE_FIXTURE,
                CraftingSourceKind.TEMPORARY_ITEM,
            }
        )
        direct_matches = match_available_sources(
            registry,
            text,
            allowed_kinds=allowed_kinds,
        )
        candidates = tuple(match.source for match in direct_matches)
        if not candidates:
            discovered = tuple(
                source
                for discovery in self.state.source_discoveries
                if discovery.zone_id == self.current_zone.id
                for source in (registry.source_by_id(discovery.source_id),)
                if source is not None and source.usable and source.kind in allowed_kinds
            )
            if len(discovered) == 1:
                candidates = discovered
            elif discovered:
                return self._reject_collection(
                    player_display_text,
                    "Nie wiadomo, który znaleziony element chcecie zabrać. Wskażcie jego nazwę po /weź.",
                )
        if not candidates:
            return self._reject_collection(
                player_display_text,
                "Nie rozpoznano istniejącego elementu do zabrania. Najpierw znajdźcie go przez /szukaj albo podajcie dokładną nazwę.",
            )
        if len(candidates) > 1:
            labels = ", ".join(source.label for source in candidates)
            return self._reject_collection(
                player_display_text,
                f"Deklaracja wskazuje kilka elementów: {labels}. Przez /weź zabierajcie jeden rodzaj elementu naraz.",
            )
        source = candidates[0]
        owner = next(
            (
                actor
                for actor in self.exploration.actors
                if str(actor.id) == self.selected_lead_actor_id and actor.faction == Faction.ALLY
            ),
            next((actor for actor in self.exploration.actors if actor.faction == Faction.ALLY), None),
        )
        try:
            plan = plan_source_collection(
                source,
                quantity=1,
                owner_actor_id=str(owner.id) if owner is not None else None,
            )
        except ValueError as exc:
            return self._reject_collection(player_display_text, str(exc))
        self.pending = PendingInteraction(
            kind=PendingKind.COLLECTION,
            stage=PendingStage.DECISION,
            collection_plan=plan,
            source_property_labels=self.exploration.crafting_policy.property_labels,
        )
        destination = {
            "actor_inventory": f"ekwipunek postaci {owner.name}" if owner is not None else "ekwipunek postaci",
            "party_treasure": "wspólne łupy drużyny",
            "scenario_quest": "zasoby fabularne scenariusza",
        }[plan.destination.value]
        self._add_message(
            "MG proponuje zabranie",
            f"Chcecie zabrać {source.label} z lokacji {self.current_zone.name} i przenieść do: {destination}.",
        )
        self._record(
            "ui_collection_proposed",
            {
                "source_id": source.id,
                "quantity": 1,
                "destination": plan.destination.value,
                "owner_actor_id": plan.owner_actor_id,
            },
        )
        return self.state_payload()

    def _reject_collection(self, player_text: str, reason: str) -> dict[str, object]:
        self._remember_scene_exchange(player_text, reason, outcome="collection_rejected")
        self._add_message("Nie można zabrać elementu", reason)
        self._record("ui_collection_rejected", {"player_text": player_text, "reason": reason})
        return self.state_payload()

    def _referenced_current_zone_point(self, text: str) -> ExplorationPoint | None:
        normalized = text.lower()
        for point in self.current_zone_points():
            point_words = [word for word in point.name.lower().replace("-", " ").split() if len(word) >= 4]
            if any(word in normalized for word in point_words):
                return point
            if point.npc_interaction is not None and "zwiadow" in normalized and "zwiadow" in point.name.lower():
                return point
        return None

    @property
    def active_challenge(self) -> ExplorationChallenge | None:
        challenge = challenge_for_zone(self.state, self.current_zone.id)
        if challenge is None:
            return None
        if challenge_state_for(self.state, challenge.id).completed:
            return None
        return challenge

    def travel_options(self) -> tuple[ExplorationZone, ...]:
        available_by_id = {zone.id: zone for zone in available_exploration_zones(self.state)}
        return tuple(
            available_by_id[zone_id]
            for zone_id in self.current_zone.adjacent_zone_ids
            if zone_id in available_by_id and zone_id != self.current_zone.id
        )

    def _preview_zone(self) -> ExplorationZone | None:
        if not self.preview_zone_id:
            return None
        return next((zone for zone in self._scene_location_zones() if zone.id == self.preview_zone_id), None)

    def _scenario_asset_root(self) -> Path:
        if self.scenario_path.is_dir():
            return self.scenario_path
        sibling = self.scenario_path.with_suffix("")
        if sibling.is_dir():
            return sibling
        return self.scenario_path.parent

    def _game_asset_root(self) -> Path:
        return Path(__file__).resolve().parents[3] / "assets"

    def travel_to(self, zone_id: str) -> dict[str, object]:
        transition = self.exploration_flow.travel(
            state=self.state,
            current_zone=self.current_zone,
            travel_options=self.travel_options(),
            zone_id=zone_id,
        )
        self.state = transition.state
        self.pending = None
        self.active_point_id = transition.active_point_id
        self.preview_zone_id = transition.preview_zone_id
        self.interaction_result = None
        self.ui_flow_stage = transition.stage
        self.exploration_board_selection_active = False
        if transition.message_title:
            self._add_message(transition.message_title, transition.message_body)
        if transition.event_type:
            self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def start_encounter_setup(self) -> dict[str, object]:
        self._refresh_pending_encounter()
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera do przygotowania.")
        trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
        if (
            trigger is not None
            and trigger.opening_policy is not None
            and self.pending_encounter.opening_resolution is None
        ):
            raise ValueError("Najpierw rozstrzygnij rozpoczęcie starcia.")
        encounter = build_encounter_from_scenario(load_scenario(self.pending_encounter.encounter_scenario))
        encounter = _encounter_with_session_spell_state(encounter, self.exploration.actors)
        steps = _build_encounter_setup_steps(encounter)
        if not steps:
            raise ValueError("Scenariusz encountera nie ma elementów do setupu.")
        self.encounter_setup_flow = EncounterSetupFlow(
            encounter=encounter,
            steps=steps,
            player_start_actor_ids=tuple(str(actor.id) for actor in encounter.actors if actor.faction == Faction.ALLY),
        )
        self._add_message(
            "Setup przed walką",
            f"Rozpoczynam setup encountera: {encounter.scenario_name}. Potwierdzajcie kolejne grupy po rozstawieniu figurek.",
        )
        self._sync_board_leds()
        return self.state_payload()

    def resolve_encounter_opening(self) -> dict[str, object]:
        self._refresh_pending_encounter()
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera.")
        if self.pending_encounter.opening_resolution is not None:
            return self.state_payload()
        trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
        if trigger is None or trigger.opening_policy is None:
            raise ValueError("Ten encounter nie definiuje osobnego rozpoczęcia starcia.")
        resolution = resolve_encounter_opening(self.state, trigger.opening_policy)
        self.pending_encounter = replace(self.pending_encounter, opening_resolution=resolution)
        self._add_message(resolution.title, resolution.narration)
        self._record(
            "ui_encounter_opening_resolved",
            {
                "trigger_id": trigger.id,
                "rule_id": resolution.rule_id,
                "outcome": resolution.outcome.value,
                "noise": resolution.noise,
                "completion_tags": list(resolution.completion_tags),
            },
        )
        self.board_message = "Rozpoczęcie starcia rozstrzygnięte. Przejdź do setupu encountera."
        self._sync_board_leds()
        return self.state_payload()

    def resolve_active_combat(self) -> dict[str, object]:
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera do rozstrzygnięcia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została jeszcze rozpoczęta.")
        if self.combat_state.winner is None:
            raise ValueError("Walka nie ma jeszcze zwycięzcy.")
        trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
        if trigger is None:
            raise ValueError(f"Nieznany trigger encountera: {self.pending_encounter.trigger_id}.")
        if self.combat_state.winner == Faction.ALLY:
            outcome = trigger.outcome_on_victory or _default_encounter_victory_outcome(self.pending_encounter.name)
        else:
            outcome = trigger.outcome_on_defeat or _default_encounter_defeat_outcome(self.pending_encounter.name)
        visible_points_before = {point.id for point in visible_exploration_points(self.state.points)}
        effects = []
        for effect in outcome.effects:
            result = apply_exploration_effect(self.state, effect)
            self.state = result.state
            self._record_effect_result(result, source="encounter_outcome", raw_effect=effect)
            effects.append(result)
        visible_points_after = {point.id for point in visible_exploration_points(self.state.points)}
        revealed_point_ids = tuple(sorted(visible_points_after - visible_points_before))
        self.resolved_encounter_trigger_ids.add(trigger.id)
        self._record(
            "ui_encounter_resolved",
            {
                "trigger_id": trigger.id,
                "winner": self.combat_state.winner.value,
                "effect_types": [result.effect_type for result in effects],
                "revealed_point_ids": list(revealed_point_ids),
            },
        )
        self._add_message(outcome.title or "Wynik encountera", outcome.body or "Encounter został rozstrzygnięty.")
        self._apply_combat_trigger_events(
            tuple(
                EffectEvent(EffectEventType.ENCOUNTER_ENDED, actor_id=str(actor.id))
                for actor in self.combat_state.actors
            )
        )
        self.combat_state, self.active_combat_effects, expired_effects = expire_combat_effects(
            self.combat_state,
            self.active_combat_effects,
            EffectEvent(EffectEventType.ENCOUNTER_ENDED),
        )
        if expired_effects:
            self._record(
                "ui_effects_expired",
                {
                    "event": EffectEventType.ENCOUNTER_ENDED.value,
                    "effect_ids": [effect.id for effect in expired_effects],
                },
            )
            self._add_message(
                "Efekty encountera wygasły",
                ", ".join(effect.label for effect in expired_effects),
            )
        self.exploration = _exploration_with_combat_actor_state(
            self.exploration,
            self.combat_state.actors,
        )
        exploration_actor_ids = {str(actor.id) for actor in self.exploration.actors}
        encounter_actor_ids = {str(actor.id) for actor in self.combat_state.actors}
        preserved_conditions = tuple(
            condition
            for condition in self.state.condition_states
            if condition.actor_id not in encounter_actor_ids
        )
        combat_conditions = tuple(
            condition
            for condition in self.combat_state.condition_states
            if condition.actor_id in exploration_actor_ids
            and condition.condition == CombatCondition.PRONE
        )
        self.state = replace(
            self.state,
            condition_states=(*preserved_conditions, *combat_conditions),
        )
        self.interaction_result = {
            "title": outcome.title or "Wynik encountera",
            "body": outcome.body or "Encounter został rozstrzygnięty.",
            "unlocked_zones": [],
            "revealed_points": [_point_payload(point) for point in self.state.points if point.id in revealed_point_ids],
            "current_zone": _zone_payload(self.current_zone, self._scenario_asset_root()),
            "next_instruction": outcome.next_instruction or "Zakończ wynik, żeby wrócić do wyboru lokacji.",
        }
        self.pending_encounter = None
        self.encounter_setup_flow = None
        self.encounter_initiative_flow = None
        self.combat_state = None
        self.pending = None
        self.preview_zone_id = ""
        self.active_point_id = ""
        self.ui_flow_stage = UiFlowStage.INTERACTION_RESULT
        self.board_message = "Encounter rozstrzygnięty. Na planszy podświetlono nowe opcje sceny."
        self._sync_board_leds()
        return self.state_payload()

    def confirm_encounter_setup_step(self) -> dict[str, object]:
        if self.encounter_setup_flow is None:
            return self.start_encounter_setup()
        flow = self.encounter_setup_flow
        step = flow.current_step
        if step is None:
            return self.state_payload()
        if flow.is_player_start_step:
            actor = flow.current_player_start_actor
            actor_name = actor.name if actor is not None else "kolejnego bohatera"
            raise ValueError(f"Ten krok wymaga kliknięcia planszy: wybierz pole startowe dla {actor_name}.")
        self._add_message("Setup potwierdzony", f"Potwierdzono: {step.label}.")
        if flow.current_index + 1 >= len(flow.steps):
            flow.completed = True
            self._add_message(
                "Setup zakończony",
                "Figurki i jawne elementy encountera są rozstawione. Następny krok to ewentualne skradanie, inicjatywa i start walki.",
            )
        else:
            flow.current_index += 1
        self._sync_board_leds()
        return self.state_payload()

    def assign_encounter_player_start_position(self, selected: Coordinate) -> dict[str, object]:
        if self.encounter_setup_flow is None:
            raise ValueError("Setup encountera nie jest aktywny.")
        flow = self.encounter_setup_flow
        if not flow.is_player_start_step:
            raise ValueError("Aktualny krok setupu nie zbiera pól startowych bohaterów.")
        actor = flow.current_player_start_actor
        if actor is None:
            return self._advance_completed_player_start_step()
        remaining = flow.remaining_player_start_positions()
        if selected not in remaining:
            self.board_message = "Kliknij wolne, podświetlone pole startowe dla aktualnego bohatera."
            return self.state_payload()
        updated_actor = replace(actor, position=selected)
        updated_actors = tuple(updated_actor if candidate.id == actor.id else candidate for candidate in flow.encounter.actors)
        flow.encounter = replace(flow.encounter, actors=updated_actors)
        flow.player_start_assignments[str(actor.id)] = selected
        self.board_message = f"Ustawiono {actor.name} na polu {selected.as_tuple()}."
        self._add_message("Pole startowe", f"{actor.name}: {selected.as_tuple()}.")
        self._record(
            "ui_encounter_player_start_assigned",
            {"actor_id": str(actor.id), "position": [selected.col, selected.row]},
        )
        if flow.current_player_start_actor is None:
            return self._advance_completed_player_start_step()
        self._sync_board_leds()
        return self.state_payload()

    def _advance_completed_player_start_step(self) -> dict[str, object]:
        if self.encounter_setup_flow is None:
            return self.state_payload()
        flow = self.encounter_setup_flow
        self._add_message("Setup potwierdzony", "Pola startowe bohaterów zostały przypisane z planszy.")
        if flow.current_index + 1 >= len(flow.steps):
            flow.completed = True
            self._add_message(
                "Setup zakończony",
                "Figurki i jawne elementy encountera są rozstawione. Następny krok to ewentualne skradanie, inicjatywa i start walki.",
            )
        else:
            flow.current_index += 1
        self._sync_board_leds()
        return self.state_payload()

    def start_encounter_initiative(self) -> dict[str, object]:
        if self.encounter_setup_flow is None or not self.encounter_setup_flow.completed:
            raise ValueError("Najpierw zakończ setup encountera.")
        if self.combat_state is not None:
            return self.state_payload()
        encounter = self.encounter_setup_flow.encounter
        opening = self.pending_encounter.opening_resolution if self.pending_encounter is not None else None
        if (
            precombat_stealth_is_available(opening)
            and self.pending_encounter is not None
            and not self.pending_encounter.precombat_stealth_completed
        ):
            raise ValueError("Najpierw zakończ etap skradania przed walką albo świadomie go pomiń.")
        trigger_id = self.pending_encounter.trigger_id if self.pending_encounter is not None else ""
        applicable_edges = {
            edge.beneficiary_actor_id: edge
            for edge in available_encounter_edges(self.state, trigger_id)
            if edge.edge_type == EncounterEdgeType.INITIATIVE_ADVANTAGE
        }
        party_disadvantaged = bool(
            opening is not None
            and opening.outcome == EncounterOpeningOutcome.ENEMIES_SURPRISE_PARTY
        )
        roll_modes_by_actor_id = {
            str(actor.id): RollMode.DISADVANTAGE
            for actor in encounter.actors
            if party_disadvantaged and actor.faction == Faction.ALLY and not actor.is_defeated()
        }
        for actor_id in applicable_edges:
            roll_modes_by_actor_id[actor_id] = (
                RollMode.NORMAL
                if roll_modes_by_actor_id.get(actor_id) == RollMode.DISADVANTAGE
                else RollMode.ADVANTAGE
            )
        prompts = build_player_initiative_prompts(
            encounter.actors,
            roll_modes_by_actor_id,
        )
        self.encounter_initiative_flow = EncounterInitiativeFlow(
            encounter=encounter,
            prompts=prompts,
            entries=[],
            edges_by_actor_id=applicable_edges,
        )
        self._add_message(
            "Inicjatywa",
            "Rozpoczyna się walka. Bohaterowie wykonują test inicjatywy po kolei; przeciwnicy rzucają automatycznie."
            + (
                " Rozpoznanie daje wskazanemu bohaterowi przewagę w tym rzucie."
                if applicable_edges
                else ""
            ),
        )
        if not prompts:
            self._finish_encounter_initiative()
        self._sync_board_leds()
        return self.state_payload()

    def submit_encounter_initiative_roll(
        self,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> dict[str, object]:
        if self.encounter_initiative_flow is None:
            raise ValueError("Inicjatywa encountera nie została rozpoczęta.")
        flow = self.encounter_initiative_flow
        prompt = flow.current_prompt
        if prompt is None:
            return self.state_payload()
        if prompt.request.mode != RollMode.NORMAL and natural_roll_2 is None:
            raise ValueError("Przewaga albo utrudnienie w inicjatywie wymaga podania wyników obu kości d20.")
        roll = resolve_d20_roll(D20RollInput(prompt.request, natural_roll, natural_roll_2))
        entry = InitiativeEntry(
            actor=prompt.actor,
            roll=roll,
            dexterity_modifier=prompt.dexterity_modifier,
            stable_order=_actor_stable_order(flow.encounter, prompt.actor),
        )
        flow.entries.append(entry)
        edge = flow.edges_by_actor_id.get(str(prompt.actor.id))
        if edge is not None:
            self.state = consume_encounter_edge(self.state, edge.id)
            self._record(
                "ui_encounter_edge_consumed",
                {
                    "edge_id": edge.id,
                    "edge_type": edge.edge_type.value,
                    "actor_id": edge.beneficiary_actor_id,
                    "encounter_trigger_id": edge.encounter_trigger_id,
                },
            )
        self._add_message(
            "Rzut inicjatywy",
            f"{prompt.actor.name}: naturalny wynik {_d20_roll_result_text(roll)}, razem {roll.total}."
            + (f" Zużyto: {edge.label}." if edge is not None else ""),
        )
        flow.current_prompt_index += 1
        if flow.current_prompt is None:
            self._finish_encounter_initiative()
        self._sync_board_leds()
        return self.state_payload()

    def _finish_encounter_initiative(self) -> None:
        if self.encounter_initiative_flow is None or self.encounter_initiative_flow.completed:
            return
        flow = self.encounter_initiative_flow
        known_actor_ids = {entry.actor.id for entry in flow.entries}
        opening = self.pending_encounter.opening_resolution if self.pending_encounter is not None else None
        enemies_disadvantaged = bool(
            opening is not None
            and opening.outcome == EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES
        )
        for actor in flow.encounter.actors:
            if actor.id in known_actor_ids or actor.faction == Faction.ALLY or actor.is_defeated():
                continue
            enemy_mode = RollMode.DISADVANTAGE if enemies_disadvantaged else RollMode.NORMAL
            entry = replace(
                roll_enemy_initiative(actor, self.encounter_rng, enemy_mode),
                stable_order=_actor_stable_order(flow.encounter, actor),
            )
            flow.entries.append(entry)
            self._add_message(
                "Inicjatywa przeciwnika",
                f"{actor.name}: automatyczny wynik {_d20_roll_result_text(entry.roll)}, razem {entry.roll.total}."
                + (" Utrudnienie za zaskoczenie." if enemy_mode == RollMode.DISADVANTAGE else ""),
            )
        order = build_initiative_order(flow.entries)
        flow.order = order
        flow.completed = True
        hidden_states = hidden_states_from_precombat_attempts(
            self.pending_encounter.precombat_stealth_attempts if self.pending_encounter is not None else (),
            flow.encounter.actors,
        )
        self.combat_state = start_combat(
            flow.encounter.actors,
            order,
            hidden_states,
            self.state.condition_states,
        )
        order_text = ", ".join(entry.actor.name for entry in order.entries)
        self._add_message(
            "Kolejność inicjatywy",
            f"Kolejność została ustalona: {order_text}. Pierwsza tura: {order.current_actor.name}.",
        )
        self._sync_board_leds()

    def submit_precombat_stealth_roll(
        self,
        *,
        actor_id: str,
        natural_roll: int,
    ) -> dict[str, object]:
        if self.encounter_setup_flow is None or not self.encounter_setup_flow.completed:
            raise ValueError("Najpierw zakończ setup encountera.")
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera.")
        if self.encounter_initiative_flow is not None or self.combat_state is not None:
            raise ValueError("Etap skradania zakończył się wraz z rozpoczęciem inicjatywy.")
        if self.pending_encounter.precombat_stealth_completed:
            raise ValueError("Etap skradania przed walką został już zakończony.")
        if not precombat_stealth_is_available(self.pending_encounter.opening_resolution):
            raise ValueError("Okoliczności rozpoczęcia tego starcia nie pozwalają na skradanie przed walką.")

        resolution = resolve_precombat_stealth(
            self.encounter_setup_flow.encounter.actors,
            self.pending_encounter.precombat_stealth_attempts,
            actor_id=actor_id,
            natural_roll=natural_roll,
        )
        self.pending_encounter = replace(
            self.pending_encounter,
            precombat_stealth_attempts=(
                *self.pending_encounter.precombat_stealth_attempts,
                resolution.attempt,
            ),
        )
        actor = next(
            actor
            for actor in self.encounter_setup_flow.encounter.actors
            if str(actor.id) == actor_id
        )
        hidden_names = _actor_names_from_actors(
            self.encounter_setup_flow.encounter.actors,
            resolution.attempt.hidden_from_actor_ids,
        )
        detected_names = _actor_names_from_actors(
            self.encounter_setup_flow.encounter.actors,
            resolution.attempt.detected_by_actor_ids,
        )
        body = f"{actor.name}: wynik Stealth {resolution.attempt.total}."
        if hidden_names:
            body += f" Ukryty przed: {', '.join(hidden_names)}."
        if detected_names:
            body += f" Wykrywają: {', '.join(detected_names)}."
        self._add_message("Skradanie przed walką", body)
        self._record(
            "ui_precombat_stealth_resolved",
            {
                "actor_id": actor_id,
                "natural_roll": resolution.attempt.natural_roll,
                "total": resolution.attempt.total,
                "hidden_from_actor_ids": list(resolution.attempt.hidden_from_actor_ids),
                "detected_by_actor_ids": list(resolution.attempt.detected_by_actor_ids),
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def finish_precombat_stealth(self) -> dict[str, object]:
        if self.encounter_setup_flow is None or not self.encounter_setup_flow.completed:
            raise ValueError("Najpierw zakończ setup encountera.")
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera.")
        if not precombat_stealth_is_available(self.pending_encounter.opening_resolution):
            raise ValueError("Ten encounter nie ma etapu skradania przed walką.")
        self.pending_encounter = replace(
            self.pending_encounter,
            precombat_stealth_completed=True,
        )
        attempts = self.pending_encounter.precombat_stealth_attempts
        self._add_message(
            "Skradanie zakończone",
            (
                f"Zapisano próby skradania {len(attempts)} bohaterów. Możecie przejść do inicjatywy."
                if attempts
                else "Drużyna pomija skradanie i przechodzi do inicjatywy."
            ),
        )
        self._record(
            "ui_precombat_stealth_finished",
            {"attempted_actor_ids": [attempt.actor_id for attempt in attempts]},
        )
        self._sync_board_leds()
        return self.state_payload()

    def _clear_player_pending_choices(self) -> None:
        self.pending_state.clear_player_choices()

    def _attack_sources_for_actor(self, actor: Actor) -> tuple:
        encounter = self._active_encounter()
        if encounter is None:
            return ()
        reserved_hands = (
            len(grappled_actor_ids(self.combat_state.condition_states, str(actor.id)))
            if self.combat_state is not None
            else 0
        )
        return _encounter_attack_sources(
            encounter,
            actor,
            reserved_hands=reserved_hands,
        )

    def _selected_attack_source(self, actor: Actor):
        sources = self._attack_sources_for_actor(actor)
        if not sources:
            return None
        selected_id = self.selected_attack_source_ids.get(str(actor.id))
        if selected_id:
            selected = next((source for source in sources if source.id == selected_id), None)
            if selected is not None and self._actor_can_use_attack_source(actor, selected):
                return selected
        return next((source for source in sources if self._actor_can_use_attack_source(actor, source)), sources[0])

    def _attack_source_by_id(self, actor: Actor, source_id: str):
        sources = self._attack_sources_for_actor(actor)
        if source_id:
            source = next((candidate for candidate in sources if candidate.id == source_id), None)
            if source is not None:
                return source
        return self._selected_attack_source(actor)

    def _actor_can_use_attack_source(self, actor: Actor, source) -> bool:
        if source is None:
            return False
        if not _source_is_prepared(actor, source):
            return False
        source_item_id = getattr(source, "source_item_id", None)
        if source_item_id is not None:
            item = _inventory_item_for_attack_source(actor, source_item_id)
            if item is None or not item.available or not item.equipped:
                return False
        resource_pool_id = getattr(source, "resource_pool_id", None)
        if resource_pool_id is not None and not can_spend_actor_resource(
            actor,
            resource_pool_id,
            int(getattr(source, "resource_cost", 1)),
        ):
            return False
        return can_consume_spell_resource(actor, getattr(source, "spell_level", 0))

    def _actor_can_use_healing_source(self, actor: Actor, source: HealingSource | None) -> bool:
        if source is None:
            return False
        if not _source_is_prepared(actor, source):
            return False
        return can_consume_spell_resource(actor, getattr(source, "spell_level", 0))

    def _healing_sources_for_actor(self, actor: Actor) -> tuple[HealingSource, ...]:
        encounter = self._active_encounter()
        if encounter is None:
            return ()
        return encounter.healing_sources_by_actor.get(actor.id, ())

    def _selected_healing_source(self, actor: Actor) -> HealingSource | None:
        sources = self._healing_sources_for_actor(actor)
        if not sources:
            return None
        selected_id = self.selected_healing_source_ids.get(str(actor.id))
        if selected_id:
            selected = next((source for source in sources if source.id == selected_id), None)
            if selected is not None:
                return selected
        return sources[0]

    def select_combat_attack_source(self, source_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        transition = self.player_combat_action_flow.select_attack_source(
            state=self.combat_state,
            sources=self._attack_sources_for_actor(actor),
            source_id=source_id,
        )
        self._clear_player_pending_choices()
        self.selected_attack_source_ids[transition.actor_id] = transition.source_id
        self.combat_targeting_attack_source_id = transition.source_id
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def select_combat_healing_source(self, source_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        transition = self.player_combat_action_flow.select_healing_source(
            state=self.combat_state,
            sources=self._healing_sources_for_actor(actor),
            source_id=source_id,
        )
        self._clear_player_pending_choices()
        self.selected_healing_source_ids[transition.actor_id] = transition.source_id
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_strength_potion(self, action_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        action = next(
            (candidate for candidate in encounter.combat_actions_by_actor.get(actor.id, ()) if candidate.id == action_id),
            None,
        )
        if action is None:
            raise ValueError("Nieznana akcja eliksiru.")
        transition = self.player_combat_resource_flow.use_strength_potion(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            action=action,
        )
        return self._apply_combat_resource_transition(transition)

    def use_targeted_combat_item(self, *, action_id: str, target_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        action = next(
            (
                candidate
                for candidate in encounter.combat_actions_by_actor.get(actor.id, ())
                if candidate.id == action_id
            ),
            None,
        )
        if action is None:
            raise ValueError("Nieznana akcja przedmiotu.")
        resolution = resolve_targeted_item_action(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            action=action,
            target_id=target_id,
        )
        self.combat_state = resolution.state
        self.active_combat_effects = resolution.active_effects
        self._clear_player_pending_choices()
        self.board_message = resolution.message_body
        self._add_message(resolution.message_title, resolution.message_body)
        self._record(resolution.event_type, dict(resolution.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_concentration_action(self, action_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        action = next(
            (candidate for candidate in encounter.combat_actions_by_actor.get(actor.id, ()) if candidate.id == action_id),
            None,
        )
        if action is None:
            raise ValueError("Nieznana akcja koncentracji.")
        transition = self.player_combat_resource_flow.start_concentration(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            action=action,
        )
        return self._apply_combat_resource_transition(transition)

    def confirm_combat_concentration_action(self, *, target_id: str) -> dict[str, object]:
        pending = self.pending_concentration_action
        if pending is None:
            raise ValueError("Nie ma czaru koncentracyjnego do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        action = next(
            (candidate for candidate in encounter.combat_actions_by_actor.get(caster.id, ()) if candidate.id == pending.action_id),
            None,
        )
        if action is None:
            raise ValueError("Nieznana akcja koncentracji.")
        transition = self.player_combat_resource_flow.confirm_concentration(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            action=action,
            pending=pending,
            target_id=target_id,
        )
        return self._apply_combat_resource_transition(transition)

    def cancel_combat_concentration_action(self) -> dict[str, object]:
        pending = self.pending_concentration_action
        if pending is None:
            raise ValueError("Nie ma czaru koncentracyjnego do anulowania.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.player_combat_resource_flow.cancel_concentration(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            pending=pending,
        )
        return self._apply_combat_resource_transition(transition)

    def _maybe_prompt_concentration_check(self, applied_damage) -> None:
        if self.combat_state is None or applied_damage is None:
            return
        transition = self.player_combat_resource_flow.handle_damage(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            applied_damage=applied_damage,
            rng=self.encounter_rng,
        )
        if transition is not None:
            self._apply_combat_resource_transition(transition, sync_board=False)

    def submit_concentration_check(self, *, natural_roll: int) -> dict[str, object]:
        pending = self.pending_concentration_check
        if pending is None:
            raise ValueError("Nie ma oczekującego rzutu na koncentrację.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.player_combat_resource_flow.resolve_concentration_check(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            actor_id=pending.actor_id,
            effect_ids=pending.effect_ids,
            damage=pending.damage,
            dc=pending.dc,
            natural_roll=int(natural_roll),
        )
        result = self._apply_combat_resource_transition(transition)
        if (
            (self.pending_approach_interaction is not None or self.pending_approach_pickup is not None)
            and self.pending_concentration_check is None
        ):
            return self._resume_pending_approach_action()
        return result

    def _apply_combat_resource_transition(
        self,
        transition: CombatResourceTransition,
        *,
        sync_board: bool = True,
    ) -> dict[str, object]:
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        if transition.clear_player_choices:
            self._clear_player_pending_choices()
        if transition.clear_pending_action:
            self.pending_concentration_action = None
        if transition.pending_action is not None:
            self.pending_concentration_action = transition.pending_action
        if transition.clear_pending_check:
            self.pending_concentration_check = None
        if transition.pending_check is not None:
            self.pending_concentration_check = transition.pending_check
        if transition.clear_movement_preview:
            self.selected_combat_movement_path = None
        if transition.board_message:
            self.board_message = transition.board_message
        if transition.message_title:
            self._add_message(transition.message_title, transition.message_body)
        if transition.event_type:
            self._record(transition.event_type, dict(transition.event_payload))
        if sync_board:
            self._sync_board_leds()
        return self.state_payload()

    def submit_player_attack(self, *, target_id: str, natural_roll: int, damage: int = 0, natural_roll_2: int | None = None) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        source = self._selected_attack_source(attacker)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        transition = self.player_combat_action_flow.resolve_direct_attack(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            target_id=target_id,
            active_effects=self.active_combat_effects,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
            damage=damage,
            scene_objects=encounter.scene_objects,
        )
        return self._apply_player_attack_transition(transition)

    def select_player_area_spell_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        caster = combat_current_actor(self.combat_state)
        source = self._selected_attack_source(caster)
        if source is None:
            raise ValueError("Wybrane źródło ataku nie jest czarem obszarowym.")
        transition = self.player_area_healing_flow.select_area_spell(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            position=position,
            scene_objects=encounter.scene_objects,
        )
        self.combat_state = transition.state
        self.pending_area_spell = transition.pending
        self.pending_player_attack = None
        self.pending_player_healing = None
        self.pending_combat_help = None
        self.combat_targeting_attack_source_id = None
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def confirm_player_area_spell(self) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None or pending.stage != "confirm_area":
            raise ValueError("Nie ma czaru obszarowego do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        source = self._attack_source_by_id(caster, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {caster.name} nie ma tego czaru.")
        transition = self.player_area_healing_flow.confirm_area_spell(
            state=self.combat_state,
            source=source,
            pending=pending,
            rng=self.encounter_rng,
        )
        return self._apply_player_area_spell_transition(transition)

    def submit_player_area_spell_damage(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekujących obrażeń czaru obszarowego.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        source = self._attack_source_by_id(caster, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {caster.name} nie ma tego czaru.")
        transition = self.player_area_healing_flow.submit_area_damage(
            state=self.combat_state,
            source=source,
            pending=pending,
            damage=damage,
        )
        return self._apply_player_area_spell_transition(transition)

    def cancel_player_area_spell(self) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None:
            raise ValueError("Nie ma czaru obszarowego do anulowania.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.player_area_healing_flow.cancel_area_spell(
            state=self.combat_state,
            pending=pending,
        )
        return self._apply_player_area_spell_transition(transition)

    def _apply_player_area_spell_transition(
        self,
        transition: PlayerAreaSpellTransition,
    ) -> dict[str, object]:
        self.combat_state = transition.state
        self.pending_area_spell = transition.pending
        if transition.clear_movement_preview:
            self.selected_combat_movement_path = None
        if transition.board_message:
            self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._apply_combat_trigger_events(
            tuple(
                EffectEvent(
                    EffectEventType.DAMAGE_TAKEN,
                    actor_id=str(applied.actor_after.id),
                )
                for applied in transition.applied_damages
                if applied.damage.total_applied > 0
            )
        )
        for applied in transition.applied_damages:
            self._maybe_prompt_concentration_check(applied)
            if self.pending_concentration_check is not None:
                break
        self._sync_board_leds()
        return self.state_payload()

    def select_player_attack_target_at_position(
        self,
        position: Coordinate,
        *,
        two_weapon_bonus: bool = False,
    ) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        source = self._selected_attack_source(attacker)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        transition = self.player_combat_action_flow.select_attack_target(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            position=position,
            active_effects=self.active_combat_effects,
            scene_objects=encounter.scene_objects,
            two_weapon_bonus=two_weapon_bonus,
        )
        self.combat_targeting_attack_source_id = None
        return self._apply_player_attack_transition(transition)

    def confirm_player_attack_target(self) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage != "confirm_attack":
            raise ValueError("Nie ma celu ataku do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        transition = self.player_combat_action_flow.confirm_attack_target(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            pending=pending,
            active_effects=self.active_combat_effects,
            rng=self.encounter_rng,
            scene_objects=encounter.scene_objects,
        )
        return self._apply_player_attack_transition(transition)

    def cancel_player_attack_target(self) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage not in {"confirm_attack", "attack_roll"}:
            raise ValueError("Nie ma wyboru celu ataku do anulowania.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.player_combat_action_flow.cancel_attack_target(
            state=self.combat_state,
            pending=pending,
            active_effects=self.active_combat_effects,
        )
        return self._apply_player_attack_transition(transition)

    def submit_player_attack_roll(self, *, natural_roll: int, natural_roll_2: int | None = None) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage != "attack_roll":
            raise ValueError("Nie ma oczekującego rzutu ataku gracza.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        transition = self.player_combat_action_flow.submit_attack_roll(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            pending=pending,
            active_effects=self.active_combat_effects,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
            scene_objects=encounter.scene_objects,
        )
        return self._apply_player_attack_transition(transition)

    def submit_player_damage_roll(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekującego rzutu obrażeń gracza.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self._active_encounter() is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        transition = self.player_combat_action_flow.submit_damage(
            state=self.combat_state,
            source=source,
            pending=pending,
            active_effects=self.active_combat_effects,
            damage=damage,
        )
        return self._apply_player_attack_transition(transition)

    def _apply_player_attack_transition(
        self,
        transition: PlayerAttackTransition,
    ) -> dict[str, object]:
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.pending_player_attack = transition.pending
        if transition.clear_combat_help:
            self.pending_combat_help = None
        if transition.clear_movement_preview:
            self.selected_combat_movement_path = None
        if transition.board_message:
            self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        payload = dict(transition.event_payload)
        attacker_id = str(payload.get("attacker_id", ""))
        target_id = str(payload.get("target_id", ""))
        trigger_events = []
        if transition.event_type == "ui_combat_player_attack_roll" and payload.get("hit"):
            trigger_events.append(
                EffectEvent(
                    EffectEventType.ATTACK_HIT,
                    actor_id=attacker_id,
                    target_actor_id=target_id,
                )
            )
        if transition.applied_damage is not None:
            target_id = str(transition.applied_damage.actor_after.id)
            if (
                transition.event_type != "ui_combat_player_damage_roll"
                and payload.get("saving_throw") is None
            ):
                trigger_events.append(
                    EffectEvent(
                        EffectEventType.ATTACK_HIT,
                        actor_id=attacker_id,
                        target_actor_id=target_id,
                    )
                )
            if transition.applied_damage.damage.total_applied > 0:
                trigger_events.append(
                    EffectEvent(
                        EffectEventType.DAMAGE_TAKEN,
                        actor_id=target_id,
                        target_actor_id=attacker_id,
                    )
                )
        self._apply_combat_trigger_events(tuple(trigger_events))
        if transition.applied_damage is not None:
            self._maybe_prompt_concentration_check(transition.applied_damage)
        self._sync_board_leds()
        return self.state_payload()

    def select_player_healing_target_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        healer = combat_current_actor(self.combat_state)
        source = self._selected_healing_source(healer)
        if source is None:
            raise ValueError(f"Aktor {healer.name} nie ma zdefiniowanego leczenia.")
        transition = self.player_area_healing_flow.select_healing_target(
            state=self.combat_state,
            board=encounter.board,
            source=source,
            position=position,
        )
        self.combat_state = transition.state
        self.pending_player_healing = transition.pending
        self.pending_player_attack = None
        self.pending_combat_help = None
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def submit_player_healing_roll(self, *, healing: int) -> dict[str, object]:
        pending = self.pending_player_healing
        if pending is None or pending.stage != "healing_roll":
            raise ValueError("Nie ma oczekującego rzutu leczenia gracza.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        healer = combat_current_actor(self.combat_state)
        source = next((candidate for candidate in self._healing_sources_for_actor(healer) if candidate.id == pending.source_id), None)
        if source is None:
            raise ValueError(f"Aktor {healer.name} nie ma tego źródła leczenia.")
        transition = self.player_area_healing_flow.submit_healing(
            state=self.combat_state,
            source=source,
            pending=pending,
            healing=healing,
        )
        self.combat_state = transition.state
        self.pending_player_healing = transition.pending
        if transition.board_message:
            self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def cancel_player_healing(self) -> dict[str, object]:
        pending = self.pending_player_healing
        if pending is None:
            raise ValueError("Nie ma leczenia do anulowania.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.player_area_healing_flow.cancel_healing(
            state=self.combat_state,
            pending=pending,
        )
        self.combat_state = transition.state
        self.pending_player_healing = transition.pending
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def preview_combat_movement(self, *, col: int, row: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        preview = self.combat_movement_flow.preview(
            state=self.combat_state,
            board=encounter.board,
            destination=Coordinate(int(col), int(row)),
        )
        self.pending_opportunity_movement = None
        self.selected_combat_movement_path = preview.path
        self.board_message = preview.board_message
        self._record(preview.event_type, dict(preview.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_movement(self, *, col: int, row: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        submission = self.combat_movement_flow.submit(
            state=self.combat_state,
            board=encounter.board,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            destination=Coordinate(int(col), int(row)),
            scene_objects=encounter.scene_objects,
        )
        if submission.requires_opportunity_confirmation:
            self.pending_opportunity_movement = PendingOpportunityMovement(
                actor_id=submission.actor_id,
                destination=submission.destination,
                path=submission.path,
                threat_actor_ids=submission.threat_actor_ids,
            )
            self.selected_combat_movement_path = submission.path
            self.board_message = submission.board_message
            self._add_message(submission.message_title, submission.message_body)
            self._record(submission.event_type, dict(submission.event_payload))
            self._sync_board_leds()
            return self.state_payload()
        self.combat_state = submission.state
        self.selected_combat_movement_path = None
        self.pending_combat_interaction = None
        self.pending_combat_help = None
        self._expire_invalid_combat_effects()
        self._add_message(submission.message_title, submission.message_body)
        self._record(submission.event_type, dict(submission.event_payload))
        movement_events = [
            EffectEvent(
                EffectEventType.ACTOR_MOVED,
                actor_id=submission.actor_id,
                position=submission.destination,
            )
        ]
        movement_payload = dict(submission.event_payload)
        dragged_actor_id = movement_payload.get("dragged_actor_id")
        dragged_destination = movement_payload.get("dragged_destination")
        if dragged_actor_id and isinstance(dragged_destination, list):
            movement_events.append(
                EffectEvent(
                    EffectEventType.ACTOR_MOVED,
                    actor_id=str(dragged_actor_id),
                    position=Coordinate(*dragged_destination),
                )
            )
        self._apply_combat_trigger_events(tuple(movement_events))
        self._sync_board_leds()
        return self.state_payload()

    def confirm_opportunity_movement(self) -> dict[str, object]:
        pending = self.pending_opportunity_movement
        if pending is None:
            raise ValueError("Nie ma ruchu z atakiem okazyjnym do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        positions_before = {
            str(actor.id): actor.position for actor in self.combat_state.actors
        }
        resolution = self.combat_reaction_flow.resolve_opportunity_movement(
            state=self.combat_state,
            actor_id=pending.actor_id,
            path=pending.path,
            threat_actor_ids=pending.threat_actor_ids,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            roll_d20=lambda request: _automatic_d20_input(request, self.encounter_rng),
            roll_damage=lambda die_sides: self.encounter_rng.randint(1, die_sides),
        )
        self.combat_state = resolution.state
        self.active_combat_effects = resolution.active_effects
        self.pending_opportunity_movement = None
        self.selected_combat_movement_path = None
        self.pending_combat_interaction = None
        self._expire_invalid_combat_effects()
        self._add_message(resolution.message_title, resolution.message_body)
        self._record(
            "ui_combat_opportunity_movement_confirmed",
            {
                "actor_id": pending.actor_id,
                "destination": [pending.destination.col, pending.destination.row],
                "threat_actor_ids": list(pending.threat_actor_ids),
            },
        )
        reaction_events = [
            EffectEvent(
                EffectEventType.DAMAGE_TAKEN,
                actor_id=str(applied.actor_after.id),
            )
            for applied in resolution.applied_damages
            if applied.damage.total_applied > 0
        ]
        if resolution.movement_performed:
            reaction_events.extend(
                EffectEvent(
                    EffectEventType.ACTOR_MOVED,
                    actor_id=str(actor.id),
                    position=actor.position,
                )
                for actor in resolution.state.actors
                if positions_before.get(str(actor.id)) != actor.position
            )
        self._apply_combat_trigger_events(tuple(reaction_events))
        for applied_damage in resolution.applied_damages:
            self._maybe_prompt_concentration_check(applied_damage)
            if self.pending_concentration_check is not None:
                break
        if self.pending_approach_interaction is not None or self.pending_approach_pickup is not None:
            return self._resume_pending_approach_action()
        self._sync_board_leds()
        return self.state_payload()

    def cancel_opportunity_movement(self) -> dict[str, object]:
        pending = self.pending_opportunity_movement
        if pending is None:
            raise ValueError("Nie ma ruchu z atakiem okazyjnym do anulowania.")
        self.pending_opportunity_movement = None
        self.pending_approach_interaction = None
        self.pending_approach_pickup = None
        self.selected_combat_movement_path = None
        self.board_message = "Anulowano ryzykowny ruch. Kliknij Skanuj planszę, żeby wybrać inne pole."
        self._add_message("Atak okazyjny", "Anulowano ruch prowokujący atak okazyjny.")
        self._record(
            "ui_combat_opportunity_movement_cancelled",
            {"actor_id": pending.actor_id, "destination": [pending.destination.col, pending.destination.row]},
        )
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_dash(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.use_dash(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_dodge(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.use_dodge(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_disengage(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.use_disengage(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def drop_combat_prone(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.drop_prone(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def stand_combat_up(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.stand_up(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_hide(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        pending = self.combat_turn_action_flow.prepare_hide(
            state=self.combat_state,
            board=encounter.board,
            scene_objects=encounter.scene_objects,
        )
        self._clear_player_pending_choices()
        self.pending_combat_skill_check = pending
        self.board_message = "Rzuć Dexterity (Stealth) i wpisz naturalny wynik d20."
        self._add_message("Hide", "Warunki pozwalają spróbować się ukryć.")
        self._record("ui_combat_hide_started", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_search(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        pending = self.combat_turn_action_flow.prepare_search(state=self.combat_state)
        self._clear_player_pending_choices()
        self.pending_combat_skill_check = pending
        self.board_message = "Rzuć Wisdom (Perception) i wpisz naturalny wynik d20."
        self._add_message("Search", "Aktywnie szukasz ukrytego przeciwnika.")
        self._record("ui_combat_search_started", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_skill_check(self, *, natural_roll: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        pending = self.pending_combat_skill_check
        if pending is None:
            raise ValueError("Nie ma oczekującego testu Hide ani Search.")
        if pending.action == "hide":
            encounter = self._active_encounter()
            if encounter is None:
                raise ValueError("Brak danych encountera dla aktywnej walki.")
            transition = self.combat_turn_action_flow.resolve_hide(
                state=self.combat_state,
                board=encounter.board,
                pending=pending,
                natural_roll=natural_roll,
                active_effects=self.active_combat_effects,
                scene_objects=encounter.scene_objects,
            )
        elif pending.action == "search":
            transition = self.combat_turn_action_flow.resolve_search(
                state=self.combat_state,
                pending=pending,
                natural_roll=natural_roll,
                active_effects=self.active_combat_effects,
            )
        else:
            raise ValueError("Nieznany rodzaj oczekującego testu walki.")
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.pending_combat_skill_check = None
        self.board_message = transition.message_body
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_skill_check(self) -> dict[str, object]:
        pending = self.pending_combat_skill_check
        if pending is None:
            raise ValueError("Nie ma oczekującego testu Hide ani Search.")
        self.pending_combat_skill_check = None
        self.board_message = "Anulowano test. Akcja nie została zużyta."
        self._record("ui_combat_skill_check_cancelled", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_shove(self, *, target_id: str, mode: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        pending = self.combat_shove_flow.prepare(
            state=self.combat_state,
            board=encounter.board,
            target_id=target_id,
            mode=ShoveMode(mode),
            scene_objects=encounter.scene_objects,
        )
        self._clear_player_pending_choices()
        self.pending_combat_shove = pending
        self.board_message = (
            f"Rzuć Strength (Athletics) dla {pending.attacker_name}. "
            f"{pending.target_name} broni się automatycznie przez "
            f"{'Athletics' if pending.defender_skill == 'athletics' else 'Acrobatics'}."
        )
        self._add_message("Shove", self.board_message)
        self._record("ui_combat_shove_started", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_shove(self, *, attacker_natural_roll: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        pending = self.pending_combat_shove
        if encounter is None or pending is None:
            raise ValueError("Nie ma oczekującego Shove.")
        defender_natural_roll = automatic_defender_roll(pending, self.encounter_rng)
        resolution = self.combat_shove_flow.resolve(
            state=self.combat_state,
            board=encounter.board,
            pending=pending,
            attacker_natural_roll=attacker_natural_roll,
            defender_natural_roll=defender_natural_roll,
            scene_objects=encounter.scene_objects,
        )
        self.combat_state = resolution.state
        self.pending_combat_shove = None
        self.board_message = resolution.message_body
        self._add_message(resolution.message_title, resolution.message_body)
        self._record(resolution.event_type, dict(resolution.event_payload))
        if (
            resolution.succeeded
            and pending.mode == ShoveMode.PUSH
            and pending.push_destination is not None
        ):
            self._apply_combat_trigger_events(
                (
                    EffectEvent(
                        EffectEventType.ACTOR_MOVED,
                        actor_id=pending.target_id,
                        position=pending.push_destination,
                    ),
                )
            )
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_shove(self) -> dict[str, object]:
        pending = self.pending_combat_shove
        if pending is None:
            raise ValueError("Nie ma oczekującego Shove.")
        self.pending_combat_shove = None
        self.board_message = "Anulowano Shove. Akcja nie została zużyta."
        self._record("ui_combat_shove_cancelled", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_grapple(self, *, target_id: str, mode: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        pending = self.combat_grapple_flow.prepare(
            state=self.combat_state,
            mode=GrappleMode(mode),
            target_id=target_id,
        )
        self._clear_player_pending_choices()
        self.pending_combat_grapple = pending
        self.board_message = (
            f"Rzuć {_skill_label_pl(pending.actor_skill)} dla {pending.actor_name}. "
            f"{pending.opponent_name} odpowiada automatycznie przez "
            f"{_skill_label_pl(pending.opponent_skill)}."
        )
        self._add_message("Grapple", self.board_message)
        self._record("ui_combat_grapple_started", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_grapple(self, *, actor_natural_roll: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        pending = self.pending_combat_grapple
        if pending is None:
            raise ValueError("Nie ma oczekującego Grapple.")
        opponent_natural_roll = automatic_grapple_opponent_roll(
            pending,
            self.encounter_rng,
        )
        resolution = self.combat_grapple_flow.resolve(
            state=self.combat_state,
            pending=pending,
            actor_natural_roll=actor_natural_roll,
            opponent_natural_roll=opponent_natural_roll,
        )
        self.combat_state = resolution.state
        self.pending_combat_grapple = None
        self.board_message = resolution.message_body
        self._add_message(resolution.message_title, resolution.message_body)
        self._record(resolution.event_type, dict(resolution.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_grapple(self) -> dict[str, object]:
        pending = self.pending_combat_grapple
        if pending is None:
            raise ValueError("Nie ma oczekującego Grapple.")
        self.pending_combat_grapple = None
        self.board_message = "Anulowano Grapple. Akcja nie została zużyta."
        self._record("ui_combat_grapple_cancelled", pending.as_payload())
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_help(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        preparation = self.combat_turn_action_flow.prepare_help(state=self.combat_state)
        self.pending_combat_help = PendingCombatHelp(
            helper_id=preparation.helper_id,
            ally_ids=preparation.ally_ids,
            target_ids=preparation.target_ids,
        )
        self.pending_player_attack = None
        self.pending_combat_interaction = None
        self.selected_combat_movement_path = None
        self.board_message = preparation.board_message
        self._add_message(preparation.message_title, preparation.message_body)
        self._record(preparation.event_type, dict(preparation.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_help(self, *, ally_id: str, target_id: str) -> dict[str, object]:
        pending = self.pending_combat_help
        if pending is None:
            raise ValueError("Nie ma akcji Help do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.confirm_help(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            helper_id=pending.helper_id,
            ally_ids=pending.ally_ids,
            target_ids=pending.target_ids,
            ally_id=ally_id,
            target_id=target_id,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.pending_combat_help = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_help(self) -> dict[str, object]:
        pending = self.pending_combat_help
        if pending is None:
            raise ValueError("Nie ma akcji Help do anulowania.")
        self.pending_combat_help = None
        self.board_message = "Anulowano Help. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
        self._add_message("Pomoc", "Anulowano akcję Help.")
        self._record("ui_combat_help_cancelled", {"helper_id": pending.helper_id})
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_ready(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        preparation = self.combat_turn_action_flow.prepare_ready(
            state=self.combat_state,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
        )
        self._clear_player_pending_choices()
        self.pending_combat_ready = PendingCombatReady(
            actor_id=preparation.actor_id,
            triggers=preparation.triggers,
        )
        self.board_message = preparation.board_message
        self._add_message(preparation.message_title, preparation.message_body)
        self._record(preparation.event_type, dict(preparation.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_ready(self, *, trigger: str) -> dict[str, object]:
        pending = self.pending_combat_ready
        if pending is None:
            raise ValueError("Nie ma akcji Ready do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_action_flow.confirm_ready(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            actor_id=pending.actor_id,
            triggers=pending.triggers,
            trigger=trigger,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.pending_combat_ready = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_ready(self) -> dict[str, object]:
        pending = self.pending_combat_ready
        if pending is None:
            raise ValueError("Nie ma akcji Ready do anulowania.")
        self.pending_combat_ready = None
        self.board_message = "Anulowano Ready. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
        self._add_message("Ready", "Anulowano przygotowaną akcję.")
        self._record("ui_combat_ready_cancelled", {"actor_id": pending.actor_id})
        self._sync_board_leds()
        return self.state_payload()

    def select_combat_interaction_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        transition = self.combat_scene_interaction_flow.select(
            state=self.combat_state,
            scene_objects=encounter.scene_objects,
            position=position,
            active_effects=self.active_combat_effects,
        )
        return self._apply_combat_scene_interaction_transition(transition)

    def confirm_combat_interaction(self, interaction_id: str) -> dict[str, object]:
        pending = self.pending_combat_interaction
        if pending is None:
            raise ValueError("Nie ma interakcji do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        transition = self.combat_scene_interaction_flow.confirm(
            state=self.combat_state,
            scene_objects=encounter.scene_objects,
            active_effects=self.active_combat_effects,
            pending=pending,
            interaction_id=interaction_id,
            rng=self.encounter_rng,
        )
        return self._apply_combat_scene_interaction_transition(transition)

    def cancel_combat_interaction(self) -> dict[str, object]:
        pending = self.pending_combat_interaction
        if pending is None:
            raise ValueError("Nie ma interakcji do anulowania.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_scene_interaction_flow.cancel(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            pending=pending,
        )
        return self._apply_combat_scene_interaction_transition(transition)

    def _apply_combat_scene_interaction_transition(
        self,
        transition: CombatSceneInteractionTransition,
    ) -> dict[str, object]:
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.pending_combat_interaction = transition.pending
        if transition.clear_movement_preview:
            self.selected_combat_movement_path = None
        if transition.clear_player_attack:
            self.pending_player_attack = None
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def _effective_attack_source(self, actor: Actor, source, target: Actor | None = None):
        if target is not None:
            return attack_source_with_target_combat_effects(actor, target, source, self.active_combat_effects)
        return attack_source_with_combat_effects(actor, source, self.active_combat_effects)

    def _available_combat_interaction_options(
        self,
        encounter: LoadedEncounter,
        actor: Actor,
        position: Coordinate,
    ) -> tuple[CombatInteractionOption, ...]:
        if self.combat_state is None:
            return ()
        return self.combat_scene_interaction_flow.options(
            state=self.combat_state,
            scene_objects=encounter.scene_objects,
            actor=actor,
            position=position,
        )

    def _combat_context_options(self, actor: Actor, position: Coordinate) -> tuple[CombatMenuOption, ...]:
        if self.combat_state is None:
            return ()
        encounter = self._active_encounter()
        if encounter is None:
            return ()
        action_available = self.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        attack_available = can_use_attack_action(self.combat_state, actor)
        object_interaction_available = self.combat_state.turn_action.object_interaction_available
        options: list[CombatMenuOption] = []
        dropped_weapons = tuple(item for item in self.combat_state.dropped_weapons if item.position == position)
        interactions = self._available_combat_interaction_options(encounter, actor, position)
        if interactions:
            first = interactions[0]
            label = first.label if len(interactions) == 1 else f"Interakcja: {first.object_name}"
            options.append(
                CombatMenuOption(
                    id=f"interact:{first.object_id}",
                    label=label,
                    description=(
                        (first.description or "Wybierz dostępną interakcję z obiektem na tym polu.")
                        + f" Koszt: {action_economy_cost_label(first.action_cost)}."
                    ),
                    category=CombatMenuCategory.FIELD,
                    action=CombatMenuAction.INTERACT,
                    position=position,
                )
            )
        else:
            approach = self.combat_scene_interaction_flow.plan_approach(
                state=self.combat_state,
                board=encounter.board,
                scene_objects=encounter.scene_objects,
                actor=actor,
                position=position,
            )
            if approach is not None and approach.path.cost_feet > 0:
                first = approach.options[0]
                interaction_label = first.label if len(approach.options) == 1 else f"użyj: {approach.object_name}"
                options.append(
                    CombatMenuOption(
                        id=f"approach-interact:{approach.object_id}",
                        label=f"Podejdź i {interaction_label.lower()}",
                        description=(
                            f"{first.description} Kliknięte pole obiektu: {position.as_tuple()}; "
                            f"faktyczne pole po ruchu: {approach.destination.as_tuple()}. "
                            f"Ruch {approach.path.cost_feet} ft, następnie interakcja; "
                            f"koszt: {action_economy_cost_label(first.action_cost)}."
                        ),
                        category=CombatMenuCategory.FIELD,
                        action=CombatMenuAction.APPROACH_AND_INTERACT,
                        position=position,
                        destination=approach.destination,
                        movement_cost_feet=approach.path.cost_feet,
                    )
                )

        if position == actor.position:
            if object_interaction_available or action_available:
                for dropped in dropped_weapons:
                    cost = "Darmowa interakcja z obiektem." if object_interaction_available else "Zużyje akcję."
                    options.append(
                        CombatMenuOption(
                            id=f"pickup:{dropped.id}",
                            label=f"Podnieś: {dropped.weapon.name}",
                            description=f"Podnieś broń z aktualnego pola. {cost} Broń pozostanie niewyposażona.",
                            category=CombatMenuCategory.FIELD,
                            action=CombatMenuAction.PICK_UP,
                            position=position,
                            dropped_weapon_id=dropped.id,
                        )
                    )
            for weapon in actor.inventory:
                if weapon.kind != "weapon" or not weapon.available:
                    continue
                if weapon.equipped:
                    options.append(
                        CombatMenuOption(
                            id=f"stow-weapon:{weapon.id}",
                            label=f"Schowaj: {weapon.name}",
                            description=(
                                "Schowaj broń w ekwipunku; zużyje darmową interakcję "
                                "z obiektem albo akcję, jeśli interakcja została już wykorzystana."
                            ),
                            category=CombatMenuCategory.EQUIPMENT,
                            action=CombatMenuAction.STOW_WEAPON,
                            item_id=weapon.id,
                        )
                    )
                    options.append(
                        CombatMenuOption(
                            id=f"drop-weapon:{weapon.id}",
                            label=f"Upuść: {weapon.name}",
                            description="Połóż wyposażoną broń na aktualnym polu bez zużywania akcji ani interakcji.",
                            category=CombatMenuCategory.EQUIPMENT,
                            action=CombatMenuAction.DROP_WEAPON,
                            item_id=weapon.id,
                        )
                    )
                    continue
                if not (object_interaction_available or action_available):
                    continue
                hand_plan = plan_hand_equip(actor.inventory, weapon.id)
                replaced = tuple(
                    item.name for item in actor.inventory if item.id in hand_plan.replaced_item_ids
                )
                interaction_count = 1 + len(replaced)
                if not can_use_object_interactions(self.combat_state, interaction_count):
                    continue
                cost = (
                    "darmową interakcję i akcję"
                    if interaction_count == 2
                    else "darmową interakcję z obiektem"
                    if object_interaction_available
                    else "akcję"
                )
                replacing = bool(replaced)
                hand_label = (
                    "obie ręce"
                    if len(hand_plan.occupied_slots) == 2
                    else "drugą rękę"
                    if hand_plan.occupied_slots[0].value == "off_hand"
                    else "główną rękę"
                )
                options.append(
                    CombatMenuOption(
                        id=f"equip-weapon:{weapon.id}",
                        label=f"{'Zamień na' if replacing else 'Wyposaż'}: {weapon.name}",
                        description=(
                            f"{'Schowaj ' + ', '.join(replaced) + ' i wyposaż' if replacing else 'Wyposaż'} "
                            f"{weapon.name}, zajmując {hand_label}; "
                            f"zużyje {cost}."
                        ),
                        category=CombatMenuCategory.EQUIPMENT,
                        action=CombatMenuAction.EQUIP_WEAPON,
                        item_id=weapon.id,
                    )
                )
            for shield in actor.inventory:
                if shield.kind != "shield" or not shield.available or not action_available:
                    continue
                if shield.equipped:
                    options.append(
                        CombatMenuOption(
                            id=f"doff-shield:{shield.id}",
                            label=f"Zdejmij: {shield.name}",
                            description=(
                                f"Zwolnij rękę i strać premię +{shield.armor_class_bonus} KP; "
                                "zużywa akcję."
                            ),
                            category=CombatMenuCategory.EQUIPMENT,
                            action=CombatMenuAction.DOFF_SHIELD,
                            item_id=shield.id,
                        )
                    )
                    continue
                proficiency_id = shield.armor_proficiency or "shield"
                if not actor.proficiencies.is_armor_proficient(proficiency_id):
                    continue
                options.append(
                    CombatMenuOption(
                        id=f"don-shield:{shield.id}",
                        label=f"Załóż: {shield.name}",
                        description=(
                            f"Zajmij jedną rękę i zyskaj +{shield.armor_class_bonus} KP; "
                            "zużywa akcję i może schować przedmiot z tej ręki."
                        ),
                        category=CombatMenuCategory.EQUIPMENT,
                        action=CombatMenuAction.DON_SHIELD,
                        item_id=shield.id,
                    )
                )
            if attack_available and not action_available:
                for source in self._attack_sources_for_actor(actor):
                    if source.source_type.value != "weapon":
                        continue
                    effective = self._effective_attack_source(actor, source)
                    if not self._actor_can_use_attack_source(actor, effective):
                        continue
                    options.append(
                        CombatMenuOption(
                            id=f"attack-source:{source.id}",
                            label=f"Atak: {source.name}",
                            description="Wybierz źródło kolejnego ataku, a następnie wskaż cel.",
                            category=_attack_context_category(source),
                            action=CombatMenuAction.SELECT_ATTACK_SOURCE,
                            source_id=source.id,
                            provider="attack_source",
                        )
                    )
            if action_available:
                grappler_id = grappled_by(self.combat_state.condition_states, str(actor.id))
                if grappler_id is not None and self.combat_grapple_flow.can_escape(self.combat_state):
                    grappler = next(
                        candidate
                        for candidate in self.combat_state.actors
                        if str(candidate.id) == grappler_id
                    )
                    options.append(
                        CombatMenuOption(
                            id=f"grapple:escape:{grappler.id}",
                            label="Uwolnij się z chwytu",
                            description=(
                                f"Zużyj akcję i wykonaj lepszy Athletics/Acrobatics przeciw Athletics {grappler.name}."
                            ),
                            category=CombatMenuCategory.MANEUVER,
                            action=CombatMenuAction.GRAPPLE,
                            target_actor_id=str(grappler.id),
                            grapple_mode=GrappleMode.ESCAPE.value,
                            provider="maneuver",
                        )
                    )
                for source in self._attack_sources_for_actor(actor):
                    effective = self._effective_attack_source(actor, source)
                    if not self._actor_can_use_attack_source(actor, effective):
                        continue
                    is_spell = source.source_type.value == "spell"
                    is_area_spell = is_spell and source.area is not None
                    if is_area_spell:
                        area = source.area
                        area_dimensions = (
                            f"linia {area.length_feet} × {area.width_feet} ft"
                            if area.shape == SpellAreaShape.LINE
                            else f"stożek {area.length_feet} ft"
                            if area.shape == SpellAreaShape.CONE
                            else f"promień {area.radius_feet} ft"
                        )
                        targeting_description = (
                            f"Czar obszarowy ({area_dimensions}). Wskaż podświetlony kierunek na planszy; "
                            "pola ruchu będą wyłączone do zakończenia celowania."
                        )
                    elif is_spell:
                        targeting_description = (
                            "Czar na pojedynczy cel. Wskaż podświetlonego przeciwnika; "
                            "pola ruchu będą wyłączone do zakończenia celowania."
                        )
                    else:
                        targeting_description = "Wybierz źródło, a następnie wskaż cel na planszy."
                    options.append(
                        CombatMenuOption(
                            id=f"attack-source:{source.id}",
                            label=f"{'Rzuć czar obszarowy' if is_area_spell else 'Rzuć czar na pojedynczy cel' if is_spell else 'Atak'}: {source.name}",
                            description=targeting_description,
                            category=_attack_context_category(source),
                            action=CombatMenuAction.SELECT_ATTACK_SOURCE,
                            source_id=source.id,
                            provider="attack_source",
                        )
                    )
                for source in self._healing_sources_for_actor(actor):
                    if not self._actor_can_use_healing_source(actor, source):
                        continue
                    options.append(
                        CombatMenuOption(
                            id=f"healing-source:{source.id}",
                            label=f"Leczenie: {source.name}",
                            description="Wybierz źródło leczenia, a następnie wskaż sojusznika na planszy.",
                            category=CombatMenuCategory.SUPPORT,
                            action=CombatMenuAction.SELECT_HEALING_SOURCE,
                            source_id=source.id,
                            provider="healing_source",
                        )
                    )
                for action in encounter.combat_actions_by_actor.get(actor.id, ()):
                    if action.action_type == "targeted_item_effect":
                        continue
                    action_payload = _combat_action_payload(action, actor)
                    if not action_payload["available"]:
                        continue
                    options.append(
                        CombatMenuOption(
                            id=f"combat-action:{action.id}",
                            label=action.label or action.name,
                            description=f"Użyj: {action.name}.",
                            category=(CombatMenuCategory.ITEM if action.source_item_id else CombatMenuCategory.MAGIC),
                            action=CombatMenuAction.COMBAT_ACTION,
                            action_id=action.id,
                            item_id=action.source_item_id,
                            provider="item_action" if action.source_item_id else "combat_action",
                        )
                    )
                options.extend(
                    (
                        CombatMenuOption("basic:dash", "Dash", "Zużyj akcję, aby zyskać dodatkowy ruch.", CombatMenuCategory.BASIC, CombatMenuAction.DASH),
                        CombatMenuOption("basic:dodge", "Unik", "Ataki przeciw tobie mają utrudnienie do początku następnej tury.", CombatMenuCategory.BASIC, CombatMenuAction.DODGE),
                        CombatMenuOption("basic:disengage", "Odwrót", "Ruch w tej turze nie prowokuje ataków okazyjnych.", CombatMenuCategory.BASIC, CombatMenuAction.DISENGAGE),
                        CombatMenuOption("basic:help", "Help", "Pomóż sojusznikowi w następnym ataku.", CombatMenuCategory.BASIC, CombatMenuAction.HELP),
                        CombatMenuOption("basic:ready", "Ready", "Przygotuj atak na wybrany warunek.", CombatMenuCategory.BASIC, CombatMenuAction.READY),
                    )
                )
                hiding = hide_eligibility(encounter.board, actor, self.combat_state.actors, encounter.scene_objects)
                if hiding.allowed:
                    options.append(
                        CombatMenuOption("basic:hide", "Hide", "Spróbuj ukryć się przed przeciwnikami, którzy nie widzą cię wyraźnie.", CombatMenuCategory.BASIC, CombatMenuAction.HIDE)
                    )
                if any(str(actor.id) in hidden.hidden_from_actor_ids for hidden in self.combat_state.hidden_states):
                    options.append(
                        CombatMenuOption("basic:search", "Search", "Użyj Perception, aby odnaleźć ukrytego przeciwnika.", CombatMenuCategory.BASIC, CombatMenuAction.SEARCH)
                    )
            is_prone = has_condition(
                self.combat_state.condition_states,
                str(actor.id),
                CombatCondition.PRONE,
            )
            if is_prone:
                stand_cost = standing_movement_cost(actor)
                if movement_remaining(self.combat_state, actor) >= stand_cost:
                    options.append(
                        CombatMenuOption(
                            "basic:stand-up",
                            "Wstań",
                            f"Usuń Powalenie, wydając {stand_cost} ft ruchu.",
                            CombatMenuCategory.BASIC,
                            CombatMenuAction.STAND_UP,
                        )
                    )
            else:
                options.append(
                    CombatMenuOption(
                        "basic:drop-prone",
                        "Padnij",
                        "Przyjmij stan Powalony bez zużywania akcji ani ruchu.",
                        CombatMenuCategory.BASIC,
                        CombatMenuAction.DROP_PRONE,
                    )
                )
            options.append(
                CombatMenuOption(
                    "turn:end",
                    "Zakończ turę",
                    "Przekaż turę następnemu aktorowi.",
                    CombatMenuCategory.TURN,
                    CombatMenuAction.END_TURN,
                )
            )
            return ContextualActionCatalog.collect(tuple(options)).options

        movement = _remaining_movement_range(encounter.board, self.combat_state, actor)
        if position in movement.reachable_tiles:
            options.append(
                CombatMenuOption(
                    id=f"move:{position.col}:{position.row}",
                    label="Podejdź na pole",
                    description="Pokaż ścieżkę ruchu; ponowne kliknięcie pola ją zatwierdzi.",
                    category=CombatMenuCategory.FIELD,
                    action=CombatMenuAction.MOVE,
                    position=position,
                )
            )
        if position in movement.reachable_tiles and (object_interaction_available or action_available):
            for dropped in dropped_weapons:
                movement_cost = movement.costs_by_tile.get(position, 0)
                interaction_cost = "darmowa interakcja" if object_interaction_available else "akcja"
                options.append(
                    CombatMenuOption(
                        id=f"approach-pickup:{dropped.id}",
                        label=f"Podejdź i podnieś: {dropped.weapon.name}",
                        description=(
                            f"Ruch {movement_cost} ft na pole {position.as_tuple()}, następnie {interaction_cost}. "
                            "Broń pozostanie niewyposażona."
                        ),
                        category=CombatMenuCategory.FIELD,
                        action=CombatMenuAction.APPROACH_AND_PICK_UP,
                        position=position,
                        destination=position,
                        movement_cost_feet=movement_cost,
                        dropped_weapon_id=dropped.id,
                    )
                )
        if action_available or attack_available:
            shove_target = next(
                (
                    candidate
                    for candidate in self.combat_state.actors
                    if candidate.position == position
                    and candidate.faction not in {actor.faction, Faction.NEUTRAL}
                    and not candidate.is_defeated()
                ),
                None,
            )
            if shove_target is not None and attack_available:
                if self.combat_grapple_flow.can_start(
                    self.combat_state,
                    str(shove_target.id),
                ):
                    options.append(
                        CombatMenuOption(
                            id=f"grapple:start:{shove_target.id}",
                            label=f"Grapple: {shove_target.name}",
                            description=(
                                "Zużyj jeden atak i wykonaj Athletics przeciw lepszemu "
                                "Athletics/Acrobatics celu. Sukces ustawia jego szybkość na 0."
                            ),
                            category=CombatMenuCategory.MANEUVER,
                            action=CombatMenuAction.GRAPPLE,
                            position=position,
                            target_actor_id=str(shove_target.id),
                            grapple_mode=GrappleMode.START.value,
                            provider="maneuver",
                        )
                    )
                for shove_mode in self.combat_shove_flow.available_modes(
                    state=self.combat_state,
                    board=encounter.board,
                    target_id=str(shove_target.id),
                    scene_objects=encounter.scene_objects,
                ):
                    is_prone_shove = shove_mode == ShoveMode.PRONE
                    options.append(
                        CombatMenuOption(
                            id=f"shove:{shove_mode.value}:{shove_target.id}",
                            label=(
                                f"Shove — powal: {shove_target.name}"
                                if is_prone_shove
                                else f"Shove — odepchnij: {shove_target.name}"
                            ),
                            description=(
                                "Zużyj jeden atak i wykonaj Athletics przeciw Athletics/Acrobatics celu. "
                                + (
                                    "Sukces nakłada stan Powalony."
                                    if is_prone_shove
                                    else "Sukces odpycha cel o 5 ft."
                                )
                            ),
                            category=CombatMenuCategory.MANEUVER,
                            action=CombatMenuAction.SHOVE,
                            position=position,
                            target_actor_id=str(shove_target.id),
                            shove_mode=shove_mode.value,
                            provider="maneuver",
                        )
                    )
            for source in self._attack_sources_for_actor(actor):
                if source.source_type.value == "weapon":
                    if not attack_available:
                        continue
                elif not action_available:
                    continue
                attack_source = self._effective_attack_source(actor, source, shove_target)
                source_item = (
                    _inventory_item_for_attack_source(actor, source.source_item_id)
                    if source.source_item_id
                    else None
                )
                usable_now = self._actor_can_use_attack_source(actor, attack_source)
                can_equip_and_attack = bool(
                    source.source_type.value == "weapon"
                    and source_item is not None
                    and source_item.available
                    and not source_item.equipped
                    and object_interaction_available
                    and not plan_hand_equip(actor.inventory, source_item.id).replaced_item_ids
                )
                if not usable_now and not can_equip_and_attack:
                    continue
                if attack_source.area is not None:
                    if not usable_now:
                        continue
                    if position in _area_spell_selection_positions(encounter.board, actor, attack_source):
                        options.append(
                            CombatMenuOption(
                                f"area:{attack_source.id}",
                                f"Rzuć: {attack_source.name}",
                                "Ustaw środek lub kierunek czaru na tym polu.",
                                CombatMenuCategory.MAGIC,
                                CombatMenuAction.AREA_SPELL,
                                position=position,
                                source_id=attack_source.id,
                                provider="attack_source",
                            )
                        )
                elif _combat_target_at_position(encounter, self.combat_state, actor, position, attack_source) is not None:
                    label_prefix = "Wyposaż i zaatakuj" if can_equip_and_attack else "Atak"
                    options.append(
                        CombatMenuOption(
                            (
                                f"equip-attack:{attack_source.id}:{source_item.id}"
                                if can_equip_and_attack and source_item is not None
                                else f"attack:{attack_source.id}"
                            ),
                            f"{label_prefix}: {attack_source.name}",
                            (
                                "Użyj darmowej interakcji, aby zmienić broń, a następnie wykonaj atak."
                                if can_equip_and_attack
                                else "Zaatakuj przeciwnika stojącego na tym polu."
                            ),
                            _attack_context_category(source),
                            (
                                CombatMenuAction.EQUIP_AND_ATTACK
                                if can_equip_and_attack
                                else CombatMenuAction.ATTACK
                            ),
                            position=position,
                            source_id=attack_source.id,
                            item_id=source_item.id if can_equip_and_attack and source_item is not None else None,
                            provider="attack_source",
                        )
                    )
            for healing_source in self._healing_sources_for_actor(actor):
                if not action_available:
                    continue
                if not self._actor_can_use_healing_source(actor, healing_source):
                    continue
                if any(
                    target.position == position
                    for target in legal_healing_targets(encounter.board, actor, self.combat_state.actors, healing_source)
                ):
                    options.append(
                        CombatMenuOption(
                            f"heal:{healing_source.id}",
                            f"Lecz: {healing_source.name}",
                            "Użyj leczenia na sojuszniku stojącym na tym polu.",
                            CombatMenuCategory.SUPPORT,
                            CombatMenuAction.HEAL,
                            position=position,
                            source_id=healing_source.id,
                            provider="healing_source",
                        )
                    )
            clicked_actor = next(
                (
                    candidate
                    for candidate in self.combat_state.actors
                    if candidate.position == position and not candidate.is_defeated()
                ),
                None,
            )
            if clicked_actor is not None:
                for action in encounter.combat_actions_by_actor.get(actor.id, ()):
                    if not action_available:
                        continue
                    if not targeted_item_action_is_legal(self.combat_state, action, clicked_actor):
                        continue
                    options.append(
                        CombatMenuOption(
                            id=f"item-action:{action.id}:{clicked_actor.id}",
                            label=action.label or action.name,
                            description=(
                                f"Użyj {action.name} na {clicked_actor.name}; koszt: "
                                f"{action_economy_cost_label(action.action_cost)}; zużywa jedną sztukę przedmiotu."
                            ),
                            category=CombatMenuCategory.ITEM,
                            action=CombatMenuAction.TARGETED_ITEM_ACTION,
                            position=position,
                            action_id=action.id,
                            item_id=action.source_item_id,
                            target_actor_id=str(clicked_actor.id),
                            provider="item_action",
                        )
                    )
        if self.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE:
            bonus_sources = eligible_two_weapon_bonus_sources(
                actor,
                self.combat_state.turn_action.two_weapon_trigger_item_id,
                self._attack_sources_for_actor(actor),
            )
            for source in bonus_sources:
                attack_source = self._effective_attack_source(
                    actor,
                    two_weapon_bonus_attack_source(actor, source),
                )
                if _combat_target_at_position(
                    encounter,
                    self.combat_state,
                    actor,
                    position,
                    attack_source,
                    require_action=False,
                ) is None:
                    continue
                options.append(
                    CombatMenuOption(
                        id=f"two-weapon:{source.id}",
                        label=f"Atak drugą bronią: {source.name}",
                        description=(
                            "Zużyj bonus action. Do obrażeń nie dodawaj dodatniego "
                            "modyfikatora cechy."
                        ),
                        category=CombatMenuCategory.ATTACK,
                        action=CombatMenuAction.TWO_WEAPON_ATTACK,
                        position=position,
                        source_id=source.id,
                        provider="two_weapon",
                    )
                )
        return ContextualActionCatalog.collect(tuple(options)).options

    def _open_combat_context_menu(self, actor: Actor, position: Coordinate, options: tuple[CombatMenuOption, ...]) -> dict[str, object]:
        self._clear_player_pending_choices()
        self.combat_targeting_attack_source_id = None
        target = (
            next(
                (
                    candidate
                    for candidate in self.combat_state.actors
                    if candidate.position == position
                    and candidate.id != actor.id
                    and candidate.faction not in {actor.faction, Faction.NEUTRAL}
                    and not candidate.is_defeated()
                ),
                None,
            )
            if self.combat_state is not None
            else None
        )
        notice = ""
        if target is not None and not can_grapple_or_shove_size(actor.size, target.size):
            maximum = largest_grapple_or_shove_target(actor.size)
            notice = (
                f"{target.name} ma rozmiar {creature_size_label_pl(target.size)}. "
                f"Grapple i Shove są niedostępne: {actor.name} może wybrać cel najwyżej "
                f"rozmiaru {creature_size_label_pl(maximum)}."
            )
        if position == actor.position:
            unprepared_spells = tuple(
                source.name
                for source in self._attack_sources_for_actor(actor)
                if source.source_type.value == "spell" and not _source_is_prepared(actor, source)
            )
            if unprepared_spells:
                notice = (
                    f"Nieprzygotowane czary są niedostępne: {', '.join(unprepared_spells)}. "
                    "Wybór przygotowanych czarów został ustalony podczas setupu."
                )
        self.pending_combat_context_menu = CombatContextMenu(
            actor_id=str(actor.id),
            position=position,
            title="Akcje bohatera" if position == actor.position else f"Opcje pola ({position.col}, {position.row})",
            options=options,
            is_self_menu=position == actor.position,
            notice=notice,
        )
        self.board_message = "Wybierz opcję strzałkami i potwierdź Enterem. Escape zamyka menu."
        self._record(
            "ui_combat_context_menu_opened",
            {"actor_id": str(actor.id), "position": [position.col, position.row], "option_ids": [option.id for option in options]},
        )
        self._sync_board_leds()
        return self.state_payload()

    def move_combat_context_menu_selection(self, delta: int) -> dict[str, object]:
        if self.pending_combat_context_menu is None:
            raise ValueError("Nie ma otwartego menu akcji.")
        self.pending_combat_context_menu = self.pending_combat_context_menu.move_selection(int(delta))
        return self.state_payload()

    def cancel_combat_context_menu(self) -> dict[str, object]:
        if self.pending_combat_context_menu is None:
            raise ValueError("Nie ma otwartego menu akcji.")
        self.pending_combat_context_menu = None
        self.board_message = "Menu zamknięte. Wybierz pole na planszy."
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_context_menu(self, option_id: str = "") -> dict[str, object]:
        menu = self.pending_combat_context_menu
        if menu is None:
            raise ValueError("Nie ma otwartego menu akcji.")
        if option_id:
            menu = menu.select(option_id)
        option = menu.selected_option
        self.pending_combat_context_menu = None
        return self._execute_combat_context_option(option)

    def _execute_combat_context_option(self, option: CombatMenuOption) -> dict[str, object]:
        if option.action == CombatMenuAction.MOVE and option.position is not None:
            return self.preview_combat_movement(col=option.position.col, row=option.position.row)
        if option.action == CombatMenuAction.ATTACK and option.position is not None:
            if option.source_id:
                actor = combat_current_actor(self.combat_state)
                self.selected_attack_source_ids[str(actor.id)] = option.source_id
            return self.select_player_attack_target_at_position(option.position)
        if option.action == CombatMenuAction.TWO_WEAPON_ATTACK and option.position is not None:
            if option.source_id:
                actor = combat_current_actor(self.combat_state)
                self.selected_attack_source_ids[str(actor.id)] = option.source_id
            return self.select_player_attack_target_at_position(
                option.position,
                two_weapon_bonus=True,
            )
        if (
            option.action == CombatMenuAction.EQUIP_AND_ATTACK
            and option.position is not None
            and option.source_id
            and option.item_id
        ):
            if self.combat_state is None or not self.combat_state.turn_action.object_interaction_available:
                raise ValueError("Zmiana broni i atak wymagają dostępnej darmowej interakcji z obiektem.")
            self._equip_combat_weapon(option.item_id)
            actor = combat_current_actor(self.combat_state)
            self.selected_attack_source_ids[str(actor.id)] = option.source_id
            return self.select_player_attack_target_at_position(option.position)
        if option.action == CombatMenuAction.AREA_SPELL and option.position is not None:
            return self.select_player_area_spell_at_position(option.position)
        if option.action == CombatMenuAction.HEAL and option.position is not None:
            if option.source_id:
                actor = combat_current_actor(self.combat_state)
                self.selected_healing_source_ids[str(actor.id)] = option.source_id
            return self.select_player_healing_target_at_position(option.position)
        if option.action == CombatMenuAction.INTERACT and option.position is not None:
            return self.select_combat_interaction_at_position(option.position)
        if option.action == CombatMenuAction.APPROACH_AND_INTERACT and option.position is not None:
            return self._start_approach_interaction(option.position)
        if option.action == CombatMenuAction.PICK_UP and option.dropped_weapon_id:
            return self._pickup_dropped_weapon(option.dropped_weapon_id)
        if option.action == CombatMenuAction.APPROACH_AND_PICK_UP and option.position is not None and option.dropped_weapon_id:
            return self._start_approach_pickup(option.dropped_weapon_id, option.position)
        if option.action == CombatMenuAction.EQUIP_WEAPON and option.item_id:
            return self._equip_combat_weapon(option.item_id)
        if option.action == CombatMenuAction.STOW_WEAPON and option.item_id:
            return self._stow_combat_weapon(option.item_id)
        if option.action == CombatMenuAction.DROP_WEAPON and option.item_id:
            return self._drop_combat_weapon(option.item_id)
        if option.action == CombatMenuAction.DON_SHIELD and option.item_id:
            return self._don_combat_shield(option.item_id)
        if option.action == CombatMenuAction.DOFF_SHIELD and option.item_id:
            return self._doff_combat_shield(option.item_id)
        if option.action == CombatMenuAction.SELECT_ATTACK_SOURCE and option.source_id:
            return self.select_combat_attack_source(option.source_id)
        if option.action == CombatMenuAction.SELECT_HEALING_SOURCE and option.source_id:
            return self.select_combat_healing_source(option.source_id)
        if (
            option.action == CombatMenuAction.TARGETED_ITEM_ACTION
            and option.action_id
            and option.target_actor_id
        ):
            return self.use_targeted_combat_item(
                action_id=option.action_id,
                target_id=option.target_actor_id,
            )
        if option.action == CombatMenuAction.COMBAT_ACTION and option.action_id:
            actor = combat_current_actor(self.combat_state)
            action = _combat_action_by_id(self._active_encounter(), actor, option.action_id)
            if action is None:
                raise ValueError("Wybrana akcja nie jest już dostępna.")
            if action.action_type == "strength_potion":
                return self.use_combat_strength_potion(option.action_id)
            if action.action_type == "concentration_attack_bonus":
                return self.start_combat_concentration_action(option.action_id)
            raise ValueError("Ten typ akcji nie ma jeszcze wykonawcy w menu walki.")
        if option.action == CombatMenuAction.DASH:
            return self.use_combat_dash()
        if option.action == CombatMenuAction.DODGE:
            return self.use_combat_dodge()
        if option.action == CombatMenuAction.DISENGAGE:
            return self.use_combat_disengage()
        if option.action == CombatMenuAction.HELP:
            return self.start_combat_help()
        if option.action == CombatMenuAction.READY:
            return self.start_combat_ready()
        if option.action == CombatMenuAction.HIDE:
            return self.start_combat_hide()
        if option.action == CombatMenuAction.SEARCH:
            return self.start_combat_search()
        if option.action == CombatMenuAction.SHOVE and option.target_actor_id and option.shove_mode:
            return self.start_combat_shove(
                target_id=option.target_actor_id,
                mode=option.shove_mode,
            )
        if option.action == CombatMenuAction.GRAPPLE and option.grapple_mode:
            return self.start_combat_grapple(
                target_id=option.target_actor_id or "",
                mode=option.grapple_mode,
            )
        if option.action == CombatMenuAction.DROP_PRONE:
            return self.drop_combat_prone()
        if option.action == CombatMenuAction.STAND_UP:
            return self.stand_combat_up()
        if option.action == CombatMenuAction.END_TURN:
            return self.finish_combat_turn()
        raise ValueError("Wybrana opcja menu nie jest obsługiwana.")

    def _start_approach_interaction(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        actor = combat_current_actor(self.combat_state)
        plan = self.combat_scene_interaction_flow.plan_approach(
            state=self.combat_state,
            board=encounter.board,
            scene_objects=encounter.scene_objects,
            actor=actor,
            position=position,
        )
        if plan is None or plan.path.cost_feet <= 0:
            raise ValueError("Nie można teraz podejść do wybranej interakcji.")
        self.pending_approach_interaction = plan
        self._record(
            "ui_combat_approach_interaction_started",
            {
                "actor_id": plan.actor_id,
                "object_id": plan.object_id,
                "interaction_position": [position.col, position.row],
                "destination": [plan.destination.col, plan.destination.row],
                "cost_feet": plan.path.cost_feet,
            },
        )
        result = self.submit_combat_movement(col=plan.destination.col, row=plan.destination.row)
        if self.pending_opportunity_movement is not None:
            return result
        return self._resume_approach_interaction()

    def _resume_approach_interaction(self) -> dict[str, object]:
        plan = self.pending_approach_interaction
        if plan is None:
            return self.state_payload()
        if self.combat_state is None:
            self.pending_approach_interaction = None
            return self.state_payload()
        actor = combat_current_actor(self.combat_state)
        if str(actor.id) != plan.actor_id or actor.position != plan.destination or actor.is_defeated():
            self.pending_approach_interaction = None
            self.board_message = "Nie udało się dotrzeć do obiektu, więc interakcja nie została wykonana."
            self._add_message("Interakcja", self.board_message)
            self._sync_board_leds()
            return self.state_payload()
        if self.pending_concentration_check is not None:
            self.board_message = "Najpierw rozstrzygnij koncentrację; potem bohater dokończy interakcję."
            self._sync_board_leds()
            return self.state_payload()
        self.pending_approach_interaction = None
        return self.select_combat_interaction_at_position(plan.interaction_position)

    def _start_approach_pickup(self, dropped_weapon_id: str, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        dropped = next(
            (
                item
                for item in self.combat_state.dropped_weapons
                if item.id == dropped_weapon_id and item.position == position
            ),
            None,
        )
        if dropped is None:
            raise ValueError("Broń nie leży już na wybranym polu.")
        self.pending_approach_pickup = PendingApproachPickup(
            actor_id=str(actor.id),
            dropped_weapon_id=dropped.id,
            destination=position,
        )
        self._record(
            "ui_combat_approach_pickup_started",
            {
                "actor_id": str(actor.id),
                "dropped_weapon_id": dropped.id,
                "destination": [position.col, position.row],
            },
        )
        result = self.submit_combat_movement(col=position.col, row=position.row)
        if self.pending_opportunity_movement is not None:
            return result
        return self._resume_approach_pickup()

    def _resume_approach_pickup(self) -> dict[str, object]:
        pending = self.pending_approach_pickup
        if pending is None:
            return self.state_payload()
        if self.combat_state is None:
            self.pending_approach_pickup = None
            return self.state_payload()
        actor = combat_current_actor(self.combat_state)
        if str(actor.id) != pending.actor_id or actor.position != pending.destination or actor.is_defeated():
            self.pending_approach_pickup = None
            self.board_message = "Nie udało się dotrzeć do broni, więc nie została podniesiona."
            self._add_message("Ekwipunek", self.board_message)
            self._sync_board_leds()
            return self.state_payload()
        if self.pending_concentration_check is not None:
            self.board_message = "Najpierw rozstrzygnij koncentrację; potem bohater podniesie broń."
            self._sync_board_leds()
            return self.state_payload()
        self.pending_approach_pickup = None
        return self._pickup_dropped_weapon(pending.dropped_weapon_id)

    def _resume_pending_approach_action(self) -> dict[str, object]:
        if self.pending_approach_interaction is not None:
            return self._resume_approach_interaction()
        if self.pending_approach_pickup is not None:
            return self._resume_approach_pickup()
        return self.state_payload()

    def _pickup_dropped_weapon(self, dropped_weapon_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = pickup_dropped_weapon(self.combat_state, dropped_weapon_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_combat_movement_path = None
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_dropped_weapon_picked_up",
            {
                "actor_id": str(result.actor.id),
                "dropped_weapon_id": dropped_weapon_id,
                "weapon_id": result.weapon.id if result.weapon is not None else None,
                "used_action": result.used_action,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _equip_combat_weapon(self, weapon_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = equip_weapon(self.combat_state, weapon_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        if result.weapon is not None:
            actor_sources = self._attack_sources_for_actor(result.actor)
            source_keys = {result.weapon.id, result.weapon.source_ref}
            selected = next(
                (source for source in actor_sources if source.source_item_id in source_keys),
                None,
            )
            if selected is not None:
                self.selected_attack_source_ids[str(result.actor.id)] = selected.id
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_weapon_equipped",
            {
                "actor_id": str(result.actor.id),
                "weapon_id": weapon_id,
                "replaced_weapon_ids": [item.id for item in result.replaced_weapons],
                "used_action": result.used_action,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _drop_combat_weapon(self, weapon_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = drop_weapon(self.combat_state, weapon_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_attack_source_ids.pop(str(result.actor.id), None)
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_weapon_dropped",
            {
                "actor_id": str(result.actor.id),
                "weapon_id": weapon_id,
                "dropped_weapon_id": result.dropped_weapon.id if result.dropped_weapon is not None else None,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _stow_combat_weapon(self, weapon_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = stow_weapon(self.combat_state, weapon_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_attack_source_ids.pop(str(result.actor.id), None)
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_weapon_stowed",
            {
                "actor_id": str(result.actor.id),
                "weapon_id": weapon_id,
                "used_action": result.used_action,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _don_combat_shield(self, shield_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = don_shield(self.combat_state, shield_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_attack_source_ids.pop(str(result.actor.id), None)
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_shield_donned",
            {
                "actor_id": str(result.actor.id),
                "shield_id": shield_id,
                "replaced_item_ids": [item.id for item in result.replaced_items],
                "armor_class": effective_armor_class(result.actor),
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _doff_combat_shield(self, shield_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = doff_shield(self.combat_state, shield_id)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.board_message = result.message
        self._add_message("Ekwipunek", result.message)
        self._record(
            "ui_combat_shield_doffed",
            {
                "actor_id": str(result.actor.id),
                "shield_id": shield_id,
                "armor_class": effective_armor_class(result.actor),
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def _combat_interaction_positions(self, encounter: LoadedEncounter, actor: Actor) -> tuple[Coordinate, ...]:
        if self.combat_state is None:
            return ()
        return self.combat_scene_interaction_flow.positions(
            state=self.combat_state,
            scene_objects=encounter.scene_objects,
            actor=actor,
        )

    def _combat_interaction_hint_positions(
        self,
        encounter: LoadedEncounter,
        actor: Actor,
        movement: MovementRangeResult,
    ) -> tuple[Coordinate, ...]:
        if self.combat_state is None:
            return ()
        return self.combat_scene_interaction_flow.hint_positions(
            state=self.combat_state,
            scene_objects=encounter.scene_objects,
            actor=actor,
            reachable_tiles=movement.reachable_tiles,
        )

    def _scene_object_by_id(self, encounter: LoadedEncounter, object_id: str):
        return scene_object_by_id(encounter.scene_objects, object_id)

    def _expire_invalid_combat_effects(self) -> None:
        if self.combat_state is None or not self.active_combat_effects:
            return
        encounter = self._active_encounter()
        scene_objects = encounter.scene_objects if encounter is not None else ()
        transition = self.combat_scene_interaction_flow.expire_invalid_effects(
            state=self.combat_state,
            scene_objects=scene_objects,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        if transition.expired_effects:
            labels = ", ".join(effect.label for effect in transition.expired_effects)
            self._add_message("Efekty", f"Wygasły efekty pozycyjne: {labels}.")

    def _expire_turn_start_effects(self) -> None:
        if self.combat_state is None or not self.active_combat_effects or self.combat_state.status.value != "active":
            return
        actor = combat_current_actor(self.combat_state)
        before = self.active_combat_effects
        self.active_combat_effects = expire_turn_start_effects(self.active_combat_effects, str(actor.id))
        if before != self.active_combat_effects:
            self._add_expired_effects_message(f"Wygasły efekty początku tury: {actor.name}", before, self.active_combat_effects)

    def _expire_turn_end_effects(self, actor: Actor) -> None:
        if not self.active_combat_effects:
            return
        before = self.active_combat_effects
        self.active_combat_effects = expire_turn_end_effects(self.active_combat_effects, str(actor.id))
        if before != self.active_combat_effects:
            self._add_expired_effects_message(f"Wygasły efekty końca tury: {actor.name}", before, self.active_combat_effects)

    def _add_expired_effects_message(
        self,
        prefix: str,
        before: tuple[ActiveCombatEffect, ...],
        after: tuple[ActiveCombatEffect, ...],
    ) -> None:
        after_ids = {effect.id for effect in after}
        expired = [effect for effect in before if effect.id not in after_ids]
        labels = ", ".join(effect.label for effect in expired) or "efekt"
        self._add_message("Efekty", f"{prefix}: {labels}.")

    def _add_expired_effect_notices(
        self,
        notices: tuple[ExpiredCombatEffects, ...],
    ) -> None:
        for notice in notices:
            labels = ", ".join(effect.label for effect in notice.effects) or "efekt"
            self._add_message("Efekty", f"{notice.message_prefix}: {labels}.")

    def _add_trigger_activation_notices(self, activations) -> None:
        for activation in activations:
            actor = next(
                (
                    candidate
                    for candidate in (
                        self.combat_state.actors
                        if self.combat_state is not None
                        else self.exploration.actors
                    )
                    if str(candidate.id) == activation.owner_actor_id
                ),
                None,
            )
            actor_name = actor.name if actor is not None else activation.owner_actor_id
            body = (
                f"{actor_name}: {activation.trigger.label} — temporary HP "
                f"{activation.previous_temp_hp} → {activation.current_temp_hp}."
            )
            self._add_message("Aktywowano cechę", body)
            self._record(
                "ui_actor_trigger_activated",
                {
                    "actor_id": activation.owner_actor_id,
                    "trigger_id": activation.trigger.id,
                    "event_type": activation.trigger.event_type.value,
                    "effect_kind": activation.trigger.effect_kind.value,
                    "changed": activation.changed,
                    "previous_temp_hp": activation.previous_temp_hp,
                    "current_temp_hp": activation.current_temp_hp,
                },
            )

    def _apply_combat_trigger_events(self, events: tuple[EffectEvent, ...]) -> None:
        if self.combat_state is None or not events:
            return
        resolution = resolve_combat_trigger_events(self.combat_state, events)
        self.combat_state = resolution.state
        self._add_trigger_activation_notices(resolution.activations)

    def _add_recharge_notices(self, results) -> None:
        for result in results:
            pool = actor_resource_pool(result.actor_after, result.resource_id)
            if pool is None or pool.recharge is None:
                continue
            outcome = "odnowiona" if result.recharged else "nadal niedostępna"
            self._add_message(
                "Recharge",
                (
                    f"{result.actor_after.name}: {pool.label} — d{pool.recharge.die_sides} "
                    f"{result.natural_roll}, wymaga {pool.recharge.minimum_roll}+; {outcome}."
                ),
            )
            self._record(
                "ui_actor_resource_recharge_rolled",
                {
                    "actor_id": str(result.actor_after.id),
                    "resource_id": result.resource_id,
                    "natural_roll": result.natural_roll,
                    "minimum_roll": pool.recharge.minimum_roll,
                    "recharged": result.recharged,
                    "current": pool.current,
                    "maximum": pool.maximum,
                },
            )

    def resolve_enemy_turn(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        if self.pending_enemy_turn_intent is None:
            transition = self.enemy_turn_flow.plan(
                state=self.combat_state,
                board=encounter.board,
                attack_sources_by_actor=encounter.attack_sources_by_actor,
                multiattack_sources_by_actor=encounter.multiattack_sources_by_actor,
                scene_objects=encounter.scene_objects,
            )
            self.pending_enemy_turn_intent = transition.intent
            self.board_message = transition.board_message
            self._add_message(transition.message_title, transition.message_body)
            self._record(transition.event_type, dict(transition.event_payload))
            self._sync_board_leds()
            return self.state_payload()
        intent = self.pending_enemy_turn_intent
        self.pending_enemy_turn_intent = None
        transition = self.enemy_turn_flow.resolve(
            state=self.combat_state,
            intent=intent,
            board=encounter.board,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            multiattack_sources_by_actor=encounter.multiattack_sources_by_actor,
            active_effects=self.active_combat_effects,
            rng=self.encounter_rng,
            scene_objects=encounter.scene_objects,
        )
        result = transition.result
        if transition.kind == EnemyTurnTransitionKind.FINISHED:
            return self._finish_pending_enemy_turn(result)
        self.pending_enemy_turn_result = result
        self.board_message = transition.board_message
        if transition.kind == EnemyTurnTransitionKind.READY:
            ready = transition.ready_trigger
            assert ready is not None
            self.pending_ready_attack = PendingReadyAttack(
                readied_actor_id=ready.readied_actor_id,
                target_id=ready.target_id,
                effect_id=ready.effect_id,
                trigger=ready.trigger,
            )
        elif transition.kind == EnemyTurnTransitionKind.OPPORTUNITY:
            self.pending_enemy_opportunity_attack = PendingEnemyOpportunityAttack(
                target_id=str(result.enemy.id),
                threat_actor_ids=transition.threat_actor_ids,
            )
        if transition.message_title:
            self._add_message(transition.message_title, transition.message_body)
        if transition.event_type:
            self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

    def _commit_pending_enemy_turn(self, result=None) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = result or self.pending_enemy_turn_result
        if result is None:
            raise ValueError("Brak oczekującej tury przeciwnika do potwierdzenia.")
        transition = self.combat_turn_finalization.commit_enemy_result(
            result=result,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_approach_interaction = None
        self.pending_approach_pickup = None
        self.pending_enemy_turn_ack_result = transition.result
        if transition.result.saving_throw_request is not None and transition.result.target is not None:
            request = transition.result.saving_throw_request
            self.pending_enemy_saving_throw = PendingEnemySavingThrow(
                target_id=transition.result.target.id,
                source_id=transition.result.source.id if transition.result.source is not None else "",
                request=request,
            )
            self.board_message = (
                f"{transition.result.target.name}: rzuć fizyczne d20 na "
                f"{request.as_payload()['ability_label']} przeciw ST {request.dc} i wpisz wynik."
            )
            self._add_message("Rzut obronny", self.board_message)
        else:
            self.pending_enemy_saving_throw = None
            self.board_message = transition.board_message
        self._record(transition.event_type, dict(transition.event_payload))
        trigger_events = []
        if result.movement_path is not None and result.moved_enemy is not None:
            trigger_events.append(
                EffectEvent(
                    EffectEventType.ACTOR_MOVED,
                    actor_id=str(result.enemy.id),
                    position=result.moved_enemy.position,
                )
            )
        if result.applied_damage is not None:
            target_id = str(result.applied_damage.actor_after.id)
            if result.attack_resolution is not None and result.attack_resolution.hit:
                trigger_events.append(
                    EffectEvent(
                        EffectEventType.ATTACK_HIT,
                        actor_id=str(result.enemy.id),
                        target_actor_id=target_id,
                    )
                )
            if result.applied_damage.damage.total_applied > 0:
                trigger_events.append(
                    EffectEvent(
                        EffectEventType.DAMAGE_TAKEN,
                        actor_id=target_id,
                        target_actor_id=str(result.enemy.id),
                    )
                )
        self._apply_combat_trigger_events(tuple(trigger_events))
        self.pending_enemy_turn_ack_result = replace(
            transition.result,
            state=self.combat_state,
        )
        if result.applied_damage is not None:
            self._maybe_prompt_concentration_check(result.applied_damage)
        self._sync_board_leds()
        return self.state_payload()

    def submit_enemy_saving_throw(
        self,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.pending_enemy_saving_throw is None:
            raise ValueError("Brak oczekującego rzutu obronnego przeciw efektowi przeciwnika.")
        result = self.pending_enemy_turn_ack_result
        if result is None:
            raise ValueError("Brak wyniku tury przeciwnika dla rzutu obronnego.")
        transition = self.enemy_turn_flow.resolve_player_saving_throw(
            result=result,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
        )
        self.combat_state = transition.result.state
        self.pending_enemy_turn_ack_result = transition.result
        self.pending_enemy_saving_throw = None
        self.board_message = transition.board_message
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        if transition.result.applied_damage is not None:
            applied = transition.result.applied_damage
            if applied.damage.total_applied > 0:
                self._apply_combat_trigger_events(
                    (
                        EffectEvent(
                            EffectEventType.DAMAGE_TAKEN,
                            actor_id=str(applied.actor_after.id),
                            target_actor_id=str(transition.result.enemy.id),
                        ),
                    )
                )
                self.pending_enemy_turn_ack_result = replace(
                    transition.result,
                    state=self.combat_state,
                )
            self._maybe_prompt_concentration_check(transition.result.applied_damage)
        self._sync_board_leds()
        return self.state_payload()

    def start_enemy_opportunity_attack(self) -> dict[str, object]:
        pending = self.pending_enemy_opportunity_attack
        if pending is None or pending.stage != "choice":
            raise ValueError("Nie ma ataku okazyjnego bohatera do rozpoczęcia.")
        attacker = self._actor_by_string_id(pending.attacker_id)
        target = self._actor_by_string_id(pending.target_id)
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = self._effective_attack_source(attacker, source, target)
        self.pending_enemy_opportunity_attack = replace(pending, stage="attack_roll")
        self.board_message = f"{attacker.name} wykonuje atak okazyjny przeciwko {target.name}. Wpisz rzut d20."
        self._add_message("Atak okazyjny", f"{attacker.name} reaguje atakiem okazyjnym. {roll_instruction(source.attack_roll_request).message}")
        self._record(
            "ui_combat_enemy_opportunity_started",
            {"attacker_id": pending.attacker_id, "target_id": pending.target_id},
        )
        self._sync_board_leds()
        return self.state_payload()

    def skip_enemy_opportunity_attack(self) -> dict[str, object]:
        pending = self.pending_enemy_opportunity_attack
        if pending is None or pending.stage != "choice":
            raise ValueError("Nie ma ataku okazyjnego bohatera do pominięcia.")
        attacker = self._actor_by_string_id(pending.attacker_id)
        self._add_message("Atak okazyjny", f"{attacker.name} nie używa reakcji.")
        self._record(
            "ui_combat_enemy_opportunity_skipped",
            {"attacker_id": pending.attacker_id, "target_id": pending.target_id},
        )
        return self._advance_enemy_opportunity_or_resume_preview()

    def submit_enemy_opportunity_attack_roll(self, *, natural_roll: int, natural_roll_2: int | None = None) -> dict[str, object]:
        pending = self.pending_enemy_opportunity_attack
        if pending is None or pending.stage != "attack_roll":
            raise ValueError("Nie ma oczekującego rzutu ataku okazyjnego.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        reaction = self.player_reaction_flow.resolve_attack_roll(
            state=self.combat_state,
            attacker_id=pending.attacker_id,
            target_id=pending.target_id,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
        )
        self.combat_state = reaction.state
        self.active_combat_effects = reaction.active_effects
        self.pending_enemy_turn_result = self._enemy_turn_result_with_spent_reactions()
        self._record(
            "ui_combat_enemy_opportunity_attack_roll",
            {
                "attacker_id": pending.attacker_id,
                "target_id": pending.target_id,
                "natural_roll": reaction.attack_roll.natural_roll,
                "natural_rolls": list(reaction.attack_roll.natural_rolls),
                "total": reaction.attack_roll.total,
                "hit": reaction.hit,
                "critical": reaction.critical,
            },
        )
        if not reaction.hit:
            self._add_message("Atak okazyjny", reaction.message)
            return self._advance_enemy_opportunity_or_resume_preview()
        self._apply_combat_trigger_events(
            (
                EffectEvent(
                    EffectEventType.ATTACK_HIT,
                    actor_id=pending.attacker_id,
                    target_actor_id=pending.target_id,
                ),
            )
        )
        if self.pending_enemy_turn_result is not None:
            self.pending_enemy_turn_result = replace(
                self.pending_enemy_turn_result,
                state=self.combat_state,
            )
        self.pending_enemy_opportunity_attack = replace(
            pending,
            stage="damage_roll",
            natural_roll=reaction.attack_roll.natural_roll,
            natural_rolls=reaction.attack_roll.natural_rolls,
            total=reaction.attack_roll.total,
            hit=True,
            critical=reaction.critical,
        )
        self._add_message(
            "Atak okazyjny",
            f"{reaction.message} Trafienie: rzuć obrażenia {reaction.source.damage_hint} i wpisz sumę.",
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_enemy_opportunity_damage_roll(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_enemy_opportunity_attack
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekujących obrażeń ataku okazyjnego.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        damage_resolution = self.player_reaction_flow.apply_damage(
            state=self.combat_state,
            attacker_id=pending.attacker_id,
            target_id=pending.target_id,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            damage=damage,
            critical=pending.critical,
        )
        applied_damage = damage_resolution.applied_damage
        updated_target = applied_damage.actor_after
        self.combat_state = damage_resolution.state
        self.pending_enemy_turn_result = self._enemy_turn_result_with_updated_actor(updated_target)
        attacker = self._actor_by_string_id(pending.attacker_id)
        message = f"{attacker.name} trafia atakiem okazyjnym. {_damage_application_message(applied_damage)}"
        self._record(
            "ui_combat_enemy_opportunity_damage",
            {
                "attacker_id": pending.attacker_id,
                "target_id": pending.target_id,
                "damage": applied_damage.damage.total_applied,
                "damage_result": _applied_damage_payload(applied_damage),
            },
        )
        reaction_events = []
        if applied_damage.damage.total_applied > 0:
            reaction_events.append(
                EffectEvent(
                    EffectEventType.DAMAGE_TAKEN,
                    actor_id=pending.target_id,
                    target_actor_id=pending.attacker_id,
                )
            )
        self._apply_combat_trigger_events(tuple(reaction_events))
        if self.pending_enemy_turn_result is not None:
            self.pending_enemy_turn_result = replace(
                self.pending_enemy_turn_result,
                state=self.combat_state,
            )
        if applied_damage.defeated_by_damage:
            self.pending_enemy_opportunity_attack = None
            self.pending_enemy_turn_result = None
            self.pending_enemy_turn_intent = None
            self.pending_enemy_turn_ack_result = None
            self._add_message("Atak okazyjny", f"{message} Ruch przeciwnika zostaje przerwany.")
            self._expire_turn_end_effects(updated_target)
            self.combat_state = finish_turn(self.combat_state)
            self._expire_turn_start_effects()
            self.board_message = f"{updated_target.name} pada od ataku okazyjnego. Tura przeciwnika zakończona."
            self._record("ui_combat_enemy_opportunity_defeated_enemy", {"enemy_id": pending.target_id})
            self._maybe_prompt_concentration_check(applied_damage)
            self._sync_board_leds()
            return self.state_payload()
        self._maybe_prompt_concentration_check(applied_damage)
        self._add_message("Atak okazyjny", message)
        return self._advance_enemy_opportunity_or_resume_preview()

    def _advance_enemy_opportunity_or_resume_preview(self) -> dict[str, object]:
        pending = self.pending_enemy_opportunity_attack
        if pending is None:
            return self.state_payload()
        next_index = pending.current_index + 1
        if next_index < len(pending.threat_actor_ids):
            self.pending_enemy_opportunity_attack = replace(
                pending,
                current_index=next_index,
                stage="choice",
                natural_roll=None,
                total=None,
                hit=None,
                critical=False,
            )
            next_attacker = self._actor_by_string_id(self.pending_enemy_opportunity_attack.attacker_id)
            target = self._actor_by_string_id(pending.target_id)
            self.board_message = f"{target.name} nadal prowokuje reakcję: {next_attacker.name}."
            self._sync_board_leds()
            return self.state_payload()
        self.pending_enemy_opportunity_attack = None
        result = self.pending_enemy_turn_result
        if result is not None and result.movement_path is not None:
            self.board_message = (
                f"{result.enemy.name} rusza na {result.movement_path.destination.as_tuple()}. "
                "Przestaw figurkę po podświetlonej ścieżce i kliknij pole docelowe."
            )
        self._sync_board_leds()
        return self.state_payload()

    def start_ready_attack(self) -> dict[str, object]:
        pending = self.pending_ready_attack
        if pending is None or pending.stage != "choice":
            raise ValueError("Nie ma przygotowanej akcji do rozpoczęcia.")
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        target = self._actor_by_string_id(pending.target_id)
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = self._effective_attack_source(attacker, source, target)
        self.pending_ready_attack = replace(pending, stage="attack_roll")
        self.board_message = f"{attacker.name} używa przygotowanej akcji przeciwko {target.name}. Wpisz rzut d20."
        self._add_message("Ready", f"{attacker.name} używa przygotowanej akcji. {roll_instruction(source.attack_roll_request).message}")
        self._record(
            "ui_combat_ready_attack_started",
            {"attacker_id": pending.readied_actor_id, "target_id": pending.target_id, "trigger": pending.trigger},
        )
        self._sync_board_leds()
        return self.state_payload()

    def skip_ready_attack(self) -> dict[str, object]:
        pending = self.pending_ready_attack
        if pending is None or pending.stage != "choice":
            raise ValueError("Nie ma przygotowanej akcji do pominięcia.")
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        self.pending_ready_attack = None
        self._add_message("Ready", f"{attacker.name} nie używa przygotowanej akcji.")
        self._record(
            "ui_combat_ready_attack_skipped",
            {"attacker_id": pending.readied_actor_id, "target_id": pending.target_id, "trigger": pending.trigger},
        )
        self._resume_enemy_turn_after_reaction_prompt()
        return self.state_payload()

    def submit_ready_attack_roll(self, *, natural_roll: int, natural_roll_2: int | None = None) -> dict[str, object]:
        pending = self.pending_ready_attack
        if pending is None or pending.stage != "attack_roll":
            raise ValueError("Nie ma oczekującego rzutu przygotowanej akcji.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        reaction = self.player_reaction_flow.resolve_attack_roll(
            state=self.combat_state,
            attacker_id=pending.readied_actor_id,
            target_id=pending.target_id,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
            consumed_effect_id=pending.effect_id,
        )
        self.combat_state = reaction.state
        self.active_combat_effects = reaction.active_effects
        self.pending_enemy_turn_result = self._enemy_turn_result_with_spent_reactions()
        self._record(
            "ui_combat_ready_attack_roll",
            {
                "attacker_id": pending.readied_actor_id,
                "target_id": pending.target_id,
                "natural_roll": reaction.attack_roll.natural_roll,
                "natural_rolls": list(reaction.attack_roll.natural_rolls),
                "total": reaction.attack_roll.total,
                "hit": reaction.hit,
                "critical": reaction.critical,
            },
        )
        if not reaction.hit:
            self.pending_ready_attack = None
            self._add_message("Ready", reaction.message)
            self._resume_enemy_turn_after_reaction_prompt()
            return self.state_payload()
        self._apply_combat_trigger_events(
            (
                EffectEvent(
                    EffectEventType.ATTACK_HIT,
                    actor_id=pending.readied_actor_id,
                    target_actor_id=pending.target_id,
                ),
            )
        )
        if self.pending_enemy_turn_result is not None:
            self.pending_enemy_turn_result = replace(
                self.pending_enemy_turn_result,
                state=self.combat_state,
            )
        self.pending_ready_attack = replace(
            pending,
            stage="damage_roll",
            natural_roll=reaction.attack_roll.natural_roll,
            natural_rolls=reaction.attack_roll.natural_rolls,
            total=reaction.attack_roll.total,
            hit=True,
            critical=reaction.critical,
        )
        self._add_message(
            "Ready",
            f"{reaction.message} Trafienie: rzuć obrażenia {reaction.source.damage_hint} i wpisz sumę.",
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_ready_damage_roll(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_ready_attack
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekujących obrażeń przygotowanej akcji.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        damage_resolution = self.player_reaction_flow.apply_damage(
            state=self.combat_state,
            attacker_id=pending.readied_actor_id,
            target_id=pending.target_id,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
            damage=damage,
            critical=pending.critical,
        )
        applied_damage = damage_resolution.applied_damage
        updated_target = applied_damage.actor_after
        self.combat_state = damage_resolution.state
        self.pending_enemy_turn_result = self._enemy_turn_result_with_updated_actor(updated_target)
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        message = f"{attacker.name} trafia przygotowaną akcją. {_damage_application_message(applied_damage)}"
        self._record(
            "ui_combat_ready_damage",
            {
                "attacker_id": pending.readied_actor_id,
                "target_id": pending.target_id,
                "damage": applied_damage.damage.total_applied,
                "damage_result": _applied_damage_payload(applied_damage),
            },
        )
        ready_events = []
        if applied_damage.damage.total_applied > 0:
            ready_events.append(
                EffectEvent(
                    EffectEventType.DAMAGE_TAKEN,
                    actor_id=pending.target_id,
                    target_actor_id=pending.readied_actor_id,
                )
            )
        self._apply_combat_trigger_events(tuple(ready_events))
        if self.pending_enemy_turn_result is not None:
            self.pending_enemy_turn_result = replace(
                self.pending_enemy_turn_result,
                state=self.combat_state,
            )
        self.pending_ready_attack = None
        if applied_damage.defeated_by_damage:
            self.pending_enemy_turn_result = None
            self.pending_enemy_turn_intent = None
            self.pending_enemy_turn_ack_result = None
            self.pending_enemy_opportunity_attack = None
            self._add_message("Ready", f"{message} Tura przeciwnika zostaje przerwana.")
            self._expire_turn_end_effects(updated_target)
            self.combat_state = finish_turn(self.combat_state)
            self._expire_turn_start_effects()
            self.board_message = f"{updated_target.name} pada od przygotowanej akcji. Tura przeciwnika zakończona."
            self._record("ui_combat_ready_defeated_enemy", {"enemy_id": pending.target_id})
            self._maybe_prompt_concentration_check(applied_damage)
            self._sync_board_leds()
            return self.state_payload()
        self._maybe_prompt_concentration_check(applied_damage)
        self._add_message("Ready", message)
        self._resume_enemy_turn_after_reaction_prompt()
        return self.state_payload()

    def _resume_enemy_turn_after_reaction_prompt(self) -> None:
        result = self.pending_enemy_turn_result
        if result is None:
            self._sync_board_leds()
            return
        if result.movement_path is not None and result.movement_path.valid and result.movement_path.destination != result.enemy.position:
            self.board_message = (
                f"{result.enemy.name} rusza na {result.movement_path.destination.as_tuple()}. "
                "Przestaw figurkę po podświetlonej ścieżce i kliknij pole docelowe."
            )
        elif result.target is not None:
            self.board_message = f"{result.enemy.name} atakuje {result.target.name}. Kliknij podświetlone pole celu, żeby potwierdzić atak."
        self._sync_board_leds()

    def _enemy_turn_result_with_updated_actor(self, updated_actor: Actor):
        result = self.pending_enemy_turn_result
        if result is None:
            return None
        result_actor = next((actor for actor in result.state.actors if actor.id == updated_actor.id), None)
        if result_actor is None:
            return result
        merged_actor = replace(
            result_actor,
            hp=updated_actor.hp,
            temp_hp=updated_actor.temp_hp,
            death_saves=updated_actor.death_saves,
        )
        updated_state = replace_actor(result.state, merged_actor)
        if self.combat_state is not None:
            updated_state = replace(updated_state, spent_reaction_actor_ids=self.combat_state.spent_reaction_actor_ids)
        moved_enemy = merged_actor if result.moved_enemy is not None and result.moved_enemy.id == merged_actor.id else result.moved_enemy
        return replace(result, state=updated_state, moved_enemy=moved_enemy)

    def _enemy_turn_result_with_spent_reactions(self):
        result = self.pending_enemy_turn_result
        if result is None or self.combat_state is None:
            return result
        return replace(result, state=replace(result.state, spent_reaction_actor_ids=self.combat_state.spent_reaction_actor_ids))

    def _pending_ready_attack_for_enemy_result(self, result) -> PendingReadyAttack | None:
        if self.combat_state is None:
            return None
        encounter = self._active_encounter()
        if encounter is None:
            return None
        trigger = self.player_reaction_flow.detect_ready_attack(
            state=self.combat_state,
            enemy_result=result,
            board=encounter.board,
            attack_sources_by_actor=encounter.attack_sources_by_actor,
            active_effects=self.active_combat_effects,
        )
        if trigger is None:
            return None
        return PendingReadyAttack(
            readied_actor_id=trigger.readied_actor_id,
            target_id=trigger.target_id,
            effect_id=trigger.effect_id,
            trigger=trigger.trigger,
        )

    def _actor_by_string_id(self, actor_id: str) -> Actor:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = next((candidate for candidate in self.combat_state.actors if str(candidate.id) == actor_id), None)
        if actor is None:
            raise ValueError(f"Nieznany aktor walki: {actor_id}.")
        return actor

    def confirm_enemy_turn_result(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = self.pending_enemy_turn_ack_result
        if result is None:
            raise ValueError("Brak wyniku tury przeciwnika do potwierdzenia.")
        if self.pending_enemy_saving_throw is not None:
            raise ValueError("Najpierw wpisz naturalny wynik rzutu obronnego gracza.")
        remaining = attack_action_remaining(self.combat_state, result.enemy)
        if self.combat_state.status.value == "active" and remaining > 0:
            self.pending_enemy_turn_ack_result = None
            self.pending_enemy_turn_intent = None
            self.board_message = (
                f"{result.enemy.name}: pozostało ataków w Multiattack: {remaining}. "
                "Potwierdź, aby zaplanować kolejny atak."
            )
            self._add_message("Multiattack", self.board_message)
            self._record(
                "ui_combat_enemy_multiattack_continues",
                {"enemy_id": str(result.enemy.id), "attacks_remaining": remaining},
            )
            self._sync_board_leds()
            return self.state_payload()
        return self._finish_pending_enemy_turn(result)

    def _finish_pending_enemy_turn(self, result) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = replace(
            result,
            state=self._resolve_automatic_condition_saves(
                result.state,
                result.enemy,
                ConditionSaveTiming.TURN_END,
            ),
        )
        transition = self.combat_turn_finalization.finalize_enemy_turn(
            result=result,
            active_effects=self.active_combat_effects,
            roll_recharge=lambda die_sides: self.encounter_rng.randint(1, die_sides),
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._add_expired_effect_notices(transition.expired_effects)
        self._add_trigger_activation_notices(transition.trigger_activations)
        self._add_recharge_notices(transition.recharge_results)
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_enemy_turn_ack_result = None
        self.pending_enemy_saving_throw = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._resolve_starting_enemy_condition_saves()
        self._sync_board_leds()
        return self.state_payload()

    def _resolve_starting_enemy_condition_saves(self) -> None:
        if self.combat_state is None or self.combat_state.status != CombatStatus.ACTIVE:
            return
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ENEMY:
            return
        self.combat_state = self._resolve_automatic_condition_saves(
            self.combat_state,
            actor,
            ConditionSaveTiming.TURN_START,
        )

    def _resolve_automatic_condition_saves(
        self,
        state: CombatState,
        actor: Actor,
        timing: ConditionSaveTiming,
    ) -> CombatState:
        condition_states = state.condition_states
        saves = pending_condition_saves(condition_states, str(actor.id), timing)
        for condition_state in saves:
            assert condition_state.save_ability is not None
            request = condition_roll_request(
                D20RollRequest(
                    modifiers=saving_throw_roll_modifiers(
                        actor,
                        condition_state.save_ability,
                    )
                ),
                condition_states,
                actor,
                saving_throw_ability=condition_state.save_ability,
            )
            natural_roll = self.encounter_rng.randint(1, 20)
            natural_roll_2 = (
                self.encounter_rng.randint(1, 20)
                if request.mode != RollMode.NORMAL
                else None
            )
            resolution = resolve_condition_save(
                condition_states,
                actor,
                condition_state,
                natural_roll=natural_roll,
                natural_roll_2=natural_roll_2,
                combat_actors=state.actors,
            )
            condition_states = resolution.condition_states
            result_label = "usunięty" if resolution.removed else "pozostaje"
            self._add_message(
                "Rzut przeciw warunkowi",
                (
                    f"{actor.name}: {condition_label(condition_state.condition)} — "
                    f"wynik {resolution.saving_throw.total} "
                    f"przeciw ST {condition_state.save_dc}; "
                    f"stan {result_label}."
                ),
            )
            self._record(
                "ui_combat_condition_save_automatic",
                {
                    "actor_id": str(actor.id),
                    "condition": condition_state.condition.value,
                    "timing": timing.value,
                    "natural_roll": natural_roll,
                    "natural_roll_2": natural_roll_2,
                    "total": resolution.saving_throw.total,
                    "removed": resolution.removed,
                },
            )
        return replace(state, condition_states=condition_states)

    def reset_board_scan(self) -> dict[str, object]:
        if self.board_adapter is None:
            raise ValueError("Najpierw podłącz backend planszy.")
        action = self.board_adapter.reset_scan()
        self.board_message = "Zresetowano oczekiwanie na kliknięcie planszy."
        self._record("ui_board_scan_reset", {"action": action})
        self._sync_board_leds()
        return self.state_payload()

    def finish_combat_turn(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if combat_current_actor(self.combat_state).needs_death_save():
            raise ValueError("Najpierw wykonaj rzut śmierci aktywnego bohatera.")
        actor = combat_current_actor(self.combat_state)
        if pending_condition_saves(
            self.combat_state.condition_states,
            str(actor.id),
            ConditionSaveTiming.TURN_END,
        ):
            raise ValueError("Najpierw wykonaj rzut obronny końca tury przeciw aktywnemu warunkowi.")
        transition = self.combat_turn_finalization.finish_active_turn(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
            roll_recharge=lambda die_sides: self.encounter_rng.randint(1, die_sides),
        )
        if transition is None:
            return self.state_payload()
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._add_expired_effect_notices(transition.expired_effects)
        self._add_trigger_activation_notices(transition.trigger_activations)
        self._add_recharge_notices(transition.recharge_results)
        self.selected_combat_movement_path = None
        self.combat_targeting_attack_source_id = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_turn_ack_result = None
        self.pending_enemy_saving_throw = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_approach_interaction = None
        self.pending_approach_pickup = None
        self._clear_player_pending_choices()
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._resolve_starting_enemy_condition_saves()
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_condition_save(
        self,
        *,
        condition: str,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        parsed = CombatCondition(condition)
        condition_state = next(
            (
                item
                for item in self.combat_state.condition_states
                if item.actor_id == str(actor.id)
                and item.condition == parsed
                and item.save_timing is not None
            ),
            None,
        )
        if condition_state is None:
            raise ValueError("Aktywny aktor nie ma takiego rzutu kończącego warunek.")
        resolution = resolve_condition_save(
            self.combat_state.condition_states,
            actor,
            condition_state,
            natural_roll=natural_roll,
            natural_roll_2=natural_roll_2,
            combat_actors=self.combat_state.actors,
        )
        self.combat_state = replace(
            self.combat_state,
            condition_states=resolution.condition_states,
        )
        outcome = "sukces — warunek usunięty" if resolution.removed else "porażka — warunek pozostaje"
        self.board_message = (
            f"{actor.name}: {condition_label(parsed)}, save {resolution.saving_throw.total} "
            f"przeciw ST {resolution.saving_throw.dc}: {outcome}."
        )
        self._add_message("Rzut przeciw warunkowi", self.board_message)
        self._record(
            "ui_combat_condition_save",
            {
                "actor_id": str(actor.id),
                "condition": parsed.value,
                "saving_throw": resolution.saving_throw.as_payload(),
                "removed": resolution.removed,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def recover_exploration_condition(
        self,
        *,
        actor_id: str,
        condition: str,
    ) -> dict[str, object]:
        if self.combat_state is not None:
            raise ValueError("W czasie walki użyj akcji właściwej dla danego stanu.")
        parsed_condition = CombatCondition(condition)
        if parsed_condition != CombatCondition.PRONE:
            raise ValueError("Tego stanu nie można usunąć prostą czynnością w eksploracji.")
        actor = next(
            (candidate for candidate in self.exploration.actors if str(candidate.id) == actor_id),
            None,
        )
        if actor is None:
            raise ValueError(f"Nieznany aktor: {actor_id}.")
        if not has_condition(self.state.condition_states, actor_id, parsed_condition):
            raise ValueError(f"{actor.name} nie jest powalony.")
        self.state = remove_exploration_condition(self.state, actor_id, parsed_condition)
        self._add_message("Powrót na nogi", f"{actor.name} wstaje i usuwa stan Powalony.")
        self._record(
            "ui_exploration_condition_recovered",
            {"actor_id": actor_id, "condition": parsed_condition.value},
        )
        return self.state_payload()

    def submit_death_save(self, natural_roll: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        resolution = resolve_death_save(actor, int(natural_roll))
        self.combat_state = replace_actor(self.combat_state, resolution.actor_after)
        saves = resolution.actor_after.death_saves
        outcome_text = {
            DeathSaveOutcome.SUCCESS: "Sukces rzutu śmierci.",
            DeathSaveOutcome.FAILURE: "Porażka rzutu śmierci.",
            DeathSaveOutcome.STABILIZED: "Trzeci sukces: bohater jest stabilny.",
            DeathSaveOutcome.DIED: "Trzecia porażka: bohater umiera.",
            DeathSaveOutcome.REVIVED: "Naturalne 20: bohater odzyskuje 1 HP i może kontynuować turę.",
        }[resolution.outcome]
        self._add_message(
            "Rzut śmierci",
            f"{actor.name}: d20 = {resolution.natural_roll}. {outcome_text} "
            f"Sukcesy: {saves.successes}/3, porażki: {saves.failures}/3.",
        )
        self._record(
            "ui_combat_death_save",
            {
                "actor_id": str(actor.id),
                "natural_roll": resolution.natural_roll,
                "outcome": resolution.outcome.value,
                "successes": saves.successes,
                "failures": saves.failures,
            },
        )
        self._clear_player_pending_choices()
        if resolution.outcome == DeathSaveOutcome.REVIVED:
            self.combat_state = replace(self.combat_state, turn_action=TurnActionState())
            self.board_message = f"{actor.name} odzyskuje przytomność i może rozegrać turę."
            self._sync_board_leds()
            return self.state_payload()
        if self.combat_state.status.value == "active":
            transition = self.combat_turn_finalization.finish_active_turn(
                state=self.combat_state,
                active_effects=self.active_combat_effects,
                roll_recharge=lambda die_sides: self.encounter_rng.randint(1, die_sides),
            )
            if transition is not None:
                self.combat_state = transition.state
                self.active_combat_effects = transition.active_effects
                self._add_expired_effect_notices(transition.expired_effects)
                self._add_trigger_activation_notices(transition.trigger_activations)
                self._add_recharge_notices(transition.recharge_results)
        self.board_message = outcome_text
        self._sync_board_leds()
        return self.state_payload()

    def stabilize_combat_actor(
        self,
        *,
        target_id: str,
        method: str,
        natural_roll: int | None = None,
    ) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        stabilization_method = StabilizationMethod(method)
        result = resolve_combat_stabilization(
            self.combat_state,
            target_id=target_id,
            method=stabilization_method,
            natural_roll=natural_roll,
        )
        self.combat_state = result.state
        if result.method == StabilizationMethod.HEALERS_KIT:
            detail = f"Zestaw uzdrowiciela: bez rzutu. Pozostałe użycia: {result.kit_remaining}."
        else:
            outcome = "sukces" if result.success else "porażka"
            detail = f"Medicine ST 10: d20 {result.natural_roll}, wynik {result.total} — {outcome}."
        effect = (
            f"{result.target.name} jest stabilny."
            if result.success
            else f"{result.target.name} nadal wykonuje rzuty śmierci."
        )
        self.board_message = f"{detail} {effect}"
        self._add_message("Stabilizacja", f"{result.stabilizer.name} pomaga {result.target.name}. {detail} {effect}")
        self._record(
            "ui_combat_stabilization",
            {
                "stabilizer_id": str(result.stabilizer.id),
                "target_id": str(result.target.id),
                "method": result.method.value,
                "natural_roll": result.natural_roll,
                "total": result.total,
                "success": result.success,
                "kit_remaining": result.kit_remaining,
            },
        )
        self._clear_player_pending_choices()
        self._sync_board_leds()
        return self.state_payload()

    def _active_encounter(self) -> LoadedEncounter | None:
        if self.encounter_initiative_flow is not None:
            return self.encounter_initiative_flow.encounter
        if self.encounter_setup_flow is not None:
            return self.encounter_setup_flow.encounter
        return None

    def _board_payload(self) -> dict[str, object]:
        return {
            "backend": self.board_backend,
            "configured_backend": self.configured_board_backend,
            "board_url": self.board_url,
            "board_serial_port": self.board_serial_port,
            "wled_url": self.wled_url,
            "scan_timeout_s": self.scan_timeout_s,
            "connected": self.board_adapter is not None,
            "message": self.board_message,
        }

    def _spell_preparation_payload(self) -> dict[str, object] | None:
        actors = tuple(actor for actor in self.exploration.actors if actor.spell_preparation is not None)
        if not actors:
            return None
        pending = self.spell_preparation_flow.pending_actors(actors)
        return {
            "complete": not pending,
            "current_actor_id": str(pending[0].id) if pending else None,
            "actors": [
                {
                    "actor_id": str(actor.id),
                    "actor_name": actor.name,
                    **actor.spell_preparation.as_payload(),
                }
                for actor in actors
                if actor.spell_preparation is not None
            ],
        }

    def _short_rest_payload(self) -> dict[str, object]:
        pending = self.pending_short_rest
        policy = pending.policy if pending is not None else self.current_zone.short_rest_policy
        completed_count = short_rest_count(self.state, policy.id) if policy is not None else 0
        unavailable_reason: str | None = None
        if policy is None:
            unavailable_reason = "W tej lokacji nie ma warunków do krótkiego odpoczynku."
        elif policy.max_completions and completed_count >= policy.max_completions:
            unavailable_reason = "Możliwość odpoczynku w tej lokacji została już wykorzystana."
        elif self.pending_encounter is not None:
            unavailable_reason = "Encounter czeka na rozpoczęcie."
        elif self.pending is not None or self.active_point is not None:
            unavailable_reason = "Najpierw zakończ aktywną interakcję."
        elif self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE and pending is None:
            unavailable_reason = "Krótki odpoczynek nie jest teraz dostępny."
        return {
            "available": unavailable_reason is None and pending is None,
            "unavailable_reason": unavailable_reason,
            "elapsed_minutes": self.state.elapsed_minutes,
            "elapsed_label": _duration_minutes_label(self.state.elapsed_minutes),
            "policy": _short_rest_policy_payload(policy, completed_count) if policy is not None else None,
            "pending": (
                {
                    "completed": pending.completed,
                    "zone_id": pending.zone_id,
                    "actors": [
                        _short_rest_actor_payload(actor, completed=pending.completed)
                        for actor in self.exploration.actors
                        if actor.faction == Faction.ALLY
                    ],
                }
                if pending is not None
                else None
            ),
        }

    def _sync_board_leds(self) -> None:
        if self.board_adapter is None:
            return
        target = self._current_board_scan_target()
        self._show_board_feedback(target.feedback)

    @staticmethod
    def _passive_focus_target(
        positions: tuple[Coordinate, ...],
        *,
        color: tuple[int, int, int],
        role: LedRole,
        message: str,
    ) -> BoardScanTarget:
        return BoardScanTarget(
            positions=(),
            feedback=(
                LedFeedback((LedFrame(positions, color, role),))
                if positions
                else LedFeedback()
            ),
            empty_message=message,
        )

    def _show_board_feedback(self, feedback: LedFeedback) -> None:
        if self.board_adapter is None:
            return
        self.board_adapter.show_feedback(feedback)

    def _current_board_scan_target(self) -> BoardScanTarget:
        if self.encounter_setup_flow is not None:
            step = self.encounter_setup_flow.current_step
            if step is not None:
                if self.encounter_setup_flow.is_player_start_step:
                    positions = self.encounter_setup_flow.remaining_player_start_positions()
                    return BoardScanTarget(
                        positions=positions,
                        feedback=setup_led_feedback(replace(step, positions=positions)),
                        empty_message="Kliknij wolne pole startowe dla aktualnego bohatera.",
                    )
                return BoardScanTarget(
                    positions=step.positions,
                    feedback=setup_led_feedback(step),
                    empty_message="Aktualny krok setupu nie ma pól do kliknięcia.",
                )
        if (
            self.encounter_setup_flow is not None
            and self.encounter_setup_flow.completed
            and self.pending_encounter is not None
            and precombat_stealth_is_available(self.pending_encounter.opening_resolution)
            and not self.pending_encounter.precombat_stealth_completed
            and self.encounter_initiative_flow is None
        ):
            attempted_actor_ids = {
                attempt.actor_id
                for attempt in self.pending_encounter.precombat_stealth_attempts
            }
            actor = next(
                (
                    candidate
                    for candidate in self.encounter_setup_flow.encounter.actors
                    if candidate.faction == Faction.ALLY
                    and not candidate.is_defeated()
                    and str(candidate.id) not in attempted_actor_ids
                ),
                None,
            )
            if actor is not None:
                return self._passive_focus_target(
                    (actor.position,),
                    color=LedColor.ACTIVE_ACTOR,
                    role=LedRole.ACTIVE_ACTOR,
                    message="Aktualny bohater czeka na rzut Stealth w UI; plansza nie wymaga kliknięcia.",
                )
        if self.encounter_initiative_flow is not None:
            prompt = self.encounter_initiative_flow.current_prompt
            if prompt is not None:
                return self._passive_focus_target(
                    (prompt.actor.position,),
                    color=LedColor.ACTIVE_ACTOR,
                    role=LedRole.ACTIVE_ACTOR,
                    message="Aktualny aktor czeka na rzut inicjatywy w UI; plansza nie wymaga kliknięcia.",
                )
        if self.combat_state is not None:
            encounter = self._active_encounter()
            actor = combat_current_actor(self.combat_state)
            if self.pending_combat_context_menu is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                    empty_message="Menu akcji czeka na wybór strzałkami i potwierdzenie Enterem.",
                )
            if self.pending_enemy_turn_intent is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=_enemy_turn_intent_led_feedback(self.pending_enemy_turn_intent),
                    empty_message="Zamiar przeciwnika czeka na potwierdzenie Enterem albo przyciskiem.",
                )
            if self.pending_enemy_opportunity_attack is not None:
                feedback = (
                    _pending_enemy_turn_led_feedback(self.pending_enemy_turn_result)
                    if self.pending_enemy_turn_result is not None
                    else active_actor_led_feedback(self.combat_state.initiative_order)
                )
                return BoardScanTarget(
                    positions=(),
                    feedback=feedback,
                    empty_message="Atak okazyjny bohatera czeka na decyzję albo rzut w UI.",
                )
            if self.pending_ready_attack is not None:
                feedback = (
                    _pending_enemy_turn_led_feedback(self.pending_enemy_turn_result)
                    if self.pending_enemy_turn_result is not None
                    else active_actor_led_feedback(self.combat_state.initiative_order)
                )
                return BoardScanTarget(
                    positions=(),
                    feedback=feedback,
                    empty_message="Przygotowana akcja czeka na decyzję albo rzut w UI.",
                )
            if self.pending_enemy_saving_throw is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                    empty_message="Efekt przeciwnika czeka na fizyczny rzut obronny i wpisanie wyniku w UI.",
                )
            if self.pending_enemy_turn_result is not None:
                target_positions = _pending_enemy_turn_target_positions(self.pending_enemy_turn_result)
                if not target_positions:
                    return BoardScanTarget(
                        positions=(),
                        feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                        empty_message="Atak przeciwnika czeka na wpisanie rzutu w UI.",
                    )
                return BoardScanTarget(
                    positions=target_positions,
                    feedback=_pending_enemy_turn_led_feedback(self.pending_enemy_turn_result),
                    empty_message="Tura przeciwnika czeka na potwierdzenie pola docelowego albo celu.",
                )
            if self.pending_player_attack is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                    empty_message="Atak gracza czeka na wpisanie rzutu w UI.",
                )
            if self.pending_player_healing is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                    empty_message="Leczenie gracza czeka na wpisanie wyniku w UI.",
                )
            if self.pending_area_spell is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=_pending_area_spell_led_feedback(self.pending_area_spell, self.combat_state),
                    empty_message="Czar obszarowy czeka na potwierdzenie albo wpisanie obrażeń w UI.",
                )
            if self.pending_combat_help is not None:
                target_positions = tuple(
                    actor.position
                    for actor in self.combat_state.actors
                    if str(actor.id) in self.pending_combat_help.target_ids
                )
                return BoardScanTarget(
                    positions=(),
                    feedback=LedFeedback((LedFrame(target_positions, LedColor.LEGAL_ATTACK_TARGET, LedRole.ENEMY),)),
                    empty_message="Help czeka na wybór sojusznika i celu w UI.",
                )
            if self.pending_concentration_action is not None:
                target_positions = tuple(
                    actor.position
                    for actor in self.combat_state.actors
                    if str(actor.id) in self.pending_concentration_action.target_ids
                )
                return BoardScanTarget(
                    positions=target_positions,
                    feedback=LedFeedback((LedFrame(target_positions, LedColor.ALLY, LedRole.ALLY),)),
                    empty_message="Czar koncentracyjny czeka na wybór sojusznika.",
                )
            if self.pending_concentration_check is not None:
                return BoardScanTarget(
                    positions=(),
                    feedback=active_actor_led_feedback(self.combat_state.initiative_order),
                    empty_message="Rzut na koncentrację czeka na wpisanie wyniku w UI.",
                )
            if self.pending_combat_interaction is not None:
                position = self.pending_combat_interaction.target_position
                scene_object_positions = ()
                if encounter is not None:
                    scene_object = self._scene_object_by_id(encounter, self.pending_combat_interaction.object_id)
                    scene_object_positions = scene_object.positions if scene_object is not None else (position,)
                return BoardScanTarget(
                    positions=(),
                    feedback=LedFeedback((LedFrame(scene_object_positions or (position,), LedColor.INTERACTIVE_OBJECT, LedRole.INTERACTIVE_OBJECT),)),
                    empty_message="Interakcja czeka na potwierdzenie przyciskiem albo Enterem.",
                )
            if encounter is not None and actor.faction == Faction.ALLY and self.combat_state.status.value == "active":
                movement = _remaining_movement_range(encounter.board, self.combat_state, actor)
                attack_source = self._selected_attack_source(actor)
                attack_source = self._effective_attack_source(actor, attack_source) if attack_source is not None else None
                if attack_source is not None and not self._actor_can_use_attack_source(actor, attack_source):
                    attack_source = None
                area_positions = _area_spell_selection_positions(encounter.board, actor, attack_source)
                attack_targets = () if area_positions else _legal_combat_targets(encounter, self.combat_state, actor, attack_source)
                targeting_source = bool(
                    attack_source is not None
                    and self.combat_targeting_attack_source_id == attack_source.id
                )
                if targeting_source:
                    target_positions = tuple(sorted(target.position for target in attack_targets))
                    frames = list(active_actor_led_feedback(self.combat_state.initiative_order).frames)
                    if area_positions:
                        frames.append(
                            LedFrame(
                                tuple(sorted(area_positions)),
                                LedColor.MARKER,
                                LedRole.DESTINATION,
                            )
                        )
                    elif target_positions:
                        frames.append(
                            LedFrame(
                                target_positions,
                                LedColor.ENEMY,
                                LedRole.ENEMY,
                            )
                        )
                    return BoardScanTarget(
                        positions=tuple(
                            sorted(
                                frozenset((actor.position,))
                                | frozenset(area_positions)
                                | frozenset(target_positions)
                            )
                        ),
                        feedback=LedFeedback(tuple(frames)),
                        empty_message=(
                            f"{attack_source.name}: wybierz podświetlony kierunek lub wróć polem bohatera."
                            if area_positions
                            else f"{attack_source.name}: wybierz podświetlony cel lub wróć polem bohatera."
                        ),
                    )
                bonus_sources = eligible_two_weapon_bonus_sources(
                    actor,
                    self.combat_state.turn_action.two_weapon_trigger_item_id,
                    self._attack_sources_for_actor(actor),
                ) if self.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE else ()
                bonus_targets = tuple(
                    target
                    for source in bonus_sources
                    for target in _legal_combat_targets(
                        encounter,
                        self.combat_state,
                        actor,
                        two_weapon_bonus_attack_source(actor, source),
                        require_action=False,
                    )
                )
                attack_targets = tuple(
                    {target.id: target for target in (*attack_targets, *bonus_targets)}.values()
                )
                healing_source = self._selected_healing_source(actor)
                healing_targets = (
                    legal_healing_targets(encounter.board, actor, self.combat_state.actors, healing_source)
                    if healing_source is not None
                    and self._actor_can_use_healing_source(actor, healing_source)
                    and self.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
                    else ()
                )
                interaction_positions = self._combat_interaction_positions(encounter, actor)
                interaction_hint_positions = self._combat_interaction_hint_positions(encounter, actor, movement)
                highlighted_interactions = tuple(sorted(frozenset(interaction_positions) | frozenset(interaction_hint_positions)))
                return BoardScanTarget(
                    positions=tuple(
                        sorted(
                            movement.reachable_tiles
                            | frozenset((actor.position,))
                            | frozenset(target.position for target in attack_targets)
                            | frozenset(area_positions)
                            | frozenset(target.position for target in healing_targets)
                            | frozenset(interaction_positions)
                            | frozenset(interaction_hint_positions)
                        )
                    ),
                    feedback=_combat_choice_led_feedback(
                        movement,
                        attack_targets,
                        healing_targets,
                        self.selected_combat_movement_path,
                        encounter.board,
                        highlighted_interactions,
                        area_positions,
                        _dragged_destination(
                            self.combat_state,
                            self.selected_combat_movement_path,
                        ),
                    ),
                    empty_message="Aktywny bohater nie ma dostępnych pól ruchu ani celów ataku.",
                )
            feedback = active_actor_led_feedback(self.combat_state.initiative_order)
            return BoardScanTarget(
                positions=(actor.position,),
                feedback=feedback,
                empty_message="Nie ma aktywnego aktora walki.",
            )
        if self.pending_encounter is not None:
            trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
            opening_required = (
                trigger is not None
                and trigger.opening_policy is not None
                and self.pending_encounter.opening_resolution is None
            )
            return BoardScanTarget(
                positions=(),
                feedback=LedFeedback(),
                empty_message=(
                    "Encounter czeka na rozstrzygnięcie rozpoczęcia starcia w UI albo Enterem."
                    if opening_required
                    else "Encounter czeka na rozpoczęcie setupu w UI albo Enterem."
                ),
            )
        if self.exploration_setup_flow is not None and self.exploration_setup_flow.current_step is not None:
            step = self.exploration_setup_flow.current_step
            return BoardScanTarget(
                positions=step.positions,
                feedback=setup_led_feedback(step),
                empty_message="Aktualny krok setupu mapy nie ma pól do kliknięcia.",
            )
        if self.ui_flow_stage in {UiFlowStage.WAITING_FOR_BOARD, UiFlowStage.READY_TO_START}:
            return BoardScanTarget(
                positions=(),
                feedback=LedFeedback(),
                empty_message="Najpierw wybierz planszę i kliknij Start.",
            )
        if self.ui_flow_stage in {
            UiFlowStage.INTERACTION_RESULT,
            UiFlowStage.SCENARIO_COMPLETE,
        }:
            return BoardScanTarget(
                positions=(),
                feedback=LedFeedback(),
                empty_message=(
                    "Scenariusz został zakończony."
                    if self.ui_flow_stage == UiFlowStage.SCENARIO_COMPLETE
                    else "Najpierw zakończ podsumowanie interakcji w UI."
                ),
            )
        if self.ui_flow_stage == UiFlowStage.PARTY_SETUP:
            position = self.current_zone.marker_position
            return BoardScanTarget(
                positions=(position,),
                feedback=LedFeedback((LedFrame((position,), LedColor.MARKER, LedRole.DESTINATION),)),
                empty_message="Nie ma pola startowego drużyny do kliknięcia.",
            )
        if self.ui_flow_stage == UiFlowStage.LOCATION_PREVIEW:
            zones = self._scene_location_zones()
            if self.preview_zone_id:
                zone = self._preview_zone()
                feedback = _single_zone_feedback(zone) if zone is not None else exploration_zone_feedback(self.state)
            else:
                feedback = _zone_markers_feedback(zones)
            return BoardScanTarget(
                positions=tuple(zone.marker_position for zone in zones),
                feedback=feedback,
                empty_message="Nie ma teraz dostępnych lokacji do kliknięcia.",
            )
        if not self.exploration_board_selection_active:
            point = self.active_point
            if point is not None:
                focus_positions = point.positions if point.npc_interaction is None else ()
                return self._passive_focus_target(
                    focus_positions,
                    color=LedColor.INTERACTIVE_OBJECT,
                    role=LedRole.INTERACTIVE_OBJECT,
                    message="Interakcja jest aktywna w UI; plansza nie wymaga kliknięcia.",
                )
            return BoardScanTarget(
                positions=(),
                feedback=_single_zone_feedback(self.current_zone),
                empty_message="Interakcja z lokacją jest aktywna w UI; plansza nie wymaga kliknięcia.",
            )
        positions = tuple(zone.marker_position for zone in self._board_selectable_zones()) + tuple(
            position for point in self.current_zone_points() for position in point.positions
        )
        return BoardScanTarget(
            positions=positions,
            feedback=exploration_zone_feedback(self.state),
            empty_message="Nie ma teraz dostępnych lokacji ani punktów do kliknięcia.",
        )

    def _board_selectable_zones(self) -> tuple[ExplorationZone, ...]:
        available_by_id = {zone.id: zone for zone in available_exploration_zones(self.state)}
        zone_ids = (self.current_zone.id, *(zone.id for zone in self.travel_options()))
        return tuple(available_by_id[zone_id] for zone_id in zone_ids if zone_id in available_by_id)

    def _scene_location_zones(self) -> tuple[ExplorationZone, ...]:
        visible = tuple(zone for zone in visible_exploration_zones(self.state.zones) if zone.id != "barracks")
        preferred = ("gate", "courtyard", "tower")
        by_id = {zone.id: zone for zone in visible}
        ordered = tuple(by_id[zone_id] for zone_id in preferred if zone_id in by_id)
        rest = tuple(zone for zone in visible if zone.id not in preferred)
        return (*ordered, *rest)

    def _handle_board_position(self, selected: Coordinate) -> dict[str, object]:
        if self.encounter_setup_flow is not None and self.encounter_setup_flow.current_step is not None:
            if self.encounter_setup_flow.is_player_start_step:
                return self.assign_encounter_player_start_position(selected)
            self.board_message = f"Potwierdzono setup kliknięciem pola {selected.as_tuple()}."
            return self.confirm_encounter_setup_step()
        if self.encounter_initiative_flow is not None and self.encounter_initiative_flow.current_prompt is not None:
            prompt = self.encounter_initiative_flow.current_prompt
            self.board_message = f"Wskazano aktora do inicjatywy: {prompt.actor.name}. Wpisz wynik d20 w UI."
            return self.state_payload()
        if self.combat_state is not None:
            actor = combat_current_actor(self.combat_state)
            if self.pending_enemy_opportunity_attack is not None:
                self.board_message = "Najpierw rozstrzygnij albo pomiń atak okazyjny bohatera w UI."
                return self.state_payload()
            if self.pending_ready_attack is not None:
                self.board_message = "Najpierw rozstrzygnij albo pomiń przygotowaną akcję w UI."
                return self.state_payload()
            if self.pending_concentration_check is not None:
                self.board_message = "Najpierw wpisz rzut na koncentrację w UI."
                return self.state_payload()
            if self.pending_enemy_saving_throw is not None:
                self.board_message = "Najpierw wpisz naturalny wynik rzutu obronnego gracza w UI."
                return self.state_payload()
            if self.pending_enemy_turn_result is not None:
                expected = _pending_enemy_turn_target_positions(self.pending_enemy_turn_result)
                if not expected:
                    self.board_message = "Atak przeciwnika czeka na wpisanie rzutu w UI."
                    return self.state_payload()
                if selected in expected:
                    self.board_message = f"Potwierdzono turę przeciwnika kliknięciem pola {selected.as_tuple()}."
                    return self._commit_pending_enemy_turn()
                self.board_message = "Kliknij podświetlone pole docelowe tury przeciwnika."
                return self.state_payload()
            if actor.faction == Faction.ALLY:
                encounter = self._active_encounter()
                try:
                    if self.pending_concentration_action is not None:
                        target = next(
                            (
                                candidate
                                for candidate in self.combat_state.actors
                                if str(candidate.id) in self.pending_concentration_action.target_ids
                                and candidate.position == selected
                            ),
                            None,
                        )
                        if target is not None:
                            self.board_message = f"Czar koncentracyjny: {actor.name} -> {selected.as_tuple()}."
                            return self.confirm_combat_concentration_action(target_id=str(target.id))
                        self.board_message = "Kliknij podświetlonego sojusznika dla czaru koncentracyjnego."
                        return self.state_payload()
                    if self.combat_targeting_attack_source_id is not None:
                        source = self._selected_attack_source(actor)
                        if source is None or source.id != self.combat_targeting_attack_source_id:
                            self.combat_targeting_attack_source_id = None
                            raise ValueError("Wybrane źródło ataku nie jest już dostępne.")
                        if selected == actor.position:
                            return self._open_combat_context_menu(
                                actor,
                                selected,
                                self._combat_context_options(actor, selected),
                            )
                        if source.area is not None:
                            return self.select_player_area_spell_at_position(selected)
                        return self.select_player_attack_target_at_position(selected)
                    if (
                        self.selected_combat_movement_path is not None
                        and self.selected_combat_movement_path.valid
                        and self.selected_combat_movement_path.destination == selected
                    ):
                        self.board_message = f"Ruch bohatera: {actor.name} -> {selected.as_tuple()}."
                        return self.submit_combat_movement(col=selected.col, row=selected.row)
                    options = self._combat_context_options(actor, selected)
                    if selected == actor.position:
                        return self._open_combat_context_menu(actor, selected, options)
                    if len(options) > 1:
                        return self._open_combat_context_menu(actor, selected, options)
                    if len(options) == 1:
                        return self._execute_combat_context_option(options[0])
                    return self.preview_combat_movement(col=selected.col, row=selected.row)
                except ValueError as exc:
                    self.board_message = str(exc)
                    return self.state_payload()
            self.board_message = f"Aktywny aktor walki: {actor.name}."
            return self.state_payload()
        if self.exploration_setup_flow is not None and self.exploration_setup_flow.current_step is not None:
            self.board_message = f"Potwierdzono setup mapy kliknięciem pola {selected.as_tuple()}."
            return self.confirm_exploration_setup_step()
        if self.ui_flow_stage == UiFlowStage.PARTY_SETUP:
            if selected == self.current_zone.marker_position:
                self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
                self.preview_zone_id = ""
                self.board_message = (
                    f"Figurka drużyny ustawiona. Dostępna lokacja: {self.current_zone.name}, "
                    f"kolor {led_color_name_pl(self.current_zone.color)}. Kliknij odpowiednią lokację, aby wejść w interakcję."
                )
                self._sync_board_leds()
                return self.state_payload()
            self.board_message = "Kliknięte pole nie jest podświetlonym polem startowym drużyny."
            return self.state_payload()
        if self.ui_flow_stage == UiFlowStage.LOCATION_PREVIEW:
            for zone in self._scene_location_zones():
                if selected == zone.marker_position:
                    if not zone_is_ui_available(self.state, zone):
                        self.preview_zone_id = zone.id
                        self.board_message = _locked_zone_message(zone)
                        self._sync_board_leds()
                        return self.state_payload()
                    self.preview_zone_id = zone.id
                    self.board_message = (
                        f"Podgląd lokacji: {zone.name}. Czy chcesz przejść do tej lokacji? "
                        "Potwierdź Enterem albo przyciskiem w UI."
                    )
                    self._sync_board_leds()
                    return self.state_payload()
            self.board_message = f"Kliknięte pole {selected.as_tuple()} nie jest teraz dostępną lokacją."
            return self.state_payload()
        for point in self.current_zone_points():
            if selected in point.positions:
                self.board_message = f"Wybrano punkt: {point.name}."
                return self.select_point(point.id)
        for zone in self._board_selectable_zones():
            if selected == zone.marker_position:
                if zone.id == self.current_zone.id:
                    self.board_message = f"Wybrano aktualną lokację: {zone.name}."
                    return self.state_payload()
                self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
                self.preview_zone_id = zone.id
                self.board_message = (
                    f"Podgląd lokacji: {zone.name}. Czy opuścić {self.current_zone.name} i przejść do {zone.name}? "
                    "Kliknij tę samą lokację ponownie, aby potwierdzić."
                )
                self._sync_board_leds()
                return self.state_payload()
        self.board_message = f"Kliknięte pole {selected.as_tuple()} nie pasuje do aktualnych opcji."
        return self.state_payload()

    def current_zone_points(self) -> tuple[ExplorationPoint, ...]:
        return tuple(point for point in visible_exploration_points(self.state.points) if point.zone_id == self.current_zone.id)

    def select_point(self, point_id: str) -> dict[str, object]:
        selection = self.exploration_flow.select_point(
            current_stage=self.ui_flow_stage,
            current_points=self.current_zone_points(),
            point_id=point_id,
        )
        self.active_point_id = selection.active_point_id
        self.exploration_board_selection_active = False
        if selection.point is None:
            return self.state_payload()
        self.pending = None
        point = selection.point
        if point.npc_interaction is not None and point.npc_interaction.dialogue_intro:
            self._add_message(point.npc_interaction.name, point.npc_interaction.dialogue_intro)
        self._sync_board_leds()
        return self.state_payload()

    def _submit_challenge_action(
        self,
        challenge: ExplorationChallenge,
        text: str,
        *,
        player_intent_hint: PlayerIntentHint | None = None,
        player_display_text: str | None = None,
        selected_goal_id: str | None = None,
        selected_check_participants: CheckParticipants | None = None,
        participant_actor_ids: tuple[str, ...] = (),
        conversation_only: bool = False,
        infer_flow_route: bool = False,
    ) -> dict[str, object]:
        conversation_text = player_display_text or text
        selected_goal_route = self.exploration_interaction_flow.route_for_goal(
            challenge=challenge,
            flows=self.exploration.flows,
            goal_id=selected_goal_id,
            flags=self.state.flags,
        )
        selected_goal = (
            selected_goal_route.goal if selected_goal_route is not None else None
        )
        available_flow_routes = (
            self.exploration_interaction_flow.available_routes(
                challenge=challenge,
                flows=self.exploration.flows,
                flags=self.state.flags,
            )
            if infer_flow_route and selected_goal_route is None
            else ()
        )
        client = self._gm_client()
        crafting_registry = build_crafting_source_registry(self.state, self.exploration.actors)
        source_matches = (
            match_available_sources(crafting_registry, text)
            if player_intent_hint == PlayerIntentHint.USE
            else match_visible_scene_sources(crafting_registry, text)
        )
        procedural_source_action = (
            next(
                (
                    (source_action, source_match)
                    for source_action in selected_goal_route.source_actions
                    for source_match in source_matches
                    if source_match.source.reference_id == source_action.source_ref
                ),
                None,
            )
            if selected_goal_route is not None and describes_direct_source_use(text)
            else None
        )
        if procedural_source_action is not None:
            source_action, source_match = procedural_source_action
            profile = next(
                (
                    option
                    for option in challenge.options
                    if option.id == source_action.option_id
                ),
                None,
            )
            if profile is None:
                raise ValueError(
                    f"Akcja źródła {source_action.id} wskazuje nieistniejącą opcję."
                )
            participants = selected_check_participants or selected_goal.check_participants
            option = replace(
                profile,
                check_participants=participants,
                check_aggregation=(
                    CheckAggregation.MAJORITY
                    if participants == CheckParticipants.WHOLE_PARTY
                    else CheckAggregation.LEAD_RESULT
                ),
            )
            self.pending = PendingInteraction(
                kind=PendingKind.CHALLENGE,
                stage=PendingStage.DECISION,
                challenge=challenge,
                option=option,
                participant_actor_ids=participant_actor_ids,
                use_source=source_match.source,
                source_property_labels=self.exploration.crafting_policy.property_labels,
            )
            self._record(
                "ui_procedural_source_action_proposed",
                {
                    "challenge_id": challenge.id,
                    "goal_id": selected_goal.id,
                    "source_action_id": source_action.id,
                    "source_id": source_match.source.id,
                    "option_id": option.id,
                },
            )
            self._add_message("Narracja MG", source_action.narration)
            return self.state_payload()
        discovered_source_ids = tuple(
            item.source_id
            for item in self.state.source_discoveries
            if item.zone_id == self.current_zone.id
            and crafting_registry.source_by_id(item.source_id) is not None
        )
        referenced_source_ids = tuple(
            dict.fromkeys(
                (*discovered_source_ids, *(match.source.id for match in source_matches))
            )
        )
        if player_intent_hint == PlayerIntentHint.USE and not referenced_source_ids:
            return self._reject_gm_declaration(
                conversation_text,
                "Nie rozpoznano istniejącego elementu do użycia. Najpierw wskaż dokładny przedmiot albo znajdź go przez /szukaj.",
                challenge,
            )
        authored_observation = (
            match_exploration_observation(
                self.exploration.observations,
                text,
                zone_id=self.current_zone.id,
                challenge_id=challenge.id,
                allowed_observation_ids=(
                    selected_goal_route.observation_ids
                    if selected_goal_route is not None
                    else ()
                ),
            )
            if player_intent_hint not in {PlayerIntentHint.BUILD, PlayerIntentHint.USE}
            else None
        )
        if (
            source_matches
            and player_intent_hint == PlayerIntentHint.SEARCH
            and authored_observation is None
            and is_source_lookup_only(
                text,
                explicit_search=True,
            )
        ):
            return self._answer_visible_source_lookup(
                challenge,
                conversation_text,
                source_matches,
            )
        effective_intent_hint = player_intent_hint
        if (
            source_matches
            and describes_direct_source_use(text)
            and player_intent_hint not in {PlayerIntentHint.BUILD, PlayerIntentHint.QUESTION}
        ):
            effective_intent_hint = PlayerIntentHint.USE
        request_data = build_gm_classifier_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            scenario_context=self.exploration.llm_context,
            state=self.state,
            player_action=text,
            declaration_thread=self._conversation_thread_for_active_interaction(exclude_latest_player=True),
            active_preparation_effects=tuple(self.active_preparation_effects),
            actors=self.exploration.actors,
            crafting_policy=self.exploration.crafting_policy,
            player_intent_hint=effective_intent_hint,
            explicit_player_intent_hint=player_intent_hint,
            observations=self.exploration.observations,
            referenced_crafting_source_ids=referenced_source_ids,
            selected_goal_id=selected_goal_id,
            selected_flow_transition_id=(
                selected_goal_route.transition.id
                if selected_goal_route is not None
                and selected_goal_route.transition is not None
                else None
            ),
            selected_flow_route_kind=(
                selected_goal_route.route_kind.value
                if selected_goal_route is not None
                else None
            ),
            selected_flow_option_id=(
                selected_goal_route.resolution_option_id
                if selected_goal_route is not None
                else None
            ),
            selected_flow_observation_ids=(
                selected_goal_route.observation_ids
                if selected_goal_route is not None
                else ()
            ),
            available_flow_routes=tuple(
                GmFlowRouteCandidate(
                    transition_id=route.transition.id,
                    goal_id=route.goal.id,
                    label=route.goal.label,
                    description=route.goal.description,
                    route_kind=route.route_kind.value,
                    suggested_tags=route.goal.suggested_tags,
                )
                for route in available_flow_routes
                if route.transition is not None
            ),
            selected_check_participants=selected_check_participants,
            selected_participant_actor_ids=participant_actor_ids,
            conversation_only=conversation_only,
        )
        fixture_action_plan: FixtureActionPlan | None = None
        try:
            matched_observation = (
                authored_observation
                if effective_intent_hint not in {PlayerIntentHint.BUILD, PlayerIntentHint.USE}
                else None
            )
            analysis = (
                GmDeclarationAnalysis.model_validate(
                    {
                        "analysis_type": "player_question",
                        "action_flow": "player_question",
                        "player_message": (
                            (
                                "Niestety świat nie składa zeznań pod wpływem samego pytania — "
                                f"jeśli chcecie pewności, spróbujcie: {matched_observation.label.lower()}."
                            )
                            if conversation_only
                            else (
                                "To uważna obserwacja, której wynik zależy od testu. "
                                "MG przygotuje warunki próby."
                            )
                        ),
                        "normalized_intent": text,
                        "reason": "Deklaracja pasuje do ustrukturyzowanej obserwacji sceny.",
                        "confidence": 1.0,
                        "response_kind": "requires_check",
                        "requires_check": True,
                        "suggested_followup": text,
                        "observation_id": matched_observation.id,
                    }
                )
                if matched_observation is not None
                else _analyze(client, request_data)
            )
            if (
                conversation_only
                and analysis.analysis_type != GmDeclarationAnalysisType.PLAYER_QUESTION
            ):
                answer = (
                    analysis.player_message
                    if analysis.analysis_type
                    in {
                        GmDeclarationAnalysisType.NEEDS_CLARIFICATION,
                        GmDeclarationAnalysisType.UNSUPPORTED,
                    }
                    and analysis.player_message.strip()
                    else (
                        "To brzmi już mniej jak pytanie, a bardziej jak plan z własnym "
                        "motywem muzycznym. Wybierzcie odpowiedni cel i opiszcie metodę "
                        "w polu „Jak to robicie?”, a wtedy świat uczciwie odpowie."
                    )
                )
                analysis = GmDeclarationAnalysis.model_validate(
                    {
                        "analysis_type": "player_question",
                        "action_flow": "player_question",
                        "player_message": answer,
                        "normalized_intent": text,
                        "reason": "Tryb swobodnej rozmowy nie wykonuje deklaracji działania.",
                        "confidence": 1.0,
                        "response_kind": "clarification",
                    }
                )
            if infer_flow_route and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE:
                transition_id = analysis.selected_flow_transition_id
                inferred_route = (
                    self.exploration_interaction_flow.route_for_transition(
                        challenge=challenge,
                        flows=self.exploration.flows,
                        transition_id=transition_id,
                        flags=self.state.flags,
                    )
                    if transition_id is not None
                    else None
                )
                if inferred_route is None:
                    self._add_message(
                        "MG dopytuje",
                        (
                            "Plan brzmi śmiało, lecz na razie rozbiega się po kilku "
                            "ścieżkach niczym drużyna po haśle „dzielimy się”. "
                            "Dopowiedzcie, co dokładnie chcecie osiągnąć i jak."
                        ),
                    )
                    return self.state_payload()
                selected_goal_route = inferred_route
                selected_goal = inferred_route.goal
                selected_check_participants = _resolve_goal_check_participants(
                    selected_goal,
                    (
                        selected_check_participants.value
                        if selected_check_participants is not None
                        else None
                    ),
                )
                participant_actor_ids = _validate_goal_participants(
                    selected_goal,
                    challenge,
                    self.exploration.actors,
                    participant_actor_ids,
                    check_participants=selected_check_participants,
                    resolution_option_id=inferred_route.resolution_option_id,
                )
                request_data = replace(
                    request_data,
                    selected_goal_id=selected_goal.id,
                    selected_flow_transition_id=inferred_route.transition.id,
                    selected_flow_route_kind=inferred_route.route_kind.value,
                    selected_flow_option_id=inferred_route.resolution_option_id,
                    selected_flow_observation_ids=inferred_route.observation_ids,
                    selected_check_participants=selected_check_participants,
                    selected_participant_actor_ids=participant_actor_ids,
                )
                self._record(
                    "ui_flow_route_inferred",
                    {
                        "challenge_id": challenge.id,
                        "transition_id": inferred_route.transition.id,
                        "goal_id": selected_goal.id,
                        "participant_actor_ids": list(participant_actor_ids),
                        "check_participants": selected_check_participants.value,
                    },
                )
            if (
                player_intent_hint == PlayerIntentHint.USE
                and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
            ):
                selected_use_source_id = analysis.use_source_id
                if selected_use_source_id is None and len(referenced_source_ids) == 1:
                    selected_use_source_id = referenced_source_ids[0]
                    analysis = analysis.model_copy(
                        update={"use_source_id": selected_use_source_id}
                    )
                if selected_use_source_id is not None:
                    if selected_use_source_id not in referenced_source_ids:
                        raise GmProposalValidationError(
                            "MG wskazał element, którego nie dopasowano do deklaracji /użyj."
                        )
                    request_data = replace(
                        request_data,
                        referenced_crafting_source_ids=(selected_use_source_id,),
                        selected_use_source_id=selected_use_source_id,
                    )
            actionable_fixture_ids = tuple(
                match.source.id
                for match in source_matches
                if match.source.kind == CraftingSourceKind.SCENE_FIXTURE
                and any(
                    fixture.id == match.source.reference_id and fixture.action_policies
                    for fixture in self.current_zone.fixtures
                )
            )
            if (
                player_intent_hint == PlayerIntentHint.ACTION
                and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
                and analysis.action_target_source_id is None
                and analysis.fixture_operation is not None
                and len(actionable_fixture_ids) == 1
            ):
                analysis = analysis.model_copy(
                    update={"action_target_source_id": actionable_fixture_ids[0]}
                )
            if (
                player_intent_hint == PlayerIntentHint.ACTION
                and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
                and (
                    analysis.action_target_source_id is not None
                    or analysis.fixture_operation is not None
                )
            ):
                if analysis.action_target_source_id is None or analysis.fixture_operation is None:
                    raise GmProposalValidationError(
                        "Operacja na elemencie sceny wymaga wskazania celu i rodzaju zmiany."
                    )
                if analysis.action_target_source_id not in referenced_source_ids:
                    raise GmProposalValidationError(
                        "MG wskazał fixture, którego nie dopasowano do deklaracji /akcja."
                    )
                try:
                    fixture_action_plan = plan_fixture_action(
                        self.state,
                        source_id=analysis.action_target_source_id,
                        operation=analysis.fixture_operation,
                    )
                except ValueError as exc:
                    raise GmProposalValidationError(str(exc)) from exc
                request_data = replace(
                    request_data,
                    selected_fixture_source_id=fixture_action_plan.source_id,
                    selected_fixture_operation=fixture_action_plan.policy.operation,
                )
            if analysis.source_query is not None:
                try:
                    validate_source_property_query(
                        required_properties=analysis.source_query.required_properties,
                        preferred_properties=analysis.source_query.preferred_properties,
                        allowed_property_ids=self.exploration.crafting_policy.property_ids,
                    )
                except ValueError as exc:
                    raise GmProposalValidationError(str(exc)) from exc
                semantic_matches = match_scene_sources_by_properties(
                    crafting_registry,
                    required_properties=analysis.source_query.required_properties,
                    preferred_properties=analysis.source_query.preferred_properties,
                )
                if not semantic_matches:
                    return self._answer_missing_scene_source(
                        challenge,
                        conversation_text,
                        analysis.source_query.purpose,
                    )
                source_matches = semantic_matches[:3]
                referenced_source_ids = tuple(match.source.id for match in source_matches)
                return self._propose_semantic_source_selection(
                    challenge,
                    conversation_text,
                    analysis,
                    source_matches,
                )
            if (
                analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
                and selected_goal_route is not None
                and selected_goal_route.default_observation_id is not None
                and effective_intent_hint
                not in {
                    PlayerIntentHint.ACTION,
                    PlayerIntentHint.BUILD,
                    PlayerIntentHint.USE,
                }
            ):
                default_observation = next(
                    (
                        item
                        for item in self.exploration.observations
                        if item.id == selected_goal_route.default_observation_id
                    ),
                    None,
                )
                if default_observation is not None:
                    analysis = GmDeclarationAnalysis.model_validate(
                        {
                            "analysis_type": "player_question",
                            "action_flow": "player_question",
                            "player_message": (
                                "To szerokie rozpoznanie otoczenia. "
                                "Wynik próby zdecyduje, ile użytecznych szczegółów zauważycie."
                            ),
                            "normalized_intent": text,
                            "reason": "Wybrany cel ma domyślną stopniowaną obserwację.",
                            "confidence": 1.0,
                            "response_kind": "requires_check",
                            "requires_check": True,
                            "suggested_followup": text,
                            "observation_id": default_observation.id,
                        }
                    )
            analysis = validate_gm_declaration_analysis(analysis, request_data)
        except GmProposalValidationError as exc:
            if conversation_only:
                return self._answer_gm_conversation_fallback(
                    challenge,
                    conversation_text,
                    technical_reason=str(exc),
                )
            return self._reject_gm_declaration(conversation_text, str(exc), challenge)
        if analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION:
            observation = next(
                (
                    item for item in self.exploration.observations
                    if analysis.observation_id is not None and item.id == analysis.observation_id
                ),
                None,
            )
            if observation is not None:
                answer = (
                    analysis.player_message
                    or (
                        "Tego nie da się pewnie stwierdzić z miejsca. "
                        f"Jeśli chcecie wiedzieć więcej, spróbujcie: {observation.label.lower()}."
                    )
                    if conversation_only
                    else (
                        "Z tego punktu obserwacji nie da się jeszcze uzyskać pewnej odpowiedzi. "
                        f"MG proponuje próbę: {observation.label}."
                    )
                )
            else:
                answer = analysis.player_message or "To pytanie nie zmienia stanu sceny."
            if observation is None and analysis.requires_check and analysis.suggested_followup.strip():
                answer = f"{answer} Możecie zadeklarować: {analysis.suggested_followup.strip()}"
            response_kind = analysis.response_kind.value if analysis.response_kind is not None else "observation"
            outcome = f"player_question:{response_kind}"
            self._remember_scene_exchange(
                conversation_text,
                answer,
                outcome=outcome,
                grounded_fact_ids=analysis.grounded_fact_ids,
                hint_level=analysis.hint_level,
            )
            self._record(
                "ui_gm_question_answered",
                {
                    "question": conversation_text,
                    "answer": answer,
                    "zone_id": self.current_zone.id,
                    "challenge_id": challenge.id,
                    "response_kind": response_kind,
                    "grounded_fact_ids": list(analysis.grounded_fact_ids),
                    "hint_level": analysis.hint_level,
                    "requires_check": analysis.requires_check,
                },
            )
            title = (
                "Podpowiedź MG"
                if response_kind in {"gentle_hint", "strong_hint"}
                else "Odpowiedź MG"
                if conversation_only
                else "MG proponuje sprawdzenie"
                if response_kind == "requires_check"
                else "Odpowiedź MG"
            )
            self._add_message(
                title,
                answer,
                outcome=outcome,
                grounded_fact_ids=analysis.grounded_fact_ids,
                hint_level=analysis.hint_level,
            )
            if observation is not None and not conversation_only:
                self.pending = PendingInteraction(
                    kind=PendingKind.OBSERVATION,
                    stage=PendingStage.DECISION,
                    proposal=analysis,
                    challenge=challenge,
                    observation=observation,
                    participant_actor_ids=participant_actor_ids,
                )
            return self.state_payload()
        if analysis.analysis_type == GmDeclarationAnalysisType.WORLD_ACTION:
            applied_effects = []
            for immediate_effect in analysis.immediate_effects:
                raw_effect = immediate_effect.as_effect_payload()
                result = apply_exploration_effect(self.state, raw_effect)
                self.state = result.state
                self._record_effect_result(
                    result,
                    source="gm_world_action",
                    raw_effect=raw_effect,
                )
                applied_effects.append(result.effect_type)
            answer = analysis.player_message
            self._remember_scene_exchange(
                conversation_text,
                answer,
                outcome=analysis.analysis_type.value,
            )
            self._record(
                "ui_gm_world_action_resolved",
                {
                    "declaration": conversation_text,
                    "challenge_id": challenge.id,
                    "effect_types": applied_effects,
                },
            )
            self._add_message("Świat odpowiada", answer, outcome=analysis.analysis_type.value)
            return self.state_payload()
        if analysis.analysis_type in {GmDeclarationAnalysisType.NEEDS_CLARIFICATION, GmDeclarationAnalysisType.UNSUPPORTED}:
            answer = analysis.player_message or analysis.reason
            self._remember_scene_exchange(conversation_text, answer, outcome=analysis.analysis_type.value)
            title = (
                "MG dopytuje"
                if analysis.analysis_type == GmDeclarationAnalysisType.NEEDS_CLARIFICATION
                else "Świat odpowiada"
            )
            self._add_message(title, answer)
            return self.state_payload()
        if analysis.normalized_intent:
            request_data = replace(request_data, player_action=analysis.normalized_intent)
        try:
            proposal = client.classify(request_data)
            validated = validate_gm_classifier_proposal(proposal, request_data)
        except GmProposalValidationError as exc:
            return self._reject_gm_declaration(conversation_text, str(exc), challenge)
        if validated.proposal != proposal:
            self._record(
                "ui_gm_proposal_grounded",
                {
                    "challenge_id": challenge.id,
                    "original": proposal.model_dump(mode="json"),
                    "grounded": validated.proposal.model_dump(mode="json"),
                },
            )
        proposal = validated.proposal
        self._record(
            "ui_gm_proposal_validated",
            {
                "challenge_id": validated.challenge.id,
                "proposal": proposal.model_dump(mode="json"),
            },
        )
        if proposal.action_flow == GmActionFlow.PREPARATION:
            effect = proposal.preparation_effect
            if effect is not None:
                if effect.type == PreparationEffectType.CREATE_TEMPORARY_ITEM:
                    if effect.crafting_draft is not None:
                        assert validated.crafting_plan is not None
                        registry = build_crafting_source_registry(self.state, self.exploration.actors)
                        self.pending = PendingInteraction(
                            kind=PendingKind.CRAFTING,
                            stage=PendingStage.DECISION,
                            proposal=proposal,
                            challenge=validated.challenge,
                            crafting_plan=validated.crafting_plan,
                            crafting_source_labels=tuple(
                                (component.source_id, registry.source_by_id(component.source_id).label)
                                for component in validated.crafting_plan.component_uses
                                if registry.source_by_id(component.source_id) is not None
                            ),
                        )
                        self._add_message(
                            "Narracja MG",
                            proposal.player_narration or "MG przedstawia sposób przygotowania konstrukcji.",
                        )
                        return self.state_payload()
                    template = next(
                        template
                        for template in challenge.llm_policy.temporary_item_templates
                        if template.id == effect.temporary_item_template_id
                    )
                    self.state, item = create_temporary_item(
                        self.state,
                        template,
                        zone_id=self.current_zone.id,
                        source_materials=effect.source_materials,
                    )
                    self._record(
                        "ui_temporary_item_created",
                        {
                            "item_id": item.id,
                            "template_id": item.template_id,
                            "uses_remaining": item.uses_remaining,
                            "source_materials": list(item.source_materials),
                        },
                    )
                    self._add_message(
                        "Utworzono przedmiot sceny",
                        f"{item.label}: {item.uses_remaining} użycia. Zniknie po zakończeniu scenariusza.",
                    )
                else:
                    self.active_preparation_effects.append(effect)
                    self._add_message("Przygotowanie", f"Przygotowanie zapisane: {effect.label}.")
            return self.state_payload()
        option = challenge_option_from_validated_proposal(validated)
        try:
            if fixture_action_plan is None:
                option = apply_goal_resolution_profile(
                    option,
                    challenge=validated.challenge,
                    selected_goal_id=selected_goal_id,
                    resolution_option_id=(
                        selected_goal_route.resolution_option_id
                        if selected_goal_route is not None
                        else None
                    ),
                    selected_check_participants=selected_check_participants,
                    player_action=text,
                    state=self.state,
                    minimum_dc=EXPLORATION_DECISION_DC_MIN,
                )
        except ValueError as exc:
            self._add_message("Świat odpowiada", str(exc))
            return self.state_payload()
        resource = validated.resources[0] if validated.resources else None
        eligible_actors = tuple(
            actor
            for actor in actors_matching_challenge_option(self.exploration.actors, option)
            if actor.faction == Faction.ALLY
        )
        if eligible_actors:
            # Każda nowa próba dostaje świeży, sensowny wybór prowadzącego.
            # Nie przenosimy Łotrzycy z poprzedniego otwierania zamka do
            # kolejnego wyważania bramy tylko dlatego, że select zachował stan.
            self.selected_lead_actor_id = str(eligible_actors[0].id)
        self.pending = PendingInteraction(
            kind=PendingKind.CHALLENGE,
            stage=PendingStage.DECISION,
            proposal=proposal,
            challenge=validated.challenge,
            option=option,
            participant_actor_ids=participant_actor_ids,
            resources=(resource,) if resource is not None else (),
            use_source=(
                build_crafting_source_registry(
                    self.state,
                    self.exploration.actors,
                ).source_by_id(request_data.selected_use_source_id)
                if request_data.selected_use_source_id is not None
                else None
            ),
            source_property_labels=self.exploration.crafting_policy.property_labels,
            fixture_action_plan=fixture_action_plan,
        )
        self._add_message(
            "Narracja MG",
            proposal.player_narration or f"MG interpretuje deklarację jako: {option.label}.",
        )
        return self.state_payload()

    def _answer_gm_conversation_fallback(
        self,
        challenge: ExplorationChallenge,
        question: str,
        *,
        technical_reason: str,
    ) -> dict[str, object]:
        answer = (
            "Ruiny nie wystawiają certyfikatów bezpieczeństwa — najwyraźniej miejscowy "
            "urząd dawno pożarł jakiś potwór. Z miejsca nie macie pewności, czy w pobliżu "
            "ktoś się kręci. Jeśli chcecie to rozstrzygnąć, nasłuchajcie, poszukajcie "
            "śladów albo znajdźcie punkt, z którego da się ostrożnie rozejrzeć."
        )
        self._remember_scene_exchange(
            question,
            answer,
            outcome="conversation_safe_fallback",
        )
        self._record(
            "ui_gm_conversation_safely_recovered",
            {
                "question": question,
                "answer": answer,
                "zone_id": self.current_zone.id,
                "challenge_id": challenge.id,
                "technical_reason": technical_reason,
            },
        )
        self._add_message("Odpowiedź MG", answer, outcome="conversation_safe_fallback")
        return self.state_payload()

    def _answer_visible_source_lookup(
        self,
        challenge: ExplorationChallenge,
        player_text: str,
        source_matches: tuple[SceneSourceMatch, ...],
    ) -> dict[str, object]:
        sources = tuple(match.source for match in source_matches)
        for source in sources:
            self.state = discover_scene_source(
                self.state,
                source,
                requested_as=player_text,
            )
        descriptions = ", ".join(
            f"{source.label} ({source.quantity} szt.)" if source.quantity > 1 else source.label
            for source in sources
        )
        answer = (
            f"W widocznym otoczeniu znajdują się: {descriptions}. "
            "Możecie wskazać, jak chcecie wykorzystać wybrany element."
        )
        grounded_fact_ids = tuple(f"source:{source.id}" for source in sources)
        self._remember_scene_exchange(
            player_text,
            answer,
            outcome="visible_source_lookup",
            grounded_fact_ids=grounded_fact_ids,
        )
        self._record(
            "ui_scene_source_lookup_answered",
            {
                "question": player_text,
                "answer": answer,
                "zone_id": self.current_zone.id,
                "challenge_id": challenge.id,
                "source_ids": [source.id for source in sources],
            },
        )
        self._add_message(
            "Odpowiedź MG",
            answer,
            outcome="visible_source_lookup",
            grounded_fact_ids=grounded_fact_ids,
        )
        return self.state_payload()

    def _propose_semantic_source_selection(
        self,
        challenge: ExplorationChallenge,
        player_text: str,
        analysis: GmDeclarationAnalysis,
        source_matches: tuple[SceneSourceMatch, ...],
    ) -> dict[str, object]:
        assert analysis.source_query is not None
        labels = ", ".join(match.source.label for match in source_matches)
        if analysis.source_query.requested_name:
            answer = (
                f"Nie widzę tutaj przedmiotu opisanego dokładnie jako „{analysis.source_query.requested_name}”. "
                f"Najbliższe funkcjonalnie dostępne elementy to: {labels}. Wybierzcie, czy któryś wam odpowiada."
            )
        else:
            answer = (
                f"Do opisanego celu mogą pasować: {labels}. "
                "Wybierzcie element, który chcecie uznać za znaleziony, albo odrzućcie propozycję."
            )
        self.pending = PendingInteraction(
            kind=PendingKind.SOURCE_SELECTION,
            stage=PendingStage.DECISION,
            proposal=analysis,
            challenge=challenge,
            source_matches=source_matches,
            source_search_text=player_text,
            source_property_labels=self.exploration.crafting_policy.property_labels,
        )
        self._record(
            "ui_scene_source_selection_proposed",
            {
                "question": player_text,
                "zone_id": self.current_zone.id,
                "challenge_id": challenge.id,
                "requested_name": analysis.source_query.requested_name,
                "purpose": analysis.source_query.purpose,
                "source_ids": [match.source.id for match in source_matches],
            },
        )
        self._add_message("Narracja MG", answer, outcome="source_selection_proposed")
        return self.state_payload()

    def _answer_missing_scene_source(
        self,
        challenge: ExplorationChallenge,
        player_text: str,
        purpose: str,
    ) -> dict[str, object]:
        need = purpose.strip()
        answer = (
            f"W widocznym otoczeniu nie ma teraz elementu, który nadawałby się do tego celu: {need}."
            if need
            else "W widocznym otoczeniu nie ma teraz elementu o potrzebnych właściwościach."
        )
        self._remember_scene_exchange(player_text, answer, outcome="visible_source_lookup:no_match")
        self._record(
            "ui_scene_source_lookup_answered",
            {
                "question": player_text,
                "answer": answer,
                "zone_id": self.current_zone.id,
                "challenge_id": challenge.id,
                "source_ids": [],
            },
        )
        self._add_message("Odpowiedź MG", answer, outcome="visible_source_lookup:no_match")
        return self.state_payload()

    def _reject_gm_declaration(
        self,
        text: str,
        reason: str,
        challenge: ExplorationChallenge,
    ) -> dict[str, object]:
        answer = _player_facing_gm_validation_message(reason)
        self._remember_scene_exchange(text, answer, outcome="validation_error")
        self._record(
            "ui_gm_declaration_rejected",
            {
                "declaration": text,
                "reason": reason,
                "zone_id": self.current_zone.id,
                "challenge_id": challenge.id,
            },
        )
        self._add_message("Deklaracja wymaga korekty", answer)
        return self.state_payload()

    def _remember_scene_exchange(
        self,
        player_text: str,
        gm_text: str,
        *,
        outcome: str,
        grounded_fact_ids: tuple[str, ...] = (),
        hint_level: int = 0,
    ) -> None:
        self.declaration_thread.extend(
            (
                GmDeclarationThreadEntry("player", player_text, outcome),
                GmDeclarationThreadEntry(
                    "gm",
                    gm_text,
                    outcome,
                    grounded_fact_ids,
                    hint_level,
                ),
            )
        )
        self.declaration_thread = self.declaration_thread[-16:]

    def _active_conversation_id(self) -> str:
        point = self.active_point
        if point is not None:
            return f"point:{point.id}"
        challenge = challenge_for_zone(self.state, self.current_zone.id)
        if challenge is not None:
            return f"challenge:{challenge.id}"
        return f"zone:{self.current_zone.id}"

    def _conversation_entries_for_active_interaction(self) -> tuple[InteractionConversationEntry, ...]:
        interaction_id = self._active_conversation_id()
        return tuple(entry for entry in self.conversation_entries if entry.interaction_id == interaction_id)

    def _conversation_thread_for_active_interaction(
        self,
        *,
        exclude_latest_player: bool = False,
    ) -> tuple[GmDeclarationThreadEntry, ...]:
        entries = self._conversation_entries_for_active_interaction()
        if exclude_latest_player and entries and entries[-1].role == "player":
            entries = entries[:-1]
        return tuple(
            GmDeclarationThreadEntry(
                entry.role,
                entry.body,
                entry.outcome,
                entry.grounded_fact_ids,
                entry.hint_level,
            )
            for entry in entries[-16:]
        )

    def _conversation_payload(self) -> dict[str, object]:
        return {
            "interaction_id": self._active_conversation_id(),
            "entries": [entry.as_payload() for entry in self._conversation_entries_for_active_interaction()],
        }

    def _submit_npc_action(
        self,
        point: ExplorationPoint,
        text: str,
        *,
        selected_goal_id: str | None = None,
        conversation_only: bool = False,
    ) -> dict[str, object]:
        npc = point.npc_interaction
        assert npc is not None
        runtime_state = npc_runtime_state_for(self.state, npc.id)
        if (
            not conversation_only
            and runtime_state is not None
            and runtime_state.interaction_status == NpcInteractionStatus.CLOSED
        ):
            self._add_message(
                "Odpowiedź NPC",
                runtime_state.closure_reason
                or f"{npc.name} nie chce już kontynuować tej rozmowy.",
            )
            return self.state_payload()
        key_issue_match = (
            None
            if conversation_only
            else match_npc_key_issue(
                npc,
                text,
                self.state.flags,
                selected_goal_id,
            )
        )
        if key_issue_match is not None:
            issue = key_issue_match.issue
            for index, raw_effect in enumerate(issue.effects):
                validate_policy_exploration_effect(
                    raw_effect,
                    self.state,
                    allowed_effect_types=npc.policy.allowed_effect_types,
                    allowed_flags=npc.policy.allowed_flags,
                    field=f"NPC key issue {issue.id}.effects[{index}]",
                )
                result = apply_exploration_effect(self.state, raw_effect)
                self.state = result.state
                self._record_effect_result(
                    result,
                    source=f"npc_key_issue:{issue.id}",
                    raw_effect=raw_effect,
                )
            self._add_message("Narracja MG", issue.narration)
            self._add_message(npc.name, issue.npc_response)
            self._record(
                "ui_npc_key_issue_triggered",
                {
                    "point_id": point.id,
                    "issue_id": issue.id,
                    "selected_goal_id": selected_goal_id,
                    "matched_phrase": key_issue_match.matched_phrase,
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        client = self._npc_client()
        zone = next(zone for zone in self.exploration.zones if zone.id == point.zone_id)
        request_data = build_npc_interaction_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            zone=zone,
            point=point,
            state=self.state,
            player_action=text,
            conversation_thread=self._conversation_thread_for_active_interaction(exclude_latest_player=True),
            selected_goal_id=selected_goal_id,
            conversation_only=conversation_only,
        )
        proposal = client.interact_npc(request_data)
        if conversation_only:
            answer = (
                proposal.player_narration.strip()
                or (
                    "To pytanie do MG, nie kwestia wypowiedziana do NPC. "
                    "Jeśli chcecie wpłynąć na rozmówcę, wybierzcie cel rozmowy "
                    "i opiszcie swoje podejście."
                )
            )
            self._record(
                "ui_npc_gm_conversation_answered",
                {"point_id": point.id, "question": text, "answer": answer},
            )
            self._add_message("Odpowiedź MG", answer)
            return self.state_payload()
        validated = validate_npc_interaction_proposal(proposal, request_data)
        self._record(
            "ui_npc_proposal_validated",
            {
                "point_id": point.id,
                "proposal": validated.proposal.model_dump(mode="json"),
            },
        )
        self.pending = PendingInteraction(
            kind=PendingKind.NPC,
            stage=PendingStage.DECISION,
            proposal=validated.proposal,
            point=point,
            social_plan=validated.social_plan,
            attempt_plan=validated.attempt_plan,
            action_plan=validated.action_plan,
        )
        if validated.proposal.player_narration:
            self._add_message("Narracja MG", validated.proposal.player_narration)
        if validated.proposal.npc_response:
            self._add_message("Odpowiedź NPC", validated.proposal.npc_response)
        self._sync_board_leds()
        return self.state_payload()

    def resolve_npc_transition(self, reaction_id: str) -> dict[str, object]:
        plan = self.pending_npc_transition
        if plan is None:
            raise ValueError("Brak oczekującej decyzji w eskalacji sceny NPC.")
        resolution = resolve_npc_transition_reaction(self.state, plan, reaction_id)
        for effect, result in zip(resolution.reaction.effects, resolution.effect_results):
            self.state = result.state
            self._record_effect_result(result, source="npc_scene_transition", raw_effect=effect)
        self.state = resolution.state
        self.resolved_encounter_trigger_ids.update(
            resolution.reaction.suppress_encounter_trigger_ids
        )
        status = resolution.reaction.npc_status
        if status is not None:
            self.state = set_npc_interaction_status(
                self.state,
                npc_id=plan.definition.npc_id,
                status=status,
                closure_reason=(
                    "Po tej eskalacji NPC nie chce już kontynuować rozmowy."
                    if status == NpcInteractionStatus.CLOSED
                    else ""
                ),
            )
        self._add_message(plan.variant.title, plan.variant.narration)
        self._add_message("Reakcja drużyny", resolution.reaction.label)
        self._add_message("Narracja MG", resolution.reaction.narration)
        self._record(
            "ui_npc_transition_resolved",
            {
                "transition_id": plan.definition.id,
                "variant_id": plan.variant.id,
                "reaction_id": resolution.reaction.id,
                "result_type": resolution.reaction.result_type.value,
                "suppressed_encounter_trigger_ids": list(
                    resolution.reaction.suppress_encounter_trigger_ids
                ),
            },
        )
        self.pending_npc_transition = None
        if resolution.reaction.result_type == NpcTransitionResultType.END_INTERACTION:
            self.active_point_id = ""
        elif resolution.reaction.result_type == NpcTransitionResultType.START_ENCOUNTER:
            self.active_point_id = ""
            self._refresh_pending_encounter()
            expected_trigger_id = resolution.reaction.encounter_trigger_id
            if self.pending_encounter is None or self.pending_encounter.trigger_id != expected_trigger_id:
                raise ValueError(
                    "Wybrana eskalacja nie uruchomiła oczekiwanego encountera; sprawdź warunek triggera."
                )
        self._sync_board_leds()
        return self.state_payload()

    def update_pending_challenge_decision(self, data: dict[str, object]) -> dict[str, object]:
        if self.pending is None or self.pending.kind != PendingKind.CHALLENGE or self.pending.stage != PendingStage.DECISION:
            raise ValueError("Korekta decyzji MG jest dostępna tylko przed zaakceptowaniem testu eksploracji.")
        if self.pending.option is None:
            raise ValueError("Brak opcji testu do poprawienia.")
        if self.pending.fixture_action_plan is not None:
            raise ValueError(
                "Parametry operacji na fixture wynikają z contentu i nie mogą zostać zmienione korektą MG."
            )
        option = self.pending.option
        default_mechanic_id = option.mechanic_id or str(mechanic_payload_for_option(option)["id"])
        mechanic_id = ExplorationMechanicId(str(data.get("mechanic_id") or default_mechanic_id))
        participants = CheckParticipants(
            str(data.get("check_participants") or option.check_participants or CheckParticipants.SINGLE_ACTOR.value)
        )
        aggregation = CheckAggregation(
            str(data.get("check_aggregation") or option.check_aggregation or CheckAggregation.LEAD_RESULT.value)
        )
        if self.pending.participant_actor_ids:
            authored_participants = option.check_participants or CheckParticipants.SINGLE_ACTOR
            authored_aggregation = option.check_aggregation or CheckAggregation.LEAD_RESULT
            if participants != authored_participants or aggregation != authored_aggregation:
                raise ValueError(
                    "Typ testu i sposób rozstrzygnięcia są przypisane do wybranego kafelka."
                )
        validate_mechanic_selection(mechanic_id, participants=participants, aggregation=aggregation)

        lead_actor_id = str(data.get("lead_actor_id") or self.selected_lead_actor_id).strip()
        actor_ids = {str(actor.id) for actor in self.exploration.actors}
        if lead_actor_id not in actor_ids:
            raise ValueError("Wybrany prowadzący test nie istnieje w drużynie.")

        helper_actor_id = str(data.get("helper_actor_id") or "").strip() or None
        if participants == CheckParticipants.LEAD_WITH_HELP:
            if helper_actor_id is not None and helper_actor_id not in actor_ids:
                raise ValueError("Wybrany pomocnik nie istnieje w drużynie.")
            if helper_actor_id is not None and helper_actor_id == lead_actor_id:
                raise ValueError("Pomocnik musi być inną postacią niż prowadzący.")
        else:
            helper_actor_id = None

        ability = str(data.get("ability") or option.ability_check.ability).strip().lower()
        if ability not in EXPLORATION_DECISION_ABILITIES:
            raise ValueError(f"Nieznana cecha testu: {ability}.")
        skill_raw = data.get("skill", option.ability_check.skill)
        skill = str(skill_raw).strip().lower() if skill_raw is not None and str(skill_raw).strip() else None
        dc = int(data.get("dc") or option.ability_check.dc)
        if not EXPLORATION_DECISION_DC_MIN <= dc <= EXPLORATION_DECISION_DC_MAX:
            raise ValueError(f"ST musi być w zakresie {EXPLORATION_DECISION_DC_MIN}-{EXPLORATION_DECISION_DC_MAX}.")
        roll_mode = RollMode(str(data.get("roll_mode") or option.roll_mode.value))
        situational_modifiers = _situational_modifiers_from_payload(
            data.get("situational_modifiers"),
            fallback=option.situational_modifiers,
        )
        roll_mode = _combined_roll_mode(roll_mode, tuple(modifier.roll_mode for modifier in situational_modifiers))
        improvised_tool = _improvised_tool_from_payload(
            data.get("improvised_tool"),
            fallback=option.improvised_tool,
        )
        if mechanic_id == ExplorationMechanicId.IMPROVISED_TOOL_CHECK and improvised_tool is None:
            raise ValueError("Mechanika improwizowanego narzędzia wymaga opisu narzędzia.")
        if mechanic_id != ExplorationMechanicId.IMPROVISED_TOOL_CHECK:
            improvised_tool = None

        updated_option = replace(
            option,
            ability_check=replace(option.ability_check, ability=ability, skill=skill, dc=dc),
            check_participants=participants,
            check_aggregation=aggregation,
            mechanic_id=mechanic_id.value,
            roll_mode=roll_mode,
            situational_modifiers=situational_modifiers,
            improvised_tool=improvised_tool,
        )
        selected_resources = self.pending.resources
        if "resource_id" in data:
            resource_id = str(data.get("resource_id") or "").strip()
            if resource_id:
                available_resources = {
                    resource.id: resource
                    for resource in matching_resources(self.state, updated_option)
                }
                if resource_id not in available_resources:
                    raise ValueError("Wybrany zasób nie jest dostępny albo nie pasuje do tego podejścia.")
                selected_resources = (available_resources[resource_id],)
            else:
                selected_resources = ()
        self.selected_lead_actor_id = lead_actor_id
        self.selected_helper_actor_id = helper_actor_id
        self.pending = replace(self.pending, option=updated_option, resources=selected_resources)
        self._record(
            "ui_gm_decision_corrected",
            {
                "mechanic_id": mechanic_id.value,
                "participants": participants.value,
                "aggregation": aggregation.value,
                "lead_actor_id": lead_actor_id,
                "helper_actor_id": helper_actor_id,
                "ability": ability,
                "skill": skill,
                "dc": dc,
                "roll_mode": roll_mode.value,
                "situational_modifiers": [modifier.as_payload() for modifier in situational_modifiers],
                "improvised_tool": improvised_tool.as_payload() if improvised_tool else None,
                "resource_id": selected_resources[0].id if selected_resources else None,
            },
        )
        self._add_message(
            "Poprawiono decyzję MG",
            f"Mechanika: {mechanic_id.value}. Test: {ability}{('/' + skill) if skill else ''}, ST {dc}. Tryb: {roll_mode.value}.",
        )
        return self.state_payload()

    def decide(
        self,
        decision: str,
        *,
        lead_actor_id: str | None = None,
        source_id: str | None = None,
        quantity: int | None = None,
    ) -> dict[str, object]:
        if self.pending is None:
            raise ValueError("Brak propozycji oczekującej na decyzję.")
        normalized = decision.strip().lower()
        self._record(
            "ui_pending_decision_submitted",
            {
                "decision": normalized,
                "pending_kind": self.pending.kind.value,
                "pending_stage": self.pending.stage.value,
                "lead_actor_id": lead_actor_id,
                "quantity": quantity,
            },
        )
        if normalized in {"reject", "odrzuc", "odrzuć", "-"}:
            message = (
                "Nie wybieracie żadnego z zaproponowanych elementów. Możecie doprecyzować dalsze poszukiwania."
                if self.pending.kind == PendingKind.SOURCE_SELECTION
                else "Odrzucono interpretację. Wpisz deklarację inaczej."
            )
            self._add_message("Decyzja", message)
            self.pending = None
            self._sync_board_leds()
            return self.state_payload()
        if normalized in {"explain", "wyjasnij", "wyjaśnij", "?"}:
            self._add_message("Wyjaśnienie", _pending_explanation(self.pending))
            return self.state_payload()
        if normalized in {"reinterpret", "r"}:
            self._add_message("Reinterpretacja", "Wpisz deklarację ponownie, akcentując korektę interpretacji.")
            self.pending = None
            self._sync_board_leds()
            return self.state_payload()
        if normalized not in {"accept", "akceptuj", "+"}:
            raise ValueError(f"Nieznana decyzja: {decision}.")
        if lead_actor_id and any(str(actor.id) == lead_actor_id for actor in self.exploration.actors):
            self.selected_lead_actor_id = lead_actor_id
        result: dict[str, object]
        if self.pending.kind == PendingKind.CHALLENGE:
            result = self._accept_challenge()
        elif self.pending.kind == PendingKind.CRAFTING:
            result = self._accept_crafting()
        elif self.pending.kind == PendingKind.OBSERVATION:
            result = self._accept_observation()
        elif self.pending.kind == PendingKind.TRAP:
            result = self._accept_trap_action()
        elif self.pending.kind == PendingKind.SOURCE_SELECTION:
            result = self._accept_source_selection(source_id)
        elif self.pending.kind == PendingKind.COLLECTION:
            result = self._accept_collection(lead_actor_id=lead_actor_id, quantity=quantity)
        else:
            result = self._accept_npc()
        self._sync_board_leds()
        return result

    def _accept_collection(
        self,
        *,
        lead_actor_id: str | None,
        quantity: int | None,
    ) -> dict[str, object]:
        assert self.pending is not None and self.pending.collection_plan is not None
        preview = self.pending.collection_plan
        selected_quantity = quantity if quantity is not None else preview.quantity
        owner_actor_id = (
            lead_actor_id
            if preview.destination.value == "actor_inventory"
            else None
        )
        plan = plan_source_collection(
            preview.source,
            quantity=selected_quantity,
            owner_actor_id=owner_actor_id,
        )
        if plan.source.kind == CraftingSourceKind.SCENE_ITEM:
            self.state = discover_scene_source(
                self.state,
                plan.source,
                requested_as=f"/weź {plan.source.label}",
            )
        result = collect_source(self.state, self.exploration.actors, plan)
        self.state = result.state
        self.exploration = replace(self.exploration, actors=result.actors)
        owner = next(
            (actor for actor in result.actors if str(actor.id) == result.collection.owner_actor_id),
            None,
        )
        destination = {
            "actor_inventory": f"ekwipunek postaci {owner.name}" if owner is not None else "ekwipunek postaci",
            "party_treasure": "wspólne łupy drużyny",
            "scenario_quest": "zasoby fabularne scenariusza",
        }[result.collection.destination]
        self._record(
            "ui_collection_confirmed",
            {
                "source_id": result.collection.source_id,
                "quantity": selected_quantity,
                "destination": result.collection.destination,
                "owner_actor_id": result.collection.owner_actor_id,
                "inventory_item_id": result.inventory_item.id if result.inventory_item else None,
            },
        )
        self._add_message(
            "Zabrano przedmiot",
            f"{result.collection.label} ×{selected_quantity} przeniesiono do: {destination}.",
        )
        self.pending = None
        return self.state_payload()

    def _accept_source_selection(self, source_id: str | None) -> dict[str, object]:
        assert self.pending is not None and self.pending.kind == PendingKind.SOURCE_SELECTION
        if not self.pending.source_matches:
            raise ValueError("Brak elementów do wyboru.")
        selected_id = source_id.strip() if source_id else self.pending.source_matches[0].source.id
        selected = next(
            (match for match in self.pending.source_matches if match.source.id == selected_id),
            None,
        )
        if selected is None:
            raise ValueError("Wybrany element nie należy do propozycji MG.")
        analysis = self.pending.proposal
        assert isinstance(analysis, GmDeclarationAnalysis) and analysis.source_query is not None
        matched_properties = tuple(
            dict.fromkeys(
                (
                    *analysis.source_query.required_properties,
                    *selected.matched_preferred_properties,
                )
            )
        )
        self.state = discover_scene_source(
            self.state,
            selected.source,
            requested_as=analysis.source_query.requested_name or self.pending.source_search_text,
            purpose=analysis.source_query.purpose,
            matched_properties=matched_properties,
            semantic_substitution=True,
        )
        property_labels = self.exploration.crafting_policy.property_label
        features = ", ".join(property_labels(item) for item in selected.source.properties)
        answer = (
            f"Znaleźliście: {selected.source.label}. Cechy: {features or 'brak opisanych cech'}. "
            "Element pozostaje częścią sceny i nie został dodany do ekwipunku."
        )
        self._record(
            "ui_scene_source_selected",
            {
                "source_id": selected.source.id,
                "zone_id": selected.source.zone_id,
                "requested_name": analysis.source_query.requested_name,
                "purpose": analysis.source_query.purpose,
                "matched_properties": list(matched_properties),
                "added_to_inventory": False,
            },
        )
        self._add_message(
            "Znaleziono w scenie",
            answer,
            outcome="source_selection_accepted",
            grounded_fact_ids=(f"source:{selected.source.id}",),
        )
        self.pending = None
        return self.state_payload()

    def _accept_crafting(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.crafting_plan is not None
        plan = self.pending.crafting_plan
        self.state, item = craft_temporary_item(
            self.state,
            plan.draft,
            build_crafting_source_registry(self.state, self.exploration.actors),
            self.exploration.crafting_policy,
        )
        self._record(
            "ui_crafting_confirmed",
            {
                "item_id": item.id,
                "purpose_id": item.purpose_id,
                "uses_remaining": item.uses_remaining,
                "time_cost_minutes": item.time_cost_minutes,
                "component_uses": [
                    {
                        "source_id": component.source_id,
                        "quantity": component.quantity,
                        "disposition": component.disposition.value,
                    }
                    for component in item.component_uses
                ],
            },
        )
        self._add_message(
            "Utworzono przedmiot sceny",
            (
                f"{item.label}: {item.uses_remaining} użycia, czas budowy {item.time_cost_minutes} min. "
                "Budowa nie wymagała rzutu; test nastąpi dopiero przy ryzykownym użyciu."
            ),
        )
        self.pending = None
        return self.state_payload()

    def dismantle_temporary_item(self, item_id: str) -> dict[str, object]:
        if self.pending is not None:
            raise ValueError("Najpierw rozstrzygnij oczekującą propozycję MG.")
        self.state, item = dismantle_crafted_item(self.state, item_id.strip())
        released = tuple(
            component.source_id
            for component in item.component_uses
            if component.disposition.value == "reserved"
        )
        self._record(
            "ui_crafting_dismantled",
            {
                "item_id": item.id,
                "purpose_id": item.purpose_id,
                "released_source_ids": list(released),
            },
        )
        release_text = (
            " Odzyskano zarezerwowane komponenty: " + ", ".join(released) + "."
            if released
            else " Zużyte materiały nie wracają do puli."
        )
        self._add_message("Rozmontowano przedmiot sceny", f"Rozmontowano: {item.label}.{release_text}")
        return self.state_payload()

    def _accept_challenge(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.option is not None and self.pending.challenge is not None
        option = self.pending.option
        participant_actor_ids = self.pending.participant_actor_ids
        lead_actor_id = (
            participant_actor_ids[0]
            if participant_actor_ids
            else self.lead_actor_id
        )
        matching_actors = actors_matching_challenge_option(self.exploration.actors, option)
        if (
            not participant_actor_ids
            and matching_actors
            and not any(str(actor.id) == lead_actor_id for actor in matching_actors)
        ):
            lead_actor_id = str(matching_actors[0].id)
            self.selected_lead_actor_id = lead_actor_id
        helper_actor_id = None
        if option.check_participants == CheckParticipants.LEAD_WITH_HELP:
            if participant_actor_ids:
                helper_actor_id = (
                    participant_actor_ids[1]
                    if len(participant_actor_ids) == 2
                    else None
                )
            else:
                actor_ids = {str(actor.id) for actor in self.exploration.actors}
                helper_actor_id = (
                    self.selected_helper_actor_id
                    if self.selected_helper_actor_id in actor_ids
                    and self.selected_helper_actor_id != lead_actor_id
                    else None
                )
            self.selected_helper_actor_id = helper_actor_id
        else:
            self.selected_helper_actor_id = None
        resource = self.pending.resources[0] if self.pending.resources else None
        if resource is not None and resource not in matching_resources(self.state, option):
            raise ValueError("Wybrany zasób nie jest już dostępny dla tego podejścia.")
        plan = _challenge_check_plan(
            option,
            lead_actor_id,
            self.exploration.actors,
            helper_actor_id=helper_actor_id,
            selected_actor_ids=participant_actor_ids,
            resource=resource,
        )
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    def _accept_npc(self) -> dict[str, object]:
        assert self.pending is not None
        proposal = self.pending.proposal
        assert isinstance(proposal, NpcInteractionProposal)
        if self.pending.attempt_plan is not None and not self.pending.attempt_plan.available:
            self._add_message("Reakcja NPC", self.pending.attempt_plan.blocked_reason)
            self.pending = None
            return self.state_payload()
        if self.pending.social_plan is not None and not self.pending.social_plan.possible:
            self._update_npc_runtime(proposal, success=False, revealed_information_ids=())
            self._add_message(
                "Reakcja NPC",
                "Przy obecnym nastawieniu NPC odmawia podjęcia takiego ryzyka. Ta prośba nie wymaga rzutu.",
            )
            self.pending = None
            return self.state_payload()
        if self.pending.action_plan is not None and not proposal.requires_roll:
            self._resolve_structured_npc_outcome(proposal, NpcOutcomeTier.SUCCESS)
            self.pending = None
            return self.state_payload()
        if not proposal.requires_roll:
            self._apply_npc_flags(proposal, success=True)
            revealed = self._reveal_npc_information(proposal)
            self._update_npc_runtime(proposal, success=True, revealed_information_ids=revealed)
            self._add_message("Wynik interakcji NPC", "Interakcja nie wymagała rzutu.")
            self.pending = None
            return self.state_payload()
        plan = _npc_check_plan(proposal, self.lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    def _accept_observation(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.observation is not None
        observation = self.pending.observation
        lead_actor_id = (
            self.pending.participant_actor_ids[0]
            if self.pending.participant_actor_ids
            else self.lead_actor_id
        )
        plan = _observation_check_plan(observation, lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wynik rzutu. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    def _accept_trap_action(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.trap is not None
        assert self.pending.trap_action is not None
        trap = self.pending.trap
        action = self.pending.trap_action
        if action == ExplorationTrapAction.TRIGGER:
            result = resolve_trap_action(self.state, trap, action)
            self.state = result.state
            self._record_trap_action_result(result, actor_id=self.lead_actor_id)
            self._queue_trap_hazard(trap, self.lead_actor_id)
            return self.state_payload()
        check = (
            trap.disarm_check
            if action == ExplorationTrapAction.DISARM
            else trap.bypass_check
        )
        if check is None:
            result = resolve_trap_action(self.state, trap, action)
            self.state = result.state
            self._record_trap_action_result(result, actor_id=self.lead_actor_id)
            self._add_message("Wynik pułapki", result.message)
            self.pending = None
            return self.state_payload()
        actor = next(
            (item for item in self.exploration.actors if str(item.id) == self.lead_actor_id),
            None,
        )
        if actor is None:
            raise ValueError("Nie znaleziono postaci prowadzącej próbę.")
        if action == ExplorationTrapAction.DISARM and trap.required_item_id is not None:
            if not any(
                item.id == trap.required_item_id and item.available
                for item in actor.inventory
            ):
                raise ValueError(
                    f"{actor.name} nie ma wymaganego przedmiotu: {trap.required_item_id}."
                )
        plan = _trap_check_plan(trap, action, self.lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wynik rzutu. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    @property
    def lead_actor_id(self) -> str:
        return self.selected_lead_actor_id

    def resolve_rolls(self, raw_rolls: dict[str, object]) -> dict[str, object]:
        if self.pending is not None and self.pending.stage == PendingStage.HAZARD_SAVE:
            self._resolve_exploration_hazard_save(raw_rolls)
            if self.pending is not None and self.pending.stage == PendingStage.HAZARD_SAVE:
                self.pending = None
            if self.pending is None:
                self._refresh_pending_encounter()
            self._sync_board_leds()
            return self.state_payload()
        if self.pending is not None and self.pending.stage == PendingStage.BREAKAGE:
            self._resolve_breakage_roll(raw_rolls)
            self.pending = None
            self._refresh_pending_encounter()
            self._sync_board_leds()
            return self.state_payload()
        if self.pending is None or self.pending.stage != PendingStage.ROLL or self.pending.check_plan is None:
            raise ValueError("Brak oczekującego rzutu.")
        plan = self.pending.check_plan
        inputs = _check_inputs_from_payload(self.exploration.actors, plan, raw_rolls)
        check_result = resolve_exploration_check(plan, inputs)
        self._record(
            "ui_rolls_resolved",
            {
                "pending_kind": self.pending.kind.value,
                "raw_rolls": raw_rolls,
                "check_result": check_result.as_payload(),
            },
        )
        if self.pending.kind == PendingKind.CHALLENGE:
            self._resolve_challenge_roll(check_result)
        elif self.pending.kind == PendingKind.OBSERVATION:
            self._resolve_observation_roll(check_result)
        elif self.pending.kind == PendingKind.TRAP:
            self._resolve_trap_roll(check_result)
        else:
            self._resolve_npc_roll(check_result)
        if self.pending is not None and self.pending.stage not in {
            PendingStage.BREAKAGE,
            PendingStage.HAZARD_SAVE,
        }:
            self.pending = None
        if self.pending is None or self.pending.stage != PendingStage.HAZARD_SAVE:
            self._refresh_pending_encounter()
        self._sync_board_leds()
        return self.state_payload()

    def _resolve_challenge_roll(self, check_result) -> None:
        assert self.pending is not None and self.pending.challenge is not None and self.pending.option is not None
        option = self.pending.option
        resource = self.pending.resources[0] if self.pending.resources else None
        challenge = self.pending.challenge
        available_before = {zone.id for zone in available_exploration_zones(self.state)}
        visible_points_before = {point.id for point in visible_exploration_points(self.state.points)}
        if self.pending.option not in challenge.options:
            challenge = replace(challenge, options=(*challenge.options, self.pending.option))
        result = resolve_challenge_option(
            self.state,
            challenge,
            self.pending.option,
            check_result.selected_roll,
            resource,
        )
        self.state = result.state
        result_message = result.message
        if challenge.id == "closed_gate":
            result_message = (
                f"{result_message} "
                f"{_gate_state_narration(self.state, challenge.id)}"
            )
        self._add_message("Wynik podejścia", result_message)
        if self.pending.fixture_action_plan is not None:
            fixture_result = apply_fixture_action(
                self.state,
                self.pending.fixture_action_plan,
                success=result.success,
            )
            self.state = fixture_result.state
            released_labels: list[str] = []
            if fixture_result.changed and fixture_result.released_item_ids:
                registry = build_crafting_source_registry(self.state, self.exploration.actors)
                for item_id in fixture_result.released_item_ids:
                    source = registry.source_by_id(
                        f"zone:{fixture_result.plan.zone_id}:item:{item_id}"
                    )
                    if source is None:
                        continue
                    self.state = discover_scene_source(
                        self.state,
                        source,
                        requested_as=f"rezultat {fixture_result.plan.policy.operation.value}",
                    )
                    released_labels.append(source.label)
            if fixture_result.changed:
                released_text = (
                    " Ujawnione elementy: " + ", ".join(released_labels) + "."
                    if released_labels
                    else ""
                )
                self._add_message(
                    "Zmiana obiektu",
                    (
                        f"{fixture_result.plan.fixture.name}: "
                        f"{fixture_result.plan.current_condition} → "
                        f"{fixture_result.plan.policy.result_condition}."
                        f"{released_text}"
                    ),
                )
            self._record(
                "ui_fixture_action_resolved",
                {
                    "source_id": fixture_result.plan.source_id,
                    "operation": fixture_result.plan.policy.operation.value,
                    "success": result.success,
                    "changed": fixture_result.changed,
                    "result_condition": (
                        fixture_result.plan.policy.result_condition
                        if fixture_result.changed
                        else fixture_result.plan.current_condition
                    ),
                    "released_item_ids": list(fixture_result.released_item_ids),
                },
            )
        if resource is not None and resource.consume_on_use:
            raw_effect = {"type": "remove_resource", "parameters": {"resource_id": resource.id}}
            consumption = apply_exploration_effect(self.state, raw_effect)
            self.state = consumption.state
            self._record_effect_result(
                consumption,
                source="challenge_resource_consumption",
                raw_effect=raw_effect,
            )
            if consumption.changed:
                self._add_message("Zużyty zasób", f"{resource.label} został zużyty podczas próby.")
        temporary_item = next(
            (item for item in self.state.temporary_items if resource is not None and item.id == resource.id),
            None,
        )
        if temporary_item is not None:
            self.state, updated_item = use_temporary_item(self.state, temporary_item.id)
            self._record(
                "ui_temporary_item_used",
                {"item_id": updated_item.id, "uses_remaining": updated_item.uses_remaining},
            )
            status = (
                f"Pozostałe użycia: {updated_item.uses_remaining}."
                if updated_item.available
                else "Przedmiot nie nadaje się już do użycia."
            )
            self._add_message("Użyto przedmiotu sceny", f"{updated_item.label}. {status}")
        self._consume_active_exploration_bonuses(check_result.selected_actor, self.pending.option)
        self._record(
            "ui_challenge_resolved",
            {
                "challenge_id": challenge.id,
                "option_id": self.pending.option.id,
                "success": result.success,
                "completed": result.completed,
                "progress_added": result.progress_added,
                "noise_added": result.noise_added,
                "complications_added": list(result.complications_added),
                "resource_id": resource.id if resource else None,
                "option_bonuses": list(check_result.plan.option_bonus_payloads),
            },
        )

        self._queue_breakage_check_if_needed(result, check_result.selected_actor)
        self._queue_exploration_hazard_if_needed(result, check_result.selected_actor)
        if result.completed:
            revealed_points = self._reveal_completed_challenge_points(challenge)
            available_after = {zone.id for zone in available_exploration_zones(self.state)}
            visible_points_after = {point.id for point in visible_exploration_points(self.state.points)}
            unlocked_zone_ids = tuple(sorted(available_after - available_before))
            revealed_point_ids = tuple(sorted((visible_points_after - visible_points_before) | {point.id for point in revealed_points}))
            if option.id == "force_gate" or "heavy_force" in option.tags:
                self.post_interaction_setup_steps = (_fallen_gate_setup_step(),)
                self.interaction_result = {
                    "title": f"Zakończono: {challenge.name}",
                    "body": result.message,
                    "unlocked_zones": [
                        _zone_payload(zone, self._scenario_asset_root()) for zone in self.state.zones if zone.id in unlocked_zone_ids
                    ],
                    "revealed_points": [_point_payload(point) for point in self.state.points if point.id in revealed_point_ids],
                    "current_zone": _zone_payload(self.current_zone, self._scenario_asset_root()),
                    "next_instruction": "Potwierdź wynik, żeby rozstawić przewróconą bramę jako nową przeszkodę.",
                }
                self.ui_flow_stage = UiFlowStage.INTERACTION_RESULT
                self.preview_zone_id = ""
                self.board_message = "Wyważenie zakończone. Potwierdź wynik, a potem ustaw przewróconą bramę."
                self._add_message(
                    "Nowy element mapy",
                    "Wyważona brama przewraca się na dziedziniec. Po potwierdzeniu wyniku ustaw przewrócone skrzydło na podświetlonych polach.",
                )
                if result.success:
                    self._queue_completed_challenge_trap(challenge, check_result.selected_actor)
                return
            self.interaction_result = {
                "title": f"Zakończono: {challenge.name}",
                "body": result.message,
                "unlocked_zones": [_zone_payload(zone, self._scenario_asset_root()) for zone in self.state.zones if zone.id in unlocked_zone_ids],
                "revealed_points": [_point_payload(point) for point in self.state.points if point.id in revealed_point_ids],
                "current_zone": _zone_payload(self.current_zone, self._scenario_asset_root()),
                "next_instruction": "Zakończ interakcję, żeby wrócić do wyboru lokacji.",
            }
            self.ui_flow_stage = UiFlowStage.INTERACTION_RESULT
            self.preview_zone_id = ""
            if result.success:
                self._queue_completed_challenge_trap(challenge, check_result.selected_actor)

    def _queue_exploration_hazard_if_needed(self, result, actor: Actor) -> None:
        if self.pending is None or self.pending.option is None:
            return
        trigger = (
            ExplorationHazardTrigger.CRITICAL_FAILURE
            if result.critical_failure
            else ExplorationHazardTrigger.FAILURE
            if not result.success
            else None
        )
        if trigger is None:
            return
        hazard = next(
            (item for item in self.pending.option.hazards if item.trigger == trigger),
            None,
        )
        if hazard is None:
            return
        self.pending = replace(
            self.pending,
            stage=PendingStage.HAZARD_SAVE,
            hazard=hazard,
            hazard_actor_id=str(actor.id),
        )
        narration = hazard.narration or f"Uruchamia się zagrożenie: {hazard.label}."
        self._add_message(
            "Zagrożenie",
            f"{narration} {actor.name} musi wykonać "
            f"{hazard.saving_throw.as_payload()['ability_label']} save przeciw "
            f"ST {hazard.saving_throw.dc}.",
        )
        self._record(
            "ui_exploration_hazard_queued",
            {
                "hazard_id": hazard.id,
                "actor_id": str(actor.id),
                "trigger": trigger.value,
                "saving_throw": hazard.saving_throw.as_payload(),
            },
        )

    def _queue_completed_challenge_trap(
        self,
        challenge: ExplorationChallenge,
        actor: Actor,
    ) -> None:
        if self.pending is not None and self.pending.stage in {
            PendingStage.BREAKAGE,
            PendingStage.HAZARD_SAVE,
        }:
            return
        trap = next(
            (
                item
                for item in self.state.traps
                if item.zone_id == challenge.zone_id
                and item.activation_challenge_id == challenge.id
                and trap_state_for(self.state, item.id).status
                in {ExplorationTrapStatus.HIDDEN, ExplorationTrapStatus.REVEALED}
            ),
            None,
        )
        if trap is None:
            return
        self.state = trigger_trap(self.state, trap)
        self._queue_trap_hazard(trap, str(actor.id))

    def _queue_trap_hazard(self, trap: ExplorationTrap, actor_id: str) -> None:
        if trap_state_for(self.state, trap.id).status != ExplorationTrapStatus.TRIGGERED:
            self.state = trigger_trap(self.state, trap)
        challenge = self.pending.challenge if self.pending is not None else self.active_challenge
        self.pending = PendingInteraction(
            kind=PendingKind.TRAP,
            stage=PendingStage.HAZARD_SAVE,
            challenge=challenge,
            trap=trap,
            trap_action=ExplorationTrapAction.TRIGGER,
            hazard=trap.hazard,
            hazard_actor_id=actor_id,
        )
        actor = next(
            (item for item in self.exploration.actors if str(item.id) == actor_id),
            None,
        )
        actor_name = actor.name if actor is not None else actor_id
        self._add_message(
            "Zagrożenie",
            f"{trap.hazard.narration} {actor_name} wykonuje "
            f"{trap.hazard.saving_throw.as_payload()['ability_label']} save przeciw "
            f"ST {trap.hazard.saving_throw.dc}.",
        )
        self._record(
            "ui_exploration_trap_triggered",
            {
                "trap_id": trap.id,
                "actor_id": actor_id,
                "hazard_id": trap.hazard.id,
            },
        )

    def _resolve_trap_roll(self, check_result) -> None:
        assert self.pending is not None and self.pending.trap is not None
        assert self.pending.trap_action is not None
        trap = self.pending.trap
        result = resolve_trap_action(
            self.state,
            trap,
            self.pending.trap_action,
            total=check_result.selected_roll.total,
        )
        self.state = result.state
        actor_id = str(check_result.selected_actor.id)
        self._record_trap_action_result(result, actor_id=actor_id)
        self._add_message(
            "Wynik pułapki",
            f"{result.message} Wynik testu: {check_result.selected_roll.total}.",
        )
        if result.triggered:
            self._queue_trap_hazard(trap, actor_id)

    def _record_trap_action_result(self, result, *, actor_id: str) -> None:
        self._record(
            "ui_exploration_trap_action_resolved",
            {
                "trap_id": result.trap.id,
                "action": result.action.value,
                "actor_id": actor_id,
                "success": result.success,
                "triggered": result.triggered,
                "status": trap_state_for(self.state, result.trap.id).status.value,
            },
        )

    def _resolve_exploration_hazard_save(self, raw_rolls: dict[str, object]) -> None:
        assert self.pending is not None
        hazard = self.pending.hazard
        actor_id = self.pending.hazard_actor_id
        if hazard is None or actor_id is None:
            raise ValueError("Brak danych oczekującego zagrożenia eksploracyjnego.")
        if actor_id not in raw_rolls:
            raise ValueError("Brakuje naturalnego wyniku d20 dla rzutu obronnego.")
        raw_roll = raw_rolls[actor_id]
        if isinstance(raw_roll, dict):
            raw_roll = raw_roll.get("natural_roll", 0)
        actor = next(
            (candidate for candidate in self.exploration.actors if str(candidate.id) == actor_id),
            None,
        )
        if actor is None:
            raise ValueError(f"Nieznany aktor zagrożenia: {actor_id}.")
        resolution = resolve_exploration_hazard(
            actor,
            hazard,
            natural_roll=int(raw_roll),
            rng=self.encounter_rng,
        )
        self.exploration = self._replace_exploration_actor(resolution.actor_after)
        if resolution.applied_damage.damage.total_applied > 0:
            trigger_resolution = resolve_actor_trigger_events(
                self.exploration.actors,
                (EffectEvent(EffectEventType.DAMAGE_TAKEN, actor_id=actor_id),),
            )
            self.exploration = replace(
                self.exploration,
                actors=trigger_resolution.actors,
            )
            self._add_trigger_activation_notices(trigger_resolution.activations)
        self._add_message("Wynik zagrożenia", resolution.message)
        challenge_id = self.pending.challenge.id if self.pending.challenge is not None else ""
        if resolution.outcome_effects:
            outcome_state, effect_results = apply_exploration_hazard_outcome(
                self.state,
                resolution.outcome_effects,
                actor_id=actor_id,
                challenge_id=challenge_id,
            )
            for effect_result, raw_effect in zip(effect_results, resolution.outcome_effects):
                self.state = effect_result.state
                self._record_effect_result(
                    effect_result,
                    source="exploration_hazard",
                    raw_effect=raw_effect,
                )
            self.state = outcome_state
            changed_messages = [result.message for result in effect_results if result.changed]
            if changed_messages:
                self._add_message("Skutek zagrożenia", " ".join(changed_messages))
        self._record(
            "ui_exploration_hazard_resolved",
            {
                "hazard_id": hazard.id,
                "actor_id": actor_id,
                "saving_throw": resolution.saving_throw.as_payload(),
                "base_damage": resolution.base_damage,
                "damage_result": applied_damage_payload(resolution.applied_damage),
                "outcome_effects": list(resolution.outcome_effects),
            },
        )
        if self.pending.breakage_actor_id is not None:
            self.pending = replace(
                self.pending,
                stage=PendingStage.BREAKAGE,
                hazard=None,
                hazard_actor_id=None,
            )
        else:
            self.pending = None

    def _resolve_observation_roll(self, check_result) -> None:
        assert self.pending is not None and self.pending.observation is not None
        observation = self.pending.observation
        resolution = resolve_observation(observation, check_result.selected_roll.total)
        fact_ids: list[str] = []
        granted_edge_labels: list[str] = []
        for fact in resolution.reached_facts:
            fact_ids.append(f"observation:{observation.id}:fact:{fact.id}")
            flag_effect = {
                "type": "set_flag",
                "parameters": {"key": fact.reveal_flag, "value": True},
            }
            effect_result = apply_exploration_effect(self.state, flag_effect)
            self.state = effect_result.state
            self._record_effect_result(effect_result, source="graded_observation", raw_effect=flag_effect)
            for effect in fact.effects:
                effect_result = apply_exploration_effect(self.state, effect)
                self.state = effect_result.state
                self._record_effect_result(effect_result, source="graded_observation", raw_effect=effect)
            if fact.encounter_edge is not None:
                edge = EncounterEdge(
                    id=(
                        f"observation:{observation.id}:fact:{fact.id}:"
                        f"actor:{check_result.selected_actor.id}"
                    ),
                    edge_type=fact.encounter_edge.edge_type,
                    label=fact.encounter_edge.label,
                    beneficiary_actor_id=str(check_result.selected_actor.id),
                    encounter_trigger_id=fact.encounter_edge.encounter_trigger_id,
                    source_observation_id=observation.id,
                    source_fact_id=fact.id,
                )
                self.state = grant_encounter_edge(self.state, edge)
                granted_edge_labels.append(edge.label)
                self._record(
                    "ui_encounter_edge_granted",
                    {
                        "edge_id": edge.id,
                        "edge_type": edge.edge_type.value,
                        "actor_id": edge.beneficiary_actor_id,
                        "encounter_trigger_id": edge.encounter_trigger_id,
                    },
                )
        self._add_message(
            "Wynik rozpoznania",
            f"{resolution.message} Wynik testu: {resolution.total}."
            + (
                " Nagroda: prowadzący obserwację otrzyma przewagę w inicjatywie "
                "podczas rozpoznanego starcia."
                if granted_edge_labels
                else ""
            ),
            outcome=f"observation:{observation.id}",
            grounded_fact_ids=tuple(fact_ids),
        )
        self._record(
            "ui_observation_resolved",
            {
                "observation_id": observation.id,
                "actor_id": str(check_result.selected_actor.id),
                "total": resolution.total,
                "success": resolution.success,
                "revealed_fact_ids": [fact.id for fact in resolution.reached_facts],
            },
        )

    def _consume_active_exploration_bonuses(self, actor: Actor, option: ExplorationChallengeOption) -> None:
        current_actor = next((candidate for candidate in self.exploration.actors if candidate.id == actor.id), actor)
        for bonus in active_option_bonuses_for_actor(current_actor, option):
            if bonus.source_type == "spell":
                spell_use = consume_spell_resource(current_actor, bonus.spell_level)
                current_actor = spell_use.actor_after
                self.exploration = self._replace_exploration_actor(current_actor)
                if spell_use.consumed:
                    self._add_message("Zużyty slot czaru", f"{bonus.label}: zużyto slot {bonus.spell_level}. poziomu.")
                    self._record(
                        "ui_exploration_spell_slot_consumed",
                        {
                            "actor_id": str(actor.id),
                            "spell_id": bonus.source_id,
                            "spell_level": bonus.spell_level,
                            "option_id": option.id,
                        },
                    )
                continue
            if bonus.source_type != "item" or not bonus.consume:
                continue
            current_actor = consume_inventory_item(current_actor, bonus.source_id)
            self.exploration = self._replace_exploration_actor(current_actor)
            self._add_message("Zużyty przedmiot", f"{bonus.label}: zasób został zużyty.")
            self._record(
                "ui_exploration_item_consumed",
                {"actor_id": str(actor.id), "item_id": bonus.source_id, "option_id": option.id},
            )

    def _queue_breakage_check_if_needed(self, result, actor: Actor) -> None:
        if self.pending is None or self.pending.option is None or not result.critical_failure:
            return
        current_actor = next((candidate for candidate in self.exploration.actors if candidate.id == actor.id), actor)
        for bonus in active_option_bonuses_for_actor(current_actor, self.pending.option):
            if bonus.source_type != "item" or bonus.breakage_risk is None:
                continue
            if bonus.breakage_risk.trigger != "critical_failure":
                continue
            self.pending = replace(
                self.pending,
                stage=PendingStage.BREAKAGE,
                breakage_actor_id=str(actor.id),
                breakage_item_id=bonus.source_id,
                breakage_item_label=bonus.label,
                breakage_chance_percent=bonus.breakage_risk.chance_percent,
            )
            self._add_message(
                "Sprawdź trwałość przedmiotu",
                f"Krytyczna porażka. Rzuć k100 dla: {bonus.label}. "
                f"Wynik {bonus.breakage_risk.chance_percent} lub mniej oznacza uszkodzenie.",
            )
            self._record(
                "ui_exploration_item_breakage_queued",
                {
                    "actor_id": str(actor.id),
                    "item_id": bonus.source_id,
                    "chance_percent": bonus.breakage_risk.chance_percent,
                },
            )
            return

    def _resolve_breakage_roll(self, raw_rolls: dict[str, object]) -> None:
        assert self.pending is not None
        actor_id = self.pending.breakage_actor_id
        item_id = self.pending.breakage_item_id
        chance = self.pending.breakage_chance_percent
        if actor_id is None or item_id is None or chance is None:
            raise ValueError("Brak danych testu trwałości przedmiotu.")
        if actor_id not in raw_rolls:
            raise ValueError("Brakuje wyniku k100 dla testu trwałości.")
        roll = int(raw_rolls[actor_id])
        if roll < 1 or roll > 100:
            raise ValueError("Test trwałości wymaga wyniku k100 od 1 do 100.")
        actor = next((candidate for candidate in self.exploration.actors if str(candidate.id) == actor_id), None)
        if actor is None:
            raise ValueError(f"Nieznany aktor testu trwałości: {actor_id}.")
        broken = roll <= chance
        if broken:
            self.exploration = self._replace_exploration_actor(break_inventory_item(actor, item_id))
            message = f"{self.pending.breakage_item_label} psuje się. Nie daje już premii i nie spełnia wymagań."
        else:
            message = f"{self.pending.breakage_item_label} wytrzymuje. Przedmiot nadal działa."
        self._add_message("Wynik trwałości przedmiotu", f"k100 {roll} / próg {chance}. {message}")
        self._record(
            "ui_exploration_item_breakage_resolved",
            {"actor_id": actor_id, "item_id": item_id, "roll": roll, "chance_percent": chance, "broken": broken},
        )

    def _replace_exploration_actor(self, updated_actor: Actor) -> LoadedExploration:
        actors = tuple(updated_actor if actor.id == updated_actor.id else actor for actor in self.exploration.actors)
        return replace(self.exploration, actors=actors)

    def _resolve_npc_roll(self, check_result) -> None:
        assert self.pending is not None
        proposal = self.pending.proposal
        assert isinstance(proposal, NpcInteractionProposal)
        if self.pending.action_plan is not None:
            outcome = npc_outcome_for_check(
                success=check_result.success,
                natural_roll=check_result.selected_roll.natural_roll,
            )
            self._resolve_structured_npc_outcome(proposal, outcome)
            return
        success = check_result.success
        message = proposal.success_message if success else proposal.failure_message
        self._add_message("Wynik interakcji NPC", message or ("Sukces." if success else "Porażka."))
        self._record("ui_npc_roll_resolved", {"success": success, "message": message})
        self._apply_npc_flags(proposal, success=success)
        revealed = self._reveal_npc_information(proposal) if success else ()
        self._update_npc_runtime(
            proposal,
            success=success,
            revealed_information_ids=revealed,
        )

    def _resolve_structured_npc_outcome(
        self,
        proposal: NpcInteractionProposal,
        outcome: NpcOutcomeTier,
    ) -> None:
        assert self.pending is not None and self.pending.action_plan is not None
        plan = self.pending.action_plan
        resolution = resolve_npc_outcome(self.state, plan, outcome)
        for effect, result in zip(resolution.branch.effects, resolution.effect_results):
            self.state = result.state
            self._record_effect_result(result, source="npc_outcome_branch", raw_effect=effect)
        self.state = resolution.state
        revealed = self._reveal_npc_information(
            proposal,
            information_ids=resolution.branch.revealed_information_ids,
        )
        success = outcome in {NpcOutcomeTier.CRITICAL_SUCCESS, NpcOutcomeTier.SUCCESS}
        self._add_message("Wynik interakcji NPC", resolution.branch.message)
        self._record(
            "ui_npc_outcome_resolved",
            {
                "intent": plan.intent,
                "target_id": plan.target.id,
                "outcome": outcome.value,
                "quantity": plan.quantity,
                "effects": list(resolution.branch.effects),
            },
        )
        self._update_npc_runtime(
            proposal,
            success=success,
            revealed_information_ids=revealed,
            state_update_override=resolution.branch.state_update,
            summary_override=resolution.branch.message,
            use_permission_update=False,
        )
        if resolution.branch.transition_id is not None:
            transition_plan = plan_npc_transition(
                self.exploration.npc_transitions,
                transition_id=resolution.branch.transition_id,
                state=self.state,
                resolved_encounter_trigger_ids=self.resolved_encounter_trigger_ids,
            )
            self.pending_npc_transition = transition_plan
            self._record(
                "ui_npc_transition_started",
                transition_plan.as_payload(),
            )

    def _apply_npc_flags(self, proposal: NpcInteractionProposal, *, success: bool) -> None:
        effects = proposal.effects_on_success if success else proposal.effects_on_failure
        if effects:
            for effect in effects:
                result = apply_exploration_effect(self.state, effect.as_effect_payload())
                self.state = result.state
                self._record_effect_result(result, source="npc_proposal", raw_effect=effect.as_effect_payload())
            return
        changes = proposal.flag_changes_on_success if success else proposal.flag_changes_on_failure
        for change in changes:
            result = apply_exploration_effect(
                self.state,
                {"type": "set_flag", "parameters": {"key": change.key, "value": change.value}},
            )
            self.state = result.state
            self._record_effect_result(
                result,
                source="npc_legacy_flag_change",
                raw_effect={"type": "set_flag", "parameters": {"key": change.key, "value": change.value}},
            )

    def _reveal_npc_information(
        self,
        proposal: NpcInteractionProposal,
        *,
        information_ids: tuple[str, ...] | None = None,
    ) -> tuple[str, ...]:
        if self.pending is None or self.pending.point is None or self.pending.point.npc_interaction is None:
            return ()
        npc = self.pending.point.npc_interaction
        known = {info.id: info for info in npc.locked_information}
        runtime_state = npc_runtime_state_for(self.state, npc.id)
        already_revealed = set(
            runtime_state.revealed_information_ids if runtime_state is not None else ()
        )
        revealed: list[str] = []
        for info_id in (
            proposal.revealed_information_ids
            if information_ids is None
            else information_ids
        ):
            info = known.get(info_id)
            if info is None or info.id in already_revealed:
                continue
            if all(scene_flag(self.state.flags, flag, False) for flag in info.reveal_if_flags):
                effects = info.effects_on_reveal or tuple(
                    {"type": "set_flag", "parameters": {"key": flag, "value": True}}
                    for flag in info.sets_flags
                )
                for effect in effects:
                    result = apply_exploration_effect(self.state, effect)
                    self.state = result.state
                    self._record_effect_result(result, source="npc_information", raw_effect=effect)
                self._add_message(f"Informacja: {info.label}", info.text)
                self._record("ui_npc_information_revealed", {"information_id": info.id, "label": info.label})
                revealed.append(info.id)
        return tuple(revealed)

    def _update_npc_runtime(
        self,
        proposal: NpcInteractionProposal,
        *,
        success: bool,
        revealed_information_ids: tuple[str, ...],
        state_update_override: NpcStateUpdate | None = None,
        summary_override: str | None = None,
        use_permission_update: bool = True,
    ) -> None:
        if self.pending is None or self.pending.point is None:
            return
        npc = self.pending.point.npc_interaction
        if npc is None:
            return
        permission = npc.policy.intent_permission(proposal.action_type)
        update = None
        if permission is not None and use_permission_update:
            update = permission.state_on_success if success else permission.state_on_failure
        if not use_permission_update:
            update = state_update_override
        summary = (
            summary_override
            or (proposal.success_message if success else proposal.failure_message)
        ) or proposal.npc_response or proposal.player_narration
        resolution = resolve_npc_runtime_interaction(
            self.state,
            npc_id=npc.id,
            intent=proposal.action_type,
            success=success,
            summary=summary,
            update=update,
            revealed_information_ids=revealed_information_ids,
            attempt_id=(
                permission.attempt_policy.attempt_id
                if proposal.requires_roll
                and permission is not None
                and permission.attempt_policy is not None
                else proposal.action_type
                if proposal.requires_roll
                else None
            ),
        )
        self.state = resolution.state
        if resolution.npc_before.attitude != resolution.npc_after.attitude:
            attitude_labels = {
                "hostile": "wrogi",
                "indifferent": "obojętny",
                "friendly": "przyjazny",
            }
            before = attitude_labels[resolution.npc_before.attitude.value]
            after = attitude_labels[resolution.npc_after.attitude.value]
            self._add_message("Zmiana nastawienia", f"{npc.name}: {before} → {after}.")
        self._record(
            "ui_npc_runtime_updated",
            {
                "npc_id": npc.id,
                "before": resolution.npc_before.as_payload(),
                "after": resolution.npc_after.as_payload(),
                "event": resolution.event.as_payload(),
            },
        )

    def _reveal_completed_challenge_points(self, challenge: ExplorationChallenge) -> tuple[ExplorationPoint, ...]:
        if not challenge.reveals_on_complete or not challenge_state_for(self.state, challenge.id).completed:
            return ()
        revealed: list[ExplorationPoint] = []
        for point_id in challenge.reveals_on_complete:
            result = apply_exploration_effect(
                self.state,
                {"type": "reveal_point", "parameters": {"point_id": point_id}},
            )
            self.state = result.state
            if result.changed:
                point = next(item for item in self.state.points if item.id == point_id)
                revealed.append(point)
            self._record_effect_result(
                result,
                source="challenge_completion",
                raw_effect={"type": "reveal_point", "parameters": {"point_id": point_id}},
            )
        for point in revealed:
            self._add_message("Nowy punkt odkryty", f"Odkrywacie nowy punkt w lokacji: {point.name}.")
        return tuple(revealed)

    def _refresh_pending_encounter(self) -> None:
        if self.pending_npc_transition is not None:
            return
        detection = self.exploration_flow.detect_encounter(
            state=self.state,
            triggers=self.exploration.encounter_triggers,
            resolved_trigger_ids=self.resolved_encounter_trigger_ids,
            blocked=bool(self.post_interaction_setup_steps) or self.exploration_setup_flow is not None,
            current_encounter=self.pending_encounter,
        )
        if detection is None:
            return
        self.pending_encounter = detection.encounter
        self._add_message(detection.message_title, detection.message_body)

    def _trigger_by_id(self, trigger_id: str) -> ExplorationEncounterTrigger | None:
        return next((trigger for trigger in self.exploration.encounter_triggers if trigger.id == trigger_id), None)

    def _pending_encounter_payload(self) -> dict[str, object] | None:
        if self.pending_encounter is None:
            return None
        trigger = self._trigger_by_id(self.pending_encounter.trigger_id)
        resolution = self.pending_encounter.opening_resolution
        return {
            "trigger_id": self.pending_encounter.trigger_id,
            "name": self.pending_encounter.name,
            "description": self.pending_encounter.description,
            "encounter_scenario": self.pending_encounter.encounter_scenario,
            "reason": self.pending_encounter.reason,
            "opening": {
                "required": bool(trigger is not None and trigger.opening_policy is not None),
                "resolved": resolution is not None,
                "rule_id": resolution.rule_id if resolution is not None else None,
                "outcome": resolution.outcome.value if resolution is not None else None,
                "outcome_label": _encounter_opening_outcome_label(resolution.outcome) if resolution is not None else "",
                "title": resolution.title if resolution is not None else "",
                "narration": resolution.narration if resolution is not None else "",
                "noise": resolution.noise if resolution is not None else None,
            },
            "command": (
                "PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop "
                f"--scenario {self.pending_encounter.encounter_scenario} --board-backend none --initiative-mode rolled"
            ),
        }

    def _precombat_stealth_payload(self) -> dict[str, object] | None:
        if self.pending_encounter is None:
            return None
        if not precombat_stealth_is_available(self.pending_encounter.opening_resolution):
            return None
        encounter = (
            self.encounter_setup_flow.encounter
            if self.encounter_setup_flow is not None
            else None
        )
        if encounter is None:
            return {
                "status": "waiting_for_setup",
                "completed": self.pending_encounter.precombat_stealth_completed,
                "actors": [],
            }
        attempts = {
            attempt.actor_id: attempt
            for attempt in self.pending_encounter.precombat_stealth_attempts
        }
        actors_by_id = {str(actor.id): actor for actor in encounter.actors}
        return {
            "status": (
                "completed"
                if self.pending_encounter.precombat_stealth_completed
                else "active"
                if self.encounter_setup_flow.completed
                else "waiting_for_setup"
            ),
            "completed": self.pending_encounter.precombat_stealth_completed,
            "instruction": (
                "Każdy bohater może wykonać jedną próbę Stealth. Wynik zostanie porównany "
                "osobno z Passive Perception każdego przeciwnika i przejdzie do pierwszej rundy."
            ),
            "actors": [
                {
                    "actor_id": str(actor.id),
                    "actor_name": actor.name,
                    "modifier": precombat_stealth_modifier(actor),
                    "attempted": str(actor.id) in attempts,
                    "can_attempt": (
                        self.encounter_setup_flow.completed
                        and not self.pending_encounter.precombat_stealth_completed
                        and str(actor.id) not in attempts
                        and not actor.is_defeated()
                    ),
                    "result": (
                        {
                            "natural_roll": attempts[str(actor.id)].natural_roll,
                            "total": attempts[str(actor.id)].total,
                            "hidden_from": [
                                {
                                    "actor_id": observer_id,
                                    "actor_name": actors_by_id[observer_id].name,
                                }
                                for observer_id in attempts[str(actor.id)].hidden_from_actor_ids
                                if observer_id in actors_by_id
                            ],
                            "detected_by": [
                                {
                                    "actor_id": observer_id,
                                    "actor_name": actors_by_id[observer_id].name,
                                }
                                for observer_id in attempts[str(actor.id)].detected_by_actor_ids
                                if observer_id in actors_by_id
                            ],
                        }
                        if str(actor.id) in attempts
                        else None
                    ),
                }
                for actor in encounter.actors
                if actor.faction == Faction.ALLY
            ],
        }

    def required_rolls_payload(self) -> list[dict[str, object]]:
        if (
            self.pending is not None
            and self.pending.stage == PendingStage.HAZARD_SAVE
            and self.pending.hazard is not None
            and self.pending.hazard_actor_id is not None
        ):
            actor = next(
                (
                    candidate
                    for candidate in self.exploration.actors
                    if str(candidate.id) == self.pending.hazard_actor_id
                ),
                None,
            )
            if actor is None:
                return []
            request = self.pending.hazard.saving_throw
            modifiers = saving_throw_roll_modifiers(actor, request.ability)
            request_payload = request.as_payload()
            return [
                {
                    "actor_id": str(actor.id),
                    "actor_name": actor.name,
                    "die_sides": 20,
                    "label": f"d20 {request_payload['ability_label']} save",
                    "modifier_total": sum(modifier.value for modifier in modifiers),
                    "active_modifiers": [
                        _roll_modifier_payload(modifier) for modifier in modifiers
                    ],
                    "ignored_modifiers": [],
                    "instruction": (
                        f"Rzuć fizyczne d20 na {request_payload['ability_label']} "
                        f"przeciw ST {request.dc}."
                    ),
                }
            ]
        if self.pending is not None and self.pending.stage == PendingStage.BREAKAGE and self.pending.breakage_actor_id is not None:
            actor = next((candidate for candidate in self.exploration.actors if str(candidate.id) == self.pending.breakage_actor_id), None)
            return [
                {
                    "actor_id": self.pending.breakage_actor_id,
                    "actor_name": actor.name if actor is not None else self.pending.breakage_actor_id,
                    "die_sides": 100,
                    "label": "k100 trwałości",
                }
            ]
        if self.pending is None or self.pending.stage != PendingStage.ROLL or self.pending.check_plan is None:
            return []
        plan = self.pending.check_plan
        rolls: list[dict[str, object]] = []
        for actor in _actors_for_plan(self.exploration.actors, plan):
            instruction = roll_instruction(_actor_check_request(actor, plan))
            payload: dict[str, object] = {
                "actor_id": str(actor.id),
                "actor_name": actor.name,
                "die_sides": 20,
                "label": "d20",
                "modifier_total": instruction.breakdown.modifier_total,
                "active_modifiers": [
                    _roll_modifier_payload(modifier)
                    for modifier in instruction.breakdown.active_modifiers
                ],
                "ignored_modifiers": [
                    _roll_modifier_payload(modifier)
                    for modifier in instruction.breakdown.ignored_modifiers
                ],
                "instruction": instruction.message,
            }
            if plan.roll_mode != RollMode.NORMAL:
                payload["roll_mode"] = plan.roll_mode.value
                payload["requires_second_roll"] = True
            rolls.append(payload)
        return rolls

    def _add_message(
        self,
        title: str,
        body: str,
        *,
        outcome: str = "",
        grounded_fact_ids: tuple[str, ...] = (),
        hint_level: int = 0,
    ) -> None:
        self.messages.append(UiMessage(title, body))
        self._record("ui_message_added", {"title": title, "body": body})
        if getattr(self, "ui_flow_stage", None) != UiFlowStage.LOCATION_ACTIVE:
            return
        point = self.active_point
        npc_title = point.npc_interaction.name if point is not None and point.npc_interaction is not None else ""
        if title != "Gracze" and title not in CONVERSATION_GM_TITLES and title != npc_title:
            return
        entry = InteractionConversationEntry(
            interaction_id=self._active_conversation_id(),
            role="player" if title == "Gracze" else "gm",
            title=title,
            body=body,
            outcome=outcome,
            grounded_fact_ids=grounded_fact_ids,
            hint_level=hint_level,
        )
        self.conversation_entries.append(entry)
        self._record("ui_conversation_entry_added", entry.as_payload())

    def _record(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self.observer.record(event_type, payload or {})

    def _record_effect_result(self, result, *, source: str, raw_effect: dict[str, object]) -> None:
        self._record(
            "ui_effect_applied",
            {
                "source": source,
                "effect_type": result.effect_type,
                "changed": result.changed,
                "message": result.message,
                "effect": raw_effect,
                "flags": [{"key": key, "value": value} for key, value in self.state.flags.values],
                "inventory_resource_ids": list(self.state.inventory_resource_ids),
                "visible_point_ids": [point.id for point in visible_exploration_points(self.state.points)],
            },
        )

    def _gm_client(self) -> object:
        if self.gm_client is None:
            raise RuntimeError("Brak klienta LLM dla challenge.")
        return self.gm_client

    def _npc_client(self) -> object:
        if self.npc_client is None:
            raise RuntimeError("Brak klienta LLM dla NPC.")
        return self.npc_client


def create_app(session: ExplorationUiSession):
    """Compatibility entry point for the Flask transport adapter."""
    from .routes import create_app as create_routes_app

    return create_routes_app(session)


def _build_encounter_setup_steps(encounter: LoadedEncounter) -> tuple[SetupStep, ...]:
    setup = EncounterSetup(
        name=encounter.scenario_name,
        actors=tuple(
            ActorSetupEntry(actor=actor, role=actor.faction.value, position=actor.position, visibility=SetupVisibility.VISIBLE)
            for actor in encounter.actors
        ),
        environment=(),
    )
    steps = list(build_setup_steps(setup))
    if encounter.player_start_zones:
        steps = [step for step in steps if not (step.kind == SetupStepKind.ACTORS and step.label == "bohaterów")]
        start_positions = tuple(sorted({position for zone in encounter.player_start_zones for position in zone}))
        ally_names = ", ".join(actor.name for actor in encounter.actors if actor.faction == Faction.ALLY)
        steps.insert(
            1,
            SetupStep(
                kind=SetupStepKind.ACTORS,
                label="pola startowe bohaterów",
                positions=start_positions,
                color=(64, 220, 255),
                message=(
                    f"Ustaw bohaterów ({ally_names}) na podświetlonych polach startowych. "
                    "Gra poprosi o kliknięcie pola dla każdego bohatera osobno."
                ),
            ),
        )
    return tuple(_split_large_setup_steps(tuple(steps), max_positions=5))


def _build_exploration_setup_steps(environment: tuple[EnvironmentSetupEntry, ...]) -> tuple[SetupStep, ...]:
    visible = tuple(entry for entry in environment if entry.visibility == SetupVisibility.VISIBLE and entry.positions)
    if not visible:
        return ()
    steps = [
        SetupStep(
            kind=SetupStepKind.ENVIRONMENT,
            label="elementy mapy",
            positions=(),
            color=LedColor.MARKER,
            message="Przed eksploracją rozstawcie jawne elementy mapy: przeszkody, rumowiska i obiekty sceny.",
        )
    ]
    for setup_type in sorted({entry.setup_type for entry in visible}, key=lambda item: item.value):
        entries = tuple(entry for entry in visible if entry.setup_type == setup_type)
        positions = tuple(sorted({position for entry in entries for position in entry.positions}))
        names = ", ".join(entry.name for entry in entries)
        label = _exploration_environment_label(setup_type)
        steps.append(
            SetupStep(
                kind=SetupStepKind.ENVIRONMENT,
                label=label,
                positions=positions,
                color=_exploration_environment_color(setup_type),
                message=f"Ustaw {label}: {names}{_setup_positions_text(positions)}.",
            )
        )
    return tuple(_split_large_setup_steps(tuple(steps), max_positions=8))


def _fallen_gate_setup_step() -> SetupStep:
    positions = (Coordinate(8, 5), Coordinate(9, 5))
    return SetupStep(
        kind=SetupStepKind.ENVIRONMENT,
        label="przewrócona brama",
        positions=positions,
        color=LedColor.BLOCKING_TERRAIN,
        message=f"Ustaw przewróconą bramę: ciężkie skrzydło leży na polach{_setup_positions_text(positions)}.",
    )


def _setup_positions_text(positions: tuple[Coordinate, ...]) -> str:
    if not positions:
        return ""
    return " na polach: " + ", ".join(f"({position.col},{position.row})" for position in positions)


def _exploration_environment_label(setup_type: EnvironmentSetupType) -> str:
    labels = {
        EnvironmentSetupType.OBSTACLE: "przeszkody",
        EnvironmentSetupType.DIFFICULT_TERRAIN: "trudny teren",
        EnvironmentSetupType.BLOCKING_TERRAIN: "blokady",
        EnvironmentSetupType.COVER: "osłony",
        EnvironmentSetupType.INTERACTABLE: "obiekty interaktywne",
        EnvironmentSetupType.NPC: "NPC",
        EnvironmentSetupType.CONTAINER: "obiekty sceny",
        EnvironmentSetupType.MARKER: "markery",
        EnvironmentSetupType.CUSTOM: "elementy otoczenia",
    }
    return labels[setup_type]


def _exploration_environment_color(setup_type: EnvironmentSetupType) -> tuple[int, int, int]:
    if setup_type in {EnvironmentSetupType.OBSTACLE, EnvironmentSetupType.BLOCKING_TERRAIN, EnvironmentSetupType.COVER}:
        return LedColor.BLOCKING_TERRAIN
    if setup_type == EnvironmentSetupType.DIFFICULT_TERRAIN:
        return LedColor.DIFFICULT_TERRAIN
    if setup_type in {EnvironmentSetupType.INTERACTABLE, EnvironmentSetupType.NPC, EnvironmentSetupType.CONTAINER}:
        return LedColor.INTERACTIVE_OBJECT
    return LedColor.MARKER


def _split_large_setup_steps(steps: tuple[SetupStep, ...], *, max_positions: int) -> tuple[SetupStep, ...]:
    result: list[SetupStep] = []
    for step in steps:
        if len(step.positions) <= max_positions:
            result.append(step)
            continue
        chunks = tuple(
            step.positions[index : index + max_positions] for index in range(0, len(step.positions), max_positions)
        )
        for index, chunk in enumerate(chunks, start=1):
            result.append(
                replace(
                    step,
                    positions=chunk,
                    label=f"{step.label} {index}",
                    message=f"{step.message} Część {index}/{len(chunks)}.",
                )
            )
    return tuple(result)


def _setup_step_payload(step: SetupStep | None) -> dict[str, object] | None:
    if step is None:
        return None
    return {
        "kind": step.kind.value,
        "label": step.label,
        "message": step.message,
        "positions": [[position.col, position.row] for position in step.positions],
        "color": _setup_color_name(step) if step.positions else None,
        "has_positions": bool(step.positions),
    }


def _environment_entry_payload(entry: EnvironmentSetupEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "name": entry.name,
        "type": entry.setup_type.value,
        "label": _exploration_environment_label(entry.setup_type),
        "description": entry.description,
        "positions": [[position.col, position.row] for position in entry.positions],
        "color": led_color_name_pl(_exploration_environment_color(entry.setup_type)) if entry.positions else None,
        "blocks_movement": entry.setup_type in {
            EnvironmentSetupType.OBSTACLE,
            EnvironmentSetupType.BLOCKING_TERRAIN,
            EnvironmentSetupType.COVER,
        },
    }


def _setup_color_name(step: SetupStep) -> str:
    if step.kind == SetupStepKind.ACTORS:
        return "turkusowy"
    if step.kind == SetupStepKind.ENEMIES:
        return "czerwony/różowy"
    return led_color_name_pl(step.color)


def _initiative_prompt_payload(
    prompt: InitiativePrompt | None,
    edge: EncounterEdge | None = None,
) -> dict[str, object] | None:
    if prompt is None:
        return None
    return {
        "actor_id": str(prompt.actor.id),
        "actor_name": prompt.actor.name,
        "message": prompt.message,
        "dexterity_modifier": prompt.dexterity_modifier,
        "roll_mode": prompt.request.mode.value,
        "requires_second_roll": prompt.request.mode != RollMode.NORMAL,
        "encounter_edge": (
            {
                "id": edge.id,
                "type": edge.edge_type.value,
                "label": edge.label,
            }
            if edge is not None
            else None
        ),
    }


def _initiative_entry_payload(entry: InitiativeEntry) -> dict[str, object]:
    return {
        "actor_id": str(entry.actor.id),
        "actor_name": entry.actor.name,
        "natural_roll": entry.roll.natural_roll,
        "natural_rolls": list(entry.roll.natural_rolls),
        "roll_mode": entry.roll.mode.value,
        "modifier": entry.roll.breakdown.modifier_total,
        "total": entry.roll.total,
        "dexterity_modifier": entry.dexterity_modifier,
        "stable_order": entry.stable_order,
    }


def _effective_attack_source_for_effects(
    actor: Actor,
    source,
    active_combat_effects: tuple[ActiveCombatEffect, ...],
):
    return attack_source_with_combat_effects(actor, source, active_combat_effects)


def _encounter_with_session_spell_state(
    encounter: LoadedEncounter,
    session_actors: tuple[Actor, ...],
) -> LoadedEncounter:
    session_by_id = {str(actor.id): actor for actor in session_actors}
    actors = tuple(
        replace(
            actor,
            hp=session_by_id[str(actor.id)].hp,
            temp_hp=session_by_id[str(actor.id)].temp_hp,
            spell_slots=session_by_id[str(actor.id)].spell_slots,
            spell_preparation=session_by_id[str(actor.id)].spell_preparation,
            hit_dice=session_by_id[str(actor.id)].hit_dice,
            resource_pools=session_by_id[str(actor.id)].resource_pools,
            death_saves=session_by_id[str(actor.id)].death_saves,
        )
        if str(actor.id) in session_by_id
        else actor
        for actor in encounter.actors
    )
    return replace(encounter, actors=actors)


def _exploration_with_combat_actor_state(
    exploration: LoadedExploration,
    combat_actors: tuple[Actor, ...],
) -> LoadedExploration:
    combat_by_id = {str(actor.id): actor for actor in combat_actors}
    actors = tuple(
        replace(
            actor,
            hp=combat_by_id[str(actor.id)].hp,
            temp_hp=combat_by_id[str(actor.id)].temp_hp,
            spell_slots=combat_by_id[str(actor.id)].spell_slots,
            spell_preparation=combat_by_id[str(actor.id)].spell_preparation,
            hit_dice=combat_by_id[str(actor.id)].hit_dice,
            resource_pools=combat_by_id[str(actor.id)].resource_pools,
            inventory=combat_by_id[str(actor.id)].inventory,
            death_saves=combat_by_id[str(actor.id)].death_saves,
        )
        if str(actor.id) in combat_by_id
        else actor
        for actor in exploration.actors
    )
    return replace(exploration, actors=actors)


def _combat_action_by_id(encounter: LoadedEncounter | None, actor: Actor, action_id: str):
    if encounter is None:
        return None
    return next((action for action in encounter.combat_actions_by_actor.get(actor.id, ()) if action.id == action_id), None)


def _automatic_d20_input(request: D20RollRequest, rng) -> D20RollInput:
    first = rng.randint(1, 20)
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, first)
    return D20RollInput(request, first, rng.randint(1, 20))


def _combat_payload(
    state: CombatState | None,
    encounter: LoadedEncounter | None = None,
    selected_movement_path=None,
    pending_enemy_turn_intent=None,
    pending_enemy_turn_result=None,
    pending_enemy_turn_ack_result=None,
    pending_enemy_saving_throw: PendingEnemySavingThrow | None = None,
    pending_player_attack: PendingPlayerAttack | None = None,
    pending_player_healing: PendingPlayerHealing | None = None,
    pending_area_spell: PendingAreaSpell | None = None,
    pending_combat_context_menu: CombatContextMenu | None = None,
    pending_combat_interaction: PendingCombatInteraction | None = None,
    pending_combat_help: PendingCombatHelp | None = None,
    pending_combat_skill_check: PendingCombatSkillCheck | None = None,
    pending_combat_shove: PendingShove | None = None,
    pending_combat_grapple: PendingGrapple | None = None,
    pending_concentration_action: PendingConcentrationAction | None = None,
    pending_concentration_check: PendingConcentrationCheck | None = None,
    pending_combat_ready: PendingCombatReady | None = None,
    pending_opportunity_movement: PendingOpportunityMovement | None = None,
    pending_enemy_opportunity_attack: PendingEnemyOpportunityAttack | None = None,
    pending_ready_attack: PendingReadyAttack | None = None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
    selected_attack_source_ids: dict[str, str] | None = None,
    selected_healing_source_ids: dict[str, str] | None = None,
    targeting_attack_source_id: str | None = None,
) -> dict[str, object] | None:
    if state is None:
        return None
    actor = combat_current_actor(state)
    selected_attack_source_ids = selected_attack_source_ids or {}
    selected_healing_source_ids = selected_healing_source_ids or {}
    attack_sources = (
        _encounter_attack_sources(
            encounter,
            actor,
            reserved_hands=len(grappled_actor_ids(state.condition_states, str(actor.id))),
        )
        if encounter is not None
        else ()
    )
    two_weapon_sources = (
        eligible_two_weapon_bonus_sources(
            actor,
            state.turn_action.two_weapon_trigger_item_id,
            attack_sources,
        )
        if state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
        else ()
    )
    selected_attack_source_id = selected_attack_source_ids.get(str(actor.id))
    attack_source = next((source for source in attack_sources if source.id == selected_attack_source_id), None) or (
        attack_sources[0] if attack_sources else None
    )
    if state.turn_action.attack_action_active and attack_source is not None:
        attack_source = next(
            (
                source
                for source in attack_sources
                if source.source_type.value == "weapon" and source.area is None
            ),
            attack_source,
        )
    if attack_source is not None and _attack_source_unavailable_reason(actor, attack_source) is not None:
        attack_source = next(
            (source for source in attack_sources if _attack_source_unavailable_reason(actor, source) is None),
            attack_source,
        )
    if attack_source is not None:
        attack_source = _effective_attack_source_for_effects(actor, attack_source, active_combat_effects)
    healing_sources = encounter.healing_sources_by_actor.get(actor.id, ()) if encounter is not None else ()
    selected_healing_source_id = selected_healing_source_ids.get(str(actor.id))
    healing_source = next((source for source in healing_sources if source.id == selected_healing_source_id), None) or (
        healing_sources[0] if healing_sources else None
    )
    targets = ()
    healing_targets = ()
    stabilization_targets = ()
    area_positions = ()
    movement = None
    if (
        encounter is not None
        and attack_source is not None
        and state.status.value == "active"
        and (
            can_use_attack_action(state, actor)
            if attack_source.source_type.value == "weapon" and attack_source.area is None
            else state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        )
        and _source_is_prepared(actor, attack_source)
        and can_consume_spell_resource(actor, attack_source.spell_level)
    ):
        if attack_source.area is not None:
            area_positions = _area_spell_selection_positions(encounter.board, actor, attack_source)
        else:
            targets = start_attack_action(
                encounter.board,
                actor,
                state.actors,
                attack_source,
                state.hidden_states,
            ).legal_targets
    if encounter is not None and two_weapon_sources:
        bonus_targets = tuple(
            target
            for source in two_weapon_sources
            for target in start_attack_action(
                encounter.board,
                actor,
                state.actors,
                two_weapon_bonus_attack_source(actor, source),
                state.hidden_states,
            ).legal_targets
        )
        targets = tuple(
            {target.id: target for target in (*targets, *bonus_targets)}.values()
        )
    if (
        encounter is not None
        and healing_source is not None
        and actor.faction == Faction.ALLY
        and state.status.value == "active"
        and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        and _source_is_prepared(actor, healing_source)
        and can_consume_spell_resource(actor, healing_source.spell_level)
    ):
        healing_targets = legal_healing_targets(encounter.board, actor, state.actors, healing_source)
    if encounter is not None and actor.faction == Faction.ALLY and state.status.value == "active":
        movement = _remaining_movement_range(encounter.board, state, actor)
        if state.turn_action.action_use == ActionUse.ACTION_AVAILABLE:
            stabilization_targets = legal_stabilization_targets(state, actor)
    healers_kit = next((item for item in actor.inventory if item.id == "healers_kit" and item.available), None)
    hiding = (
        hide_eligibility(encounter.board, actor, state.actors, encounter.scene_objects)
        if encounter is not None and actor.faction == Faction.ALLY and not actor.is_defeated()
        else None
    )
    condition_saves = tuple(
        item
        for item in state.condition_states
        if item.actor_id == str(actor.id) and item.save_timing is not None
    )
    return {
        "status": state.status.value,
        "round_number": state.round_number,
        "current_actor": {
            **_combat_actor_payload_with_conditions(
                actor,
                state,
                active_combat_effects,
                turn_action=state.turn_action,
                movement_remaining_feet=movement_remaining(state, actor) if movement is not None else None,
            ),
            "hidden": _hidden_actor_payload(state, actor),
        },
        "actors": [
            {
                **_combat_actor_payload_with_conditions(candidate, state, active_combat_effects),
                "hidden": _hidden_actor_payload(state, candidate),
            }
            for candidate in state.actors
        ],
        "auras": [
            {
                "id": item.aura.id,
                "label": item.aura.label,
                "source_actor_id": str(item.source.id),
                "source_actor_name": item.source.name,
                "radius_feet": item.aura.radius_feet,
                "target": item.aura.target.value,
                "effect_kind": item.aura.effect_kind.value,
                "value": item.aura.value,
                "affected_actor_ids": list(item.affected_actor_ids),
            }
            for item in active_auras(state.actors)
        ],
        "dropped_weapons": [
            {
                "id": dropped.id,
                "source_actor_id": str(dropped.source_actor_id),
                "name": dropped.weapon.name,
                "item_id": dropped.weapon.id,
                "position": [dropped.position.col, dropped.position.row],
                "dropped_round": dropped.dropped_round,
                "item": inventory_item_payload(dropped.weapon),
            }
            for dropped in state.dropped_weapons
        ],
        "winner": state.winner.value if state.winner is not None else None,
        "death_save_required": actor.needs_death_save(),
        "condition_saves": [
            _condition_save_payload(actor, state, item) for item in condition_saves
        ],
        "turn_action": {
            "action_use": state.turn_action.action_use.value,
            "bonus_action_use": state.turn_action.bonus_action_use.value,
            "reaction_available": state.turn_action.reaction_available,
            "movement_used_feet": state.turn_action.movement_used_feet,
            "extra_movement_feet": state.turn_action.extra_movement_feet,
            "object_interaction_available": state.turn_action.object_interaction_available,
            "free_object_interaction_available": state.turn_action.object_interaction_available,
            "two_weapon_trigger_item_id": state.turn_action.two_weapon_trigger_item_id,
            "attack_action_active": state.turn_action.attack_action_active,
            "attacks_used": state.turn_action.attacks_used,
            "attacks_maximum": state.turn_action.attacks_maximum,
            "attacks_remaining": attack_action_remaining(state, actor),
        },
        "two_weapon": {
            "available": bool(two_weapon_sources),
            "trigger_item_id": state.turn_action.two_weapon_trigger_item_id,
            "source_ids": [source.id for source in two_weapon_sources],
            "source_names": [source.name for source in two_weapon_sources],
        },
        "available_attack": _attack_source_payload(attack_source, actor) if attack_source is not None else None,
        "available_attack_sources": [_attack_source_payload(source, actor) for source in attack_sources],
        "selected_attack_source_id": attack_source.id if attack_source is not None else None,
        "targeting": (
            {
                "active": True,
                "source_id": attack_source.id,
                "source_name": attack_source.name,
                "kind": "area" if attack_source.area is not None else "single_target",
                "area_shape": attack_source.area.shape.value if attack_source.area is not None else None,
            }
            if attack_source is not None and targeting_attack_source_id == attack_source.id
            else None
        ),
        "available_healing_sources": [_healing_source_payload(source, actor) for source in healing_sources],
        "selected_healing_source_id": healing_source.id if healing_source is not None else None,
        "legal_healing_targets": [_combat_target_payload(target) for target in healing_targets],
        "stabilization": {
            "dc": 10,
            "medicine_modifier": skill_modifier(actor, "medicine"),
            "healers_kit_uses": healers_kit.quantity if healers_kit is not None else 0,
            "targets": [_combat_actor_payload(target, active_combat_effects) for target in stabilization_targets],
        },
        "stealth": {
            "hide_available": bool(
                hiding is not None
                and hiding.allowed
                and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
            ),
            "hide_blocking_actor_ids": list(hiding.blocking_observer_ids) if hiding is not None else [],
            "stealth_modifier": skill_modifier(actor, "stealth"),
            "passive_perception": passive_skill_score(actor, "perception"),
            "search_available": any(
                str(actor.id) in hidden.hidden_from_actor_ids
                for hidden in state.hidden_states
            ) and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE,
        },
        "combat_actions": [
            _combat_action_payload(action, actor)
            for action in (encounter.combat_actions_by_actor.get(actor.id, ()) if encounter is not None else ())
        ],
        "legal_targets": [_combat_target_payload(target) for target in targets],
        "legal_area_positions": [[position.col, position.row] for position in area_positions],
        "movement": _movement_payload(movement, state, actor) if movement is not None else None,
        "movement_preview": _movement_preview_payload(selected_movement_path, state),
        "enemy_turn_intent": _enemy_turn_intent_payload(pending_enemy_turn_intent, encounter, active_combat_effects),
        "enemy_turn_preview": _enemy_turn_preview_payload(pending_enemy_turn_result, encounter, active_combat_effects),
        "enemy_turn_result": _enemy_turn_result_payload(pending_enemy_turn_ack_result, encounter, active_combat_effects),
        "pending_enemy_saving_throw": _pending_enemy_saving_throw_payload(
            pending_enemy_saving_throw,
            state,
        ),
        "pending_player_attack": _pending_player_attack_payload(pending_player_attack, state, encounter, active_combat_effects),
        "pending_player_healing": _pending_player_healing_payload(pending_player_healing, state, encounter),
        "pending_area_spell": _pending_area_spell_payload(pending_area_spell, state, encounter, active_combat_effects),
        "context_menu": pending_combat_context_menu.as_payload() if pending_combat_context_menu is not None else None,
        "pending_combat_interaction": pending_combat_interaction.as_payload() if pending_combat_interaction is not None else None,
        "pending_combat_help": pending_combat_help.as_payload(state, active_combat_effects) if pending_combat_help is not None else None,
        "pending_combat_skill_check": pending_combat_skill_check.as_payload() if pending_combat_skill_check is not None else None,
        "pending_combat_shove": pending_combat_shove.as_payload() if pending_combat_shove is not None else None,
        "pending_combat_grapple": pending_combat_grapple.as_payload() if pending_combat_grapple is not None else None,
        "pending_concentration_action": (
            _pending_concentration_action_payload(
                pending_concentration_action,
                state,
                active_combat_effects,
                _combat_action_by_id(encounter, actor, pending_concentration_action.action_id),
            )
            if pending_concentration_action is not None
            else None
        ),
        "pending_concentration_check": (
            _pending_concentration_check_payload(
                pending_concentration_check,
                state,
                active_combat_effects,
            )
            if pending_concentration_check is not None
            else None
        ),
        "pending_combat_ready": pending_combat_ready.as_payload(state, active_combat_effects) if pending_combat_ready is not None else None,
        "pending_opportunity_movement": (
            pending_opportunity_movement.as_payload(state, active_combat_effects)
            if pending_opportunity_movement is not None
            else None
        ),
        "pending_enemy_opportunity_attack": _pending_enemy_opportunity_attack_payload(
            pending_enemy_opportunity_attack,
            state,
            encounter,
            active_combat_effects,
        ),
        "pending_ready_attack": _pending_ready_attack_payload(pending_ready_attack, state, encounter, active_combat_effects),
        "active_effects": [effect.as_payload() for effect in active_combat_effects],
    }


def _actor_portrait_url(actor: Actor) -> str | None:
    portrait = actor.portrait.strip().lstrip("/")
    return f"/game-assets/{portrait}" if portrait else None


def _combat_actor_payload(
    actor: Actor,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
    *,
    turn_action: TurnActionState | None = None,
    movement_remaining_feet: int | None = None,
) -> dict[str, object]:
    concentration_effects = [
        effect.as_payload()
        for effect in active_combat_effects
        if effect.source_actor_id == str(actor.id) and effect.kind.startswith("concentration_")
    ]
    actor_effects = [effect.as_payload() for effect in active_combat_effects if effect.actor_id == str(actor.id)]
    return {
        "id": str(actor.id),
        "name": actor.name,
        "portrait_url": _actor_portrait_url(actor),
        "faction": actor.faction.value,
        "size": actor.size.value,
        "size_label": creature_size_label_pl(actor.size),
        "damage_affinities": _damage_affinities_payload(actor),
        "condition_immunities": list(actor.condition_immunities),
        "triggers": [
            {
                "id": trigger.id,
                "label": trigger.label,
                "event_type": trigger.event_type.value,
                "effect_kind": trigger.effect_kind.value,
                "value": trigger.value,
            }
            for trigger in actor.triggers
        ],
        "features": [_feature_grant_payload(feature) for feature in actor.features],
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "temp_hp": actor.temp_hp,
        "ac": effective_armor_class(actor),
        "base_ac": actor.ac,
        "equipment_ac_bonus": effective_armor_class(actor) - actor.ac,
        "position": [actor.position.col, actor.position.row],
        "defeated": actor.is_defeated(),
        "dead": actor.is_dead(),
        "unconscious": actor.is_unconscious(),
        "death_save_required": actor.needs_death_save(),
        "death_saves": {
            "successes": actor.death_saves.successes,
            "failures": actor.death_saves.failures,
            "stable": actor.death_saves.stable,
            "dead": actor.death_saves.dead,
        },
        "spell_slots": [
            {"level": slot.level, "remaining": slot.remaining, "maximum": slot.maximum}
            for slot in actor.spell_slots
        ],
        "spell_save_dc": actor.spell_save_dc,
        "resource_pools": [
            {
                "id": pool.id,
                "label": pool.label,
                "current": pool.current,
                "maximum": pool.maximum,
                "recovery": pool.recovery.value,
                "recharge": (
                    None
                    if pool.recharge is None
                    else {
                        "die_sides": pool.recharge.die_sides,
                        "minimum_roll": pool.recharge.minimum_roll,
                    }
                ),
            }
            for pool in actor.resource_pools
        ],
        "proficiency_bonus": actor.proficiency_bonus,
        "proficiencies": {
            "saving_throws": list(actor.proficiencies.saving_throws),
            "skills": list(actor.proficiencies.skills),
            "expertise": list(actor.proficiencies.expertise),
            "weapons": list(actor.proficiencies.weapons),
            "armor": list(actor.proficiencies.armor),
            "tools": list(actor.proficiencies.tools),
        },
        "inventory": [inventory_item_payload(item) for item in actor.inventory],
        "hands": hand_loadout_payload(actor.inventory),
        "effects": actor_effects,
        "concentration": concentration_effects[0] if concentration_effects else None,
        "status_chips": _combat_actor_status_chips(
            actor,
            actor_effects=actor_effects,
            concentration=concentration_effects[0] if concentration_effects else None,
            turn_action=turn_action,
            movement_remaining_feet=movement_remaining_feet,
        ),
    }


def _combat_actor_payload_with_conditions(
    actor: Actor,
    state: CombatState,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
    *,
    turn_action: TurnActionState | None = None,
    movement_remaining_feet: int | None = None,
) -> dict[str, object]:
    payload = _combat_actor_payload(
        actor,
        active_combat_effects,
        turn_action=turn_action,
        movement_remaining_feet=movement_remaining_feet,
    )
    conditions = tuple(
        condition.condition
        for condition in state.condition_states
        if condition.actor_id == str(actor.id)
    )
    payload["conditions"] = [condition.value for condition in conditions]
    reserved_hands = sum(
        1
        for condition in state.condition_states
        if condition.condition == CombatCondition.GRAPPLED
        and condition.source_actor_id == str(actor.id)
    )
    payload["hands"] = hand_loadout_payload(actor.inventory, reserved_hands=reserved_hands)
    if CombatCondition.PRONE in conditions:
        payload["status_chips"] = [
            *payload["status_chips"],
            _status_chip(
                "Powalony",
                tone="penalty",
                title="Ataki aktora mają utrudnienie; wstawanie kosztuje połowę szybkości.",
            ),
        ]
    for condition in conditions:
        if condition in {CombatCondition.PRONE, CombatCondition.GRAPPLED}:
            continue
        definition = condition_definition(condition)
        condition_state = next(
            item
            for item in state.condition_states
            if item.actor_id == str(actor.id) and item.condition == condition
        )
        details = definition.description
        if condition_state.source_label:
            details = f"{details} Źródło: {condition_state.source_label}."
        if condition_state.save_ability is not None:
            details = (
                f"{details} Save: {condition_state.save_ability} ST {condition_state.save_dc} "
                f"na {condition_state.save_timing.value}."
            )
        payload["status_chips"] = [
            *payload["status_chips"],
            _status_chip(definition.label, tone="penalty", title=details),
        ]
    grapple = next(
        (
            condition
            for condition in state.condition_states
            if condition.actor_id == str(actor.id)
            and condition.condition == CombatCondition.GRAPPLED
        ),
        None,
    )
    if grapple is not None:
        source = next(
            (
                candidate
                for candidate in state.actors
                if str(candidate.id) == grapple.source_actor_id
            ),
            None,
        )
        payload["status_chips"] = [
            *payload["status_chips"],
            _status_chip(
                "Chwytany",
                tone="penalty",
                title=(
                    f"Szybkość 0; chwyt utrzymuje {source.name}."
                    if source is not None
                    else "Szybkość 0 do zakończenia chwytu."
                ),
            ),
        ]
    return payload


def _condition_save_payload(
    actor: Actor,
    state: CombatState,
    condition_state: ConditionState,
) -> dict[str, object]:
    ability = condition_state.save_ability or ""
    request = condition_roll_request(
        D20RollRequest(
            modifiers=(
                *saving_throw_roll_modifiers(actor, ability),
                *saving_throw_aura_modifiers(state.actors, actor),
            )
        ),
        state.condition_states,
        actor,
        saving_throw_ability=ability,
    )
    return {
        "condition": condition_state.condition.value,
        "label": condition_label(condition_state.condition),
        "ability": ability,
        "dc": condition_state.save_dc,
        "timing": condition_state.save_timing.value if condition_state.save_timing is not None else None,
        "source_label": condition_state.source_label,
        "roll_mode": request.mode.value,
        "instruction": roll_instruction(request).message,
    }


def _hidden_actor_payload(state: CombatState, actor: Actor) -> dict[str, object] | None:
    hidden = next(
        (hidden for hidden in state.hidden_states if hidden.actor_id == str(actor.id)),
        None,
    )
    if hidden is None:
        return None
    return {
        "stealth_total": hidden.stealth_total,
        "hidden_from_actor_ids": list(hidden.hidden_from_actor_ids),
    }


def _status_chip(label: str, *, tone: str = "neutral", title: str = "") -> dict[str, str]:
    return {"label": label, "tone": tone, "title": title}


def _combat_actor_status_chips(
    actor: Actor,
    *,
    actor_effects: list[dict[str, object]],
    concentration: dict[str, object] | None,
    turn_action: TurnActionState | None = None,
    movement_remaining_feet: int | None = None,
) -> list[dict[str, str]]:
    chips: list[dict[str, str]] = []
    if actor.death_saves.dead:
        chips.append(_status_chip("Martwy", tone="danger"))
    elif actor.death_saves.stable and actor.hp <= 0:
        chips.append(_status_chip("Stabilny (0 HP)", tone="ready"))
    elif actor.needs_death_save():
        chips.append(_status_chip("Nieprzytomny", tone="danger"))
        chips.append(
            _status_chip(
                f"Death saves {actor.death_saves.successes}✓ / {actor.death_saves.failures}✗",
                tone="danger",
            )
        )
    elif actor.is_defeated():
        chips.append(_status_chip("Pokonany", tone="danger"))
    if turn_action is not None:
        chips.append(
            _status_chip(
                "Darmowa interakcja dostępna" if turn_action.object_interaction_available else "Darmowa interakcja zużyta",
                tone="ready" if turn_action.object_interaction_available else "spent",
            )
        )
        if turn_action.attack_action_active:
            remaining = max(0, turn_action.attacks_maximum - turn_action.attacks_used)
            chips.append(
                _status_chip(
                    f"Ataki {remaining}/{turn_action.attacks_maximum}",
                    tone="ready" if remaining else "spent",
                    title="Pozostałe ataki w bieżącej akcji Attack.",
                )
            )
        chips.append(
            _status_chip(
                "Akcja zużyta" if turn_action.action_use == ActionUse.ACTION_USED else "Akcja dostępna",
                tone="spent" if turn_action.action_use == ActionUse.ACTION_USED else "ready",
            )
        )
        chips.append(
            _status_chip(
                "Bonus zużyty" if turn_action.bonus_action_use == ActionUse.ACTION_USED else "Bonus dostępny",
                tone="spent" if turn_action.bonus_action_use == ActionUse.ACTION_USED else "ready",
            )
        )
        chips.append(
            _status_chip(
                "Reakcja dostępna" if turn_action.reaction_available else "Reakcja zużyta",
                tone="ready" if turn_action.reaction_available else "spent",
            )
        )
        if movement_remaining_feet is not None:
            chips.append(_status_chip(f"Ruch {movement_remaining_feet} ft", tone="movement"))
    if concentration is not None:
        chips.append(
            _status_chip(
                f"Koncentracja: {concentration.get('label', '-')}",
                tone="magic",
                title=str(concentration.get("expires", "")),
            )
        )
    for effect in actor_effects:
        label = str(effect.get("label") or effect.get("kind") or "Efekt")
        value = str(effect.get("value_label") or "")
        chip_label = f"{label}: {value}" if value else label
        chips.append(_status_chip(chip_label, tone=_effect_chip_tone(str(effect.get("kind", ""))), title=str(effect.get("expires", ""))))
    return chips


def _effect_chip_tone(kind: str) -> str:
    if kind in {"grant_ac_bonus_until_move", "dodge_until_next_turn", "disengage_until_turn_end"}:
        return "defense"
    if kind in {"grant_attack_bonus_while_on_object", "help_attack_advantage", "strength_potion", "concentration_attack_bonus"}:
        return "offense"
    if kind in {"grant_next_attack_penalty"}:
        return "penalty"
    if kind in {"ready_attack"}:
        return "ready"
    return "neutral"


def _actor_by_string_id_from_state(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _actor_names_from_actors(
    actors: tuple[Actor, ...],
    actor_ids: tuple[str, ...],
) -> tuple[str, ...]:
    names_by_id = {str(actor.id): actor.name for actor in actors}
    return tuple(names_by_id[actor_id] for actor_id in actor_ids if actor_id in names_by_id)


def _pending_concentration_action_payload(
    pending: PendingConcentrationAction,
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
    action=None,
) -> dict[str, object]:
    return {
        "caster": _combat_actor_payload(
            _actor_by_string_id_from_state(state, pending.caster_id),
            active_effects,
        ),
        "action": _combat_action_payload(action) if action is not None else None,
        "targets": [
            _combat_actor_payload(actor, active_effects)
            for actor in state.actors
            if str(actor.id) in pending.target_ids
        ],
    }


def _pending_concentration_check_payload(
    pending: PendingConcentrationCheck,
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> dict[str, object]:
    actor = _actor_by_string_id_from_state(state, pending.actor_id)
    modifiers = (
        *saving_throw_roll_modifiers(actor, "constitution"),
        *saving_throw_aura_modifiers(state.actors, actor),
    )
    modifier = sum(item.value for item in modifiers)
    effects = tuple(
        effect for effect in active_effects if effect.id in pending.effect_ids
    )
    return {
        "actor": _combat_actor_payload(actor, active_effects),
        "effect_ids": list(pending.effect_ids),
        "effects": [effect.as_payload() for effect in effects],
        "damage": pending.damage,
        "dc": pending.dc,
        "modifier": modifier,
        "modifier_components": [_roll_modifier_payload(item) for item in modifiers],
        "instruction": (
            f"{actor.name} otrzymał {pending.damage} obrażeń. "
            f"Rzuć CON save przeciw ST {pending.dc}."
        ),
    }


def _ready_trigger_label(trigger: str) -> str:
    labels = {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
    }
    return labels.get(trigger, trigger)


def _attack_source_payload(source, actor: Actor | None = None) -> dict[str, object]:
    prepared = _source_is_prepared(actor, source)
    unavailable_reason = _attack_source_unavailable_reason(actor, source)
    attack_kind = effective_attack_kind(source)
    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type.value,
        "attack_kind": attack_kind.value,
        "range_feet": source.range_feet,
        "reach_feet": melee_reach_feet(source) if attack_kind == AttackKind.MELEE else None,
        "damage_hint": source.damage_hint,
        "damage_fixed": source.damage_fixed,
        "damage_die_sides": source.damage_die_sides,
        "damage_modifier": source.damage_modifier,
        "damage_type": source.damage_type,
        "ability": source.ability,
        "spell_level": source.spell_level,
        "casting_kind": source.casting_kind.value,
        "prepared": prepared,
        "available": unavailable_reason is None,
        "unavailable_reason": unavailable_reason,
        "source_item_id": source.source_item_id,
        "resource_label": _source_resource_label(source, actor),
        "resource_pool_id": source.resource_pool_id,
        "resource_cost": source.resource_cost,
        "area": _spell_area_payload(source.area),
        "save_ability": source.save_ability,
        "save_dc": source.save_dc,
        "save_damage_on_success": source.save_damage_on_success,
        "mechanic": action_mechanic_payload(attack_mechanic_from_source(source)),
    }


def _healing_source_payload(
    source: HealingSource,
    actor: Actor | None = None,
) -> dict[str, object]:
    prepared = _source_is_prepared(actor, source)
    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type.value,
        "range_feet": source.range_feet,
        "healing_hint": source.healing_hint,
        "healing_fixed": source.healing_fixed,
        "healing_die_sides": source.healing_die_sides,
        "healing_modifier": source.healing_modifier,
        "spell_level": source.spell_level,
        "casting_kind": source.casting_kind.value,
        "prepared": prepared,
        "available": prepared and (
            actor is None or can_consume_spell_resource(actor, source.spell_level)
        ),
        "unavailable_reason": _spell_source_unavailable_reason(actor, source),
        "resource_label": _source_resource_label(source),
        "mechanic": action_mechanic_payload(healing_mechanic_from_source(source)),
    }


def _source_resource_label(source, actor: Actor | None = None) -> str:
    resource_pool_id = getattr(source, "resource_pool_id", None)
    if resource_pool_id is not None:
        pool = actor_resource_pool(actor, resource_pool_id) if actor is not None else None
        if pool is not None:
            recharge = (
                f", Recharge {pool.recharge.minimum_roll}–{pool.recharge.die_sides}"
                if pool.recharge is not None
                else ""
            )
            return f"{pool.label} {pool.current}/{pool.maximum}{recharge}"
        return f"zasób: {resource_pool_id}"
    casting_kind = getattr(source, "casting_kind", None)
    casting_value = getattr(casting_kind, "value", str(casting_kind or "none"))
    if casting_value == "cantrip":
        return "cantrip"
    spell_level = int(getattr(source, "spell_level", 0) or 0)
    if casting_value == "leveled" or spell_level > 0:
        return f"slot {spell_level}. poziomu"
    return ""


def _source_is_prepared(actor: Actor | None, source) -> bool:
    if actor is None:
        return bool(getattr(source, "prepared", True))
    casting_kind = getattr(source, "casting_kind", None)
    casting_value = getattr(casting_kind, "value", None)
    if casting_value is None:
        casting_value = (
            "leveled" if int(getattr(source, "spell_level", 0) or 0) > 0 else "none"
        )
    return spell_is_prepared(
        actor.spell_preparation,
        str(source.id),
        casting_kind=casting_value,
        legacy_prepared=bool(getattr(source, "prepared", True)),
    )


def _spell_source_unavailable_reason(actor: Actor | None, source) -> str | None:
    if not _source_is_prepared(actor, source):
        return "Czar nie został przygotowany."
    if actor is not None and not can_consume_spell_resource(
        actor,
        int(getattr(source, "spell_level", 0)),
    ):
        return "Brak dostępnych slotów czaru."
    return None


def _attack_source_unavailable_reason(actor: Actor | None, source) -> str | None:
    spell_reason = _spell_source_unavailable_reason(actor, source)
    if spell_reason is not None:
        return spell_reason
    source_item_id = getattr(source, "source_item_id", None)
    if actor is not None and source_item_id is not None:
        item = _inventory_item_for_attack_source(actor, source_item_id)
        if item is None or not item.available or not item.equipped:
            return "Broń leży na polu lub pozostaje niewyposażona w ekwipunku."
    resource_pool_id = getattr(source, "resource_pool_id", None)
    resource_cost = int(getattr(source, "resource_cost", 1))
    if actor is not None and resource_pool_id is not None and not can_spend_actor_resource(
        actor,
        resource_pool_id,
        resource_cost,
    ):
        pool = actor_resource_pool(actor, resource_pool_id)
        label = pool.label if pool is not None else resource_pool_id
        return f"Brak dostępnych użyć: {label}."
    return None


def _inventory_item_for_attack_source(actor: Actor, source_item_id: str):
    matches = tuple(
        item
        for item in actor.inventory
        if item.id == source_item_id or item.source_ref == source_item_id
    )
    return next((item for item in matches if item.equipped and item.available), matches[0] if matches else None)


def _encounter_attack_sources(
    encounter: LoadedEncounter,
    actor: Actor,
    *,
    reserved_hands: int = 0,
) -> tuple:
    sources = list(encounter.attack_source_options_by_actor.get(actor.id, ()))
    known_ids = {source.id for source in sources}
    for item in actor.inventory:
        if item.kind != "weapon":
            continue
        source_keys = tuple(dict.fromkeys(key for key in (item.id, item.source_ref) if key))
        for key in source_keys:
            for source in encounter.weapon_attack_sources_by_item_id.get(key, ()):
                if source.id in known_ids:
                    continue
                sources.append(source)
                known_ids.add(source.id)
    bound_sources = tuple(attack_source_for_actor(source, actor) for source in sources)
    return attack_sources_with_versatile_variants(
        actor,
        bound_sources,
        reserved_hands=reserved_hands,
    )


def _spell_area_payload(area) -> dict[str, object] | None:
    if area is None:
        return None
    return {
        "shape": area.shape.value,
        "radius_feet": area.radius_feet,
        "length_feet": area.length_feet,
        "width_feet": area.width_feet,
        "target_mode": area.target_mode.value,
    }


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _skill_label_pl(skill: str) -> str:
    return {
        "acrobatics": "Akrobatyka",
        "animal_handling": "Opieka nad zwierzętami",
        "arcana": "Wiedza tajemna",
        "athletics": "Atletyka",
        "deception": "Oszustwo",
        "history": "Historia",
        "insight": "Intuicja",
        "intimidation": "Zastraszanie",
        "investigation": "Śledztwo",
        "medicine": "Medycyna",
        "nature": "Natura",
        "perception": "Spostrzegawczość",
        "performance": "Występy",
        "persuasion": "Perswazja",
        "religion": "Religia",
        "sleight_of_hand": "Zwinne dłonie",
        "stealth": "Skradanie się",
        "survival": "Sztuka przetrwania",
    }.get(skill, skill)


def _ability_label_pl(ability: str) -> str:
    return {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
    }.get(ability, ability)


def _attack_context_category(source) -> CombatMenuCategory:
    source_type = getattr(getattr(source, "source_type", None), "value", "")
    if source_type == "spell":
        return CombatMenuCategory.MAGIC
    if source_type == "item":
        return CombatMenuCategory.ITEM
    return CombatMenuCategory.ATTACK


def _combat_action_payload(action, actor: Actor | None = None) -> dict[str, object]:
    quantity = _combat_action_item_quantity(action, actor)
    prepared = _source_is_prepared(actor, action)
    has_spell_resource = actor is None or can_consume_spell_resource(actor, action.spell_level)
    available = prepared and has_spell_resource and (quantity is None or quantity > 0)
    return {
        "id": action.id,
        "name": action.name,
        "action_type": action.action_type,
        "label": action.label,
        "value": action.value,
        "ability": action.ability,
        "duration": action.duration,
        "target_faction": action.target_faction,
        "spell_level": action.spell_level,
        "casting_kind": action.casting_kind.value,
        "prepared": prepared,
        "concentration": action.concentration,
        "source_item_id": action.source_item_id,
        "range_feet": action.range_feet,
        "effect_kind": action.effect_kind,
        "action_cost": action.action_cost.value,
        "action_cost_label": action_economy_cost_label(action.action_cost),
        "source_item_quantity": quantity,
        "available": available,
        "unavailable_reason": _combat_action_unavailable_reason(
            action,
            actor,
            quantity=quantity,
        ),
        "resource_label": _source_resource_label(action),
        "mechanic": action_mechanic_payload(combat_action_mechanic_from_definition(action)),
    }


def _combat_action_item_quantity(action, actor: Actor | None) -> int | None:
    if actor is None or action.source_item_id is None:
        return None
    item = next((candidate for candidate in actor.inventory if candidate.id == action.source_item_id), None)
    return item.quantity if item is not None else 0


def _combat_action_unavailable_reason(
    action,
    actor: Actor | None,
    *,
    quantity: int | None,
) -> str | None:
    spell_reason = _spell_source_unavailable_reason(actor, action)
    if spell_reason is not None:
        return spell_reason
    if quantity is not None and quantity <= 0:
        return "Brak wymaganego przedmiotu."
    return None


def _pending_player_attack_payload(
    pending: PendingPlayerAttack | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if pending is None or encounter is None:
        return None
    attacker = next((actor for actor in state.actors if str(actor.id) == pending.attacker_id), None)
    target = next((actor for actor in state.actors if str(actor.id) == pending.target_id), None)
    if attacker is None or target is None:
        return None
    sources = _encounter_attack_sources(
        encounter,
        attacker,
        reserved_hands=len(grappled_actor_ids(state.condition_states, str(attacker.id))),
    )
    source = next((candidate for candidate in sources if candidate.id == pending.source_id), None) or (
        sources[0] if sources else None
    )
    if source is None:
        return None
    if pending.two_weapon_bonus:
        source = two_weapon_bonus_attack_source(attacker, source)
    source = attack_source_with_target_combat_effects(attacker, target, source, active_combat_effects)
    source = attack_source_with_hidden_advantage(
        source,
        is_hidden_from(state.hidden_states, str(attacker.id), str(target.id)),
    )
    positioning = AttackPositioning(
        cover_level=CoverLevel(pending.cover_level),
        cover_bonus=pending.cover_bonus,
        cover_sources=pending.cover_sources,
        ranged_threat_actor_ids=pending.ranged_threat_actor_ids,
        flanking_ally_ids=pending.flanking_ally_ids,
    )
    source = attack_source_with_positioning(source, positioning)
    source = attack_source_with_prone(source, state.condition_states, attacker, target)
    instruction = roll_instruction(source.attack_roll_request)
    ranged_threats = tuple(
        candidate
        for candidate in state.actors
        if str(candidate.id) in pending.ranged_threat_actor_ids
    )
    return {
        "stage": pending.stage,
        "two_weapon_bonus": pending.two_weapon_bonus,
        "attacker": _combat_actor_payload(attacker, active_combat_effects),
        "target": _combat_actor_payload(target, active_combat_effects),
        "source": _attack_source_payload(source),
        "attack_instruction": instruction.message,
        "attack_modifier": instruction.breakdown.modifier_total,
        "attack_mode": instruction.mode.value,
        "active_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.ignored_modifiers],
        "damage_instruction": _damage_roll_instruction(source),
        "natural_roll": pending.natural_roll,
        "natural_rolls": list(pending.natural_rolls),
        "total": pending.total,
        "target_ac": effective_armor_class(target) + pending.cover_bonus,
        "positioning": {
            "cover_level": pending.cover_level,
            "cover_bonus": pending.cover_bonus,
            "cover_sources": list(pending.cover_sources),
            "ranged_in_melee": bool(pending.ranged_threat_actor_ids),
            "ranged_threat_actor_ids": list(pending.ranged_threat_actor_ids),
            "ranged_threats": [
                {
                    "id": str(candidate.id),
                    "name": candidate.name,
                    "position": [candidate.position.col, candidate.position.row],
                }
                for candidate in ranged_threats
            ],
            "flanking": bool(pending.flanking_ally_ids),
            "flanking_ally_ids": list(pending.flanking_ally_ids),
        },
        "hit": pending.hit,
        "critical": pending.critical,
        "saving_throws": [save.as_payload() for save in pending.saving_throws],
        "spell_save_dc": source.save_dc or attacker.spell_save_dc,
    }


def _pending_player_healing_payload(
    pending: PendingPlayerHealing | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
) -> dict[str, object] | None:
    if pending is None or encounter is None:
        return None
    healer = next((actor for actor in state.actors if str(actor.id) == pending.healer_id), None)
    target = next((actor for actor in state.actors if str(actor.id) == pending.target_id), None)
    if healer is None or target is None:
        return None
    source = next(
        (candidate for candidate in encounter.healing_sources_by_actor.get(healer.id, ()) if candidate.id == pending.source_id),
        None,
    )
    if source is None:
        return None
    return {
        "stage": pending.stage,
        "healer": _combat_actor_payload(healer),
        "target": _combat_actor_payload(target),
        "source": _healing_source_payload(source),
        "healing_instruction": f"Rzuć {source.healing_hint} i wpisz sumę leczenia.",
    }


def _pending_area_spell_payload(
    pending: PendingAreaSpell | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if pending is None or encounter is None:
        return None
    caster = next((actor for actor in state.actors if str(actor.id) == pending.caster_id), None)
    if caster is None:
        return None
    source = next(
        (candidate for candidate in encounter.attack_source_options_by_actor.get(caster.id, ()) if candidate.id == pending.source_id),
        None,
    )
    if source is None:
        return None
    return {
        "stage": pending.stage,
        "caster": _combat_actor_payload(caster, active_combat_effects),
        "source": _attack_source_payload(source),
        "origin": [pending.origin.col, pending.origin.row],
        "anchor": [pending.anchor.col, pending.anchor.row],
        "area_positions": [[position.col, position.row] for position in pending.area_positions],
        "targets": [
            _combat_actor_payload(actor, active_combat_effects)
            for actor in state.actors
            if str(actor.id) in pending.target_ids
        ],
        "saving_throws": [save.as_payload() for save in pending.saving_throws],
        "target_cover": [
            {
                "actor_id": actor_id,
                "cover_level": positioning.cover_level.value,
                "cover_bonus": positioning.cover_bonus,
                "cover_sources": list(positioning.cover_sources),
            }
            for actor_id, positioning in pending.target_positioning
        ],
        "spell_save_dc": source.save_dc or caster.spell_save_dc,
        "damage_instruction": _damage_roll_instruction(source),
    }


def _pending_enemy_opportunity_attack_payload(
    pending: PendingEnemyOpportunityAttack | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if pending is None or encounter is None:
        return None
    attacker = next((actor for actor in state.actors if str(actor.id) == pending.attacker_id), None)
    target = next((actor for actor in state.actors if str(actor.id) == pending.target_id), None)
    if attacker is None or target is None:
        return None
    source = encounter.attack_sources_by_actor.get(attacker.id)
    if source is None:
        return None
    source = attack_source_with_target_combat_effects(attacker, target, source, active_combat_effects)
    instruction = roll_instruction(source.attack_roll_request)
    threats = [
        _combat_actor_payload(actor, active_combat_effects)
        for actor in state.actors
        if str(actor.id) in pending.threat_actor_ids
    ]
    return {
        "stage": pending.stage,
        "attacker": _combat_actor_payload(attacker, active_combat_effects),
        "target": _combat_actor_payload(target, active_combat_effects),
        "threats": threats,
        "current_index": pending.current_index,
        "source": _attack_source_payload(source),
        "attack_instruction": instruction.message,
        "attack_modifier": instruction.breakdown.modifier_total,
        "attack_mode": instruction.mode.value,
        "active_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.ignored_modifiers],
        "damage_instruction": _damage_roll_instruction(source),
        "natural_roll": pending.natural_roll,
        "natural_rolls": list(pending.natural_rolls),
        "total": pending.total,
        "target_ac": target.ac,
        "hit": pending.hit,
        "critical": pending.critical,
    }


def _pending_ready_attack_payload(
    pending: PendingReadyAttack | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if pending is None or encounter is None:
        return None
    attacker = next((actor for actor in state.actors if str(actor.id) == pending.readied_actor_id), None)
    target = next((actor for actor in state.actors if str(actor.id) == pending.target_id), None)
    if attacker is None or target is None:
        return None
    source = encounter.attack_sources_by_actor.get(attacker.id)
    if source is None:
        return None
    source = attack_source_with_target_combat_effects(attacker, target, source, active_combat_effects)
    instruction = roll_instruction(source.attack_roll_request)
    return {
        "stage": pending.stage,
        "trigger": pending.trigger,
        "trigger_label": _ready_trigger_label(pending.trigger),
        "attacker": _combat_actor_payload(attacker, active_combat_effects),
        "target": _combat_actor_payload(target, active_combat_effects),
        "source": _attack_source_payload(source),
        "attack_instruction": instruction.message,
        "attack_modifier": instruction.breakdown.modifier_total,
        "attack_mode": instruction.mode.value,
        "active_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.ignored_modifiers],
        "damage_instruction": _damage_roll_instruction(source),
        "natural_roll": pending.natural_roll,
        "natural_rolls": list(pending.natural_rolls),
        "total": pending.total,
        "target_ac": target.ac,
        "hit": pending.hit,
        "critical": pending.critical,
    }


def _roll_modifier_payload(modifier: RollModifier) -> dict[str, object]:
    return {
        "label": modifier.label,
        "value": modifier.value,
        "type": modifier.modifier_type.value,
    }


def _damage_roll_instruction(source) -> str:
    if source.damage_fixed is not None:
        return f"Obrażenia stałe: {source.damage_fixed} {source.damage_type}. Wpisz {source.damage_fixed}."
    return f"Rzuć obrażenia: {source.damage_hint}. Wpisz sumę po modyfikatorach."


def _combat_target_payload(target) -> dict[str, object]:
    return {
        "id": target.id,
        "name": target.name,
        "ac": target.ac,
        "hp": target.hp,
        "max_hp": target.max_hp,
        "temp_hp": target.temp_hp,
        "defeated": target.defeated,
        "position": [target.position.col, target.position.row],
    }


def _remaining_movement_range(board, state: CombatState, actor: Actor) -> MovementRangeResult:
    remaining = movement_remaining(state, actor)
    movement_actor = replace(actor, speed_feet=remaining)
    result = movement_range(board, movement_actor, state.actors)
    return movement_range_with_condition_cost(
        result,
        state.condition_states,
        str(actor.id),
        movement_budget_feet=remaining,
    )


def _legal_combat_targets(
    encounter: LoadedEncounter,
    state: CombatState,
    actor: Actor,
    source=None,
    *,
    require_action: bool = True,
):
    source = source or encounter.attack_sources_by_actor.get(actor.id)
    if source is None:
        return ()
    if require_action:
        if source.source_type.value == "weapon" and source.area is None:
            if not can_use_attack_action(state, actor):
                return ()
        elif state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            return ()
    return start_attack_action(
        encounter.board,
        actor,
        state.actors,
        source,
        state.hidden_states,
    ).legal_targets


def _combat_target_at_position(
    encounter: LoadedEncounter,
    state: CombatState,
    actor: Actor,
    position: Coordinate,
    source=None,
    *,
    require_action: bool = True,
):
    for target in _legal_combat_targets(
        encounter,
        state,
        actor,
        source,
        require_action=require_action,
    ):
        if target.position == position:
            return target
    return None


def _area_spell_selection_positions(board, actor: Actor, source) -> tuple[Coordinate, ...]:
    if source is None or source.area is None:
        return ()
    if source.area.shape == SpellAreaShape.RADIUS:
        return legal_area_centers(board, actor.position, source.range_feet)
    return direction_anchor_positions(board, actor.position)


def _combat_choice_led_feedback(
    movement: MovementRangeResult,
    attack_targets,
    healing_targets=(),
    selected_path=None,
    board=None,
    interaction_positions: tuple[Coordinate, ...] = (),
    area_spell_positions: tuple[Coordinate, ...] = (),
    dragged_destination: Coordinate | None = None,
) -> LedFeedback:
    frames = list(movement_led_feedback(movement).frames)
    if board is not None:
        difficult_tiles = tuple(
            sorted(tile for tile in movement.reachable_tiles if tile != movement.origin and board.terrain_at(tile).is_difficult)
        )
        if difficult_tiles:
            frames.append(LedFrame(difficult_tiles, LedColor.DIFFICULT_TERRAIN, LedRole.DIFFICULT_TERRAIN))
    if selected_path is not None and selected_path.valid and selected_path.path:
        path_without_origin = tuple(tile for tile in selected_path.path if tile != selected_path.origin)
        if path_without_origin:
            frames.append(LedFrame(path_without_origin, LedColor.PLAYER_MOVEMENT_PATH, LedRole.SELECTED_PATH))
        frames.append(LedFrame((selected_path.destination,), LedColor.MOVEMENT_DESTINATION, LedRole.DESTINATION))
    target_positions = tuple(sorted(target.position for target in attack_targets))
    if target_positions:
        frames.append(LedFrame(target_positions, LedColor.ENEMY, LedRole.ENEMY))
    healing_positions = tuple(sorted(target.position for target in healing_targets))
    if healing_positions:
        frames.append(LedFrame(healing_positions, LedColor.ALLY, LedRole.ALLY))
    if interaction_positions:
        frames.append(LedFrame(tuple(sorted(interaction_positions)), LedColor.INTERACTIVE_OBJECT, LedRole.INTERACTIVE_OBJECT))
    if area_spell_positions:
        frames.append(LedFrame(tuple(sorted(area_spell_positions)), LedColor.MARKER, LedRole.DESTINATION))
    if dragged_destination is not None:
        frames.append(
            LedFrame(
                (dragged_destination,),
                LedColor.MENU_PINK,
                LedRole.ENEMY,
            )
        )
    return LedFeedback(tuple(frames))


def _pending_area_spell_led_feedback(pending: PendingAreaSpell, state: CombatState | None = None) -> LedFeedback:
    frames: list[LedFrame] = []
    if pending.area_positions:
        frames.append(LedFrame(pending.area_positions, LedColor.MARKER, LedRole.SELECTED_PATH))
    if pending.anchor is not None:
        frames.append(LedFrame((pending.anchor,), LedColor.MOVEMENT_DESTINATION, LedRole.DESTINATION))
    if state is not None:
        target_positions = tuple(
            actor.position
            for actor in state.actors
            if str(actor.id) in pending.target_ids and not actor.is_defeated()
        )
        if target_positions:
            frames.append(LedFrame(target_positions, LedColor.ENEMY, LedRole.ENEMY))
    return LedFeedback(tuple(frames))


def _pending_enemy_turn_target_positions(result) -> tuple[Coordinate, ...]:
    if result is None:
        return ()
    if result.movement_path is not None and result.movement_path.valid:
        return (result.movement_path.destination,)
    if result.target is not None:
        return (result.target.position,)
    return ()


def _pending_enemy_turn_led_feedback(result) -> LedFeedback:
    if result is None:
        return LedFeedback()
    if result.movement_path is not None and result.movement_path.valid:
        path_positions = tuple(position for position in result.movement_path.path if position != result.movement_path.origin)
        frames: list[LedFrame] = []
        if path_positions:
            frames.append(LedFrame(path_positions, LedColor.ENEMY_MOVEMENT_PATH, LedRole.SELECTED_PATH))
        frames.append(LedFrame((result.movement_path.destination,), LedColor.ENEMY_MOVEMENT_DESTINATION, LedRole.DESTINATION))
        return LedFeedback(tuple(frames))
    if result.target is not None:
        return LedFeedback((LedFrame((result.target.position,), LedColor.ENEMY, LedRole.ENEMY),))
    return LedFeedback()


def _enemy_turn_intent_led_feedback(intent) -> LedFeedback:
    if intent is None:
        return LedFeedback()
    frames: list[LedFrame] = []
    if intent.movement_path is not None and intent.movement_path.valid:
        path_positions = tuple(position for position in intent.movement_path.path if position != intent.movement_path.origin)
        if path_positions:
            frames.append(LedFrame(path_positions, LedColor.ENEMY_MOVEMENT_PATH, LedRole.SELECTED_PATH))
        frames.append(LedFrame((intent.movement_path.destination,), LedColor.ENEMY_MOVEMENT_DESTINATION, LedRole.DESTINATION))
    if intent.target is not None:
        frames.append(LedFrame((intent.target.position,), LedColor.ENEMY, LedRole.ENEMY))
    return LedFeedback(tuple(frames))


def _enemy_turn_intent_payload(
    intent,
    encounter: LoadedEncounter | None = None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if intent is None:
        return None
    payload: dict[str, object] = {
        "enemy_id": str(intent.enemy.id),
        "enemy_name": intent.enemy.name,
        "message": _enemy_turn_intent_message(intent),
    }
    source = encounter.attack_sources_by_actor.get(intent.enemy.id) if encounter is not None else None
    if source is not None and intent.target is not None:
        target_actor = next((actor for actor in intent.state.actors if str(actor.id) == intent.target.id), None)
        source = (
            attack_source_with_target_combat_effects(intent.enemy, target_actor, source, active_combat_effects)
            if target_actor is not None
            else _effective_attack_source_for_effects(intent.enemy, source, active_combat_effects)
        )
        if target_actor is not None and encounter is not None:
            positioning = evaluate_attack_positioning(
                encounter.board,
                intent.enemy,
                target_actor,
                source,
                intent.state.actors,
                encounter.scene_objects,
            )
            source = attack_source_with_positioning(source, positioning)
            source = attack_source_with_prone(
                source,
                intent.state.condition_states,
                intent.enemy,
                target_actor,
            )
            payload["positioning"] = _attack_positioning_payload(positioning)
    elif source is not None:
        source = _effective_attack_source_for_effects(intent.enemy, source, active_combat_effects)
    if intent.target is not None:
        payload["target_id"] = intent.target.id
        payload["target_name"] = intent.target.name
        payload["target_position"] = [intent.target.position.col, intent.target.position.row]
    if source is not None:
        instruction = roll_instruction(source.attack_roll_request)
        payload["source"] = _attack_source_payload(source)
        payload["attack_instruction"] = instruction.message
        payload["attack_modifier"] = instruction.breakdown.modifier_total
        payload["damage_instruction"] = _damage_roll_instruction(source)
    if intent.movement_path is not None and intent.movement_path.valid:
        payload["kind"] = "movement"
        payload["destination"] = [intent.movement_path.destination.col, intent.movement_path.destination.row]
        payload["path"] = [[position.col, position.row] for position in intent.movement_path.path]
        payload["cost_feet"] = intent.movement_path.cost_feet
    elif intent.target is not None:
        payload["kind"] = "attack"
    else:
        payload["kind"] = "wait"
    return payload


def _enemy_turn_preview_payload(
    result,
    encounter: LoadedEncounter | None = None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    if result is None:
        return None
    payload: dict[str, object] = {"enemy_id": str(result.enemy.id), "enemy_name": result.enemy.name}
    source = result.source or (
        encounter.attack_sources_by_actor.get(result.enemy.id) if encounter is not None else None
    )
    if source is not None and result.target is not None:
        target_actor = next((actor for actor in result.state.actors if str(actor.id) == result.target.id), None)
        source = (
            attack_source_with_target_combat_effects(result.enemy, target_actor, source, active_combat_effects)
            if target_actor is not None
            else _effective_attack_source_for_effects(result.enemy, source, active_combat_effects)
        )
        positioning = getattr(result, "positioning", AttackPositioning())
        source = attack_source_with_positioning(source, positioning)
        if target_actor is not None:
            source = attack_source_with_prone(
                source,
                result.state.condition_states,
                result.enemy,
                target_actor,
            )
        payload["positioning"] = _attack_positioning_payload(positioning)
    elif source is not None:
        source = _effective_attack_source_for_effects(result.enemy, source, active_combat_effects)
    if result.target is not None:
        payload["target_id"] = result.target.id
        payload["target_name"] = result.target.name
        payload["target_position"] = [result.target.position.col, result.target.position.row]
    if source is not None:
        instruction = roll_instruction(source.attack_roll_request)
        payload["source"] = _attack_source_payload(source)
        payload["attack_instruction"] = instruction.message
        payload["attack_modifier"] = instruction.breakdown.modifier_total
        payload["damage_instruction"] = _damage_roll_instruction(source)
    if result.attack_roll is not None:
        payload["natural_roll"] = result.attack_roll.natural_roll
        payload["natural_rolls"] = list(result.attack_roll.natural_rolls)
        payload["total"] = result.attack_roll.total
    if result.attack_resolution is not None:
        payload["hit"] = result.attack_resolution.hit
        payload["critical"] = result.attack_resolution.critical
        payload["target_ac"] = result.attack_resolution.attack_roll_result.target_ac
    if result.saving_throw_request is not None:
        payload["saving_throw_request"] = result.saving_throw_request.as_payload()
        payload["base_damage"] = result.base_damage
    if result.saving_throw_result is not None:
        payload["saving_throw_result"] = result.saving_throw_result.as_payload()
    if result.damage is not None:
        payload["damage"] = result.damage.total_applied
    if getattr(result, "applied_damage", None) is not None:
        payload["damage_result"] = _applied_damage_payload(result.applied_damage)
    if result.movement_path is not None and result.movement_path.valid:
        payload["kind"] = "movement"
        payload["destination"] = [result.movement_path.destination.col, result.movement_path.destination.row]
        payload["path"] = [[position.col, position.row] for position in result.movement_path.path]
        payload["cost_feet"] = result.movement_path.cost_feet
    elif result.target is not None:
        payload["kind"] = "attack"
    return payload


def _pending_enemy_saving_throw_payload(
    pending: PendingEnemySavingThrow | None,
    state: CombatState,
) -> dict[str, object] | None:
    if pending is None:
        return None
    target = next(
        (actor for actor in state.actors if str(actor.id) == pending.target_id),
        None,
    )
    if target is None:
        return None
    roll_request = condition_roll_request(
        D20RollRequest(
            modifiers=(
                *saving_throw_roll_modifiers(target, pending.request.ability),
                *saving_throw_aura_modifiers(state.actors, target),
            )
        ),
        state.condition_states,
        target,
        saving_throw_ability=pending.request.ability,
    )
    modifiers = roll_request.modifiers
    request_payload = pending.request.as_payload()
    return {
        "target": _combat_actor_payload(target),
        "source_id": pending.source_id,
        "request": request_payload,
        "modifier": sum(modifier.value for modifier in modifiers),
        "modifier_components": [_roll_modifier_payload(modifier) for modifier in modifiers],
        "roll_mode": roll_request.mode.value,
        "instruction": (
            f"{target.name}: {roll_instruction(roll_request).message} "
            f"Rzut na {request_payload['ability_label']} przeciw ST {pending.request.dc}."
        ),
    }


def _attack_positioning_payload(positioning: AttackPositioning) -> dict[str, object]:
    return {
        "cover_level": positioning.cover_level.value,
        "cover_bonus": positioning.cover_bonus,
        "cover_sources": list(positioning.cover_sources),
        "ranged_in_melee": bool(positioning.ranged_threat_actor_ids),
        "ranged_threat_actor_ids": list(positioning.ranged_threat_actor_ids),
        "flanking": bool(positioning.flanking_ally_ids),
        "flanking_ally_ids": list(positioning.flanking_ally_ids),
    }


def _enemy_turn_result_payload(
    result,
    encounter: LoadedEncounter | None = None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
) -> dict[str, object] | None:
    payload = _enemy_turn_preview_payload(result, encounter, active_combat_effects)
    if payload is None:
        return None
    payload["message"] = _enemy_turn_message(result)
    payload["summary"] = _enemy_roll_summary(result)
    return payload


def _enemy_roll_summary(result) -> str:
    if result.saving_throw_result is not None:
        save = result.saving_throw_result
        outcome = "sukces" if save.success else "porażka"
        parts = [
            f"Rzut obronny d20: {save.natural_roll}",
            f"modyfikator: {save.modifier:+d}",
            f"wynik końcowy: {save.total} przeciw ST {save.dc}: {outcome}",
        ]
        if result.damage is not None:
            parts.append(f"obrażenia: {result.damage.total_applied}")
        return ". ".join(parts) + "."
    if result.attack_roll is None or result.target is None:
        return ""
    parts = [
        f"Rzut d20: {_d20_roll_result_text(result.attack_roll)}",
        f"wynik końcowy: {result.attack_roll.total}",
    ]
    if result.attack_resolution is not None:
        parts.append("trafienie" if result.attack_resolution.hit else "pudło")
        if result.attack_resolution.critical:
            parts.append("krytyk")
    if result.damage is not None:
        parts.append(f"obrażenia: {result.damage.total_applied}")
    if getattr(result, "applied_damage", None) is not None:
        parts.append(f"HP celu: {result.applied_damage.hp_before} -> {result.applied_damage.hp_after}")
        if result.applied_damage.defeated_by_damage:
            parts.append("cel pokonany")
    return ". ".join(parts) + "."


def _d20_roll_result_text(roll) -> str:
    natural_rolls = getattr(roll, "natural_rolls", ()) or ()
    if len(natural_rolls) > 1:
        return f"{' / '.join(str(value) for value in natural_rolls)} -> {roll.natural_roll}"
    return str(roll.natural_roll)


def _enemy_turn_intent_message(intent) -> str:
    return intent.message


def _enemy_turn_message(result) -> str:
    summary = _enemy_roll_summary(result)
    if not summary:
        return result.message
    return f"{result.message} {summary}"


def _movement_preview_payload(path, state: CombatState) -> dict[str, object] | None:
    if path is None or not path.valid:
        return None
    payload = {
        "destination": [path.destination.col, path.destination.row],
        "cost_feet": path.cost_feet,
        "path": [[position.col, position.row] for position in path.path],
    }
    dragged = _dragged_movement_preview(state, path)
    if dragged is not None:
        payload["dragged_actor"] = dragged
    return payload


def _movement_payload(result, state: CombatState, actor: Actor) -> dict[str, object]:
    remaining = movement_remaining(state, actor)
    effective_speed = effective_movement_speed(actor, state.condition_states)
    destinations = tuple(sorted(tile for tile in result.reachable_tiles if tile != result.origin))
    return {
        "remaining_feet": remaining,
        "base_speed_feet": actor.speed_feet,
        "effective_speed_feet": effective_speed,
        "speed_reduction": "grappling" if effective_speed < actor.speed_feet and effective_speed > 0 else None,
        "extra_movement_feet": state.turn_action.extra_movement_feet,
        "destinations": [
            {
                "col": tile.col,
                "row": tile.row,
                "cost_feet": result.costs_by_tile[tile],
                "path": [[position.col, position.row] for position in result.paths_by_tile.get(tile, ())],
            }
            for tile in destinations
        ],
    }


def _dragged_destination(
    state: CombatState,
    path,
) -> Coordinate | None:
    preview = _dragged_movement_preview(state, path)
    if preview is None:
        return None
    col, row = preview["destination"]
    return Coordinate(col, row)


def _dragged_movement_preview(
    state: CombatState,
    path,
) -> dict[str, object] | None:
    if path is None or not path.valid or len(path.path) < 2:
        return None
    actor = combat_current_actor(state)
    dragged_ids = tuple(
        condition.actor_id
        for condition in state.condition_states
        if condition.condition == CombatCondition.GRAPPLED
        and condition.source_actor_id == str(actor.id)
    )
    if not dragged_ids:
        return None
    dragged = next(
        (candidate for candidate in state.actors if str(candidate.id) == dragged_ids[0]),
        None,
    )
    if dragged is None:
        return None
    destination = path.path[-2]
    return {
        "id": str(dragged.id),
        "name": dragged.name,
        "destination": [destination.col, destination.row],
    }


def _damage_application_message(result) -> str:
    return applied_damage_message(result)


def _applied_damage_payload(result) -> dict[str, object] | None:
    return applied_damage_payload(result)


def _default_encounter_victory_outcome(name: str) -> EncounterOutcome:
    return EncounterOutcome(
        title="Encounter rozstrzygnięty",
        body=f"Drużyna wygrywa encounter: {name}.",
        next_instruction="Zakończ wynik, żeby wrócić do eksploracji.",
    )


def _encounter_opening_outcome_label(outcome: EncounterOpeningOutcome) -> str:
    return {
        EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES: "Przeciwnicy mają utrudnienie do inicjatywy",
        EncounterOpeningOutcome.NO_SURPRISE: "Nikt nie jest zaskoczony",
        EncounterOpeningOutcome.ENEMIES_SURPRISE_PARTY: "Drużyna ma utrudnienie do inicjatywy",
    }[outcome]


def _default_encounter_defeat_outcome(name: str) -> EncounterOutcome:
    return EncounterOutcome(
        title="Drużyna pokonana",
        body=f"Drużyna przegrywa encounter: {name}. Zapisz konsekwencje ręcznie albo zresetuj scenę.",
        next_instruction="Zakończ wynik, żeby wrócić do eksploracji.",
    )


def _actor_stable_order(encounter: LoadedEncounter, actor: Actor) -> int:
    for index, candidate in enumerate(encounter.actors):
        if candidate.id == actor.id:
            return index
    return len(encounter.actors)


def _coordinate_from_scan(raw: object) -> Coordinate:
    if not isinstance(raw, (tuple, list)) or len(raw) != 2:
        raise ValueError(f"Niepoprawna odpowiedź scan_board: {raw!r}.")
    return Coordinate(int(raw[0]), int(raw[1]))


def _load_board_defaults() -> dict[str, str]:
    from board.settings import connection_backend, hardware_scan_config, load_board_config, simulator_url, wled_config

    config = load_board_config()
    return {
        "backend": connection_backend(config) or "hardware",
        "board_url": simulator_url(config) or "http://127.0.0.1:5000",
        "serial_port": str((hardware_scan_config(config) or {}).get("serial_port") or "").strip(),
        "wled_url": str((wled_config(config) or {}).get("base_url") or "").strip(),
    }


def _ui_session_id() -> str:
    return f"exploration_ui_{uuid.uuid4().hex[:10]}"


def _analyze(client: object, request_data: object) -> GmDeclarationAnalysis:
    analyze = getattr(client, "analyze", None)
    if callable(analyze):
        return analyze(request_data)
    return GmDeclarationAnalysis(
        analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
        player_message="",
        normalized_intent=getattr(request_data, "player_action", ""),
        reason="Klient testowy bez analyzer; uznaję deklarację za wiarygodną.",
        confidence=1.0,
    )


def _validate_goal_participants(
    goal: InteractionGoal,
    challenge: ExplorationChallenge,
    actors: tuple[Actor, ...],
    requested_actor_ids: tuple[str, ...],
    *,
    check_participants: CheckParticipants,
    resolution_option_id: str | None = None,
) -> tuple[str, ...]:
    ally_ids = tuple(str(actor.id) for actor in actors if actor.faction == Faction.ALLY)
    requested = tuple(dict.fromkeys(actor_id.strip() for actor_id in requested_actor_ids if actor_id.strip()))
    if len(requested) != len(requested_actor_ids):
        raise ValueError("Każdą postać można wskazać tylko raz.")
    unknown = tuple(actor_id for actor_id in requested if actor_id not in ally_ids)
    if unknown:
        raise ValueError("Wybrano postać, która nie należy do drużyny.")

    if check_participants == CheckParticipants.WHOLE_PARTY:
        if requested:
            raise ValueError("W teście grupowym rzuca automatycznie cała drużyna.")
        selected = ally_ids
    elif check_participants == CheckParticipants.SINGLE_ACTOR:
        if len(requested) != 1:
            raise ValueError("Ten test wykonuje dokładnie jedna wybrana postać.")
        selected = requested
    elif check_participants == CheckParticipants.LEAD_WITH_HELP:
        if len(requested) not in {1, 2}:
            raise ValueError(
                "Wybierz głównego wykonawcę oraz opcjonalnie jednego pomocnika."
            )
        selected = requested
    else:
        raise ValueError("Kafelek ma nieobsługiwany model uczestników.")

    profile = next(
        (
            option
            for option in challenge.options
            if option.id == (resolution_option_id or goal.resolution_option_id)
        ),
        None,
    )
    if profile is not None and check_participants != CheckParticipants.WHOLE_PARTY:
        eligible_ids = {
            str(actor.id)
            for actor in actors_matching_challenge_option(actors, profile)
            if actor.faction == Faction.ALLY
        }
        incapable = tuple(actor_id for actor_id in selected if actor_id not in eligible_ids)
        if incapable:
            names = ", ".join(
                actor.name for actor in actors if str(actor.id) in set(incapable)
            )
            raise ValueError(
                f"Te postacie nie spełniają wymagań tego sposobu: {names}."
            )
    return selected


def _resolve_goal_check_participants(
    goal: InteractionGoal,
    requested: str | None,
) -> CheckParticipants:
    if goal.participant_mode == InteractionParticipantMode.MUST:
        if requested is not None and CheckParticipants(requested) != goal.check_participants:
            raise ValueError("Ten kafelek wymusza inny typ testu.")
        return goal.check_participants
    if requested is None:
        raise ValueError("Najpierw wybierz typ testu dla tego kafelka.")
    selected = CheckParticipants(requested)
    if selected not in goal.participant_options:
        raise ValueError("Wybrany typ testu nie jest dozwolony dla tego kafelka.")
    return selected


def _challenge_check_plan(
    option: ExplorationChallengeOption,
    lead_actor_id: str,
    actors: tuple[Actor, ...],
    *,
    helper_actor_id: str | None = None,
    selected_actor_ids: tuple[str, ...] = (),
    resource: ExplorationResource | None = None,
) -> ExplorationCheckPlan:
    resource_modifier = resource.as_roll_modifier() if resource is not None else None
    participants = option.check_participants or CheckParticipants.SINGLE_ACTOR
    rolling_actor_ids = (
        {str(actor.id) for actor in actors}
        if participants in {
            CheckParticipants.WHOLE_PARTY,
            CheckParticipants.SELECTED_ACTORS,
        }
        else {lead_actor_id}
    )
    roll_modifiers_by_actor_id = tuple(
        (
            str(actor.id),
            (
                *option_roll_modifiers_for_actor(actor, option),
                *((resource_modifier,) if resource_modifier is not None else ()),
            ),
        )
        for actor in actors
        if str(actor.id) in rolling_actor_ids
        if option_roll_modifiers_for_actor(actor, option) or resource_modifier is not None
    )
    option_bonus_payloads = tuple(
        {
            **bonus.as_payload(),
            "actor_id": str(actor.id),
            "actor_name": actor.name,
        }
        for actor in actors
        for bonus in active_option_bonuses_for_actor(actor, option)
    )
    return ExplorationCheckPlan(
        participants=participants,
        aggregation=option.check_aggregation or CheckAggregation.LEAD_RESULT,
        consequence_targets=option.consequence_targets or (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.SCENE),
        ability=option.ability_check.ability,
        skill=option.ability_check.skill,
        tool=option.ability_check.tool,
        tool_label=_tool_label_for_check(option.ability_check.tool, option, actors),
        dc=option.ability_check.dc,
        lead_actor_id=lead_actor_id,
        helper_actor_id=helper_actor_id,
        selected_actor_ids=selected_actor_ids,
        reason_for_players=option.description,
        roll_mode=_combined_roll_mode(
            option.roll_mode,
            (
                *((RollMode.ADVANTAGE,) if helper_actor_id is not None else ()),
                *((RollMode.ADVANTAGE,) if resource is not None and resource.advantage else ()),
            ),
        ),
        situational_modifiers=option.situational_modifiers,
        improvised_tool=option.improvised_tool,
        roll_modifiers_by_actor_id=roll_modifiers_by_actor_id,
        option_bonus_payloads=option_bonus_payloads,
        resource_payload=_resource_payload(resource) if resource is not None else None,
        mechanic_payload=mechanic_payload_for_option(option),
    )


def _npc_check_plan(proposal: NpcInteractionProposal, lead_actor_id: str) -> ExplorationCheckPlan:
    participants = proposal.check_participants or (CheckParticipants.WHOLE_PARTY if proposal.action_type == "search" else CheckParticipants.SINGLE_ACTOR)
    aggregation = proposal.check_aggregation or (CheckAggregation.HIGHEST if participants == CheckParticipants.WHOLE_PARTY else CheckAggregation.LEAD_RESULT)
    consequence_targets = proposal.consequence_targets or (ConsequenceTarget.NPC,)
    return ExplorationCheckPlan(
        participants=participants,
        aggregation=aggregation,
        consequence_targets=tuple(consequence_targets),
        ability=proposal.ability or "wisdom",
        skill=proposal.skill,
        dc=proposal.dc or 10,
        lead_actor_id=lead_actor_id,
        reason_for_players=proposal.player_narration,
    )


def _observation_check_plan(
    observation: ExplorationObservation,
    lead_actor_id: str,
) -> ExplorationCheckPlan:
    return ExplorationCheckPlan(
        participants=observation.participants,
        aggregation=observation.aggregation,
        consequence_targets=(ConsequenceTarget.SCENE,),
        ability=observation.ability,
        skill=observation.skill,
        dc=observation.dc,
        lead_actor_id=lead_actor_id,
        reason_for_players=observation.description,
        roll_mode=observation.roll_mode,
        mechanic_payload={
            "id": "graded_observation",
            "label": "Stopniowane rozpoznanie",
            "participants": observation.participants.value,
            "aggregation": observation.aggregation.value,
        },
    )


def _trap_check_plan(
    trap: ExplorationTrap,
    action: ExplorationTrapAction,
    lead_actor_id: str,
) -> ExplorationCheckPlan:
    check = (
        trap.disarm_check
        if action == ExplorationTrapAction.DISARM
        else trap.bypass_check
    )
    if check is None:
        raise ValueError("Ta akcja na pułapce nie wymaga testu.")
    action_label = "Rozbrojenie pułapki" if action == ExplorationTrapAction.DISARM else "Ominięcie pułapki"
    return ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ability=check.ability,
        skill=check.skill,
        tool=check.tool,
        tool_label="Narzędzia złodziejskie" if check.tool == "thieves_tools" else (check.tool or ""),
        dc=check.dc,
        lead_actor_id=lead_actor_id,
        reason_for_players=f"{action_label}: {trap.name}.",
        roll_modifiers_by_actor_id=((lead_actor_id, check.modifiers),),
        mechanic_payload={
            "id": "exploration_trap_action",
            "label": action_label,
            "trap_id": trap.id,
            "action": action.value,
        },
    )


def _check_inputs_from_payload(
    actors: tuple[Actor, ...],
    plan: ExplorationCheckPlan,
    raw_rolls: dict[str, object],
) -> tuple[PartyCheckInput, ...]:
    result: list[PartyCheckInput] = []
    for actor in _actors_for_plan(actors, plan):
        actor_id = str(actor.id)
        if actor_id not in raw_rolls:
            raise ValueError(f"Brakuje wyniku rzutu dla: {actor.name}.")
        natural_roll, natural_roll_2 = _manual_rolls_from_payload(raw_rolls[actor_id], plan.roll_mode)
        request = _actor_check_request(actor, plan)
        result.append(PartyCheckInput(actor, natural_roll, request, natural_roll_2))
    return tuple(result)


def _actor_check_request(actor: Actor, plan: ExplorationCheckPlan) -> D20RollRequest:
    return D20RollRequest(
        mode=plan.roll_mode,
        modifiers=(
            *ability_check_roll_modifiers(
                actor,
                plan.ability,
                skill=plan.skill,
                tool=plan.tool,
            ),
            *_plan_roll_modifiers(actor, plan),
        ),
    )


def _manual_rolls_from_payload(raw_roll: object, roll_mode: RollMode) -> tuple[int, int | None]:
    if isinstance(raw_roll, dict):
        natural_roll = int(raw_roll.get("natural_roll") or raw_roll.get("roll") or 0)
        raw_second = raw_roll.get("natural_roll_2") or raw_roll.get("roll_2")
        natural_roll_2 = int(raw_second) if raw_second not in (None, "") else None
    else:
        natural_roll = int(raw_roll)
        natural_roll_2 = None
    if roll_mode != RollMode.NORMAL and natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return natural_roll, natural_roll_2


def _actors_for_plan(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> tuple[Actor, ...]:
    if plan.participants == CheckParticipants.WHOLE_PARTY:
        return actors
    if plan.participants == CheckParticipants.SELECTED_ACTORS:
        selected = tuple(actor for actor in actors if str(actor.id) in set(plan.selected_actor_ids))
        return selected or actors
    lead = next((actor for actor in actors if str(actor.id) == plan.lead_actor_id), actors[0])
    return (lead,)


def _plan_roll_modifiers(actor: Actor, plan: ExplorationCheckPlan) -> tuple[RollModifier, ...]:
    situational = tuple(
        modifier
        for modifier in (item.as_roll_modifier() for item in plan.situational_modifiers)
        if modifier is not None
    )
    improvised = (plan.improvised_tool.as_roll_modifier(),) if plan.improvised_tool is not None else ()
    base_modifiers = (*situational, *improvised)
    actor_id = str(actor.id)
    for candidate_actor_id, modifiers in plan.roll_modifiers_by_actor_id:
        if candidate_actor_id == actor_id:
            return (*base_modifiers, *modifiers)
    return base_modifiers


def _situational_modifiers_from_payload(
    raw_modifiers: object,
    *,
    fallback: tuple[ExplorationSituationalModifier, ...] = (),
) -> tuple[ExplorationSituationalModifier, ...]:
    if raw_modifiers is None:
        return fallback
    if not isinstance(raw_modifiers, list):
        raise ValueError("Modyfikatory sytuacyjne muszą być listą.")
    if len(raw_modifiers) > EXPLORATION_DECISION_MAX_SITUATIONAL_MODIFIERS:
        raise ValueError(f"Maksymalnie {EXPLORATION_DECISION_MAX_SITUATIONAL_MODIFIERS} modyfikatory sytuacyjne.")
    result: list[ExplorationSituationalModifier] = []
    for raw in raw_modifiers:
        if not isinstance(raw, dict):
            raise ValueError("Modyfikator sytuacyjny musi być obiektem.")
        label = str(raw.get("label") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        modifier = int(raw.get("modifier") or 0)
        roll_mode = RollMode(str(raw.get("roll_mode") or RollMode.NORMAL.value))
        if not label and not reason and modifier == 0 and roll_mode == RollMode.NORMAL:
            continue
        source = ExplorationSituationalModifierSource(str(raw.get("source") or ExplorationSituationalModifierSource.GM.value))
        result.append(
            ExplorationSituationalModifier(
                label=label,
                modifier=modifier,
                source=source,
                reason=reason,
                roll_mode=roll_mode,
            )
        )
    return tuple(result)


def _improvised_tool_from_payload(
    raw_tool: object,
    *,
    fallback: ImprovisedToolUse | None = None,
) -> ImprovisedToolUse | None:
    if raw_tool is None:
        return fallback
    if not isinstance(raw_tool, dict):
        raise ValueError("Improwizowane narzędzie musi być obiektem.")
    label = str(raw_tool.get("label") or "").strip()
    source_detail = str(raw_tool.get("source_detail") or "").strip()
    reason = str(raw_tool.get("reason") or "").strip()
    effect_modifier = int(raw_tool.get("effect_modifier") or 0)
    risk = str(raw_tool.get("risk") or "").strip()
    if not label and not source_detail and not reason and effect_modifier == 0 and not risk:
        return None
    source = ExplorationSituationalModifierSource(str(raw_tool.get("source") or ExplorationSituationalModifierSource.GM.value))
    return ImprovisedToolUse(
        label=label,
        source=source,
        source_detail=source_detail,
        source_id=fallback.source_id if fallback is not None else None,
        effect_modifier=effect_modifier,
        risk=risk,
        reason=reason,
    )


def _combined_roll_mode(base_mode: RollMode, modifier_modes: tuple[RollMode, ...]) -> RollMode:
    modes = {mode for mode in (base_mode, *modifier_modes) if mode != RollMode.NORMAL}
    if RollMode.ADVANTAGE in modes and RollMode.DISADVANTAGE in modes:
        return RollMode.NORMAL
    if RollMode.DISADVANTAGE in modes:
        return RollMode.DISADVANTAGE
    if RollMode.ADVANTAGE in modes:
        return RollMode.ADVANTAGE
    return RollMode.NORMAL


def _player_facing_gm_validation_message(reason: str) -> str:
    if "temporary_item_template_id" in reason:
        return (
            "Nie udało mi się jednoznacznie dopasować przedmiotu do tego, co można zbudować w tej scenie. "
            "Powiedz, jaki przedmiot chcecie zrobić i z których dostępnych materiałów."
        )
    if "source_materials" in reason or "materiałów spoza sceny" in reason:
        return (
            "Do zbudowania tego przedmiotu potrzebuję wskazania materiałów dostępnych w tej scenie. "
            "Możecie wcześniej zapytać MG, co leży w pobliżu."
        )
    component_marker = "Konstrukcja wymaga komponentów ["
    if component_marker in reason:
        raw_properties = reason.split(component_marker, 1)[1].split("]", 1)[0]
        property_labels = {
            "binding": "wiążącego",
            "hard": "twardego",
            "heavy": "ciężkiego",
            "load_bearing": "zdolnego utrzymać ciężar",
            "long": "długiego",
            "metallic": "metalowego",
            "prying": "nadającego się do podważania",
            "rigid": "sztywnego",
            "short": "krótkiego",
        }
        missing = [
            property_labels.get(property_id.strip(), property_id.strip().replace("_", " "))
            for property_id in raw_properties.split(",")
            if property_id.strip()
        ]
        missing_text = " i ".join(missing)
        return (
            "Wybrane elementy nie wystarczą do zbudowania tej konstrukcji. "
            f"Brakuje komponentu {missing_text}. Możecie wskazać dodatkowy element albo użyć "
            "tego materiału bezpośrednio, bez budowania osobnej konstrukcji."
        )
    return f"Nie mogę jeszcze rozstrzygnąć tej deklaracji: {reason}"


def _pending_explanation(pending: PendingInteraction) -> str:
    if pending.attempt_plan is not None:
        plan = pending.attempt_plan
        if not plan.available:
            return plan.blocked_reason
        attempt_number = plan.attempts_used + 1
        return (
            f"To próba {attempt_number}/{plan.max_attempts} dla tego podejścia. "
            "Licznik zwiększy się dopiero po zaakceptowaniu i rozstrzygnięciu rzutu."
        )
    if pending.fixture_action_plan is not None:
        plan = pending.fixture_action_plan
        return (
            f"Operacja {plan.policy.operation.value} na {plan.fixture.name} jest dozwolona "
            f"dla stanu {plan.current_condition}. Po sukcesie stan zmieni się na "
            f"{plan.policy.result_condition}; parametry testu pochodzą z contentu fixture'a."
        )
    if pending.collection_plan is not None:
        plan = pending.collection_plan
        return (
            f"Silnik sprawdził, że {plan.source.label} jest dostępny i przenośny. "
            f"Po akceptacji {plan.quantity} szt. trafi do {plan.destination.value}, "
            "a ta sama liczba przestanie być dostępna w scenie."
        )
    if pending.crafting_plan is not None:
        return _crafting_confirmation_text(pending.crafting_plan)
    notes = getattr(pending.proposal, "gm_notes", "")
    if notes:
        return str(notes)
    return "Ta propozycja jest interpretacją deklaracji graczy zwalidowaną przez deterministyczny silnik."


def _crafting_confirmation_text(plan: CraftingPlan) -> str:
    component_cost = ", ".join(
        f"{component.source_id} x{component.quantity} ({'zużyte' if component.disposition.value == 'consumed' else 'zarezerwowane'})"
        for component in plan.component_uses
    )
    return (
        f"{plan.draft.label}: {plan.draft.description} "
        f"Koszt: {component_cost}; czas {plan.purpose.time_cost_minutes} min. "
        f"Efekt przy użyciu: {plan.purpose.modifier:+d}, {plan.purpose.uses} użycia. "
        "Sama budowa nie wymaga testu."
    )


def _check_plan_text(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> str:
    rolling_actors = _actors_for_plan(actors, plan)
    names = ", ".join(actor.name for actor in rolling_actors)
    ability_label = _ability_label_pl(plan.ability)
    check_label = (
        f"{_skill_label_pl(plan.skill)} ({ability_label})"
        if plan.skill
        else f"{plan.tool_label or plan.tool} ({ability_label})"
        if plan.tool
        else ability_label
    )
    if plan.participants == CheckParticipants.LEAD_WITH_HELP:
        lead = next(
            (actor for actor in actors if str(actor.id) == plan.lead_actor_id),
            rolling_actors[0],
        )
        helper = next(
            (actor for actor in actors if str(actor.id) == plan.helper_actor_id),
            None,
        )
        helper_text = (
            f" {helper.name} pomaga i nie wykonuje osobnego rzutu."
            if helper is not None
            else ""
        )
        roll_mode_text = {
            RollMode.ADVANTAGE: "z przewagą",
            RollMode.DISADVANTAGE: "z utrudnieniem",
            RollMode.NORMAL: "bez przewagi ani utrudnienia",
        }[plan.roll_mode]
        return (
            f"{lead.name} wykonuje test {check_label} przeciw ST {plan.dc} "
            f"{roll_mode_text}.{helper_text}"
        )
    return (
        f"Test {check_label} przeciw ST {plan.dc}. Rzucają: {names}. "
        f"Tryb rzutu: {plan.roll_mode.value}."
    )


def _zone_payload(zone: ExplorationZone, asset_root: Path | None = None, state: ExplorationState | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": zone.id,
        "name": zone.name,
        "description": zone.description,
        "summary": zone.llm_context.summary,
        "color": led_color_name_pl(zone.color),
        "available": zone_is_ui_available(state, zone) if state is not None else True,
    }
    if state is not None and not zone_is_ui_available(state, zone):
        payload["locked_reason"] = _locked_zone_message(zone)
    if zone.image:
        image_path = zone.image.lstrip("/")
        payload["image"] = zone.image
        payload["image_url"] = f"/scenario-assets/{image_path}"
    return payload


def _single_zone_feedback(zone: ExplorationZone | None) -> LedFeedback:
    if zone is None:
        return LedFeedback()
    return LedFeedback((LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION),))


def _zone_markers_feedback(zones: tuple[ExplorationZone, ...]) -> LedFeedback:
    return LedFeedback(tuple(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION) for zone in zones))


def _npc_state_for_point(
    state: ExplorationState,
    point: ExplorationPoint,
) -> NpcRuntimeState | None:
    if point.npc_interaction is None:
        return None
    return npc_runtime_state_for(state, point.npc_interaction.id)


def _point_payload(
    point: ExplorationPoint | None,
    npc_state: NpcRuntimeState | None = None,
    flags: SceneFlags | None = None,
) -> dict[str, object] | None:
    if point is None:
        return None
    payload: dict[str, object] = {
        "id": point.id,
        "name": point.name,
        "zone_id": point.zone_id,
        "description": point.description,
        "positions": [[position.col, position.row] for position in point.positions],
        "color": led_color_name_pl(point.color),
        "has_npc": point.npc_interaction is not None,
    }
    if point.npc_interaction is not None:
        payload["npc"] = {
            "name": point.npc_interaction.name,
            "public_description": point.npc_interaction.public_description,
            "current_state": point.npc_interaction.current_state,
            "dialogue_intro": point.npc_interaction.dialogue_intro,
            "runtime_state": npc_state.as_payload() if npc_state is not None else None,
            "goals": [
                goal.as_payload()
                for goal in (
                    available_interaction_goals(point.npc_interaction.goals, flags)
                    if flags is not None
                    else point.npc_interaction.goals
                )
            ],
        }
    return payload


def _challenge_payload(
    state: ExplorationState,
    challenge: ExplorationChallenge | None,
    actors: tuple[Actor, ...] = (),
    flows: tuple[ExplorationFlowGraph, ...] = (),
    flow_service: ExplorationInteractionFlowService | None = None,
) -> dict[str, object] | None:
    if challenge is None:
        return None
    challenge_state = challenge_state_for(state, challenge.id)
    interaction_flow = flow_service or ExplorationInteractionFlowService()
    available_goals = interaction_flow.available_goals(
        challenge=challenge,
        flows=flows,
        flags=state.flags,
    )
    return {
        "id": challenge.id,
        "name": challenge.name,
        "progress_required": challenge.progress_required,
        "current_progress": challenge_state.current_progress,
        "noise": challenge_state.noise,
        "uses_progress": not bool(
            challenge.completion_all_flags or challenge.completion_any_flags
        ),
        "completed": challenge_state.completed,
        "complications": list(challenge_state.complications),
        "goals": [
            _challenge_goal_payload(
                goal,
                challenge,
                actors,
                resolution_option_id=(
                    route.resolution_option_id if route is not None else None
                ),
            )
            for goal in available_goals
            for route in (
                interaction_flow.route_for_goal(
                    challenge=challenge,
                    flows=flows,
                    goal_id=goal.id,
                    flags=state.flags,
                ),
            )
        ],
    }


def _challenge_goal_payload(
    goal: InteractionGoal,
    challenge: ExplorationChallenge,
    actors: tuple[Actor, ...],
    *,
    resolution_option_id: str | None = None,
) -> dict[str, object]:
    payload = goal.as_payload()
    profile = next(
        (
            option
            for option in challenge.options
            if option.id == (resolution_option_id or goal.resolution_option_id)
        ),
        None,
    )
    eligible = (
        actors
        if profile is None or goal.check_participants == CheckParticipants.WHOLE_PARTY
        else actors_matching_challenge_option(actors, profile)
    )
    payload["eligible_actor_ids"] = [
        str(actor.id) for actor in eligible if actor.faction == Faction.ALLY
    ]
    return payload


def _exploration_actor_payload(
    actor: Actor,
    condition_states: tuple[ConditionState, ...] = (),
) -> dict[str, object]:
    conditions = [
        _exploration_condition_payload(condition)
        for condition in condition_states
        if condition.actor_id == str(actor.id)
    ]
    return {
        "id": str(actor.id),
        "name": actor.name,
        "portrait_url": _actor_portrait_url(actor),
        "ac": actor.ac,
        "size": actor.size.value,
        "size_label": creature_size_label_pl(actor.size),
        "damage_affinities": _damage_affinities_payload(actor),
        "condition_immunities": list(actor.condition_immunities),
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "temp_hp": actor.temp_hp,
        "speed_feet": actor.speed_feet,
        "spell_save_dc": actor.spell_save_dc,
        "proficiency_bonus": actor.proficiency_bonus,
        "proficiencies": {
            "saving_throws": list(actor.proficiencies.saving_throws),
            "skills": list(actor.proficiencies.skills),
            "expertise": list(actor.proficiencies.expertise),
            "weapons": list(actor.proficiencies.weapons),
            "armor": list(actor.proficiencies.armor),
            "tools": list(actor.proficiencies.tools),
        },
        "conditions": conditions,
        "ability_scores": {
            "strength": actor.ability_scores.strength,
            "dexterity": actor.ability_scores.dexterity,
            "constitution": actor.ability_scores.constitution,
            "intelligence": actor.ability_scores.intelligence,
            "wisdom": actor.ability_scores.wisdom,
            "charisma": actor.ability_scores.charisma,
        },
        "inventory": [inventory_item_payload(item) for item in actor.inventory],
        "hands": hand_loadout_payload(actor.inventory),
        "spell_ids": list(actor.spell_ids),
        "spell_slots": [
            {"level": slot.level, "remaining": slot.remaining, "maximum": slot.maximum}
            for slot in actor.spell_slots
        ],
        "hit_dice": [
            {"die_sides": pool.die_sides, "remaining": pool.remaining, "maximum": pool.maximum}
            for pool in actor.hit_dice
        ],
        "resource_pools": [
            {
                "id": pool.id,
                "label": pool.label,
                "current": pool.current,
                "maximum": pool.maximum,
                "recovery": pool.recovery.value,
                "recharge": (
                    None
                    if pool.recharge is None
                    else {
                        "die_sides": pool.recharge.die_sides,
                        "minimum_roll": pool.recharge.minimum_roll,
                    }
                ),
            }
            for pool in actor.resource_pools
        ],
        "features": [_feature_grant_payload(feature) for feature in actor.features],
    }


def _feature_grant_payload(feature: FeatureGrant) -> dict[str, object]:
    return {
        "id": feature.feature_id,
        "label": feature.label,
        "description": feature.description,
        "source_kind": feature.source_kind.value,
        "source_ref": feature.source_ref,
        "resource_ids": list(feature.resource_ids),
        "action_ids": list(feature.action_ids),
        "trigger_ids": list(feature.trigger_ids),
        "aura_ids": list(feature.aura_ids),
    }


def _exploration_condition_payload(condition: ConditionState) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": condition.condition.value,
        "label": condition_label(condition.condition),
        "recoverable": condition.condition == CombatCondition.PRONE,
    }
    if (
        condition.source_label
        or condition.duration != EffectDuration.PERMANENT
        or condition.save_ability is not None
    ):
        payload.update(
            {
                "description": condition_definition(condition.condition).description,
                "source_label": condition.source_label,
                "duration": condition.duration.value,
                "save_ability": condition.save_ability,
                "save_dc": condition.save_dc,
                "save_timing": (
                    condition.save_timing.value if condition.save_timing is not None else None
                ),
            }
        )
    return payload


def _damage_affinities_payload(actor: Actor) -> dict[str, object]:
    def values(items) -> list[dict[str, str]]:
        return [
            {"id": damage_type.value, "label": damage_type_label_pl(damage_type)}
            for damage_type in items
        ]

    return {
        "resistances": values(actor.damage_affinities.resistances),
        "immunities": values(actor.damage_affinities.immunities),
        "vulnerabilities": values(actor.damage_affinities.vulnerabilities),
    }


def _short_rest_policy_payload(
    policy: ShortRestPolicy,
    completed_count: int,
) -> dict[str, object]:
    return {
        "id": policy.id,
        "safety": policy.safety.value,
        "duration_minutes": policy.duration_minutes,
        "duration_label": _duration_minutes_label(policy.duration_minutes),
        "risk_summary": policy.risk_summary,
        "max_completions": policy.max_completions,
        "completed_count": completed_count,
        "has_completion_effects": bool(policy.completion_effects),
    }


def _short_rest_actor_payload(actor: Actor, *, completed: bool) -> dict[str, object]:
    return {
        "actor_id": str(actor.id),
        "actor_name": actor.name,
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "constitution_modifier": ability_modifier(actor.ability_scores.constitution),
        "can_spend_hit_die": completed and actor.hp < actor.max_hp and any(
            pool.remaining > 0 for pool in actor.hit_dice
        ),
        "hit_dice": [
            {"die_sides": pool.die_sides, "remaining": pool.remaining, "maximum": pool.maximum}
            for pool in actor.hit_dice
        ],
        "short_rest_resources": [
            {
                "id": pool.id,
                "label": pool.label,
                "current": pool.current,
                "maximum": pool.maximum,
            }
            for pool in actor.resource_pools
            if pool.recovery.value == "short_rest"
        ],
    }


def _duration_minutes_label(minutes: int) -> str:
    hours, remainder = divmod(max(0, minutes), 60)
    if hours and remainder:
        return f"{hours} godz. {remainder} min"
    if hours:
        return f"{hours} godz."
    return f"{remainder} min"


def _scene_status_payload(state: ExplorationState) -> list[dict[str, str]]:
    flags = dict(state.flags.values)
    status: list[dict[str, str]] = []
    gate_state = "otwarta" if flags.get("gate_passed") is True else "zamknięta"
    status.append({"label": "Brama", "value": gate_state})
    closed_gate = next((challenge for challenge in state.challenges if challenge.id == "closed_gate"), None)
    if closed_gate is not None:
        closed_gate_state = challenge_state_for(state, closed_gate.id)
        status.append(
            {
                "label": "Zamek",
                "value": "otwarty" if flags.get("gate_lock_cleared") is True else "zamknięty",
            }
        )
        status.append(
            {
                "label": "Rygiel",
                "value": "zdjęty" if flags.get("gate_bolt_cleared") is True else "założony",
            }
        )
        status.append(
            {
                "label": "Czujność goblinów",
                "value": _gate_alert_label(closed_gate_state.noise),
            }
        )
        if closed_gate_state.complications:
            status.append({"label": "Komplikacje", "value": ", ".join(closed_gate_state.complications)})
    courtyard = next((challenge for challenge in state.challenges if challenge.id == "courtyard_search"), None)
    if courtyard is not None:
        courtyard_state = challenge_state_for(state, courtyard.id)
        courtyard_value = "przeszukany" if courtyard_state.completed else f"w toku {courtyard_state.current_progress}/{courtyard.progress_required}"
        status.append({"label": "Dziedziniec", "value": courtyard_value})
    visible_point_ids = {point.id for point in visible_exploration_points(state.points)}
    if "wounded_scout" in visible_point_ids:
        if flags.get("scout_stabilized") is True:
            scout_state = "opatrzony"
        elif flags.get("scout_calmed") is True:
            scout_state = "uspokojony"
        elif flags.get("scout_panicked") is True:
            scout_state = "spanikowany"
        else:
            scout_state = "odkryty, ranny"
        status.append({"label": "Ranny zwiadowca", "value": scout_state})
    if flags.get("tower_hint_learned") is True:
        status.append({"label": "Trop", "value": "coś ciężkiego przeciągnięto ku wieży"})
    if flags.get("beast_hint_learned") is True:
        status.append({"label": "Trop bestii", "value": "rany wskazują na wielkie pazury i dziób"})
    if flags.get("commander_curse_suspected") is True:
        status.append({"label": "Podejrzenie", "value": "bestia może mieć związek z dawnym komendantem"})
    if "hidden_cache" in visible_point_ids:
        status.append({"label": "Ukryta skrytka", "value": "odkryta"})
    return status


def _noise_label(noise: int) -> str:
    if noise <= 0:
        return "brak"
    if noise <= 2:
        return f"niski ({noise})"
    if noise <= 4:
        return f"średni ({noise})"
    return f"wysoki ({noise})"


def _gate_alert_label(level: int) -> str:
    return {
        0: "cisza po drugiej stronie",
        1: "coś wzbudziło podejrzenia",
        2: "gobliny są zaalarmowane",
    }.get(level, "gobliny przygotowały zasadzkę")


def _gate_state_narration(state: ExplorationState, challenge_id: str) -> str:
    flags = dict(state.flags.values)
    lock = "otwarty" if flags.get("gate_lock_cleared") is True else "zamknięty"
    bolt = "zdjęty" if flags.get("gate_bolt_cleared") is True else "założony"
    alert = challenge_state_for(state, challenge_id).noise
    alert_text = {
        0: "Za bramą nadal panuje cisza.",
        1: "Po drugiej stronie słychać krótki, podejrzliwy szmer.",
        2: "Gobliny są już zaalarmowane i zajmują pozycje.",
    }.get(alert, "Po drugiej stronie zapada cisza kogoś, kto właśnie kończy zastawiać pułapkę.")
    return f"Stan bramy — zamek: {lock}; rygiel: {bolt}. {alert_text}"


def _resource_payload(resource: ExplorationResource) -> dict[str, object]:
    return {
        "id": resource.id,
        "label": resource.label,
        "bonus_tags": list(resource.bonus_tags),
        "modifier": resource.modifier,
        "advantage": resource.advantage,
        "mitigates_complications": list(resource.mitigates_complications),
        "mitigates_noise": resource.mitigates_noise,
        "consume_on_use": resource.consume_on_use,
    }


def _tool_label_for_check(
    tool_id: str | None,
    option: ExplorationChallengeOption,
    actors: tuple[Actor, ...],
) -> str:
    if tool_id is None:
        return ""
    bonus = next((item for item in option.bonuses if item.source_id == tool_id), None)
    if bonus is not None and bonus.label:
        return bonus.label
    for actor in actors:
        item = next(
            (
                candidate
                for candidate in actor.inventory
                if candidate.id == tool_id or candidate.source_ref == tool_id
            ),
            None,
        )
        if item is not None:
            return item.name
    return tool_id.replace("_", " ")


def _temporary_item_payload(item: TemporaryItem) -> dict[str, object]:
    return {
        **_resource_payload(item.as_resource()),
        "temporary": True,
        "uses_remaining": item.uses_remaining,
        "description": item.description,
        "risk": item.risk,
        "source_materials": list(item.source_materials),
        "purpose_id": item.purpose_id,
        "time_cost_minutes": item.time_cost_minutes,
        "scope": item.scope.value,
        "dismantled": item.dismantled,
        "component_uses": [
            {
                "source_id": component.source_id,
                "quantity": component.quantity,
                "disposition": component.disposition.value,
            }
            for component in item.component_uses
        ],
    }


def _challenge_option_payload(option: ExplorationChallengeOption, actors: tuple[Actor, ...] = ()) -> dict[str, object]:
    eligible_actors = actors_matching_challenge_option(actors, option) if actors else ()
    return {
        "id": option.id,
        "label": option.label,
        "description": option.description,
        "ability": option.ability_check.ability,
        "skill": option.ability_check.skill,
        "tool": option.ability_check.tool,
        "tool_label": _tool_label_for_check(option.ability_check.tool, option, actors),
        "dc": option.ability_check.dc,
        "progress_on_success": option.progress_on_success,
        "progress_on_failure": option.progress_on_failure,
        "check_participants": (option.check_participants or CheckParticipants.SINGLE_ACTOR).value,
        "check_aggregation": (option.check_aggregation or CheckAggregation.LEAD_RESULT).value,
        "roll_mode": option.roll_mode.value,
        "situational_modifiers": [modifier.as_payload() for modifier in option.situational_modifiers],
        "improvised_tool": option.improvised_tool.as_payload() if option.improvised_tool else None,
        "mechanic": (
            {
                **mechanic_payload_for_option(option),
                **({"id": option.mechanic_id} if option.mechanic_id is not None else {}),
            }
        ),
        "tags": list(option.tags),
        "requires_item_ids": list(option.requires_item_ids),
        "requires_spell_ids": list(option.requires_spell_ids),
        "requires_ability_scores": [
            {"ability": ability, "minimum": minimum}
            for ability, minimum in option.requires_ability_scores
        ],
        "bonuses": [bonus.as_payload() for bonus in option.bonuses],
        "eligible_actors": [{"id": str(actor.id), "name": actor.name} for actor in eligible_actors],
    }


def zone_is_ui_available(state: ExplorationState, zone: ExplorationZone) -> bool:
    return zone.available_if_flag is None or scene_flag(state.flags, zone.available_if_flag, None) == zone.available_if_value


def _locked_zone_message(zone: ExplorationZone) -> str:
    if zone.available_if_flag == "gate_passed":
        return f"{zone.name} jest jeszcze niedostępna. Najpierw trzeba otworzyć bramę."
    return f"{zone.name} jest jeszcze niedostępna."
