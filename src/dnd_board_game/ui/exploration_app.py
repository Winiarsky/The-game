from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from dnd_board_game.actions import (
    action_mechanic_payload,
    attack_mechanic_from_source,
    combat_action_mechanic_from_definition,
    healing_mechanic_from_source,
)
from dnd_board_game.application import (
    CombatMovementFlowService,
    CombatReactionFlowService,
    CombatSceneInteractionFlowService,
    CombatSceneInteractionTransition,
    CombatTurnActionFlowService,
    CombatTurnFinalizationService,
    CombatResourceTransition,
    EnemyTurnFlowService,
    EnemyTurnTransitionKind,
    ExpiredCombatEffects,
    ExplorationFlowService,
    ExplorationFlowStage,
    PendingAreaSpell,
    PendingCombatInteraction,
    PendingConcentrationAction,
    PendingConcentrationCheck,
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
)
from dnd_board_game.actors import Actor, Faction, spell_is_prepared
from dnd_board_game.combat import (
    ActorSetupEntry,
    ActionUse,
    ActiveCombatEffect,
    CombatState,
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
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    initiative_prompt_led_feedback,
    movement_remaining,
    legal_healing_targets,
    legal_area_centers,
    can_consume_spell_resource,
    consume_spell_resource,
    direction_anchor_positions,
    replace_actor,
    roll_enemy_initiative,
    scene_flag,
    scene_object_by_id,
    setup_led_feedback,
    start_combat,
    start_attack_action,
)
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    EncounterOutcome,
    ExplorationChallenge,
    ExplorationEncounterTrigger,
    ExplorationChallengeOption,
    ExplorationCheckPlan,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    ExplorationMechanicId,
    ExplorationSituationalModifier,
    ExplorationSituationalModifierSource,
    ImprovisedToolUse,
    PartyCheckInput,
    PendingEncounter,
    ShortRestPolicy,
    MECHANIC_TOOLS,
    active_option_bonuses_for_actor,
    apply_exploration_effect,
    actors_matching_challenge_option,
    available_challenge_options,
    available_exploration_zones,
    available_challenge_options_for_actors,
    challenge_for_zone,
    challenge_state_for,
    exploration_zone_feedback,
    mechanic_payload_for_option,
    matching_resources,
    reveal_exploration_points,
    resolve_challenge_option,
    resolve_exploration_check,
    validate_mechanic_selection,
    visible_exploration_points,
    visible_exploration_zones,
    option_roll_modifiers_for_actor,
)
from dnd_board_game.llm import (
    GmActionFlow,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    GmDeclarationThreadEntry,
    GmClassifierProposal,
    GmPreparationEffect,
    NpcInteractionProposal,
    build_gm_classifier_request,
    build_npc_interaction_request,
    challenge_option_from_validated_proposal,
    validate_gm_declaration_analysis,
    validate_gm_classifier_proposal,
    validate_npc_interaction_proposal,
)
from dnd_board_game.hardware import BoardSessionAdapter, LedColor, LedFeedback, LedFrame, LedRole, led_color_name_pl, movement_led_feedback
from dnd_board_game.inventory import break_inventory_item, consume_inventory_item, inventory_item_payload
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectEvent,
    EffectEventType,
    RollMode,
    RollModifier,
    RollModifierType,
    ability_modifier,
    complete_long_rest,
    expire_active_effects,
    resolve_d20_roll,
    roll_instruction,
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


class PendingKind(StrEnum):
    CHALLENGE = "challenge"
    NPC = "npc"


class PendingStage(StrEnum):
    DECISION = "decision"
    ROLL = "roll"
    BREAKAGE = "breakage"


UiFlowStage = ExplorationFlowStage


EXPLORATION_DECISION_ABILITIES = frozenset(
    {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
)
EXPLORATION_DECISION_DC_MIN = 5
EXPLORATION_DECISION_DC_MAX = 25
EXPLORATION_DECISION_MAX_SITUATIONAL_MODIFIERS = 3


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
    proposal: GmClassifierProposal | NpcInteractionProposal
    challenge: ExplorationChallenge | None = None
    option: ExplorationChallengeOption | None = None
    resources: tuple[ExplorationResource, ...] = ()
    point: ExplorationPoint | None = None
    check_plan: ExplorationCheckPlan | None = None
    breakage_actor_id: str | None = None
    breakage_item_id: str | None = None
    breakage_item_label: str = ""
    breakage_chance_percent: int | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "stage": self.stage.value,
            "proposal": self.proposal.model_dump(mode="json"),
        }
        if self.challenge is not None:
            payload["challenge_id"] = self.challenge.id
            payload["challenge_name"] = self.challenge.name
        if self.option is not None:
            payload["option"] = _challenge_option_payload(self.option)
        if self.resources:
            payload["resources"] = [_resource_payload(resource) for resource in self.resources]
        if self.point is not None:
            payload["point_id"] = self.point.id
            payload["point_name"] = self.point.name
        if self.check_plan is not None:
            payload["check_plan"] = self.check_plan.as_payload()
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
            "current_prompt": _initiative_prompt_payload(prompt) if prompt is not None else None,
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
        session_id: str | None = None,
        observation_dir: str | Path = "data/session_observations",
    ) -> None:
        self.scenario_path = Path(scenario_path)
        self.gm_client = gm_client
        self.npc_client = npc_client
        self.debug_point_id = debug_point_id or ""
        self._fixed_session_id = session_id
        self.observation_dir = Path(observation_dir)
        self.observer = SessionObserver(session_id or _ui_session_id(), self.observation_dir)
        self.combat_movement_flow = CombatMovementFlowService()
        self.combat_reaction_flow = CombatReactionFlowService()
        self.combat_scene_interaction_flow = CombatSceneInteractionFlowService()
        self.combat_turn_action_flow = CombatTurnActionFlowService()
        self.combat_turn_finalization = CombatTurnFinalizationService()
        self.enemy_turn_flow = EnemyTurnFlowService()
        self.player_area_healing_flow = PlayerAreaHealingFlowService()
        self.player_combat_action_flow = PlayerCombatActionFlowService()
        self.player_combat_resource_flow = PlayerCombatResourceFlowService()
        self.player_reaction_flow = PlayerReactionFlowService()
        self.spell_preparation_flow = SpellPreparationFlowService()
        self.short_rest_flow = ShortRestFlowService()
        self.exploration_flow = ExplorationFlowService()
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
        self.exploration = replace(
            self.exploration,
            actors=tuple(rested_actors.get(actor.id, actor) for actor in self.exploration.actors),
        )
        self.state = ExplorationState(
            self.exploration.zones,
            self.exploration.points,
            self.exploration.party_position,
            SceneFlags(),
            challenges=self.exploration.challenges,
            resources=self.exploration.resources,
            inventory_resource_ids=self.exploration.initial_resource_ids,
        )
        if self.debug_point_id:
            self.state, _revealed = reveal_exploration_points(self.state, (self.debug_point_id,))
        self.messages: list[UiMessage] = []
        self.pending_state = UiPendingState()
        self.declaration_thread: list[GmDeclarationThreadEntry] = []
        self.active_preparation_effects: list[GmPreparationEffect] = []
        self.selected_lead_actor_id = str(self.exploration.actors[0].id)
        self.selected_helper_actor_id: str | None = None
        self.active_point_id = self.debug_point_id
        self.exploration_setup_flow: ExplorationSetupFlow | None = None
        self.post_interaction_setup_steps: tuple[SetupStep, ...] = ()
        self.selected_combat_movement_path = None
        self.encounter_setup_flow: EncounterSetupFlow | None = None
        self.encounter_initiative_flow: EncounterInitiativeFlow | None = None
        self.combat_state: CombatState | None = None
        self.resolved_encounter_trigger_ids: set[str] = set()
        self.selected_attack_source_ids: dict[str, str] = {}
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
        if self.debug_point_id:
            self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        elif self.spell_preparation_flow.pending_actors(self.exploration.actors):
            self.ui_flow_stage = UiFlowStage.SPELL_PREPARATION
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
    def pending_combat_help(self) -> PendingCombatHelp | None:
        return self.pending_state.combat_help

    @pending_combat_help.setter
    def pending_combat_help(self, value: PendingCombatHelp | None) -> None:
        self.pending_state.combat_help = value

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
            self._refresh_pending_encounter()
        self._expire_invalid_combat_effects()
        active_challenge = self.active_challenge if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else None
        current_zone_points = self.current_zone_points() if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else ()
        scene_status = _scene_status_payload(self.state)
        scene_status.append({"label": "Czas scenariusza", "value": _duration_minutes_label(self.state.elapsed_minutes)})
        if self.pending_encounter is not None:
            scene_status.append({"label": "Encounter", "value": self.pending_encounter.name})
        preview_zone = self._preview_zone()
        return UiSessionView(
            scenario={"id": self.exploration.scenario_id, "name": self.exploration.scenario_name},
            session_log={
                "session_id": self.observer.session_id,
                "path": str(self.observer.path),
            },
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
            visible_points=[_point_payload(point) for point in visible_exploration_points(self.state.points)],
            current_zone_points=[_point_payload(point) for point in current_zone_points],
            active_challenge=_challenge_payload(self.state, active_challenge, self.exploration.actors) if active_challenge else None,
            active_point=_point_payload(self.active_point) if self.active_point else None,
            resources=[_resource_payload(resource) for resource in self.state.resources if resource.id in self.state.inventory_resource_ids],
            actors=[_exploration_actor_payload(actor) for actor in self.exploration.actors],
            active_effects=[effect.as_payload() for effect in self.active_combat_effects],
            scene_status=scene_status,
            flags=[{"key": key, "value": value} for key, value in self.state.flags.values],
            messages=[message.as_payload() for message in self.messages],
            pending=self.pending.as_payload() if self.pending else None,
            selected_lead_actor_id=self.selected_lead_actor_id,
            selected_helper_actor_id=self.selected_helper_actor_id,
            allowed_mechanics=[tool.as_payload() for tool in MECHANIC_TOOLS.values()],
            pending_encounter=self._pending_encounter_payload(),
            exploration_setup=self.exploration_setup_flow.as_payload() if self.exploration_setup_flow else None,
            encounter_setup=self.encounter_setup_flow.as_payload() if self.encounter_setup_flow else None,
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
                self.pending_player_attack,
                self.pending_player_healing,
                self.pending_area_spell,
                self.pending_combat_interaction,
                self.pending_combat_help,
                self.pending_concentration_action,
                self.pending_concentration_check,
                self.pending_combat_ready,
                self.pending_opportunity_movement,
                self.pending_enemy_opportunity_attack,
                self.pending_ready_attack,
                self.active_combat_effects,
                self.selected_attack_source_ids,
                self.selected_healing_source_ids,
            )
            if self.combat_state
            else None,
            board=self._board_payload(),
            required_rolls=self.required_rolls_payload(),
        ).as_payload()

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
            if not self.debug_point_id and self.ui_flow_stage != UiFlowStage.SPELL_PREPARATION:
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
            if self.board_adapter is not None and self.board_backend in {"simulator", "hardware"}:
                self.ui_flow_stage = UiFlowStage.READY_TO_START
                self.board_message = "Przygotowanie zakończone. Plansza gotowa do rozpoczęcia scenariusza."
            else:
                self.ui_flow_stage = UiFlowStage.WAITING_FOR_BOARD
                self.board_message = "Przygotowanie zakończone. Wybierz backend planszy."
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
        self.pending_encounter = None
        self.ui_flow_stage = UiFlowStage.SCENARIO_COMPLETE
        self.board_message = "Scenariusz zakończony. Efekty dzienne wygasły."
        self._record(
            "ui_scenario_completed",
            {
                "elapsed_minutes": self.state.elapsed_minutes,
                "expired_effect_ids": [effect.id for effect in expiration.expired_effects],
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
        )
        if transition is None:
            return self.state_payload()
        self.exploration_setup_flow = (
            ExplorationSetupFlow(transition.setup_steps) if transition.setup_steps else None
        )
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
        self.post_interaction_setup_steps = ()
        self.ui_flow_stage = transition.stage
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
        )
        if transition is None:
            return self.state_payload()
        self._add_message("Setup mapy", f"Potwierdzono: {transition.confirmed_label}.")
        if transition.completed:
            flow.completed = True
            self.exploration_setup_flow = None
            self.ui_flow_stage = transition.stage
            self.preview_zone_id = ""
            self.board_message = transition.board_message
            self._refresh_pending_encounter()
            if self.pending_encounter is not None:
                self.board_message = "Encounter gotowy. Potwierdź rozpoczęcie setupu w UI albo Enterem."
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
        self._show_board_feedback(target.feedback)
        selected_raw = self.board_adapter.scan(target.positions, timeout_s=self.scan_timeout_s)
        if selected_raw is None:
            self.board_message = "Nie wybrano pola na planszy."
            self._record("ui_board_scan_timeout", {"stage": self.ui_flow_stage.value})
            return self.state_payload()
        selected = _coordinate_from_scan(selected_raw)
        self._record("ui_board_scan_received", {"stage": self.ui_flow_stage.value, "position": [selected.col, selected.row]})
        return self._handle_board_position(selected)

    def select_board_position(self, selected: Coordinate) -> dict[str, object]:
        target = self._current_board_scan_target()
        if target.positions and selected not in target.positions:
            raise ValueError("Wybrane pole nie jest teraz aktywnym polem planszy.")
        self._record("ui_board_position_selected", {"stage": self.ui_flow_stage.value, "position": [selected.col, selected.row]})
        return self._handle_board_position(selected)

    def submit_action(self, text: str) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE:
            raise ValueError("Najpierw rozpocznij sesję i potwierdź wejście do lokacji na planszy.")
        text = text.strip()
        if not text:
            raise ValueError("Deklaracja nie może być pusta.")
        self._record(
            "ui_action_submitted",
            {
                "text": text,
                "zone_id": self.current_zone.id,
                "active_point_id": self.active_point.id if self.active_point else None,
                "active_challenge_id": self.active_challenge.id if self.active_challenge else None,
            },
        )
        point = self.active_point
        if point is not None and point.npc_interaction is not None:
            return self._submit_npc_action(point, text)
        referenced_point = self._referenced_current_zone_point(text)
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
        return self._submit_challenge_action(challenge, text)

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
                "Figurki i jawne elementy encountera są rozstawione. Następny krok to inicjatywa i start walki.",
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
                "Figurki i jawne elementy encountera są rozstawione. Następny krok to inicjatywa i start walki.",
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
        prompts = build_player_initiative_prompts(encounter.actors)
        self.encounter_initiative_flow = EncounterInitiativeFlow(encounter=encounter, prompts=prompts, entries=[])
        self._add_message(
            "Inicjatywa",
            "Rozpoczyna się walka. Bohaterowie wykonują test inicjatywy po kolei; przeciwnicy rzucają automatycznie.",
        )
        if not prompts:
            self._finish_encounter_initiative()
        self._sync_board_leds()
        return self.state_payload()

    def submit_encounter_initiative_roll(self, natural_roll: int) -> dict[str, object]:
        if self.encounter_initiative_flow is None:
            raise ValueError("Inicjatywa encountera nie została rozpoczęta.")
        flow = self.encounter_initiative_flow
        prompt = flow.current_prompt
        if prompt is None:
            return self.state_payload()
        roll = resolve_d20_roll(D20RollInput(prompt.request, natural_roll))
        entry = InitiativeEntry(
            actor=prompt.actor,
            roll=roll,
            dexterity_modifier=prompt.dexterity_modifier,
            stable_order=_actor_stable_order(flow.encounter, prompt.actor),
        )
        flow.entries.append(entry)
        self._add_message(
            "Rzut inicjatywy",
            f"{prompt.actor.name}: naturalny wynik {roll.natural_roll}, razem {roll.total}.",
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
        for actor in flow.encounter.actors:
            if actor.id in known_actor_ids or actor.faction == Faction.ALLY or actor.is_defeated():
                continue
            entry = replace(roll_enemy_initiative(actor, self.encounter_rng), stable_order=_actor_stable_order(flow.encounter, actor))
            flow.entries.append(entry)
            self._add_message(
                "Inicjatywa przeciwnika",
                f"{actor.name}: automatyczny wynik {entry.roll.natural_roll}, razem {entry.roll.total}.",
            )
        order = build_initiative_order(flow.entries)
        flow.order = order
        flow.completed = True
        self.combat_state = start_combat(flow.encounter.actors, order)
        order_text = ", ".join(entry.actor.name for entry in order.entries)
        self._add_message(
            "Kolejność inicjatywy",
            f"Kolejność została ustalona: {order_text}. Pierwsza tura: {order.current_actor.name}.",
        )
        self._sync_board_leds()

    def _clear_player_pending_choices(self) -> None:
        self.pending_state.clear_player_choices()

    def _attack_sources_for_actor(self, actor: Actor) -> tuple:
        encounter = self._active_encounter()
        if encounter is None:
            return ()
        return encounter.attack_source_options_by_actor.get(actor.id, ())

    def _selected_attack_source(self, actor: Actor):
        sources = self._attack_sources_for_actor(actor)
        if not sources:
            return None
        selected_id = self.selected_attack_source_ids.get(str(actor.id))
        if selected_id:
            selected = next((source for source in sources if source.id == selected_id), None)
            if selected is not None:
                return selected
        return sources[0]

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
        return self._apply_combat_resource_transition(transition)

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
        )
        self.combat_state = transition.state
        self.pending_area_spell = transition.pending
        self.pending_player_attack = None
        self.pending_player_healing = None
        self.pending_combat_help = None
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
        for applied in transition.applied_damages:
            self._maybe_prompt_concentration_check(applied)
            if self.pending_concentration_check is not None:
                break
        self._sync_board_leds()
        return self.state_payload()

    def select_player_attack_target_at_position(self, position: Coordinate) -> dict[str, object]:
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
        )
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
        for applied_damage in resolution.applied_damages:
            self._maybe_prompt_concentration_check(applied_damage)
            if self.pending_concentration_check is not None:
                break
        self._sync_board_leds()
        return self.state_payload()

    def cancel_opportunity_movement(self) -> dict[str, object]:
        pending = self.pending_opportunity_movement
        if pending is None:
            raise ValueError("Nie ma ruchu z atakiem okazyjnym do anulowania.")
        self.pending_opportunity_movement = None
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
            active_effects=self.active_combat_effects,
            rng=self.encounter_rng,
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
        self.pending_enemy_turn_ack_result = transition.result
        self.board_message = transition.board_message
        self._record(transition.event_type, dict(transition.event_payload))
        if result.applied_damage is not None:
            self._maybe_prompt_concentration_check(result.applied_damage)
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
        merged_actor = replace(result_actor, hp=updated_actor.hp, temp_hp=updated_actor.temp_hp)
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
        return self._finish_pending_enemy_turn(result)

    def _finish_pending_enemy_turn(self, result) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        transition = self.combat_turn_finalization.finalize_enemy_turn(
            result=result,
            active_effects=self.active_combat_effects,
        )
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._add_expired_effect_notices(transition.expired_effects)
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_enemy_turn_ack_result = None
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
        self._sync_board_leds()
        return self.state_payload()

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
        transition = self.combat_turn_finalization.finish_active_turn(
            state=self.combat_state,
            active_effects=self.active_combat_effects,
        )
        if transition is None:
            return self.state_payload()
        self.combat_state = transition.state
        self.active_combat_effects = transition.active_effects
        self._add_expired_effect_notices(transition.expired_effects)
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_turn_ack_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self._clear_player_pending_choices()
        self._add_message(transition.message_title, transition.message_body)
        self._record(transition.event_type, dict(transition.event_payload))
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
        if self.encounter_initiative_flow is not None:
            prompt = self.encounter_initiative_flow.current_prompt
            if prompt is not None:
                return BoardScanTarget(
                    positions=(prompt.actor.position,),
                    feedback=initiative_prompt_led_feedback(prompt),
                    empty_message="Nie ma aktywnego aktora do podświetlenia inicjatywy.",
                )
        if self.combat_state is not None:
            encounter = self._active_encounter()
            actor = combat_current_actor(self.combat_state)
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
                    feedback=LedFeedback((LedFrame(scene_object_positions or (position,), LedColor.INTERACTIVE_OBJECT, LedRole.DESTINATION),)),
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
            return BoardScanTarget(
                positions=(),
                feedback=LedFeedback(),
                empty_message="Encounter czeka na rozpoczęcie setupu w UI albo Enterem.",
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
                    attack_source = self._selected_attack_source(actor) if encounter is not None else None
                    attack_source = self._effective_attack_source(actor, attack_source) if attack_source is not None else None
                    if attack_source is not None and not self._actor_can_use_attack_source(actor, attack_source):
                        attack_source = None
                    if (
                        encounter is not None
                        and attack_source is not None
                        and attack_source.area is not None
                        and selected in _area_spell_selection_positions(encounter.board, actor, attack_source)
                    ):
                        self.board_message = f"Czar obszarowy: {actor.name} -> {selected.as_tuple()}."
                        return self.select_player_area_spell_at_position(selected)
                    if encounter is not None and _combat_target_at_position(encounter, self.combat_state, actor, selected, attack_source) is not None:
                        self.board_message = f"Atak bohatera: {actor.name} -> {selected.as_tuple()}."
                        return self.select_player_attack_target_at_position(selected)
                    healing_source = self._selected_healing_source(actor) if encounter is not None else None
                    if (
                        encounter is not None
                        and healing_source is not None
                        and any(
                            target.position == selected
                            for target in legal_healing_targets(encounter.board, actor, self.combat_state.actors, healing_source)
                        )
                    ):
                        self.board_message = f"Leczenie: {actor.name} -> {selected.as_tuple()}."
                        return self.select_player_healing_target_at_position(selected)
                    if encounter is not None and self._available_combat_interaction_options(encounter, actor, selected):
                        return self.select_combat_interaction_at_position(selected)
                    if (
                        self.selected_combat_movement_path is not None
                        and self.selected_combat_movement_path.valid
                        and self.selected_combat_movement_path.destination == selected
                    ):
                        self.board_message = f"Ruch bohatera: {actor.name} -> {selected.as_tuple()}."
                        return self.submit_combat_movement(col=selected.col, row=selected.row)
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
        if selection.point is None:
            return self.state_payload()
        self.pending = None
        point = selection.point
        if point.npc_interaction is not None and point.npc_interaction.dialogue_intro:
            self._add_message(point.npc_interaction.name, point.npc_interaction.dialogue_intro)
        self._sync_board_leds()
        return self.state_payload()

    def _submit_challenge_action(self, challenge: ExplorationChallenge, text: str) -> dict[str, object]:
        client = self._gm_client()
        request_data = build_gm_classifier_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            scenario_context=self.exploration.llm_context,
            state=self.state,
            player_action=text,
            declaration_thread=tuple(self.declaration_thread[-8:]),
            active_preparation_effects=tuple(self.active_preparation_effects),
            actors=self.exploration.actors,
        )
        analysis = _analyze(client, request_data)
        validate_gm_declaration_analysis(analysis, request_data)
        if analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION:
            self._add_message("Odpowiedź MG", analysis.player_message or "To pytanie nie zmienia stanu sceny.")
            return self.state_payload()
        if analysis.analysis_type in {GmDeclarationAnalysisType.NEEDS_CLARIFICATION, GmDeclarationAnalysisType.UNSUPPORTED}:
            self._add_message("Deklaracja wymaga doprecyzowania", analysis.player_message or analysis.reason)
            return self.state_payload()
        if analysis.normalized_intent:
            request_data = replace(request_data, player_action=analysis.normalized_intent)
        proposal = client.classify(request_data)
        validated = validate_gm_classifier_proposal(proposal, request_data)
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
                self.active_preparation_effects.append(effect)
                self._add_message("Przygotowanie", f"Przygotowanie zapisane: {effect.label}.")
            return self.state_payload()
        option = challenge_option_from_validated_proposal(validated)
        resource = validated.resources[0] if validated.resources else None
        self.pending = PendingInteraction(
            kind=PendingKind.CHALLENGE,
            stage=PendingStage.DECISION,
            proposal=proposal,
            challenge=validated.challenge,
            option=option,
            resources=(resource,) if resource is not None else (),
        )
        self._add_message("Propozycja MG", _challenge_proposal_text(proposal, option, resource))
        return self.state_payload()

    def _submit_npc_action(self, point: ExplorationPoint, text: str) -> dict[str, object]:
        client = self._npc_client()
        zone = next(zone for zone in self.exploration.zones if zone.id == point.zone_id)
        request_data = build_npc_interaction_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            zone=zone,
            point=point,
            state=self.state,
            player_action=text,
        )
        proposal = client.interact_npc(request_data)
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
        )
        if proposal.player_narration:
            self._add_message("Narracja MG", proposal.player_narration)
        if proposal.npc_response:
            self._add_message("Odpowiedź NPC", proposal.npc_response)
        self._add_message("Propozycja interakcji", _npc_proposal_text(proposal))
        return self.state_payload()

    def update_pending_challenge_decision(self, data: dict[str, object]) -> dict[str, object]:
        if self.pending is None or self.pending.kind != PendingKind.CHALLENGE or self.pending.stage != PendingStage.DECISION:
            raise ValueError("Korekta decyzji MG jest dostępna tylko przed zaakceptowaniem testu eksploracji.")
        if self.pending.option is None:
            raise ValueError("Brak opcji testu do poprawienia.")
        option = self.pending.option
        default_mechanic_id = option.mechanic_id or str(mechanic_payload_for_option(option)["id"])
        mechanic_id = ExplorationMechanicId(str(data.get("mechanic_id") or default_mechanic_id))
        participants = CheckParticipants(str(data.get("check_participants") or option.check_participants or CheckParticipants.SINGLE_ACTOR.value))
        aggregation = CheckAggregation(str(data.get("check_aggregation") or option.check_aggregation or CheckAggregation.LEAD_RESULT.value))
        validate_mechanic_selection(mechanic_id, participants=participants, aggregation=aggregation)

        lead_actor_id = str(data.get("lead_actor_id") or self.selected_lead_actor_id).strip()
        actor_ids = {str(actor.id) for actor in self.exploration.actors}
        if lead_actor_id not in actor_ids:
            raise ValueError("Wybrany prowadzący test nie istnieje w drużynie.")

        helper_actor_id = str(data.get("helper_actor_id") or "").strip() or None
        if participants == CheckParticipants.LEAD_WITH_HELP:
            if helper_actor_id is None:
                raise ValueError("Mechanika prowadzący z pomocą wymaga wyboru pomocnika.")
            if helper_actor_id not in actor_ids:
                raise ValueError("Wybrany pomocnik nie istnieje w drużynie.")
            if helper_actor_id == lead_actor_id:
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

    def decide(self, decision: str, *, lead_actor_id: str | None = None) -> dict[str, object]:
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
            },
        )
        if normalized in {"reject", "odrzuc", "odrzuć", "-"}:
            self._add_message("Decyzja", "Odrzucono interpretację. Wpisz deklarację inaczej.")
            self.pending = None
            return self.state_payload()
        if normalized in {"explain", "wyjasnij", "wyjaśnij", "?"}:
            self._add_message("Wyjaśnienie", _pending_explanation(self.pending))
            return self.state_payload()
        if normalized in {"reinterpret", "r"}:
            self._add_message("Reinterpretacja", "Wpisz deklarację ponownie, akcentując korektę interpretacji.")
            self.pending = None
            return self.state_payload()
        if normalized not in {"accept", "akceptuj", "+"}:
            raise ValueError(f"Nieznana decyzja: {decision}.")
        if lead_actor_id and any(str(actor.id) == lead_actor_id for actor in self.exploration.actors):
            self.selected_lead_actor_id = lead_actor_id
        if self.pending.kind == PendingKind.CHALLENGE:
            return self._accept_challenge()
        return self._accept_npc()

    def _accept_challenge(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.option is not None and self.pending.challenge is not None
        option = self.pending.option
        lead_actor_id = self.lead_actor_id
        matching_actors = actors_matching_challenge_option(self.exploration.actors, option)
        if matching_actors and not any(str(actor.id) == lead_actor_id for actor in matching_actors):
            lead_actor_id = str(matching_actors[0].id)
            self.selected_lead_actor_id = lead_actor_id
        helper_actor_id = None
        if option.check_participants == CheckParticipants.LEAD_WITH_HELP:
            actor_ids = {str(actor.id) for actor in self.exploration.actors}
            helper_actor_id = (
                self.selected_helper_actor_id
                if self.selected_helper_actor_id in actor_ids and self.selected_helper_actor_id != lead_actor_id
                else None
            )
            if helper_actor_id is None:
                helper_actor = next((actor for actor in self.exploration.actors if str(actor.id) != lead_actor_id), None)
                if helper_actor is None:
                    raise ValueError("Mechanika prowadzący z pomocą wymaga drugiej postaci.")
                helper_actor_id = str(helper_actor.id)
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
            resource=resource,
        )
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    def _accept_npc(self) -> dict[str, object]:
        assert self.pending is not None
        proposal = self.pending.proposal
        assert isinstance(proposal, NpcInteractionProposal)
        if not proposal.requires_roll:
            self._apply_npc_flags(proposal, success=True)
            self._reveal_npc_information(proposal)
            self._add_message("Wynik interakcji NPC", "Interakcja nie wymagała rzutu.")
            self.pending = None
            return self.state_payload()
        plan = _npc_check_plan(proposal, self.lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    @property
    def lead_actor_id(self) -> str:
        return self.selected_lead_actor_id

    def resolve_rolls(self, raw_rolls: dict[str, object]) -> dict[str, object]:
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
        else:
            self._resolve_npc_roll(check_result)
        if self.pending is not None and self.pending.stage != PendingStage.BREAKAGE:
            self.pending = None
        self._refresh_pending_encounter()
        self._sync_board_leds()
        return self.state_payload()

    def _resolve_challenge_roll(self, check_result) -> None:
        assert self.pending is not None and self.pending.challenge is not None and self.pending.option is not None
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
        self._add_message("Wynik podejścia", result.message)
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
        if result.completed:
            revealed_points = self._reveal_completed_challenge_points(self.pending.challenge)
            available_after = {zone.id for zone in available_exploration_zones(self.state)}
            visible_points_after = {point.id for point in visible_exploration_points(self.state.points)}
            unlocked_zone_ids = tuple(sorted(available_after - available_before))
            revealed_point_ids = tuple(sorted((visible_points_after - visible_points_before) | {point.id for point in revealed_points}))
            if self.pending.option.id == "force_gate" or "heavy_force" in self.pending.option.tags:
                self.post_interaction_setup_steps = (_fallen_gate_setup_step(),)
                self.interaction_result = {
                    "title": f"Zakończono: {self.pending.challenge.name}",
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
                return
            self.interaction_result = {
                "title": f"Zakończono: {self.pending.challenge.name}",
                "body": result.message,
                "unlocked_zones": [_zone_payload(zone, self._scenario_asset_root()) for zone in self.state.zones if zone.id in unlocked_zone_ids],
                "revealed_points": [_point_payload(point) for point in self.state.points if point.id in revealed_point_ids],
                "current_zone": _zone_payload(self.current_zone, self._scenario_asset_root()),
                "next_instruction": "Zakończ interakcję, żeby wrócić do wyboru lokacji.",
            }
            self.ui_flow_stage = UiFlowStage.INTERACTION_RESULT
            self.preview_zone_id = ""

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
        success = check_result.success
        message = proposal.success_message if success else proposal.failure_message
        self._add_message("Wynik interakcji NPC", message or ("Sukces." if success else "Porażka."))
        self._record("ui_npc_roll_resolved", {"success": success, "message": message})
        self._apply_npc_flags(proposal, success=success)
        self._reveal_npc_information(proposal)

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

    def _reveal_npc_information(self, proposal: NpcInteractionProposal) -> None:
        if self.pending is None or self.pending.point is None or self.pending.point.npc_interaction is None:
            return
        npc = self.pending.point.npc_interaction
        known = {info.id: info for info in npc.locked_information}
        for info_id in proposal.revealed_information_ids:
            info = known.get(info_id)
            if info is None:
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
        return {
            "trigger_id": self.pending_encounter.trigger_id,
            "name": self.pending_encounter.name,
            "description": self.pending_encounter.description,
            "encounter_scenario": self.pending_encounter.encounter_scenario,
            "reason": self.pending_encounter.reason,
            "command": (
                "PYTHONPATH=src python -m dnd_board_game.runtime.demo_mini_combat_loop "
                f"--scenario {self.pending_encounter.encounter_scenario} --board-backend none --initiative-mode rolled"
            ),
        }

    def required_rolls_payload(self) -> list[dict[str, object]]:
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
            payload: dict[str, object] = {"actor_id": str(actor.id), "actor_name": actor.name, "die_sides": 20, "label": "d20"}
            if plan.roll_mode != RollMode.NORMAL:
                payload["roll_mode"] = plan.roll_mode.value
                payload["requires_second_roll"] = True
            rolls.append(payload)
        return rolls

    def _add_message(self, title: str, body: str) -> None:
        self.messages.append(UiMessage(title, body))
        self._record("ui_message_added", {"title": title, "body": body})

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


def _initiative_prompt_payload(prompt: InitiativePrompt | None) -> dict[str, object] | None:
    if prompt is None:
        return None
    return {
        "actor_id": str(prompt.actor.id),
        "actor_name": prompt.actor.name,
        "message": prompt.message,
        "dexterity_modifier": prompt.dexterity_modifier,
    }


def _initiative_entry_payload(entry: InitiativeEntry) -> dict[str, object]:
    return {
        "actor_id": str(entry.actor.id),
        "actor_name": entry.actor.name,
        "natural_roll": entry.roll.natural_roll,
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
    pending_player_attack: PendingPlayerAttack | None = None,
    pending_player_healing: PendingPlayerHealing | None = None,
    pending_area_spell: PendingAreaSpell | None = None,
    pending_combat_interaction: PendingCombatInteraction | None = None,
    pending_combat_help: PendingCombatHelp | None = None,
    pending_concentration_action: PendingConcentrationAction | None = None,
    pending_concentration_check: PendingConcentrationCheck | None = None,
    pending_combat_ready: PendingCombatReady | None = None,
    pending_opportunity_movement: PendingOpportunityMovement | None = None,
    pending_enemy_opportunity_attack: PendingEnemyOpportunityAttack | None = None,
    pending_ready_attack: PendingReadyAttack | None = None,
    active_combat_effects: tuple[ActiveCombatEffect, ...] = (),
    selected_attack_source_ids: dict[str, str] | None = None,
    selected_healing_source_ids: dict[str, str] | None = None,
) -> dict[str, object] | None:
    if state is None:
        return None
    actor = combat_current_actor(state)
    selected_attack_source_ids = selected_attack_source_ids or {}
    selected_healing_source_ids = selected_healing_source_ids or {}
    attack_sources = encounter.attack_source_options_by_actor.get(actor.id, ()) if encounter is not None else ()
    selected_attack_source_id = selected_attack_source_ids.get(str(actor.id))
    attack_source = next((source for source in attack_sources if source.id == selected_attack_source_id), None) or (
        attack_sources[0] if attack_sources else None
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
    area_positions = ()
    movement = None
    if (
        encounter is not None
        and attack_source is not None
        and state.status.value == "active"
        and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        and _source_is_prepared(actor, attack_source)
        and can_consume_spell_resource(actor, attack_source.spell_level)
    ):
        if attack_source.area is not None:
            area_positions = _area_spell_selection_positions(encounter.board, actor, attack_source)
        else:
            targets = start_attack_action(encounter.board, actor, state.actors, attack_source).legal_targets
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
    return {
        "status": state.status.value,
        "round_number": state.round_number,
        "current_actor": _combat_actor_payload(
            actor,
            active_combat_effects,
            turn_action=state.turn_action,
            movement_remaining_feet=movement_remaining(state, actor) if movement is not None else None,
        ),
        "actors": [_combat_actor_payload(candidate, active_combat_effects) for candidate in state.actors],
        "winner": state.winner.value if state.winner is not None else None,
        "turn_action": {
            "action_use": state.turn_action.action_use.value,
            "bonus_action_use": state.turn_action.bonus_action_use.value,
            "reaction_available": state.turn_action.reaction_available,
            "movement_used_feet": state.turn_action.movement_used_feet,
            "extra_movement_feet": state.turn_action.extra_movement_feet,
        },
        "available_attack": _attack_source_payload(attack_source, actor) if attack_source is not None else None,
        "available_attack_sources": [_attack_source_payload(source, actor) for source in attack_sources],
        "selected_attack_source_id": attack_source.id if attack_source is not None else None,
        "available_healing_sources": [_healing_source_payload(source, actor) for source in healing_sources],
        "selected_healing_source_id": healing_source.id if healing_source is not None else None,
        "legal_healing_targets": [_combat_target_payload(target) for target in healing_targets],
        "combat_actions": [
            _combat_action_payload(action, actor)
            for action in (encounter.combat_actions_by_actor.get(actor.id, ()) if encounter is not None else ())
        ],
        "legal_targets": [_combat_target_payload(target) for target in targets],
        "legal_area_positions": [[position.col, position.row] for position in area_positions],
        "movement": _movement_payload(movement, state, actor) if movement is not None else None,
        "movement_preview": _movement_preview_payload(selected_movement_path),
        "enemy_turn_intent": _enemy_turn_intent_payload(pending_enemy_turn_intent, encounter, active_combat_effects),
        "enemy_turn_preview": _enemy_turn_preview_payload(pending_enemy_turn_result, encounter, active_combat_effects),
        "enemy_turn_result": _enemy_turn_result_payload(pending_enemy_turn_ack_result, encounter, active_combat_effects),
        "pending_player_attack": _pending_player_attack_payload(pending_player_attack, state, encounter, active_combat_effects),
        "pending_player_healing": _pending_player_healing_payload(pending_player_healing, state, encounter),
        "pending_area_spell": _pending_area_spell_payload(pending_area_spell, state, encounter, active_combat_effects),
        "pending_combat_interaction": pending_combat_interaction.as_payload() if pending_combat_interaction is not None else None,
        "pending_combat_help": pending_combat_help.as_payload(state, active_combat_effects) if pending_combat_help is not None else None,
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
        "faction": actor.faction.value,
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "temp_hp": actor.temp_hp,
        "ac": actor.ac,
        "position": [actor.position.col, actor.position.row],
        "defeated": actor.is_defeated(),
        "spell_slots": [
            {"level": slot.level, "remaining": slot.remaining, "maximum": slot.maximum}
            for slot in actor.spell_slots
        ],
        "spell_save_dc": actor.spell_save_dc,
        "inventory": [inventory_item_payload(item) for item in actor.inventory],
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
    if actor.is_defeated():
        chips.append(_status_chip("Pokonany", tone="danger"))
    if turn_action is not None:
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
    modifier = ability_modifier(actor.ability_scores.constitution)
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
    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type.value,
        "range_feet": source.range_feet,
        "damage_hint": source.damage_hint,
        "damage_fixed": source.damage_fixed,
        "damage_die_sides": source.damage_die_sides,
        "damage_modifier": source.damage_modifier,
        "damage_type": source.damage_type,
        "ability": source.ability,
        "spell_level": source.spell_level,
        "casting_kind": source.casting_kind.value,
        "prepared": prepared,
        "available": prepared and (
            actor is None or can_consume_spell_resource(actor, source.spell_level)
        ),
        "unavailable_reason": _spell_source_unavailable_reason(actor, source),
        "resource_label": _source_resource_label(source),
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


def _source_resource_label(source) -> str:
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


def _spell_area_payload(area) -> dict[str, object] | None:
    if area is None:
        return None
    return {
        "shape": area.shape.value,
        "radius_feet": area.radius_feet,
        "length_feet": area.length_feet,
        "width_feet": area.width_feet,
    }


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


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
    sources = encounter.attack_source_options_by_actor.get(attacker.id, ())
    source = next((candidate for candidate in sources if candidate.id == pending.source_id), None) or (
        sources[0] if sources else None
    )
    if source is None:
        return None
    source = attack_source_with_target_combat_effects(attacker, target, source, active_combat_effects)
    instruction = roll_instruction(source.attack_roll_request)
    return {
        "stage": pending.stage,
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
    reachable = frozenset(tile for tile in result.reachable_tiles if result.costs_by_tile.get(tile, 999) <= remaining)
    costs = {tile: cost for tile, cost in result.costs_by_tile.items() if tile in reachable}
    paths = {tile: path for tile, path in result.paths_by_tile.items() if tile in reachable}
    return MovementRangeResult(origin=result.origin, reachable_tiles=reachable, costs_by_tile=costs, paths_by_tile=paths)


def _legal_combat_targets(encounter: LoadedEncounter, state: CombatState, actor: Actor, source=None):
    if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
        return ()
    source = source or encounter.attack_sources_by_actor.get(actor.id)
    if source is None:
        return ()
    return start_attack_action(encounter.board, actor, state.actors, source).legal_targets


def _combat_target_at_position(encounter: LoadedEncounter, state: CombatState, actor: Actor, position: Coordinate, source=None):
    for target in _legal_combat_targets(encounter, state, actor, source):
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
        frames.append(LedFrame(tuple(sorted(interaction_positions)), LedColor.INTERACTIVE_OBJECT, LedRole.DESTINATION))
    if area_spell_positions:
        frames.append(LedFrame(tuple(sorted(area_spell_positions)), LedColor.MARKER, LedRole.DESTINATION))
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
    source = encounter.attack_sources_by_actor.get(result.enemy.id) if encounter is not None else None
    if source is not None and result.target is not None:
        target_actor = next((actor for actor in result.state.actors if str(actor.id) == result.target.id), None)
        source = (
            attack_source_with_target_combat_effects(result.enemy, target_actor, source, active_combat_effects)
            if target_actor is not None
            else _effective_attack_source_for_effects(result.enemy, source, active_combat_effects)
        )
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


def _movement_preview_payload(path) -> dict[str, object] | None:
    if path is None or not path.valid:
        return None
    return {
        "destination": [path.destination.col, path.destination.row],
        "cost_feet": path.cost_feet,
        "path": [[position.col, position.row] for position in path.path],
    }


def _movement_payload(result, state: CombatState, actor: Actor) -> dict[str, object]:
    remaining = movement_remaining(state, actor)
    destinations = tuple(sorted(tile for tile in result.reachable_tiles if tile != result.origin))
    return {
        "remaining_feet": remaining,
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


def _damage_application_message(result) -> str:
    defeated_text = " Cel zostaje pokonany." if result.defeated_by_damage else ""
    temp_text = ""
    if result.temp_hp_before > 0 or result.absorbed_by_temp_hp > 0:
        temp_text = f" Temp HP {result.temp_hp_before} -> {result.temp_hp_after}, pochłonięto {result.absorbed_by_temp_hp}."
    return (
        f"Obrażenia: {result.damage.total_applied}. "
        f"{result.actor_before.name}: HP {result.hp_before} -> {result.hp_after} / {result.actor_after.max_hp}."
        f"{temp_text}{defeated_text}"
    )


def _applied_damage_payload(result) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "damage": result.damage.total_applied,
        "hp_before": result.hp_before,
        "hp_after": result.hp_after,
        "temp_hp_before": result.temp_hp_before,
        "temp_hp_after": result.temp_hp_after,
        "absorbed_by_temp_hp": result.absorbed_by_temp_hp,
        "applied_to_hp": result.applied_to_hp,
        "defeated": result.defeated,
        "defeated_by_damage": result.defeated_by_damage,
    }


def _default_encounter_victory_outcome(name: str) -> EncounterOutcome:
    return EncounterOutcome(
        title="Encounter rozstrzygnięty",
        body=f"Drużyna wygrywa encounter: {name}.",
        next_instruction="Zakończ wynik, żeby wrócić do eksploracji.",
    )


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


def _challenge_check_plan(
    option: ExplorationChallengeOption,
    lead_actor_id: str,
    actors: tuple[Actor, ...],
    *,
    helper_actor_id: str | None = None,
    resource: ExplorationResource | None = None,
) -> ExplorationCheckPlan:
    resource_modifier = resource.as_roll_modifier() if resource is not None else None
    roll_modifiers_by_actor_id = tuple(
        (
            str(actor.id),
            (
                *option_roll_modifiers_for_actor(actor, option),
                *((resource_modifier,) if resource_modifier is not None else ()),
            ),
        )
        for actor in actors
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
        participants=option.check_participants or CheckParticipants.SINGLE_ACTOR,
        aggregation=option.check_aggregation or CheckAggregation.LEAD_RESULT,
        consequence_targets=option.consequence_targets or (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.SCENE),
        ability=option.ability_check.ability,
        skill=option.ability_check.skill,
        dc=option.ability_check.dc,
        lead_actor_id=lead_actor_id,
        helper_actor_id=helper_actor_id,
        reason_for_players=option.description,
        roll_mode=_combined_roll_mode(
            option.roll_mode,
            (RollMode.ADVANTAGE,) if resource is not None and resource.advantage else (),
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
        request = D20RollRequest(
            mode=plan.roll_mode,
            modifiers=(
                *_ability_roll_modifiers(actor, plan.ability, plan.skill),
                *_plan_roll_modifiers(actor, plan),
            ),
        )
        result.append(PartyCheckInput(actor, natural_roll, request, natural_roll_2))
    return tuple(result)


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
    if plan.participants == CheckParticipants.LEAD_WITH_HELP:
        helper = next((actor for actor in actors if str(actor.id) == plan.helper_actor_id), None)
        if helper is not None and helper != lead:
            return (lead, helper)
    return (lead,)


def _ability_roll_modifiers(actor: Actor, ability: str, skill: str | None = None) -> tuple[RollModifier, ...]:
    score = getattr(actor.ability_scores, ability)
    label = f"Modyfikator {ability}"
    if skill:
        label = f"Modyfikator {ability}/{skill}"
    return (RollModifier(label, ability_modifier(score), RollModifierType.ABILITY, stacking_key=f"ability:{ability}"),)


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


def _challenge_proposal_text(
    proposal: GmClassifierProposal,
    option: ExplorationChallengeOption,
    resource: ExplorationResource | None,
) -> str:
    resource_text = f"\nZasób: {resource.label}" if resource else ""
    modifier_text = ""
    if option.situational_modifiers:
        items = ", ".join(
            f"{modifier.label} {modifier.modifier:+d}/{modifier.roll_mode.value}"
            for modifier in option.situational_modifiers
        )
        modifier_text = f"\nModyfikatory sytuacyjne: {items}."
    improvised_text = ""
    if option.improvised_tool is not None:
        tool = option.improvised_tool
        risk = f", ryzyko: {tool.risk}" if tool.risk else ""
        improvised_text = f"\nImprowizowane narzędzie: {tool.label} {tool.effect_modifier:+d} ({tool.source_detail}{risk})."
    roll_mode_text = f"\nTryb rzutu: {option.roll_mode.value}." if option.roll_mode != RollMode.NORMAL else ""
    return (
        f"{proposal.player_narration}\n"
        f"Podejście: {option.label}. Test: {option.ability_check.ability}/{option.ability_check.skill or '-'}, "
        f"ST {option.ability_check.dc}. Sukces: +{option.progress_on_success} postępu, "
        f"porażka: +{option.progress_on_failure} postępu.{resource_text}{roll_mode_text}{modifier_text}{improvised_text}"
    ).strip()


def _npc_proposal_text(proposal: NpcInteractionProposal) -> str:
    if proposal.requires_roll:
        skill = f"/{proposal.skill}" if proposal.skill else ""
        return f"Akcja: {proposal.action_type}. Test: {proposal.ability}{skill}, ST {proposal.dc}."
    return f"Akcja: {proposal.action_type}. Bez rzutu."


def _pending_explanation(pending: PendingInteraction) -> str:
    notes = getattr(pending.proposal, "gm_notes", "")
    if notes:
        return str(notes)
    return "Ta propozycja jest interpretacją deklaracji graczy zwalidowaną przez deterministyczny silnik."


def _check_plan_text(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> str:
    names = ", ".join(actor.name for actor in _actors_for_plan(actors, plan))
    return (
        f"Uczestnicy: {plan.participants.value} ({names}). "
        f"Agregacja: {plan.aggregation.value}. Tryb rzutu: {plan.roll_mode.value}. Konsekwencje: "
        f"{', '.join(target.value for target in plan.consequence_targets)}."
    )


def _zone_payload(zone: ExplorationZone, asset_root: Path | None = None, state: ExplorationState | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": zone.id,
        "name": zone.name,
        "description": zone.description,
        "summary": zone.llm_context.summary,
        "available_materials": list(zone.llm_context.available_materials),
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


def _point_payload(point: ExplorationPoint | None) -> dict[str, object] | None:
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
        }
    return payload


def _challenge_payload(
    state: ExplorationState,
    challenge: ExplorationChallenge | None,
    actors: tuple[Actor, ...] = (),
) -> dict[str, object] | None:
    if challenge is None:
        return None
    challenge_state = challenge_state_for(state, challenge.id)
    options = available_challenge_options_for_actors(state, challenge, actors) if actors else available_challenge_options(state, challenge)
    return {
        "id": challenge.id,
        "name": challenge.name,
        "description": challenge.llm_context.summary,
        "summary": challenge.llm_context.summary,
        "reasonable_approaches": list(challenge.llm_context.reasonable_approaches),
        "risk_notes": list(challenge.llm_context.risk_notes),
        "progress_required": challenge.progress_required,
        "current_progress": challenge_state.current_progress,
        "noise": challenge_state.noise,
        "completed": challenge_state.completed,
        "complications": list(challenge_state.complications),
        "options": [_challenge_option_payload(option, actors) for option in options],
    }


def _exploration_actor_payload(actor: Actor) -> dict[str, object]:
    return {
        "id": str(actor.id),
        "name": actor.name,
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "ability_scores": {
            "strength": actor.ability_scores.strength,
            "dexterity": actor.ability_scores.dexterity,
            "constitution": actor.ability_scores.constitution,
            "intelligence": actor.ability_scores.intelligence,
            "wisdom": actor.ability_scores.wisdom,
            "charisma": actor.ability_scores.charisma,
        },
        "inventory": [inventory_item_payload(item) for item in actor.inventory],
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
            }
            for pool in actor.resource_pools
        ],
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
                "label": "Postęp bramy",
                "value": f"{closed_gate_state.current_progress}/{closed_gate.progress_required}",
            }
        )
        status.append({"label": "Hałas", "value": _noise_label(closed_gate_state.noise)})
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


def _challenge_option_payload(option: ExplorationChallengeOption, actors: tuple[Actor, ...] = ()) -> dict[str, object]:
    eligible_actors = actors_matching_challenge_option(actors, option) if actors else ()
    return {
        "id": option.id,
        "label": option.label,
        "description": option.description,
        "ability": option.ability_check.ability,
        "skill": option.ability_check.skill,
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
