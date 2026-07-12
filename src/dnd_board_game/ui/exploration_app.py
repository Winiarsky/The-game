from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request, send_from_directory

from dnd_board_game.actions import (
    ActionResourceResolver,
    AreaSpellResolver,
    HealingActionResolver,
    SpellSaveAttackResolver,
    action_mechanic_payload,
    attack_mechanic_from_source,
    combat_action_mechanic_from_definition,
    healing_mechanic_from_source,
)
from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActorSetupEntry,
    ActionUse,
    ActiveCombatEffect,
    AttackDeclaration,
    CombatState,
    CombatInteractionOption,
    EncounterSetup,
    InitiativeEntry,
    InitiativeOrder,
    DamageComponentInput,
    DamageType,
    HealingSource,
    InitiativePrompt,
    SpellAreaShape,
    SpellSaveResult,
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
    combat_interaction_hint_positions,
    combat_interaction_positions,
    consume_next_attack_effects,
    current_actor as combat_current_actor,
    expire_turn_end_effects,
    expire_turn_start_effects,
    finish_turn,
    active_actor_led_feedback,
    apply_combat_interaction_effects,
    apply_damage_result,
    actors_in_area,
    area_positions_for_center,
    area_positions_for_direction,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    actor_as_combat_target,
    available_combat_interaction_options,
    available_scene_interactions,
    expire_invalid_combat_effects,
    initiative_prompt_led_feedback,
    movement_remaining,
    legal_healing_targets,
    legal_area_centers,
    can_consume_spell_resource,
    consume_spell_resource,
    direction_anchor_positions,
    opportunity_attackers_for_movement,
    replace_actor,
    resolve_attack,
    resolve_damage,
    resolve_enemy_auto_turn,
    roll_enemy_initiative,
    plan_enemy_turn,
    reaction_available_for,
    scene_flag,
    scene_object_at_position,
    scene_object_by_id,
    select_attack_target,
    setup_led_feedback,
    start_combat,
    start_attack_action,
    use_dash,
    use_actor_reaction,
    use_turn_action,
    use_movement,
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
    PartyCheckInput,
    PendingEncounter,
    active_option_bonuses_for_actor,
    apply_exploration_effect,
    actors_matching_challenge_option,
    available_challenge_options,
    available_exploration_zones,
    available_challenge_options_for_actors,
    challenge_for_zone,
    challenge_state_for,
    exploration_zone_feedback,
    party_position_feedback,
    reveal_exploration_points,
    resolve_challenge_option,
    resolve_exploration_check,
    set_party_zone,
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
from dnd_board_game.hardware import BoardLedAdapter, LedColor, LedFeedback, LedFrame, LedRole, led_color_name_pl, movement_led_feedback
from dnd_board_game.inventory import break_inventory_item, consume_inventory_item, has_inventory_quantity, inventory_item_payload
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollMode, RollModifier, RollModifierType, ability_modifier, resolve_d20_roll, roll_instruction
from dnd_board_game.scenarios import (
    LoadedEncounter,
    LoadedExploration,
    build_encounter_from_scenario,
    build_exploration_from_scenario,
    load_scenario,
)
from dnd_board_game.runtime.session_observer import SessionObserver
from dnd_board_game.world import Coordinate, MovementRangeResult, PathResult, find_path, movement_range


class PendingKind(StrEnum):
    CHALLENGE = "challenge"
    NPC = "npc"


class PendingStage(StrEnum):
    DECISION = "decision"
    ROLL = "roll"
    BREAKAGE = "breakage"


class UiFlowStage(StrEnum):
    WAITING_FOR_BOARD = "waiting_for_board"
    READY_TO_START = "ready_to_start"
    PARTY_SETUP = "party_setup"
    LOCATION_PREVIEW = "location_preview"
    LOCATION_ACTIVE = "location_active"
    INTERACTION_RESULT = "interaction_result"


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
class PendingPlayerAttack:
    attacker_id: str
    target_id: str
    source_id: str = ""
    stage: str = "confirm_attack"
    natural_roll: int | None = None
    natural_rolls: tuple[int, ...] = ()
    total: int | None = None
    hit: bool | None = None
    critical: bool = False
    saving_throws: tuple[SpellSaveResult, ...] = ()


@dataclass(frozen=True, slots=True)
class PendingPlayerHealing:
    healer_id: str
    target_id: str
    source_id: str
    stage: str = "healing_roll"


@dataclass(frozen=True, slots=True)
class PendingAreaSpell:
    caster_id: str
    source_id: str
    origin: Coordinate
    anchor: Coordinate
    area_positions: tuple[Coordinate, ...]
    target_ids: tuple[str, ...]
    stage: str = "confirm_area"
    saving_throws: tuple[SpellSaveResult, ...] = ()


@dataclass(frozen=True, slots=True)
class PendingCombatInteraction:
    actor_id: str
    object_id: str
    object_name: str
    target_position: Coordinate
    options: tuple[CombatInteractionOption, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "target_position": [self.target_position.col, self.target_position.row],
            "options": [option.as_payload() for option in self.options],
        }


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
class PendingConcentrationAction:
    caster_id: str
    action_id: str
    target_ids: tuple[str, ...]

    def as_payload(self, state: CombatState, active_effects: tuple[ActiveCombatEffect, ...], action=None) -> dict[str, object]:
        return {
            "caster": _combat_actor_payload(_actor_by_string_id_from_state(state, self.caster_id), active_effects),
            "action": _combat_action_payload(action) if action is not None else None,
            "targets": [
                _combat_actor_payload(actor, active_effects)
                for actor in state.actors
                if str(actor.id) in self.target_ids
            ],
        }


@dataclass(frozen=True, slots=True)
class PendingConcentrationCheck:
    actor_id: str
    effect_ids: tuple[str, ...]
    damage: int
    dc: int

    def as_payload(self, state: CombatState, active_effects: tuple[ActiveCombatEffect, ...]) -> dict[str, object]:
        actor = _actor_by_string_id_from_state(state, self.actor_id)
        modifier = ability_modifier(actor.ability_scores.constitution)
        effects = tuple(effect for effect in active_effects if effect.id in self.effect_ids)
        return {
            "actor": _combat_actor_payload(actor, active_effects),
            "effect_ids": list(self.effect_ids),
            "effects": [effect.as_payload() for effect in effects],
            "damage": self.damage,
            "dc": self.dc,
            "modifier": modifier,
            "instruction": f"{actor.name} otrzymał {self.damage} obrażeń. Rzuć CON save przeciw ST {self.dc}.",
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
        self.action_resource_resolver = ActionResourceResolver()
        self.spell_save_attack_resolver = SpellSaveAttackResolver()
        self.area_spell_resolver = AreaSpellResolver()
        self.healing_action_resolver = HealingActionResolver()
        self.reset()

    def reset(self) -> None:
        if self._fixed_session_id is None:
            self.observer = SessionObserver(_ui_session_id(), self.observation_dir)
        self.exploration = build_exploration_from_scenario(load_scenario(self.scenario_path))
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
        self.pending: PendingInteraction | None = None
        self.declaration_thread: list[GmDeclarationThreadEntry] = []
        self.active_preparation_effects: list[GmPreparationEffect] = []
        self.selected_lead_actor_id = str(self.exploration.actors[0].id)
        self.active_point_id = self.debug_point_id
        self.pending_encounter: PendingEncounter | None = None
        self.exploration_setup_flow: ExplorationSetupFlow | None = None
        self.post_interaction_setup_steps: tuple[SetupStep, ...] = ()
        self.selected_combat_movement_path = None
        self.encounter_setup_flow: EncounterSetupFlow | None = None
        self.encounter_initiative_flow: EncounterInitiativeFlow | None = None
        self.combat_state: CombatState | None = None
        self.resolved_encounter_trigger_ids: set[str] = set()
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_turn_ack_result = None
        self.pending_player_attack: PendingPlayerAttack | None = None
        self.pending_player_healing: PendingPlayerHealing | None = None
        self.pending_area_spell: PendingAreaSpell | None = None
        self.pending_combat_interaction: PendingCombatInteraction | None = None
        self.pending_combat_help: PendingCombatHelp | None = None
        self.pending_concentration_action: PendingConcentrationAction | None = None
        self.pending_concentration_check: PendingConcentrationCheck | None = None
        self.pending_combat_ready: PendingCombatReady | None = None
        self.pending_opportunity_movement: PendingOpportunityMovement | None = None
        self.pending_enemy_opportunity_attack: PendingEnemyOpportunityAttack | None = None
        self.pending_ready_attack: PendingReadyAttack | None = None
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
        self.board_adapter: BoardLedAdapter | None = None
        self.board_message = (
            "Plansza niepodłączona. Domyślne ustawienia wczytane z board/config.json "
            f"({self.configured_board_backend})."
        )
        self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE if self.debug_point_id else UiFlowStage.WAITING_FOR_BOARD
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
            },
        )

    @property
    def current_zone(self) -> ExplorationZone:
        return next(zone for zone in self.state.zones if zone.id == self.state.party_position.zone_id)

    @property
    def active_point(self) -> ExplorationPoint | None:
        if not self.active_point_id:
            return None
        return next((point for point in self.state.points if point.id == self.active_point_id), None)

    def state_payload(self) -> dict[str, object]:
        self._refresh_pending_encounter()
        self._expire_invalid_combat_effects()
        active_challenge = self.active_challenge if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else None
        current_zone_points = self.current_zone_points() if self.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE else ()
        scene_status = _scene_status_payload(self.state)
        if self.pending_encounter is not None:
            scene_status.append({"label": "Encounter", "value": self.pending_encounter.name})
        preview_zone = self._preview_zone()
        return {
            "scenario": {"id": self.exploration.scenario_id, "name": self.exploration.scenario_name},
            "session_log": {
                "session_id": self.observer.session_id,
                "path": str(self.observer.path),
            },
            "flow": {
                "stage": self.ui_flow_stage.value,
                "can_start": self.ui_flow_stage == UiFlowStage.READY_TO_START,
                "preview_zone": _zone_payload(preview_zone, self._scenario_asset_root(), self.state) if preview_zone else None,
                "available_locations": [_zone_payload(zone, self._scenario_asset_root(), self.state) for zone in self._scene_location_zones()],
                "interaction_result": self.interaction_result,
            },
            "current_zone": _zone_payload(self.current_zone, self._scenario_asset_root()),
            "available_zones": [_zone_payload(zone, self._scenario_asset_root()) for zone in visible_exploration_zones(self.state.zones) if zone_is_ui_available(self.state, zone)],
            "visible_environment": [_environment_entry_payload(entry) for entry in self.exploration.environment if entry.visibility == SetupVisibility.VISIBLE],
            "travel_options": [_zone_payload(zone, self._scenario_asset_root()) for zone in self.travel_options()],
            "visible_points": [_point_payload(point) for point in visible_exploration_points(self.state.points)],
            "current_zone_points": [_point_payload(point) for point in current_zone_points],
            "active_challenge": _challenge_payload(self.state, active_challenge, self.exploration.actors) if active_challenge else None,
            "active_point": _point_payload(self.active_point) if self.active_point else None,
            "resources": [_resource_payload(resource) for resource in self.state.resources if resource.id in self.state.inventory_resource_ids],
            "actors": [_exploration_actor_payload(actor) for actor in self.exploration.actors],
            "scene_status": scene_status,
            "flags": [{"key": key, "value": value} for key, value in self.state.flags.values],
            "messages": [message.as_payload() for message in self.messages],
            "pending": self.pending.as_payload() if self.pending else None,
            "pending_encounter": self._pending_encounter_payload(),
            "exploration_setup": self.exploration_setup_flow.as_payload() if self.exploration_setup_flow else None,
            "encounter_setup": self.encounter_setup_flow.as_payload() if self.encounter_setup_flow else None,
            "encounter_initiative": (
                self.encounter_initiative_flow.as_payload() if self.encounter_initiative_flow else None
            ),
            "combat": _combat_payload(
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
            "board": self._board_payload(),
            "required_rolls": self.required_rolls_payload(),
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
            if not self.debug_point_id:
                self.ui_flow_stage = UiFlowStage.WAITING_FOR_BOARD
            self._record("ui_board_configured", {"backend": backend, "connected": False})
            return self.state_payload()
        from board.connection import Connection

        if backend == "simulator":
            connection = Connection(backend="simulator", simulator_url=self.board_url)
        else:
            connection = Connection(backend="hardware", serial_port=self.board_serial_port or None, wled_url=self.wled_url or None)
        self.attach_board_connection(connection, backend=backend)
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
        self.board_adapter = BoardLedAdapter(connection)  # type: ignore[arg-type]
        self.board_message = f"Plansza podłączona: {backend}."
        if backend in {"simulator", "hardware"} and self.ui_flow_stage == UiFlowStage.WAITING_FOR_BOARD:
            self.ui_flow_stage = UiFlowStage.READY_TO_START

    def start_session(self) -> dict[str, object]:
        if self.board_adapter is None or self.board_backend not in {"simulator", "hardware"}:
            raise ValueError("Najpierw wybierz i zastosuj backend planszy: symulator albo hardware.")
        if self.ui_flow_stage not in {UiFlowStage.READY_TO_START, UiFlowStage.WAITING_FOR_BOARD}:
            return self.state_payload()
        setup_steps = _build_exploration_setup_steps(self.exploration.environment)
        if setup_steps:
            self.exploration_setup_flow = ExplorationSetupFlow(setup_steps)
            self.ui_flow_stage = UiFlowStage.PARTY_SETUP
            self.board_message = "Najpierw rozstaw widoczne elementy mapy i potwierdź kroki setupu."
        else:
            self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
            self.board_message = "Wybierz jawny element sceny na planszy."
        self.preview_zone_id = ""
        self.pending = None
        self.active_point_id = ""
        self._sync_board_leds()
        self._record("ui_play_session_started", {"stage": self.ui_flow_stage.value, "board_backend": self.board_backend})
        return self.state_payload()

    def finish_interaction_result(self) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.INTERACTION_RESULT:
            return self.state_payload()
        self.interaction_result = None
        self.preview_zone_id = ""
        if self.post_interaction_setup_steps:
            self.exploration_setup_flow = ExplorationSetupFlow(self.post_interaction_setup_steps)
            self.post_interaction_setup_steps = ()
            self.ui_flow_stage = UiFlowStage.PARTY_SETUP
            self.board_message = "Rozstaw nowy element mapy wynikający z interakcji."
            self._sync_board_leds()
            return self.state_payload()
        self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
        self.board_message = "Wybierz kolejną dostępną lokację na planszy."
        self._sync_board_leds()
        return self.state_payload()

    def cancel_location_preview(self) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_PREVIEW:
            return self.state_payload()
        self.preview_zone_id = ""
        self.board_message = "Wrócono do wyboru dostępnych lokacji."
        self._sync_board_leds()
        return self.state_payload()

    def confirm_location_preview(self) -> dict[str, object]:
        if self.ui_flow_stage != UiFlowStage.LOCATION_PREVIEW:
            return self.state_payload()
        zone = self._preview_zone()
        if zone is None:
            raise ValueError("Najpierw wybierz element sceny na planszy.")
        if not zone_is_ui_available(self.state, zone):
            raise ValueError(_locked_zone_message(zone))
        if zone.id != self.current_zone.id:
            self.state = set_party_zone(self.state, zone)
            self.active_point_id = ""
        self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        self.preview_zone_id = ""
        self.board_message = f"Drużyna wchodzi do lokacji: {zone.name}."
        self._record("ui_location_preview_confirmed", {"zone_id": zone.id})
        self._sync_board_leds()
        return self.state_payload()

    def confirm_exploration_setup_step(self) -> dict[str, object]:
        if self.exploration_setup_flow is None:
            return self.state_payload()
        flow = self.exploration_setup_flow
        step = flow.current_step
        if step is None:
            return self.state_payload()
        self._add_message("Setup mapy", f"Potwierdzono: {step.label}.")
        if flow.current_index + 1 >= len(flow.steps):
            flow.completed = True
            self.exploration_setup_flow = None
            self.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
            self.preview_zone_id = ""
            self.board_message = "Elementy mapy ustawione. Wybierz jawny element sceny na planszy."
            self._refresh_pending_encounter()
            if self.pending_encounter is not None:
                self.board_message = "Encounter gotowy. Potwierdź rozpoczęcie setupu w UI albo Enterem."
        else:
            flow.current_index += 1
            self.board_message = "Potwierdź kolejny element mapy."
        self._sync_board_leds()
        return self.state_payload()

    def scan_board_selection(self) -> dict[str, object]:
        if self.board_adapter is None:
            raise ValueError("Najpierw podłącz backend planszy.")
        target = self._current_board_scan_target()
        if not target.positions:
            raise ValueError(target.empty_message)
        self._show_board_feedback(target.feedback)
        scan_board = getattr(self.board_adapter.connection, "scan_board", None)
        if not callable(scan_board):
            raise ValueError("Aktualny backend planszy nie obsługuje scan_board.")
        selected_raw = scan_board([position.as_tuple() for position in target.positions], timeout_s=self.scan_timeout_s)
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
        destination = next((zone for zone in self.travel_options() if zone.id == zone_id), None)
        if destination is None:
            raise ValueError("Ta lokacja nie jest teraz dostępna.")
        previous = self.current_zone
        self.state = set_party_zone(self.state, destination)
        self.pending = None
        self.active_point_id = ""
        self.preview_zone_id = ""
        self.interaction_result = None
        self.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        self._add_message("Przejście", f"Drużyna przechodzi z {previous.name} do lokacji: {destination.name}.")
        self._record("ui_zone_traveled", {"from_zone_id": previous.id, "to_zone_id": destination.id})
        self._sync_board_leds()
        return self.state_payload()

    def start_encounter_setup(self) -> dict[str, object]:
        self._refresh_pending_encounter()
        if self.pending_encounter is None:
            raise ValueError("Nie ma aktywnego encountera do przygotowania.")
        encounter = build_encounter_from_scenario(load_scenario(self.pending_encounter.encounter_scenario))
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
        self.pending_player_attack = None
        self.pending_player_healing = None
        self.pending_area_spell = None
        self.pending_combat_interaction = None
        self.pending_combat_help = None
        self.pending_concentration_action = None
        self.pending_combat_ready = None
        self.pending_opportunity_movement = None

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
        if getattr(source, "prepared", True) is False:
            return False
        return can_consume_spell_resource(actor, getattr(source, "spell_level", 0))

    def _actor_can_use_healing_source(self, actor: Actor, source: HealingSource | None) -> bool:
        if source is None:
            return False
        if getattr(source, "prepared", True) is False:
            return False
        return can_consume_spell_resource(actor, getattr(source, "spell_level", 0))

    def _actor_can_use_combat_action(self, actor: Actor, action) -> bool:
        if action is None:
            return False
        if getattr(action, "prepared", True) is False:
            return False
        return can_consume_spell_resource(actor, getattr(action, "spell_level", 0))

    def _concentration_targets_for_action(self, actor: Actor, action) -> tuple[Actor, ...]:
        if self.combat_state is None:
            return ()
        if getattr(action, "target_faction", "self") == "ally":
            return tuple(
                candidate
                for candidate in self.combat_state.actors
                if candidate.faction == actor.faction and not candidate.is_defeated()
            )
        return (actor,)

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
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        sources = self._attack_sources_for_actor(actor)
        source = next((candidate for candidate in sources if candidate.id == source_id), None)
        if source is None:
            raise ValueError("Nieznane źródło ataku.")
        if not self._actor_can_use_attack_source(actor, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        self._clear_player_pending_choices()
        self.selected_attack_source_ids[str(actor.id)] = source.id
        self.board_message = f"Wybrano źródło ataku: {source.name}. Kliknij Skanuj planszę i wskaż legalny czerwony cel."
        self._add_message("Atak", f"{actor.name} wybiera: {source.name}.")
        self._record("ui_combat_attack_source_selected", {"actor_id": str(actor.id), "source_id": source.id})
        self._sync_board_leds()
        return self.state_payload()

    def select_combat_healing_source(self, source_id: str) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        sources = self._healing_sources_for_actor(actor)
        source = next((candidate for candidate in sources if candidate.id == source_id), None)
        if source is None:
            raise ValueError("Nieznane źródło leczenia.")
        if not self._actor_can_use_healing_source(actor, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        self._clear_player_pending_choices()
        self.selected_healing_source_ids[str(actor.id)] = source.id
        self.board_message = f"Wybrano leczenie: {source.name}. Kliknij Skanuj planszę i wskaż rannego sojusznika."
        self._add_message("Leczenie", f"{actor.name} wybiera: {source.name}.")
        self._record("ui_combat_healing_source_selected", {"actor_id": str(actor.id), "source_id": source.id})
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
        if action is None or action.action_type != "strength_potion":
            raise ValueError("Nieznana akcja eliksiru.")
        if action.source_item_id is not None and not has_inventory_quantity(actor, action.source_item_id):
            raise ValueError("Ten przedmiot został już zużyty.")
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        self.combat_state = action_result.state
        actor_after_action = combat_current_actor(self.combat_state)
        if action.source_item_id is not None:
            actor_after_action = consume_inventory_item(actor_after_action, action.source_item_id)
            self.combat_state = replace_actor(self.combat_state, actor_after_action)
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.actor_id == str(actor_after_action.id) and effect.kind == "strength_potion")
        ) + (
            ActiveCombatEffect(
                id=f"strength_potion:{actor_after_action.id}:{action.id}",
                actor_id=str(actor_after_action.id),
                kind="strength_potion",
                label=action.label,
                object_id=f"combat_action:{action.id}",
                value=action.value,
            ),
        )
        self._clear_player_pending_choices()
        self.board_message = f"{actor_after_action.name} wypija {action.label}. Ataki i obrażenia z Siły mają {action.value:+d} do następnej tury."
        self._add_message("Eliksir", self.board_message)
        self._record(
            "ui_combat_strength_potion_used",
            {"actor_id": str(actor_after_action.id), "action_id": action.id, "source_item_id": action.source_item_id, "value": action.value},
        )
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
        if action is None or action.action_type != "concentration_attack_bonus":
            raise ValueError("Nieznana akcja koncentracji.")
        if not self._actor_can_use_combat_action(actor, action):
            raise ValueError(f"Brak slotów czaru dla {action.label}.")
        targets = self._concentration_targets_for_action(actor, action)
        if not targets:
            raise ValueError("Brak legalnego celu czaru koncentracyjnego.")
        self._clear_player_pending_choices()
        self.pending_concentration_action = PendingConcentrationAction(
            caster_id=str(actor.id),
            action_id=action.id,
            target_ids=tuple(str(target.id) for target in targets),
        )
        self.board_message = f"{action.label}: wybierz sojusznika dla efektu koncentracji."
        self._add_message("Koncentracja", f"{actor.name} przygotowuje {action.label}. Wybierz sojusznika.")
        self._record(
            "ui_combat_concentration_started",
            {"caster_id": str(actor.id), "action_id": action.id, "target_ids": [str(target.id) for target in targets]},
        )
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_concentration_action(self, *, target_id: str) -> dict[str, object]:
        pending = self.pending_concentration_action
        if pending is None:
            raise ValueError("Nie ma czaru koncentracyjnego do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        if str(caster.id) != pending.caster_id:
            raise ValueError("Oczekujący czar koncentracyjny nie należy do aktywnego aktora.")
        if target_id not in pending.target_ids:
            raise ValueError("Wybrany cel nie jest legalnym celem czaru koncentracyjnego.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        action = next(
            (candidate for candidate in encounter.combat_actions_by_actor.get(caster.id, ()) if candidate.id == pending.action_id),
            None,
        )
        if action is None:
            raise ValueError("Nieznana akcja koncentracji.")
        if not self._actor_can_use_combat_action(caster, action):
            raise ValueError(f"Brak slotów czaru dla {action.label}.")
        target = _actor_by_string_id_from_state(self.combat_state, target_id)
        resource_use = self.action_resource_resolver.consume_action_and_source_resource(
            self.combat_state,
            caster,
            spell_level=action.spell_level,
        )
        self.combat_state = resource_use.state
        removed = tuple(
            effect
            for effect in self.active_combat_effects
            if effect.kind.startswith("concentration_") and effect.source_actor_id == str(caster.id)
        )
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.kind.startswith("concentration_") and effect.source_actor_id == str(caster.id))
        ) + (
            ActiveCombatEffect(
                id=f"concentration_attack_bonus:{caster.id}:{target.id}:{action.id}",
                actor_id=str(target.id),
                kind="concentration_attack_bonus",
                label=action.label,
                object_id=f"combat_action:{action.id}",
                value=action.value,
                source_actor_id=str(caster.id),
                target_actor_id=str(target.id),
            ),
        )
        self.pending_concentration_action = None
        self.selected_combat_movement_path = None
        ended = f" Poprzednia koncentracja zakończona: {', '.join(effect.label for effect in removed)}." if removed else ""
        message = f"{caster.name} rzuca {action.label}. {target.name} ma {action.value:+d} do ataku, dopóki koncentracja trwa.{ended}"
        self.board_message = message
        self._add_message("Koncentracja", message)
        self._record(
            "ui_combat_concentration_confirmed",
            {
                "caster_id": str(caster.id),
                "target_id": str(target.id),
                "action_id": action.id,
                "value": action.value,
                "removed_effect_ids": [effect.id for effect in removed],
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_concentration_action(self) -> dict[str, object]:
        pending = self.pending_concentration_action
        if pending is None:
            raise ValueError("Nie ma czaru koncentracyjnego do anulowania.")
        self.pending_concentration_action = None
        self.board_message = "Anulowano czar koncentracyjny. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
        self._add_message("Koncentracja", "Anulowano czar koncentracyjny.")
        self._record("ui_combat_concentration_cancelled", {"caster_id": pending.caster_id, "action_id": pending.action_id})
        self._sync_board_leds()
        return self.state_payload()

    def _concentration_effects_for_actor(self, actor_id: str) -> tuple[ActiveCombatEffect, ...]:
        return tuple(
            effect
            for effect in self.active_combat_effects
            if effect.kind.startswith("concentration_") and effect.source_actor_id == actor_id
        )

    def _remove_concentration_effects_for_actor(self, actor_id: str) -> tuple[ActiveCombatEffect, ...]:
        removed = self._concentration_effects_for_actor(actor_id)
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.kind.startswith("concentration_") and effect.source_actor_id == actor_id)
        )
        return removed

    def _maybe_prompt_concentration_check(self, applied_damage) -> None:
        if self.combat_state is None or applied_damage is None:
            return
        damage = int(getattr(applied_damage.damage, "total_applied", 0) or 0)
        if damage <= 0:
            return
        actor_id = str(applied_damage.actor_after.id)
        effects = self._concentration_effects_for_actor(actor_id)
        if not effects:
            return
        actor = self._actor_by_string_id(actor_id)
        if actor.is_defeated():
            removed = self._remove_concentration_effects_for_actor(actor_id)
            self._add_message("Koncentracja", f"{actor.name} pada. Koncentracja zakończona: {', '.join(effect.label for effect in removed)}.")
            return
        dc = max(10, damage // 2)
        if actor.faction != Faction.ALLY:
            natural_roll = self.encounter_rng.randint(1, 20)
            self._resolve_concentration_check(actor_id=actor_id, effect_ids=tuple(effect.id for effect in effects), damage=damage, dc=dc, natural_roll=natural_roll)
            return
        self.pending_concentration_check = PendingConcentrationCheck(
            actor_id=actor_id,
            effect_ids=tuple(effect.id for effect in effects),
            damage=damage,
            dc=dc,
        )
        self.board_message = f"{actor.name}: rzut na utrzymanie koncentracji, ST {dc}."
        self._add_message("Koncentracja", f"{actor.name} otrzymuje {damage} obrażeń. Rzuć CON save przeciw ST {dc}.")

    def submit_concentration_check(self, *, natural_roll: int) -> dict[str, object]:
        pending = self.pending_concentration_check
        if pending is None:
            raise ValueError("Nie ma oczekującego rzutu na koncentrację.")
        self._resolve_concentration_check(
            actor_id=pending.actor_id,
            effect_ids=pending.effect_ids,
            damage=pending.damage,
            dc=pending.dc,
            natural_roll=int(natural_roll),
        )
        self.pending_concentration_check = None
        self._sync_board_leds()
        return self.state_payload()

    def _resolve_concentration_check(
        self,
        *,
        actor_id: str,
        effect_ids: tuple[str, ...],
        damage: int,
        dc: int,
        natural_roll: int,
    ) -> None:
        actor = self._actor_by_string_id(actor_id)
        modifier = ability_modifier(actor.ability_scores.constitution)
        request = D20RollRequest(
            modifiers=(
                RollModifier(
                    "Modyfikator Kondycji",
                    modifier,
                    RollModifierType.ABILITY,
                    stacking_key="ability:constitution",
                ),
            )
        )
        roll = resolve_d20_roll(D20RollInput(request, int(natural_roll)))
        success = roll.total >= int(dc)
        effect_labels = tuple(
            effect.label
            for effect in self.active_combat_effects
            if effect.id in effect_ids
        )
        removed_effect_ids: list[str] = []
        if not success:
            removed = self._remove_concentration_effects_for_actor(actor_id)
            removed_effect_ids = [effect.id for effect in removed if effect.id in effect_ids]
        result_text = "koncentracja utrzymana" if success else f"koncentracja przerwana: {', '.join(effect_labels) or 'efekt'}"
        self.board_message = f"{actor.name}: CON save {roll.natural_roll} + {modifier} = {roll.total} / ST {dc}; {result_text}."
        self._add_message("Koncentracja", self.board_message)
        self._record(
            "ui_combat_concentration_check",
            {
                "actor_id": actor_id,
                "effect_ids": list(effect_ids),
                "removed_effect_ids": removed_effect_ids,
                "damage": damage,
                "dc": dc,
                "natural_roll": roll.natural_roll,
                "modifier": modifier,
                "total": roll.total,
                "success": success,
            },
        )

    def submit_player_attack(self, *, target_id: str, natural_roll: int, damage: int = 0, natural_roll_2: int | None = None) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        if attacker.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        source = self._selected_attack_source(attacker)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        if not self._actor_can_use_attack_source(attacker, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=target_id)
        assert selected.selected_target is not None
        target_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == selected.selected_target.id), None)
        if target_actor is None:
            raise ValueError(f"Nieznany cel ataku: {selected.selected_target.id}.")
        source = self._effective_attack_source(attacker, source, target_actor)
        declaration = AttackDeclaration(attacker=attacker, target=selected.selected_target, source=source)
        attack_roll = resolve_d20_roll(_manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2))
        resource_use = self.action_resource_resolver.consume_action_and_source_resource(
            self.combat_state,
            attacker,
            spell_level=source.spell_level,
        )
        self.combat_state = resource_use.state
        resolution = resolve_attack(declaration, attack_roll, selected.action_use)
        self.active_combat_effects = consume_next_attack_effects(
            self.active_combat_effects,
            str(attacker.id),
            selected.selected_target.id,
        )
        updated_state = self.combat_state
        message = _player_attack_message(attacker.name, selected.selected_target.name, attack_roll.total, resolution.hit, resolution.critical)
        applied_damage = None
        if resolution.hit:
            damage_amount = max(0, int(damage))
            damage_result = resolve_damage((DamageComponentInput(damage_amount, DamageType(source.damage_type), source.name),))
            target_actor = next((actor for actor in updated_state.actors if str(actor.id) == selected.selected_target.id), target_actor)
            applied_damage = apply_damage_result(target_actor, damage_result)
            updated_target = applied_damage.actor_after
            updated_state = replace_actor(updated_state, updated_target)
            message = f"{message} {_damage_application_message(applied_damage)}"
        self.combat_state = updated_state
        self.pending_player_attack = None
        self.pending_combat_help = None
        self.selected_combat_movement_path = None
        self._add_message("Atak", message)
        self._record(
            "ui_combat_player_attack",
            {
                "attacker_id": str(attacker.id),
                "target_id": selected.selected_target.id,
                "natural_roll": attack_roll.natural_roll,
                "natural_rolls": list(attack_roll.natural_rolls),
                "total": attack_roll.total,
                "hit": resolution.hit,
                "critical": resolution.critical,
                "damage": int(damage) if resolution.hit else 0,
                "target_ac": selected.selected_target.ac,
                "damage_result": _applied_damage_payload(applied_damage),
            },
        )
        if applied_damage is not None:
            self._maybe_prompt_concentration_check(applied_damage)
        self._sync_board_leds()
        return self.state_payload()

    def select_player_area_spell_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        caster = combat_current_actor(self.combat_state)
        if caster.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        source = self._selected_attack_source(caster)
        if source is None or source.area is None:
            raise ValueError("Wybrane źródło ataku nie jest czarem obszarowym.")
        if not self._actor_can_use_attack_source(caster, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        if source.area.shape == SpellAreaShape.RADIUS:
            centers = legal_area_centers(encounter.board, caster.position, source.range_feet)
            if position not in centers:
                raise ValueError("Wybrane pole nie jest legalnym środkiem obszaru czaru.")
            area_positions = area_positions_for_center(encounter.board, position, source.area)
            anchor = position
        else:
            anchors = direction_anchor_positions(encounter.board, caster.position)
            if position not in anchors:
                raise ValueError("Kliknij sąsiednie pole, żeby wybrać kierunek czaru.")
            area_positions = area_positions_for_direction(encounter.board, caster.position, position, source.area)
            anchor = position
        targets = actors_in_area(self.combat_state.actors, area_positions, caster)
        self.pending_area_spell = PendingAreaSpell(
            caster_id=str(caster.id),
            source_id=source.id,
            origin=caster.position,
            anchor=anchor,
            area_positions=area_positions,
            target_ids=tuple(str(target.id) for target in targets),
        )
        self.pending_player_attack = None
        self.pending_player_healing = None
        self.pending_combat_help = None
        target_names = ", ".join(target.name for target in targets) or "brak celów"
        self.board_message = f"{source.name}: podgląd obszaru gotowy. Cele: {target_names}. Potwierdź Enterem albo przyciskiem."
        self._add_message("Czar obszarowy", f"{caster.name} wyznacza obszar {source.name}. Cele w obszarze: {target_names}.")
        self._record(
            "ui_combat_area_spell_selected",
            {
                "caster_id": str(caster.id),
                "source_id": source.id,
                "anchor": [anchor.col, anchor.row],
                "area_positions": [[tile.col, tile.row] for tile in area_positions],
                "target_ids": [str(target.id) for target in targets],
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def confirm_player_area_spell(self) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None or pending.stage != "confirm_area":
            raise ValueError("Nie ma czaru obszarowego do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        if str(caster.id) != pending.caster_id:
            raise ValueError("Oczekujący czar nie należy do aktywnego aktora.")
        source = self._attack_source_by_id(caster, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {caster.name} nie ma tego czaru.")
        if not self._actor_can_use_attack_source(caster, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        confirmation = self.area_spell_resolver.confirm_area_spell(
            self.combat_state,
            caster=caster,
            source=source,
            target_ids=pending.target_ids,
            rng=self.encounter_rng,
        )
        self.combat_state = confirmation.state
        saves = confirmation.saving_throws
        self.pending_area_spell = replace(pending, stage="damage_roll", saving_throws=saves)
        self.selected_combat_movement_path = None
        save_text = " ".join(_spell_save_message(save) for save in saves)
        self.board_message = (
            f"{source.name} potwierdzony. Rzuć obrażenia {source.damage_hint}; "
            f"sukces save oznacza {_save_damage_on_success_label(source.save_damage_on_success)}."
        )
        self._add_message(
            "Czar obszarowy",
            f"{caster.name} rzuca {source.name}. {save_text} Rzuć obrażenia {source.damage_hint}.",
        )
        self._record(
            "ui_combat_area_spell_confirmed",
            {"caster_id": str(caster.id), "source_id": source.id, "saving_throws": [save.as_payload() for save in saves]},
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_player_area_spell_damage(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekujących obrażeń czaru obszarowego.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        caster = combat_current_actor(self.combat_state)
        if str(caster.id) != pending.caster_id:
            raise ValueError("Oczekujące obrażenia czaru nie należą do aktywnego aktora.")
        source = self._attack_source_by_id(caster, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {caster.name} nie ma tego czaru.")
        damage_amount = max(0, int(damage))
        resolution = self.area_spell_resolver.apply_area_damage(
            self.combat_state,
            source=source,
            target_ids=pending.target_ids,
            base_damage=damage_amount,
            saving_throws=pending.saving_throws,
        )
        applied_results = [(target.applied_damage, target.saving_throw) for target in resolution.targets]
        self.combat_state = resolution.state
        self.pending_area_spell = None
        if applied_results:
            result_text = "; ".join(
                f"{applied.actor_before.name}: HP {applied.hp_before} -> {applied.hp_after}"
                for applied, _save in applied_results
            )
        else:
            result_text = "brak trafionych celów."
        self._add_message("Obrażenia obszarowe", f"{caster.name} kończy {source.name}: {result_text}")
        self._record(
            "ui_combat_area_spell_damage",
            {
                "caster_id": str(caster.id),
                "source_id": source.id,
                "base_damage": damage_amount,
                "targets": [
                    {"damage_result": _applied_damage_payload(applied), "saving_throw": save.as_payload() if save is not None else None}
                    for applied, save in applied_results
                ],
            },
        )
        for applied, _save in applied_results:
            self._maybe_prompt_concentration_check(applied)
            if self.pending_concentration_check is not None:
                break
        self._sync_board_leds()
        return self.state_payload()

    def cancel_player_area_spell(self) -> dict[str, object]:
        pending = self.pending_area_spell
        if pending is None:
            raise ValueError("Nie ma czaru obszarowego do anulowania.")
        self.pending_area_spell = None
        self.board_message = "Anulowano czar obszarowy. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo akcję."
        self._add_message("Czar obszarowy", "Anulowano czar obszarowy.")
        self._record("ui_combat_area_spell_cancelled", {"caster_id": pending.caster_id, "source_id": pending.source_id})
        self._sync_board_leds()
        return self.state_payload()

    def select_player_attack_target_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        if attacker.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        source = self._selected_attack_source(attacker)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        if not self._actor_can_use_attack_source(attacker, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, position=position)
        assert selected.selected_target is not None
        self.pending_player_attack = PendingPlayerAttack(
            attacker_id=str(attacker.id),
            target_id=selected.selected_target.id,
            source_id=source.id,
        )
        self.pending_combat_help = None
        self.board_message = f"Wybrano cel ataku: {selected.selected_target.name}. Potwierdź atak Enterem albo przyciskiem."
        self._add_message(
            "Podgląd ataku",
            f"{attacker.name} celuje w {selected.selected_target.name}. Sprawdź warunki ataku i potwierdź przed rzutem.",
        )
        self._record(
            "ui_combat_player_attack_target_selected",
            {"attacker_id": str(attacker.id), "target_id": selected.selected_target.id},
        )
        self._sync_board_leds()
        return self.state_payload()

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
        if str(attacker.id) != pending.attacker_id:
            raise ValueError("Oczekujący atak nie należy do aktywnego aktora.")
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=pending.target_id)
        assert selected.selected_target is not None
        target_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == selected.selected_target.id), None)
        if target_actor is None:
            raise ValueError(f"Nieznany cel ataku: {selected.selected_target.id}.")
        source = self._effective_attack_source(attacker, source, target_actor)
        if source.save_ability:
            if not self._actor_can_use_attack_source(attacker, source):
                raise ValueError(f"Brak slotów czaru dla {source.name}.")
            confirmation = self.spell_save_attack_resolver.confirm_target_save_spell(
                self.combat_state,
                caster=attacker,
                target=target_actor,
                source=source,
                rng=self.encounter_rng,
            )
            self.combat_state = confirmation.state
            save = confirmation.saving_throw
            self.selected_combat_movement_path = None
            save_text = _spell_save_message(save)
            if save.damage_multiplier <= 0:
                self.pending_player_attack = None
                self.pending_combat_help = None
                self.board_message = f"{source.name}: {save.actor_name} zdaje rzut obronny. Brak obrażeń."
                self._add_message("Czar", f"{attacker.name} rzuca {source.name}. {save_text} Sukces: brak obrażeń.")
                self._record(
                    "ui_combat_player_save_spell_resolved",
                    {
                        "attacker_id": str(attacker.id),
                        "target_id": selected.selected_target.id,
                        "source_id": source.id,
                        "saving_throw": save.as_payload(),
                        "damage_required": False,
                    },
                )
                self._sync_board_leds()
                return self.state_payload()
            self.pending_player_attack = replace(pending, stage="damage_roll", saving_throws=(save,), hit=True)
            self.board_message = f"{source.name}: {save.actor_name} nie zdaje rzutu obronnego. Wpisz obrażenia."
            self._add_message("Czar", f"{attacker.name} rzuca {source.name}. {save_text} Wpisz obrażenia {source.damage_hint}.")
            self._record(
                "ui_combat_player_save_spell_confirmed",
                {
                    "attacker_id": str(attacker.id),
                    "target_id": selected.selected_target.id,
                    "source_id": source.id,
                    "saving_throw": save.as_payload(),
                    "damage_required": True,
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        self.pending_player_attack = replace(pending, stage="attack_roll")
        instruction = roll_instruction(source.attack_roll_request)
        self.board_message = f"Potwierdzono atak: {attacker.name} -> {selected.selected_target.name}. Wpisz rzut d20 w panelu walki."
        self._add_message(
            "Atak",
            f"{attacker.name} atakuje {selected.selected_target.name}. {instruction.message}",
        )
        self._record(
            "ui_combat_player_attack_target_confirmed",
            {"attacker_id": str(attacker.id), "target_id": selected.selected_target.id},
        )
        self._sync_board_leds()
        return self.state_payload()

    def cancel_player_attack_target(self) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage not in {"confirm_attack", "attack_roll"}:
            raise ValueError("Nie ma wyboru celu ataku do anulowania.")
        self.pending_player_attack = None
        self.board_message = "Anulowano wybór celu ataku. Kliknij Skanuj planszę, żeby wybrać ruch albo cel."
        self._add_message("Atak", "Anulowano wybór celu ataku.")
        self._record(
            "ui_combat_player_attack_target_cancelled",
            {"attacker_id": pending.attacker_id, "target_id": pending.target_id},
        )
        self._sync_board_leds()
        return self.state_payload()

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
        if str(attacker.id) != pending.attacker_id:
            raise ValueError("Oczekujący atak nie należy do aktywnego aktora.")
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=pending.target_id)
        assert selected.selected_target is not None
        target_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == selected.selected_target.id), None)
        if target_actor is None:
            raise ValueError(f"Nieznany cel ataku: {selected.selected_target.id}.")
        source = self._effective_attack_source(attacker, source, target_actor)
        declaration = AttackDeclaration(attacker=attacker, target=selected.selected_target, source=source)
        attack_roll = resolve_d20_roll(_manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2))
        resource_use = self.action_resource_resolver.consume_action_and_source_resource(
            self.combat_state,
            attacker,
            spell_level=source.spell_level,
        )
        self.combat_state = resource_use.state
        resolution = resolve_attack(declaration, attack_roll, selected.action_use)
        self.active_combat_effects = consume_next_attack_effects(
            self.active_combat_effects,
            str(attacker.id),
            selected.selected_target.id,
        )
        self.selected_combat_movement_path = None
        message = _player_attack_message(attacker.name, selected.selected_target.name, attack_roll.total, resolution.hit, resolution.critical)
        if not resolution.hit:
            self.pending_player_attack = None
            self.pending_combat_help = None
            self._add_message("Atak", message)
            self._record(
                "ui_combat_player_attack_roll",
                {
                    "attacker_id": str(attacker.id),
                    "target_id": selected.selected_target.id,
                    "natural_roll": attack_roll.natural_roll,
                    "natural_rolls": list(attack_roll.natural_rolls),
                    "total": attack_roll.total,
                    "hit": False,
                    "critical": resolution.critical,
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        self.pending_player_attack = replace(
            pending,
            stage="damage_roll",
            natural_roll=attack_roll.natural_roll,
            natural_rolls=attack_roll.natural_rolls,
            total=attack_roll.total,
            hit=True,
            critical=resolution.critical,
        )
        self._add_message("Atak", f"{message} Trafienie: rzuć obrażenia {source.damage_hint} i wpisz sumę.")
        self._record(
            "ui_combat_player_attack_roll",
            {
                "attacker_id": str(attacker.id),
                "target_id": selected.selected_target.id,
                "natural_roll": attack_roll.natural_roll,
                "natural_rolls": list(attack_roll.natural_rolls),
                "total": attack_roll.total,
                "hit": True,
                "critical": resolution.critical,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_player_damage_roll(self, *, damage: int) -> dict[str, object]:
        pending = self.pending_player_attack
        if pending is None or pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekującego rzutu obrażeń gracza.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        attacker = combat_current_actor(self.combat_state)
        if str(attacker.id) != pending.attacker_id:
            raise ValueError("Oczekujące obrażenia nie należą do aktywnego aktora.")
        source = self._attack_source_by_id(attacker, pending.source_id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = self._effective_attack_source(attacker, source)
        target_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == pending.target_id), None)
        if target_actor is None:
            raise ValueError(f"Nieznany cel ataku: {pending.target_id}.")
        damage_amount = max(0, int(damage))
        save = pending.saving_throws[0] if pending.saving_throws else None
        damage_resolution = self.spell_save_attack_resolver.apply_target_damage(
            self.combat_state,
            target_id=pending.target_id,
            source=source,
            base_damage=damage_amount,
            saving_throw=save,
        )
        applied_damage = damage_resolution.applied_damage
        damage_result = applied_damage.damage
        self.combat_state = damage_resolution.state
        self.pending_player_attack = None
        self.pending_combat_help = None
        self._add_message(
            "Obrażenia",
            f"{attacker.name} zadaje obrażenia. {_damage_application_message(applied_damage)}",
        )
        self._record(
            "ui_combat_player_damage_roll",
            {
                "attacker_id": str(attacker.id),
                "target_id": str(target_actor.id),
                "base_damage": damage_amount,
                "damage": damage_result.total_applied,
                "saving_throw": save.as_payload() if save is not None else None,
                "damage_result": _applied_damage_payload(applied_damage),
            },
        )
        self._maybe_prompt_concentration_check(applied_damage)
        self._sync_board_leds()
        return self.state_payload()

    def select_player_healing_target_at_position(self, position: Coordinate) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        healer = combat_current_actor(self.combat_state)
        if healer.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        source = self._selected_healing_source(healer)
        if source is None:
            raise ValueError(f"Aktor {healer.name} nie ma zdefiniowanego leczenia.")
        targets = legal_healing_targets(encounter.board, healer, self.combat_state.actors, source)
        target = next((candidate for candidate in targets if candidate.position == position), None)
        if target is None:
            raise ValueError("Wybrane pole nie jest legalnym celem leczenia.")
        self.pending_player_healing = PendingPlayerHealing(
            healer_id=str(healer.id),
            target_id=target.id,
            source_id=source.id,
        )
        self.pending_player_attack = None
        self.pending_combat_help = None
        self.board_message = f"Wybrano leczenie: {source.name} -> {target.name}. Wpisz wynik leczenia."
        self._add_message("Leczenie", f"{healer.name} leczy {target.name}. Rzuć {source.healing_hint} i wpisz sumę.")
        self._record(
            "ui_combat_player_healing_target_selected",
            {"healer_id": str(healer.id), "target_id": target.id, "source_id": source.id},
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_player_healing_roll(self, *, healing: int) -> dict[str, object]:
        pending = self.pending_player_healing
        if pending is None or pending.stage != "healing_roll":
            raise ValueError("Nie ma oczekującego rzutu leczenia gracza.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        healer = combat_current_actor(self.combat_state)
        if str(healer.id) != pending.healer_id:
            raise ValueError("Oczekujące leczenie nie należy do aktywnego aktora.")
        source = next((candidate for candidate in self._healing_sources_for_actor(healer) if candidate.id == pending.source_id), None)
        if source is None:
            raise ValueError(f"Aktor {healer.name} nie ma tego źródła leczenia.")
        if not self._actor_can_use_healing_source(healer, source):
            raise ValueError(f"Brak slotów czaru dla {source.name}.")
        healing_resolution = self.healing_action_resolver.apply_healing(
            self.combat_state,
            healer=healer,
            target_id=pending.target_id,
            source=source,
            amount=int(healing),
        )
        applied = healing_resolution.applied_healing
        target_actor = applied.actor_before
        self.combat_state = healing_resolution.state
        self.pending_player_healing = None
        self._add_message(
            "Leczenie",
            f"{healer.name} używa {source.name}. {target_actor.name}: HP {applied.hp_before} -> {applied.hp_after} ({applied.effective_healing} realnie przywrócone).",
        )
        self._record(
            "ui_combat_player_healing_roll",
            {
                "healer_id": str(healer.id),
                "target_id": str(target_actor.id),
                "source_id": source.id,
                "healing": applied.amount,
                "effective_healing": applied.effective_healing,
                "hp_before": applied.hp_before,
                "hp_after": applied.hp_after,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def cancel_player_healing(self) -> dict[str, object]:
        pending = self.pending_player_healing
        if pending is None:
            raise ValueError("Nie ma leczenia do anulowania.")
        self.pending_player_healing = None
        self.board_message = "Anulowano leczenie. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo akcję."
        self._add_message("Leczenie", "Anulowano leczenie.")
        self._record("ui_combat_player_healing_cancelled", {"healer_id": pending.healer_id, "target_id": pending.target_id})
        self._sync_board_leds()
        return self.state_payload()

    def preview_combat_movement(self, *, col: int, row: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        destination = Coordinate(int(col), int(row))
        movement_actor = replace(actor, speed_feet=movement_remaining(self.combat_state, actor))
        path = find_path(encounter.board, movement_actor, self.combat_state.actors, destination)
        if not path.valid:
            raise ValueError("Nie można dojść do wskazanego pola.")
        self.pending_opportunity_movement = None
        self.selected_combat_movement_path = path
        self.board_message = (
            f"Wybrano ścieżkę ruchu {actor.name} -> {destination.as_tuple()} "
            f"({path.cost_feet} ft). Kliknij to pole ponownie, żeby zatwierdzić."
        )
        self._record(
            "ui_combat_movement_previewed",
            {
                "actor_id": str(actor.id),
                "destination": [destination.col, destination.row],
                "path": [[position.col, position.row] for position in path.path],
                "cost_feet": path.cost_feet,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def submit_combat_movement(self, *, col: int, row: int) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        destination = Coordinate(int(col), int(row))
        movement_actor = replace(actor, speed_feet=movement_remaining(self.combat_state, actor))
        path = find_path(encounter.board, movement_actor, self.combat_state.actors, destination)
        if not path.valid:
            raise ValueError("Nie można wykonać ruchu na wybrane pole.")
        threats = opportunity_attackers_for_movement(
            self.combat_state,
            actor,
            actor.position,
            destination,
            encounter.attack_sources_by_actor,
            self.active_combat_effects,
        )
        if threats:
            self.pending_opportunity_movement = PendingOpportunityMovement(
                actor_id=str(actor.id),
                destination=destination,
                path=path,
                threat_actor_ids=tuple(str(threat.attacker.id) for threat in threats),
            )
            self.selected_combat_movement_path = path
            threat_names = ", ".join(threat.attacker.name for threat in threats)
            self.board_message = f"Ten ruch prowokuje atak okazyjny: {threat_names}. Potwierdź Enterem albo przyciskiem."
            self._add_message(
                "Atak okazyjny",
                f"{actor.name} opuszcza zasięg wroga. Zagrożenia: {threat_names}. Potwierdź ruch, żeby rozstrzygnąć reakcje.",
            )
            self._record(
                "ui_combat_opportunity_movement_pending",
                {
                    "actor_id": str(actor.id),
                    "destination": [destination.col, destination.row],
                    "threat_actor_ids": [str(threat.attacker.id) for threat in threats],
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        result = use_movement(self.combat_state, actor, path)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_combat_movement_path = None
        self.pending_combat_interaction = None
        self.pending_combat_help = None
        self._expire_invalid_combat_effects()
        self._add_message("Ruch", result.message)
        self._record(
            "ui_combat_player_moved",
            {
                "actor_id": str(actor.id),
                "destination": [destination.col, destination.row],
                "path": [[position.col, position.row] for position in path.path],
                "cost_feet": path.cost_feet,
                "movement_remaining_feet": result.movement_remaining_feet,
            },
        )
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
        actor = next((candidate for candidate in self.combat_state.actors if str(candidate.id) == pending.actor_id), None)
        if actor is None:
            raise ValueError("Aktor oczekującego ruchu nie istnieje.")

        messages: list[str] = []
        applied_damages = []
        updated_state = self.combat_state
        for attacker_id in pending.threat_actor_ids:
            actor = next((candidate for candidate in updated_state.actors if str(candidate.id) == pending.actor_id), actor)
            if actor.is_defeated():
                break
            attacker = next((candidate for candidate in updated_state.actors if str(candidate.id) == attacker_id), None)
            if attacker is None or attacker.is_defeated():
                continue
            source = encounter.attack_sources_by_actor.get(attacker.id)
            if source is None:
                continue
            reaction = use_actor_reaction(updated_state, attacker)
            if not reaction.accepted:
                continue
            updated_state = reaction.state
            actor = next(candidate for candidate in updated_state.actors if str(candidate.id) == pending.actor_id)
            source = attack_source_with_target_combat_effects(attacker, actor, source, self.active_combat_effects)
            attack_roll = resolve_d20_roll(_automatic_d20_input(source.attack_roll_request, self.encounter_rng))
            declaration = AttackDeclaration(attacker=attacker, target=actor_as_combat_target(actor), source=source)
            resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
            self.active_combat_effects = consume_next_attack_effects(
                self.active_combat_effects,
                str(attacker.id),
                str(actor.id),
            )
            if resolution.hit:
                if source.damage_fixed is not None:
                    damage_amount = source.damage_fixed + source.damage_modifier
                else:
                    damage_amount = self.encounter_rng.randint(1, source.damage_die_sides or 6) + source.damage_modifier
                damage_type = DamageType(source.damage_type)
                damage_result = resolve_damage((DamageComponentInput(damage_amount, damage_type, source.name),))
                applied_damage = apply_damage_result(actor, damage_result)
                applied_damages.append(applied_damage)
                updated_state = replace_actor(updated_state, applied_damage.actor_after)
                defeated_text = " Cel zostaje pokonany." if applied_damage.defeated_by_damage else ""
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, trafienie. "
                    f"{_damage_application_message(applied_damage)}{defeated_text}"
                )
            else:
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, pudło przeciwko {actor.name}."
                )

        actor = next((candidate for candidate in updated_state.actors if str(candidate.id) == pending.actor_id), actor)
        if not actor.is_defeated() and updated_state.status.value == "active":
            movement = use_movement(updated_state, actor, pending.path)
            if not movement.accepted:
                raise ValueError(movement.message)
            updated_state = movement.state
            messages.append(movement.message)
        elif actor.is_defeated():
            messages.append(f"{actor.name} pada przed wykonaniem ruchu.")

        self.combat_state = updated_state
        self.pending_opportunity_movement = None
        self.selected_combat_movement_path = None
        self.pending_combat_interaction = None
        self._expire_invalid_combat_effects()
        message = " ".join(messages) if messages else "Brak dostępnych reakcji. Ruch zostaje wykonany."
        self._add_message("Atak okazyjny", message)
        self._record(
            "ui_combat_opportunity_movement_confirmed",
            {
                "actor_id": pending.actor_id,
                "destination": [pending.destination.col, pending.destination.row],
                "threat_actor_ids": list(pending.threat_actor_ids),
            },
        )
        for applied_damage in applied_damages:
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
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        result = use_dash(self.combat_state, actor)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        self._add_message("Dash", result.message)
        self._record("ui_combat_dash", {"actor_id": str(actor.id), "extra_movement_feet": actor.speed_feet})
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_dodge(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        self.combat_state = action_result.state
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.actor_id == str(actor.id) and effect.kind == "dodge_until_next_turn")
        ) + (
            ActiveCombatEffect(
                id=f"dodge_until_next_turn:{actor.id}",
                actor_id=str(actor.id),
                kind="dodge_until_next_turn",
                label="Unik",
                object_id="combat_action:dodge",
                value=0,
            ),
        )
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        message = f"Unik: ataki przeciwko {actor.name} mają utrudnienie do początku następnej tury tego aktora."
        self._add_message("Unik", message)
        self._record("ui_combat_dodge", {"actor_id": str(actor.id), "attack_mode": "disadvantage"})
        self._sync_board_leds()
        return self.state_payload()

    def use_combat_disengage(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        self.combat_state = action_result.state
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.actor_id == str(actor.id) and effect.kind == "disengage_until_turn_end")
        ) + (
            ActiveCombatEffect(
                id=f"disengage_until_turn_end:{actor.id}",
                actor_id=str(actor.id),
                kind="disengage_until_turn_end",
                label="Odwrót",
                object_id="combat_action:disengage",
                value=0,
            ),
        )
        self._clear_player_pending_choices()
        self.selected_combat_movement_path = None
        message = f"Odwrót: {actor.name} może bezpiecznie odejść do końca tej tury."
        self._add_message("Odwrót", message)
        self._record("ui_combat_disengage", {"actor_id": str(actor.id)})
        self._sync_board_leds()
        return self.state_payload()

    def start_combat_help(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        if self.combat_state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        allies = tuple(
            candidate
            for candidate in self.combat_state.actors
            if candidate.faction == actor.faction and candidate.id != actor.id and not candidate.is_defeated()
        )
        targets = tuple(
            candidate
            for candidate in self.combat_state.actors
            if candidate.faction not in {actor.faction, Faction.NEUTRAL}
            and not candidate.is_defeated()
            and _coordinates_in_reach(actor.position, candidate.position, 5)
        )
        if not allies:
            raise ValueError("Brak żywego sojusznika, któremu można pomóc.")
        if not targets:
            raise ValueError("Brak przeciwnika w zasięgu 5 ft pomagającego.")
        self.pending_combat_help = PendingCombatHelp(
            helper_id=str(actor.id),
            ally_ids=tuple(str(ally.id) for ally in allies),
            target_ids=tuple(str(target.id) for target in targets),
        )
        self.pending_player_attack = None
        self.pending_combat_interaction = None
        self.selected_combat_movement_path = None
        self.board_message = "Wybierz sojusznika i cel pomocy w panelu walki."
        self._add_message("Pomoc", f"{actor.name} przygotowuje akcję Help.")
        self._record(
            "ui_combat_help_started",
            {
                "helper_id": str(actor.id),
                "ally_ids": [str(ally.id) for ally in allies],
                "target_ids": [str(target.id) for target in targets],
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_help(self, *, ally_id: str, target_id: str) -> dict[str, object]:
        pending = self.pending_combat_help
        if pending is None:
            raise ValueError("Nie ma akcji Help do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        helper = combat_current_actor(self.combat_state)
        if str(helper.id) != pending.helper_id:
            raise ValueError("Oczekująca akcja Help nie należy do aktywnego aktora.")
        if ally_id not in pending.ally_ids:
            raise ValueError("Wybrany sojusznik nie jest legalnym celem Help.")
        if target_id not in pending.target_ids:
            raise ValueError("Wybrany przeciwnik nie jest legalnym celem Help.")
        ally = _actor_by_string_id_from_state(self.combat_state, ally_id)
        target = _actor_by_string_id_from_state(self.combat_state, target_id)
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        self.combat_state = action_result.state
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (
                effect.kind == "help_attack_advantage"
                and effect.source_actor_id == str(helper.id)
            )
        ) + (
            ActiveCombatEffect(
                id=f"help_attack_advantage:{helper.id}:{ally.id}:{target.id}",
                actor_id=str(ally.id),
                kind="help_attack_advantage",
                label=f"Pomoc: {helper.name}",
                object_id="combat_action:help",
                value=0,
                source_actor_id=str(helper.id),
                target_actor_id=str(target.id),
            ),
        )
        self.pending_combat_help = None
        message = f"Help: {helper.name} pomaga {ally.name}. Następny atak {ally.name} przeciwko {target.name} ma przewagę."
        self._add_message("Pomoc", message)
        self._record(
            "ui_combat_help_confirmed",
            {"helper_id": str(helper.id), "ally_id": str(ally.id), "target_id": str(target.id)},
        )
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
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        actor = combat_current_actor(self.combat_state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        if self.combat_state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        encounter = self._active_encounter()
        if encounter is None or encounter.attack_sources_by_actor.get(actor.id) is None:
            raise ValueError(f"Aktor {actor.name} nie ma zdefiniowanego ataku do przygotowania.")
        self._clear_player_pending_choices()
        self.pending_combat_ready = PendingCombatReady(actor_id=str(actor.id))
        self.board_message = "Wybierz warunek przygotowanej akcji w panelu walki."
        self._add_message("Ready", f"{actor.name} przygotowuje akcję.")
        self._record("ui_combat_ready_started", {"actor_id": str(actor.id)})
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_ready(self, *, trigger: str) -> dict[str, object]:
        pending = self.pending_combat_ready
        if pending is None:
            raise ValueError("Nie ma akcji Ready do potwierdzenia.")
        if trigger not in pending.triggers:
            raise ValueError("Nieznany warunek przygotowanej akcji.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        actor = combat_current_actor(self.combat_state)
        if str(actor.id) != pending.actor_id:
            raise ValueError("Oczekująca akcja Ready nie należy do aktywnego aktora.")
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        self.combat_state = action_result.state
        object_id = f"combat_action:ready:{trigger}"
        self.active_combat_effects = tuple(
            effect
            for effect in self.active_combat_effects
            if not (effect.actor_id == str(actor.id) and effect.kind == "ready_attack")
        ) + (
            ActiveCombatEffect(
                id=f"ready_attack:{actor.id}:{trigger}",
                actor_id=str(actor.id),
                kind="ready_attack",
                label="Ready",
                object_id=object_id,
                value=0,
            ),
        )
        self.pending_combat_ready = None
        message = f"Ready: {actor.name} przygotowuje atak, {_ready_trigger_label(trigger)}."
        self._add_message("Ready", message)
        self._record("ui_combat_ready_confirmed", {"actor_id": str(actor.id), "trigger": trigger})
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
        actor = combat_current_actor(self.combat_state)
        options = self._available_combat_interaction_options(encounter, actor, position)
        if not options:
            raise ValueError("To pole nie ma teraz dostępnej interakcji.")
        scene_object = self._scene_object_at_position(encounter, position)
        assert scene_object is not None
        self.pending_combat_interaction = PendingCombatInteraction(
            actor_id=str(actor.id),
            object_id=scene_object.id,
            object_name=scene_object.name,
            target_position=position,
            options=options,
        )
        self.selected_combat_movement_path = None
        self.pending_player_attack = None
        option_labels = ", ".join(option.label for option in options)
        self.board_message = f"Wybrano interakcję z obiektem: {scene_object.name}. Wybierz w UI: {option_labels}."
        self._add_message(
            "Interakcja",
            f"{actor.name} wybiera {scene_object.name}. Dostępne opcje: {option_labels}.",
        )
        self._record(
            "ui_combat_interaction_selected",
            {
                "actor_id": str(actor.id),
                "object_id": scene_object.id,
                "position": [position.col, position.row],
                "options": [option.id for option in options],
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def confirm_combat_interaction(self, interaction_id: str) -> dict[str, object]:
        pending = self.pending_combat_interaction
        if pending is None:
            raise ValueError("Nie ma interakcji do potwierdzenia.")
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        actor = combat_current_actor(self.combat_state)
        if str(actor.id) != pending.actor_id:
            raise ValueError("Oczekująca interakcja nie należy do aktywnego aktora.")
        option = next((candidate for candidate in pending.options if candidate.id == interaction_id), None)
        if option is None:
            raise ValueError("Nieznana opcja interakcji.")
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        scene_object = self._scene_object_by_id(encounter, option.object_id)
        if scene_object is None:
            raise ValueError("Obiekt interakcji nie istnieje w aktywnym encounterze.")
        interaction = next((candidate for candidate in available_scene_interactions(scene_object) if candidate.id == option.id), None)
        if interaction is None:
            raise ValueError("Interakcja nie istnieje w aktywnym encounterze.")
        applied = apply_combat_interaction_effects(
            state=action_result.state,
            actor=actor,
            scene_object=scene_object,
            interaction=interaction,
            target_position=option.target_position,
            active_effects=self.active_combat_effects,
            rng=self.encounter_rng,
        )
        self.combat_state = applied.state
        self.active_combat_effects = applied.active_effects
        message = f"{actor.name}: {applied.message}"
        self.pending_combat_interaction = None
        self.selected_combat_movement_path = None
        self._add_message("Interakcja", message)
        self.board_message = message
        self._record(
            "ui_combat_interaction_confirmed",
            {
                "actor_id": str(actor.id),
                "object_id": scene_object.id,
                "interaction_id": option.id,
                "message": message,
                "saving_throw": applied.saving_throw.as_payload() if applied.saving_throw is not None else None,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def cancel_combat_interaction(self) -> dict[str, object]:
        pending = self.pending_combat_interaction
        if pending is None:
            raise ValueError("Nie ma interakcji do anulowania.")
        self.pending_combat_interaction = None
        self.board_message = "Anulowano interakcję. Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
        self._add_message("Interakcja", "Anulowano wybór interakcji.")
        self._record(
            "ui_combat_interaction_cancelled",
            {"actor_id": pending.actor_id, "object_id": pending.object_id},
        )
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
        if self.combat_state is None or actor.faction != Faction.ALLY:
            return ()
        if self.combat_state.status.value != "active":
            return ()
        return available_combat_interaction_options(encounter.scene_objects, self.combat_state, actor, position)

    def _combat_interaction_positions(self, encounter: LoadedEncounter, actor: Actor) -> tuple[Coordinate, ...]:
        if self.combat_state is None:
            return ()
        return combat_interaction_positions(encounter.scene_objects, self.combat_state, actor)

    def _combat_interaction_hint_positions(
        self,
        encounter: LoadedEncounter,
        actor: Actor,
        movement: MovementRangeResult,
    ) -> tuple[Coordinate, ...]:
        if self.combat_state is None:
            return ()
        return combat_interaction_hint_positions(encounter.scene_objects, self.combat_state, actor, movement.reachable_tiles)

    def _scene_object_at_position(self, encounter: LoadedEncounter, position: Coordinate):
        return scene_object_at_position(encounter.scene_objects, position)

    def _scene_object_by_id(self, encounter: LoadedEncounter, object_id: str):
        return scene_object_by_id(encounter.scene_objects, object_id)

    def _expire_invalid_combat_effects(self) -> None:
        if self.combat_state is None or not self.active_combat_effects:
            return
        encounter = self._active_encounter()
        scene_objects = encounter.scene_objects if encounter is not None else ()
        before = self.active_combat_effects
        self.combat_state, self.active_combat_effects = expire_invalid_combat_effects(
            self.combat_state,
            scene_objects,
            self.active_combat_effects,
        )
        if before != self.active_combat_effects:
            self._add_expired_effects_message("Wygasły efekty pozycyjne", before, self.active_combat_effects)

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

    def resolve_enemy_turn(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            raise ValueError("Walka nie jest aktywna.")
        encounter = self._active_encounter()
        if encounter is None:
            raise ValueError("Brak danych encountera dla aktywnej walki.")
        enemy = combat_current_actor(self.combat_state)
        if enemy.faction != Faction.ENEMY:
            raise ValueError("To nie jest tura przeciwnika.")
        source = encounter.attack_sources_by_actor.get(enemy.id)
        if source is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        if self.pending_enemy_turn_intent is None:
            intent = plan_enemy_turn(encounter.board, self.combat_state, enemy)
            self.pending_enemy_turn_intent = intent
            self.board_message = _enemy_turn_intent_message(intent)
            self._add_message("Zamiar przeciwnika", f"{_enemy_turn_intent_message(intent)} Potwierdź Enterem albo przyciskiem.")
            self._record(
                "ui_combat_enemy_turn_intent",
                {
                    "enemy_id": str(enemy.id),
                    "target_id": intent.target.id if intent.target is not None else None,
                    "message": intent.message,
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        intent = self.pending_enemy_turn_intent
        self.pending_enemy_turn_intent = None
        target_actor = None
        if intent is not None and intent.target is not None:
            target_actor = next(
                (actor for actor in self.combat_state.actors if str(actor.id) == intent.target.id),
                None,
            )
        source = self._effective_attack_source(enemy, source, target_actor)
        result = resolve_enemy_auto_turn(encounter.board, self.combat_state, enemy, source, self.encounter_rng)
        ready = self._pending_ready_attack_for_enemy_result(result)
        if ready is not None:
            self.pending_enemy_turn_result = result
            self.pending_ready_attack = ready
            readied_actor = self._actor_by_string_id(ready.readied_actor_id)
            self.board_message = f"Wyzwolono Ready: {readied_actor.name} może użyć przygotowanego ataku."
            self._add_message(
                "Ready",
                f"{readied_actor.name}: warunek przygotowanej akcji został spełniony ({_ready_trigger_label(ready.trigger)}).",
            )
            self._record(
                "ui_combat_ready_triggered",
                {
                    "readied_actor_id": ready.readied_actor_id,
                    "target_id": ready.target_id,
                    "trigger": ready.trigger,
                },
            )
            self._sync_board_leds()
            return self.state_payload()
        if result.movement_path is not None and result.movement_path.valid and result.movement_path.destination != enemy.position:
            threats = tuple(
                threat
                for threat in opportunity_attackers_for_movement(
                    self.combat_state,
                    enemy,
                    enemy.position,
                    result.movement_path.destination,
                    encounter.attack_sources_by_actor,
                    self.active_combat_effects,
                )
                if threat.attacker.faction == Faction.ALLY
            )
            if threats:
                self.pending_enemy_turn_result = result
                self.pending_enemy_opportunity_attack = PendingEnemyOpportunityAttack(
                    target_id=str(enemy.id),
                    threat_actor_ids=tuple(str(threat.attacker.id) for threat in threats),
                )
                threat_names = ", ".join(threat.attacker.name for threat in threats)
                self.board_message = (
                    f"{enemy.name} opuszcza zasięg: {threat_names}. "
                    "Wybierz atak okazyjny albo pomiń reakcję."
                )
                self._add_message(
                    "Atak okazyjny",
                    f"{enemy.name} prowokuje atak okazyjny. Reakcję może wykonać: {threat_names}.",
                )
                self._record(
                    "ui_combat_enemy_opportunity_pending",
                    {
                        "enemy_id": str(enemy.id),
                        "destination": [result.movement_path.destination.col, result.movement_path.destination.row],
                        "threat_actor_ids": [str(threat.attacker.id) for threat in threats],
                    },
                )
                self._sync_board_leds()
                return self.state_payload()
            self.pending_enemy_turn_result = result
            self.board_message = (
                f"{enemy.name} rusza na {result.movement_path.destination.as_tuple()}. "
                "Przestaw figurkę po podświetlonej ścieżce i kliknij pole docelowe."
            )
            self._add_message(
                "Ruch przeciwnika",
                f"{enemy.name} planuje ruch na {result.movement_path.destination.as_tuple()}. Potwierdź pole docelowe na planszy.",
            )
            self._sync_board_leds()
            return self.state_payload()
        if result.target is not None:
            self.pending_enemy_turn_result = result
            self.board_message = (
                f"{enemy.name} atakuje {result.target.name}. Kliknij podświetlone pole celu, żeby potwierdzić atak."
            )
            self._add_message(
                "Atak przeciwnika",
                f"{enemy.name} atakuje {result.target.name}. {_enemy_roll_summary(result)} Potwierdź atak klikając pole celu.",
            )
            self._sync_board_leds()
            return self.state_payload()
        return self._finish_pending_enemy_turn(result)

    def _commit_pending_enemy_turn(self, result=None) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        result = result or self.pending_enemy_turn_result
        if result is None:
            raise ValueError("Brak oczekującej tury przeciwnika do potwierdzenia.")
        self.combat_state = result.state
        if result.attack_roll is not None:
            self.active_combat_effects = consume_next_attack_effects(
                self.active_combat_effects,
                str(result.enemy.id),
                result.target.id if result.target is not None else None,
            )
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_enemy_turn_ack_result = result
        self.board_message = "Wynik tury przeciwnika gotowy. Potwierdź Enterem albo przyciskiem w UI."
        self._record(
            "ui_combat_enemy_turn_board_confirmed",
            {
                "enemy_id": str(result.enemy.id),
                "target_id": result.target.id if result.target is not None else None,
                "message": _enemy_turn_message(result),
            },
        )
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
        attacker = self._actor_by_string_id(pending.attacker_id)
        target = self._actor_by_string_id(pending.target_id)
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        reaction = use_actor_reaction(self.combat_state, attacker)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        self.combat_state = reaction.state
        self.pending_enemy_turn_result = self._enemy_turn_result_with_spent_reactions()
        attacker = self._actor_by_string_id(pending.attacker_id)
        target = self._actor_by_string_id(pending.target_id)
        source = self._effective_attack_source(attacker, source, target)
        attack_roll = resolve_d20_roll(_manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2))
        declaration = AttackDeclaration(attacker=attacker, target=actor_as_combat_target(target), source=source)
        resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
        self.active_combat_effects = consume_next_attack_effects(
            self.active_combat_effects,
            str(attacker.id),
            pending.target_id,
        )
        message = _player_attack_message(attacker.name, target.name, attack_roll.total, resolution.hit, resolution.critical)
        self._record(
            "ui_combat_enemy_opportunity_attack_roll",
            {
                "attacker_id": pending.attacker_id,
                "target_id": pending.target_id,
                "natural_roll": attack_roll.natural_roll,
                "natural_rolls": list(attack_roll.natural_rolls),
                "total": attack_roll.total,
                "hit": resolution.hit,
                "critical": resolution.critical,
            },
        )
        if not resolution.hit:
            self._add_message("Atak okazyjny", message)
            return self._advance_enemy_opportunity_or_resume_preview()
        self.pending_enemy_opportunity_attack = replace(
            pending,
            stage="damage_roll",
            natural_roll=attack_roll.natural_roll,
            natural_rolls=attack_roll.natural_rolls,
            total=attack_roll.total,
            hit=True,
            critical=resolution.critical,
        )
        self._add_message("Atak okazyjny", f"{message} Trafienie: rzuć obrażenia {source.damage_hint} i wpisz sumę.")
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
        attacker = self._actor_by_string_id(pending.attacker_id)
        target = self._actor_by_string_id(pending.target_id)
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = self._effective_attack_source(attacker, source, target)
        damage_result = resolve_damage((DamageComponentInput(max(0, int(damage)), DamageType(source.damage_type), source.name),))
        applied_damage = apply_damage_result(target, damage_result)
        updated_target = applied_damage.actor_after
        self.combat_state = replace_actor(self.combat_state, updated_target)
        self.pending_enemy_turn_result = self._enemy_turn_result_with_updated_actor(updated_target)
        message = f"{attacker.name} trafia atakiem okazyjnym. {_damage_application_message(applied_damage)}"
        self._record(
            "ui_combat_enemy_opportunity_damage",
            {
                "attacker_id": pending.attacker_id,
                "target_id": pending.target_id,
                "damage": damage_result.total_applied,
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
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        target = self._actor_by_string_id(pending.target_id)
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        reaction = use_actor_reaction(self.combat_state, attacker)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        self.combat_state = reaction.state
        self.pending_enemy_turn_result = self._enemy_turn_result_with_spent_reactions()
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        target = self._actor_by_string_id(pending.target_id)
        source = self._effective_attack_source(attacker, source, target)
        attack_roll = resolve_d20_roll(_manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2))
        declaration = AttackDeclaration(attacker=attacker, target=actor_as_combat_target(target), source=source)
        resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
        self.active_combat_effects = self._consume_ready_attack_effect(pending.effect_id)
        self.active_combat_effects = consume_next_attack_effects(
            self.active_combat_effects,
            str(attacker.id),
            pending.target_id,
        )
        message = _player_attack_message(attacker.name, target.name, attack_roll.total, resolution.hit, resolution.critical)
        self._record(
            "ui_combat_ready_attack_roll",
            {
                "attacker_id": pending.readied_actor_id,
                "target_id": pending.target_id,
                "natural_roll": attack_roll.natural_roll,
                "natural_rolls": list(attack_roll.natural_rolls),
                "total": attack_roll.total,
                "hit": resolution.hit,
                "critical": resolution.critical,
            },
        )
        if not resolution.hit:
            self.pending_ready_attack = None
            self._add_message("Ready", message)
            self._resume_enemy_turn_after_reaction_prompt()
            return self.state_payload()
        self.pending_ready_attack = replace(
            pending,
            stage="damage_roll",
            natural_roll=attack_roll.natural_roll,
            natural_rolls=attack_roll.natural_rolls,
            total=attack_roll.total,
            hit=True,
            critical=resolution.critical,
        )
        self._add_message("Ready", f"{message} Trafienie: rzuć obrażenia {source.damage_hint} i wpisz sumę.")
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
        attacker = self._actor_by_string_id(pending.readied_actor_id)
        target = self._actor_by_string_id(pending.target_id)
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = self._effective_attack_source(attacker, source, target)
        damage_result = resolve_damage((DamageComponentInput(max(0, int(damage)), DamageType(source.damage_type), source.name),))
        applied_damage = apply_damage_result(target, damage_result)
        updated_target = applied_damage.actor_after
        self.combat_state = replace_actor(self.combat_state, updated_target)
        self.pending_enemy_turn_result = self._enemy_turn_result_with_updated_actor(updated_target)
        message = f"{attacker.name} trafia przygotowaną akcją. {_damage_application_message(applied_damage)}"
        self._record(
            "ui_combat_ready_damage",
            {
                "attacker_id": pending.readied_actor_id,
                "target_id": pending.target_id,
                "damage": damage_result.total_applied,
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

    def _consume_ready_attack_effect(self, effect_id: str) -> tuple[ActiveCombatEffect, ...]:
        return tuple(effect for effect in self.active_combat_effects if effect.id != effect_id)

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
        trigger = _ready_trigger_for_enemy_result(result)
        if trigger is None:
            return None
        trigger_target = result.moved_enemy if result.moved_enemy is not None else result.enemy
        if trigger_target is None or trigger_target.is_defeated():
            return None
        for effect in self.active_combat_effects:
            if effect.kind != "ready_attack" or effect.object_id != f"combat_action:ready:{trigger}":
                continue
            readied_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == effect.actor_id), None)
            if readied_actor is None or readied_actor.is_defeated() or not reaction_available_for(self.combat_state, readied_actor):
                continue
            source = encounter.attack_sources_by_actor.get(readied_actor.id)
            if source is None:
                continue
            actors_for_target = result.state.actors if result.state is not None else self.combat_state.actors
            targets = start_attack_action(encounter.board, readied_actor, actors_for_target, source).legal_targets
            if any(target.id == str(trigger_target.id) for target in targets):
                return PendingReadyAttack(
                    readied_actor_id=str(readied_actor.id),
                    target_id=str(trigger_target.id),
                    effect_id=effect.id,
                    trigger=trigger,
                )
        return None

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
        self._expire_turn_end_effects(result.enemy)
        self.combat_state = finish_turn(result.state)
        self._expire_turn_start_effects()
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self.pending_enemy_turn_ack_result = None
        self._add_message("Tura przeciwnika", _enemy_turn_message(result))
        self._record(
            "ui_combat_enemy_turn",
            {
                "enemy_id": str(result.enemy.id),
                "target_id": result.target.id if result.target is not None else None,
                "message": _enemy_turn_message(result),
                "action_used": result.action_used,
            },
        )
        self._sync_board_leds()
        return self.state_payload()

    def reset_board_scan(self) -> dict[str, object]:
        if self.board_adapter is None:
            raise ValueError("Najpierw podłącz backend planszy.")
        connection = self.board_adapter.connection
        resetter = getattr(connection, "reset_connection", None)
        rearmer = getattr(connection, "rearm_scan", None)
        canceller = getattr(connection, "cancel_scan", None)
        if callable(resetter):
            resetter()
            action = "reset_connection"
        elif callable(rearmer):
            rearmer()
            action = "rearm_scan"
        elif callable(canceller):
            canceller()
            action = "cancel_scan"
        else:
            raise ValueError("Aktualny backend planszy nie obsługuje resetu skanu.")
        self.board_message = "Zresetowano oczekiwanie na kliknięcie planszy."
        self._record("ui_board_scan_reset", {"action": action})
        self._sync_board_leds()
        return self.state_payload()

    def finish_combat_turn(self) -> dict[str, object]:
        if self.combat_state is None:
            raise ValueError("Walka nie została rozpoczęta.")
        if self.combat_state.status.value != "active":
            return self.state_payload()
        actor = combat_current_actor(self.combat_state)
        self._expire_turn_end_effects(actor)
        self.combat_state = finish_turn(self.combat_state)
        self._expire_turn_start_effects()
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_turn_ack_result = None
        self.pending_enemy_opportunity_attack = None
        self.pending_ready_attack = None
        self._clear_player_pending_choices()
        self._add_message("Koniec tury", f"Zakończono turę: {actor.name}.")
        self._record("ui_combat_turn_finished", {"actor_id": str(actor.id)})
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

    def _sync_board_leds(self) -> None:
        if self.board_adapter is None:
            return
        target = self._current_board_scan_target()
        self._show_board_feedback(target.feedback)

    def _show_board_feedback(self, feedback: LedFeedback) -> None:
        if self.board_adapter is None:
            return
        self.board_adapter.clear()
        if feedback.frames:
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
        if self.ui_flow_stage == UiFlowStage.INTERACTION_RESULT:
            return BoardScanTarget(
                positions=(),
                feedback=LedFeedback(),
                empty_message="Najpierw zakończ podsumowanie interakcji w UI.",
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
        if self.ui_flow_stage != UiFlowStage.LOCATION_ACTIVE:
            raise ValueError("Najpierw potwierdź wejście do lokacji.")
        if not point_id:
            self.active_point_id = ""
            return self.state_payload()
        point = next((candidate for candidate in self.current_zone_points() if candidate.id == point_id), None)
        if point is None:
            raise ValueError("Ten punkt nie jest dostępny w aktualnej lokacji.")
        self.active_point_id = point.id
        self.pending = None
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
        plan = _challenge_check_plan(option, lead_actor_id, self.exploration.actors)
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
        if self.post_interaction_setup_steps:
            return
        if self.exploration_setup_flow is not None:
            return
        if self.pending_encounter is not None:
            return
        for trigger in self.exploration.encounter_triggers:
            if trigger.id in self.resolved_encounter_trigger_ids:
                continue
            reason = self._trigger_reason(trigger)
            if reason:
                self.pending_encounter = PendingEncounter(
                    trigger_id=trigger.id,
                    name=trigger.name,
                    description=trigger.description,
                    encounter_scenario=trigger.encounter_scenario,
                    reason=reason,
                )
                self._add_message("Encounter", f"{trigger.name}. {trigger.description}".strip())
                return

    def _trigger_by_id(self, trigger_id: str) -> ExplorationEncounterTrigger | None:
        return next((trigger for trigger in self.exploration.encounter_triggers if trigger.id == trigger_id), None)

    def _trigger_reason(self, trigger: ExplorationEncounterTrigger) -> str:
        if trigger.condition.value == "noise_at_least" and trigger.challenge_id is not None and trigger.noise is not None:
            noise = challenge_state_for(self.state, trigger.challenge_id).noise
            if noise >= trigger.noise:
                return f"Hałas osiągnął {noise}, próg: {trigger.noise}."
        if trigger.condition.value == "flag_equals" and trigger.flag_key:
            value = scene_flag(self.state.flags, trigger.flag_key, None)
            if value == trigger.flag_value:
                return f"Flaga {trigger.flag_key} ma wartość {trigger.flag_value}."
        if trigger.condition.value == "point_revealed" and trigger.point_id:
            visible_ids = {point.id for point in visible_exploration_points(self.state.points)}
            if trigger.point_id in visible_ids:
                return f"Ujawniono punkt: {trigger.point_id}."
        return ""

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
        return [
            {"actor_id": str(actor.id), "actor_name": actor.name, "die_sides": 20, "label": "d20"}
            for actor in _actors_for_plan(self.exploration.actors, self.pending.check_plan)
        ]

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


def create_app(session: ExplorationUiSession) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(_HTML)

    @app.get("/scenario-assets/<path:filename>")
    def scenario_assets(filename: str):
        return send_from_directory(session._scenario_asset_root().resolve(), filename)

    @app.get("/api/state")
    def api_state():
        return jsonify(session.state_payload())

    @app.get("/api/session-log")
    def api_session_log():
        return jsonify(_session_log_payload(session))

    @app.post("/api/start")
    def api_start():
        try:
            return jsonify(session.start_session())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/action")
    def api_action():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_action(str(data.get("text", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/decision")
    def api_decision():
        data = request.get_json(silent=True) or {}
        try:
            lead_actor_id = data.get("lead_actor_id")
            return jsonify(session.decide(str(data.get("decision", "")), lead_actor_id=str(lead_actor_id) if lead_actor_id else None))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rolls")
    def api_rolls():
        data = request.get_json(silent=True) or {}
        rolls = data.get("rolls", {})
        if not isinstance(rolls, dict):
            return jsonify({"error": "Pole rolls musi być obiektem.", "state": session.state_payload()}), 400
        try:
            return jsonify(session.resolve_rolls(rolls))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/interaction/finish")
    def api_interaction_finish():
        try:
            return jsonify(session.finish_interaction_result())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/location/cancel-preview")
    def api_location_cancel_preview():
        try:
            return jsonify(session.cancel_location_preview())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/location/confirm-preview")
    def api_location_confirm_preview():
        try:
            return jsonify(session.confirm_location_preview())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/setup/confirm")
    def api_exploration_setup_confirm():
        try:
            return jsonify(session.confirm_exploration_setup_step())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/travel")
    def api_travel():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.travel_to(str(data.get("zone_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/point")
    def api_point():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_point(str(data.get("point_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/configure")
    def api_board_configure():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.configure_board(
                    backend=str(data.get("backend", "none")),
                    board_url=str(data.get("board_url", "")),
                    board_serial_port=str(data.get("board_serial_port", "")),
                    wled_url=str(data.get("wled_url", "")),
                    scan_timeout_s=float(data["scan_timeout_s"]) if data.get("scan_timeout_s") not in {None, ""} else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/scan")
    def api_board_scan():
        try:
            return jsonify(session.scan_board_selection())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/select")
    def api_board_select():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_board_position(Coordinate(int(data.get("col", 0)), int(data.get("row", 0)))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/reset-scan")
    def api_board_reset_scan():
        try:
            return jsonify(session.reset_board_scan())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/setup/start")
    def api_encounter_setup_start():
        try:
            return jsonify(session.start_encounter_setup())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/setup/confirm")
    def api_encounter_setup_confirm():
        try:
            return jsonify(session.confirm_encounter_setup_step())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/initiative/start")
    def api_encounter_initiative_start():
        try:
            return jsonify(session.start_encounter_initiative())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/initiative/roll")
    def api_encounter_initiative_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_encounter_initiative_roll(int(data.get("natural_roll", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-roll")
    def api_combat_player_attack_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_player_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/attack-source")
    def api_combat_attack_source():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_combat_attack_source(str(data.get("source_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/healing-source")
    def api_combat_healing_source():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_combat_healing_source(str(data.get("source_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-confirm")
    def api_combat_player_attack_confirm():
        try:
            return jsonify(session.confirm_player_attack_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-cancel")
    def api_combat_player_attack_cancel():
        try:
            return jsonify(session.cancel_player_attack_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-damage")
    def api_combat_player_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-healing")
    def api_combat_player_healing():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_healing_roll(healing=int(data.get("healing", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-healing-cancel")
    def api_combat_player_healing_cancel():
        try:
            return jsonify(session.cancel_player_healing())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/confirm")
    def api_combat_area_spell_confirm():
        try:
            return jsonify(session.confirm_player_area_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/damage")
    def api_combat_area_spell_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_area_spell_damage(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/cancel")
    def api_combat_area_spell_cancel():
        try:
            return jsonify(session.cancel_player_area_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/strength-potion")
    def api_combat_strength_potion():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.use_combat_strength_potion(str(data.get("action_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/start")
    def api_combat_concentration_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.start_combat_concentration_action(str(data.get("action_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/confirm")
    def api_combat_concentration_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_concentration_action(target_id=str(data.get("target_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/cancel")
    def api_combat_concentration_cancel():
        try:
            return jsonify(session.cancel_combat_concentration_action())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration-check")
    def api_combat_concentration_check():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_concentration_check(natural_roll=int(data.get("natural_roll", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/interaction/confirm")
    def api_combat_interaction_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_interaction(str(data.get("interaction_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/interaction/cancel")
    def api_combat_interaction_cancel():
        try:
            return jsonify(session.cancel_combat_interaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/move")
    def api_combat_move():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_combat_movement(col=int(data.get("col", 0)), row=int(data.get("row", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/opportunity-movement/confirm")
    def api_combat_opportunity_movement_confirm():
        try:
            return jsonify(session.confirm_opportunity_movement())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/opportunity-movement/cancel")
    def api_combat_opportunity_movement_cancel():
        try:
            return jsonify(session.cancel_opportunity_movement())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/dash")
    def api_combat_dash():
        try:
            return jsonify(session.use_combat_dash())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/dodge")
    def api_combat_dodge():
        try:
            return jsonify(session.use_combat_dodge())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/disengage")
    def api_combat_disengage():
        try:
            return jsonify(session.use_combat_disengage())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/start")
    def api_combat_help_start():
        try:
            return jsonify(session.start_combat_help())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/confirm")
    def api_combat_help_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_help(ally_id=str(data.get("ally_id", "")), target_id=str(data.get("target_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/cancel")
    def api_combat_help_cancel():
        try:
            return jsonify(session.cancel_combat_help())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/start")
    def api_combat_ready_start():
        try:
            return jsonify(session.start_combat_ready())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/confirm")
    def api_combat_ready_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_ready(trigger=str(data.get("trigger", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/cancel")
    def api_combat_ready_cancel():
        try:
            return jsonify(session.cancel_combat_ready())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-turn")
    def api_combat_enemy_turn():
        try:
            return jsonify(session.resolve_enemy_turn())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/start")
    def api_combat_enemy_opportunity_start():
        try:
            return jsonify(session.start_enemy_opportunity_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/skip")
    def api_combat_enemy_opportunity_skip():
        try:
            return jsonify(session.skip_enemy_opportunity_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/roll")
    def api_combat_enemy_opportunity_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_enemy_opportunity_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/damage")
    def api_combat_enemy_opportunity_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_enemy_opportunity_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/start")
    def api_combat_ready_attack_start():
        try:
            return jsonify(session.start_ready_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/skip")
    def api_combat_ready_attack_skip():
        try:
            return jsonify(session.skip_ready_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/roll")
    def api_combat_ready_attack_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_ready_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/damage")
    def api_combat_ready_attack_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_ready_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-turn/confirm")
    def api_combat_enemy_turn_confirm():
        try:
            return jsonify(session.confirm_enemy_turn_result())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/end-turn")
    def api_combat_end_turn():
        try:
            return jsonify(session.finish_combat_turn())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/combat/resolve")
    def api_encounter_combat_resolve():
        try:
            return jsonify(session.resolve_active_combat())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/reset")
    def api_reset():
        session.reset()
        return jsonify(session.state_payload())

    return app


def _session_log_payload(session: ExplorationUiSession, *, limit: int = 200) -> dict[str, object]:
    path = session.observer.path
    events: list[dict[str, object]] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        import json

        for line in lines:
            if not line.strip():
                continue
            events.append(json.loads(line))
    return {
        "session_id": session.observer.session_id,
        "path": str(path),
        "events": events,
    }


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


def _combat_action_by_id(encounter: LoadedEncounter | None, actor: Actor, action_id: str):
    if encounter is None:
        return None
    return next((action for action in encounter.combat_actions_by_actor.get(actor.id, ()) if action.id == action_id), None)


def _manual_d20_input(request: D20RollRequest, natural_roll: int, natural_roll_2: int | None = None) -> D20RollInput:
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, int(natural_roll))
    if natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return D20RollInput(request, int(natural_roll), int(natural_roll_2))


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
        "available_attack": _attack_source_payload(attack_source) if attack_source is not None else None,
        "available_attack_sources": [_attack_source_payload(source) for source in attack_sources],
        "selected_attack_source_id": attack_source.id if attack_source is not None else None,
        "available_healing_sources": [_healing_source_payload(source) for source in healing_sources],
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
            pending_concentration_action.as_payload(
                state,
                active_combat_effects,
                _combat_action_by_id(encounter, actor, pending_concentration_action.action_id),
            )
            if pending_concentration_action is not None
            else None
        ),
        "pending_concentration_check": (
            pending_concentration_check.as_payload(state, active_combat_effects)
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


def _ready_trigger_label(trigger: str) -> str:
    labels = {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
    }
    return labels.get(trigger, trigger)


def _ready_trigger_for_enemy_result(result) -> str | None:
    if result is None:
        return None
    if result.movement_path is not None and result.movement_path.valid and result.movement_path.destination != result.enemy.position:
        return "enemy_moves"
    if result.target is not None:
        return "enemy_attacks"
    return None


def _attack_source_payload(source) -> dict[str, object]:
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
        "prepared": source.prepared,
        "resource_label": _source_resource_label(source),
        "area": _spell_area_payload(source.area),
        "save_ability": source.save_ability,
        "save_dc": source.save_dc,
        "save_damage_on_success": source.save_damage_on_success,
        "mechanic": action_mechanic_payload(attack_mechanic_from_source(source)),
    }


def _healing_source_payload(source: HealingSource) -> dict[str, object]:
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
        "prepared": source.prepared,
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


def _spell_area_payload(area) -> dict[str, object] | None:
    if area is None:
        return None
    return {
        "shape": area.shape.value,
        "radius_feet": area.radius_feet,
        "length_feet": area.length_feet,
        "width_feet": area.width_feet,
    }


def _spell_save_for_actor(saves: tuple[SpellSaveResult, ...], actor_id: str) -> SpellSaveResult | None:
    return next((save for save in saves if save.actor_id == actor_id), None)


def _spell_save_message(save: SpellSaveResult) -> str:
    payload = save.as_payload()
    outcome = "sukces" if save.success else "porażka"
    return (
        f"{save.actor_name}: rzut obronny na {payload['ability_label']} "
        f"d20 {save.natural_roll}, modyfikator {_format_signed(save.modifier)}, razem {save.total} "
        f"przeciw ST {save.dc}: {outcome}."
    )


def _save_damage_on_success_label(value: str) -> str:
    if value == "half":
        return "połowę obrażeń przy sukcesie"
    return "brak obrażeń przy sukcesie"


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _combat_action_payload(action, actor: Actor | None = None) -> dict[str, object]:
    quantity = _combat_action_item_quantity(action, actor)
    available = action.prepared and (quantity is None or quantity > 0)
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
        "prepared": action.prepared,
        "concentration": action.concentration,
        "source_item_id": action.source_item_id,
        "source_item_quantity": quantity,
        "available": available,
        "resource_label": _source_resource_label(action),
        "mechanic": action_mechanic_payload(combat_action_mechanic_from_definition(action)),
    }


def _combat_action_item_quantity(action, actor: Actor | None) -> int | None:
    if actor is None or action.source_item_id is None:
        return None
    item = next((candidate for candidate in actor.inventory if candidate.id == action.source_item_id), None)
    return item.quantity if item is not None else 0


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


def _coordinates_in_reach(a: Coordinate, b: Coordinate, reach_feet: int) -> bool:
    if reach_feet <= 0:
        return False
    distance_feet = max(abs(a.col - b.col), abs(a.row - b.row)) * 5
    return 0 < distance_feet <= reach_feet


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


def _player_attack_message(attacker_name: str, target_name: str, total: int, hit: bool, critical: bool) -> str:
    if critical:
        return f"{attacker_name} trafia krytycznie {target_name}. Wynik ataku: {total}."
    if hit:
        return f"{attacker_name} trafia {target_name}. Wynik ataku: {total}."
    return f"{attacker_name} pudłuje przeciwko {target_name}. Wynik ataku: {total}."


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


def _challenge_check_plan(option: ExplorationChallengeOption, lead_actor_id: str, actors: tuple[Actor, ...]) -> ExplorationCheckPlan:
    roll_modifiers_by_actor_id = tuple(
        (str(actor.id), option_roll_modifiers_for_actor(actor, option))
        for actor in actors
        if option_roll_modifiers_for_actor(actor, option)
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
        reason_for_players=option.description,
        roll_modifiers_by_actor_id=roll_modifiers_by_actor_id,
        option_bonus_payloads=option_bonus_payloads,
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
        natural_roll = int(raw_rolls[actor_id])
        request = D20RollRequest(modifiers=(*_ability_roll_modifiers(actor, plan.ability, plan.skill), *_plan_roll_modifiers(actor, plan)))
        result.append(PartyCheckInput(actor, natural_roll, request))
    return tuple(result)


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
    actor_id = str(actor.id)
    for candidate_actor_id, modifiers in plan.roll_modifiers_by_actor_id:
        if candidate_actor_id == actor_id:
            return modifiers
    return ()


def _challenge_proposal_text(
    proposal: GmClassifierProposal,
    option: ExplorationChallengeOption,
    resource: ExplorationResource | None,
) -> str:
    resource_text = f"\nZasób: {resource.label}" if resource else ""
    return (
        f"{proposal.player_narration}\n"
        f"Podejście: {option.label}. Test: {option.ability_check.ability}/{option.ability_check.skill or '-'}, "
        f"ST {option.ability_check.dc}. Sukces: +{option.progress_on_success} postępu, "
        f"porażka: +{option.progress_on_failure} postępu.{resource_text}"
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
        f"Agregacja: {plan.aggregation.value}. Konsekwencje: "
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
    }


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
    return {"id": resource.id, "label": resource.label, "bonus_tags": list(resource.bonus_tags)}


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


_HTML = """
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eksploracja</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #101214; color: #ece7dc; }
    main { min-height: 100vh; }
    aside { position: fixed; inset: 0 auto 0 0; z-index: 30; width: 280px; border-right: 1px solid #34383d; padding: 16px; background: #171a1e; overflow: auto; transform: translateX(-100%); transition: transform 160ms ease; box-shadow: 12px 0 28px rgba(0,0,0,0.28); }
    body.side-panel-open aside { transform: translateX(0); }
    section { padding: 18px 18px 18px 64px; overflow: auto; }
    .side-panel-toggle { position: fixed; z-index: 45; top: 14px; left: 12px; width: 40px; height: 40px; padding: 0; border: 1px solid #3a3f45; background: #20252b; color: #ece7dc; display: grid; place-items: center; }
    .side-panel-close { width: 32px; height: 32px; padding: 0; background: #3a3f45; }
    .side-panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
    .side-panel-scrim { position: fixed; inset: 0; z-index: 25; background: rgba(0,0,0,0.42); opacity: 0; pointer-events: none; transition: opacity 160ms ease; }
    body.side-panel-open .side-panel-scrim { opacity: 1; pointer-events: auto; }
    @media (max-width: 720px) {
      aside { width: min(320px, calc(100vw - 52px)); }
      section { padding-left: 58px; }
    }
    h1, h2, h3 { margin: 0 0 10px; }
    .muted { color: #a9a298; font-size: 13px; }
    .card { border: 1px solid #34383d; border-radius: 6px; padding: 12px; margin: 0 0 12px; background: #1d2126; }
    .message { border-left: 3px solid #58a6ff; padding: 10px 12px; margin: 0 0 10px; background: #171b20; }
    .result { border-left: 3px solid #3fb950; padding: 10px 12px; margin: 0 0 10px; background: #132018; }
    .scene-description h3 { margin-top: 0; }
    .scene-description p { margin: 7px 0; line-height: 1.45; }
    .scene-description ul { margin: 6px 0 0 20px; padding: 0; }
    .scene-description li { margin: 3px 0; }
    .start-panel { min-height: 220px; display: grid; place-items: center; text-align: center; }
    .start-panel .inner { max-width: 620px; }
    .start-button { font-size: 18px; padding: 12px 22px; margin-top: 12px; }
    .start-button:disabled { background: #3a3f45; color: #a9a298; cursor: not-allowed; }
    .location-preview-image { width: 100%; max-height: 360px; object-fit: cover; border-radius: 6px; border: 1px solid #34383d; margin: 8px 0 12px; }
    .scene-thumb { width: 180px; height: 96px; object-fit: cover; border-radius: 5px; border: 1px solid #34383d; float: right; margin: 0 0 10px 14px; }
    .hint-panel { margin-top: 10px; padding-top: 10px; border-top: 1px solid #34383d; }
    .hint-panel[hidden] { display: none; }
    .debug-panel { margin-top: 10px; }
    details.debug-panel summary { cursor: pointer; color: #a9a298; }
    .log-toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: end; margin: 8px 0 10px; }
    .log-toolbar input { width: 220px; }
    .log-meta { color: #a9a298; font-size: 12px; word-break: break-all; margin: 6px 0 10px; }
    .log-event { border-left: 3px solid #3a3f45; padding: 8px 10px; margin: 0 0 8px; background: #14181d; }
    .log-event.important { border-left-color: #f5c542; background: #1d1a11; }
    .log-event.effect { border-left-color: #3fb950; background: #111d16; }
    .log-event .event-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .log-event code { color: #d2e7ff; }
    .log-event details { margin-top: 6px; }
    .log-event summary { cursor: pointer; color: #a9a298; }
    .status { border-left: 3px solid #f5c542; padding: 10px 12px; margin: 0 0 12px; background: #211f16; color: #f5e3a1; }
    .status[hidden] { display: none; }
    .status-list { display: grid; gap: 8px; margin-top: 6px; }
    .status-item { border-bottom: 1px solid #34383d; padding-bottom: 7px; }
    .status-item.defeated { opacity: 0.55; }
    .status-item:last-child { border-bottom: 0; padding-bottom: 0; }
    .status-item b { display: block; }
    .combat-current-step { border: 1px solid #4b4227; border-radius: 6px; background: #181713; padding: 12px; }
    .combat-prompt { border-left: 4px solid #f5c542; background: #211f16; color: #f5e3a1; padding: 12px 14px; margin: 0 0 10px; }
    .combat-prompt b { display: block; font-size: 18px; margin-bottom: 4px; }
    .combat-mini-status { display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 10px; color: #d6d0c4; font-size: 13px; }
    .combat-mini-status span { border: 1px solid #34383d; border-radius: 999px; padding: 3px 8px; background: #111417; }
    .status-chips { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0 10px; }
    .status-chip { border: 1px solid #34383d; border-radius: 999px; padding: 3px 8px; background: #111417; color: #d6d0c4; font-size: 12px; line-height: 1.35; }
    .status-chip.ready { border-color: #2f8f55; color: #d7f6df; background: #102018; }
    .status-chip.spent { border-color: #5a6068; color: #a9a298; background: #151719; }
    .status-chip.movement { border-color: #2f6feb; color: #d2e7ff; background: #111927; }
    .status-chip.magic { border-color: #9b74ff; color: #eadfff; background: #1a1428; }
    .status-chip.offense { border-color: #d88b26; color: #ffe1b8; background: #24170b; }
    .status-chip.defense { border-color: #3fb950; color: #d7f6df; background: #102018; }
    .status-chip.penalty { border-color: #db6d6d; color: #ffd6d6; background: #241111; }
    .status-chip.danger { border-color: #db6d6d; color: #ffd6d6; background: #241111; }
    .combat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin: 0 0 12px; }
    .combat-section { border: 1px solid #34383d; border-radius: 6px; padding: 10px 12px; background: #171b20; }
    .combat-section h4 { margin: 0 0 7px; font-size: 14px; color: #f5e3a1; }
    .combat-section p { margin: 0 0 7px; }
    .combat-section p:last-child { margin-bottom: 0; }
    .combat-empty { color: #a9a298; }
    .combat-stage { display: grid; gap: 12px; margin: 0 0 12px; }
    .combat-action-card { border: 1px solid #34383d; border-radius: 6px; padding: 10px; background: #171b20; }
    .combat-action-card p { margin: 0 0 8px; }
    .combat-last-result { border-left: 3px solid #3fb950; padding: 10px 12px; background: #132018; }
    .combat-last-result h4 { margin: 0 0 6px; color: #d7f6df; }
    .combat-effects { border: 1px solid #34383d; border-radius: 6px; padding: 10px 12px; background: #151a20; }
    .combat-effects h4 { margin: 0 0 7px; color: #f5e3a1; font-size: 14px; }
    .combat-effect-list { display: grid; gap: 6px; }
    .combat-effect { border-left: 3px solid #58a6ff; padding: 6px 8px; background: #10151a; }
    .combat-effect b { display: block; }
    .combat-details { border-top: 1px solid #34383d; margin-top: 12px; padding-top: 10px; }
    .combat-details summary { cursor: pointer; color: #a9a298; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    input, textarea, button { font: inherit; }
    textarea { width: 100%; min-height: 80px; box-sizing: border-box; background: #0f1113; color: #ece7dc; border: 1px solid #3a3f45; border-radius: 5px; padding: 10px; }
    input { width: 90px; background: #0f1113; color: #ece7dc; border: 1px solid #3a3f45; border-radius: 5px; padding: 8px; }
    select { background: #0f1113; color: #ece7dc; border: 1px solid #3a3f45; border-radius: 5px; padding: 8px; }
    .wide-input { width: 100%; box-sizing: border-box; margin-top: 5px; }
    button { background: #2f6feb; color: white; border: 0; border-radius: 5px; padding: 9px 12px; cursor: pointer; }
    button.secondary { background: #3a3f45; }
    button.danger { background: #b42318; }
    pre { white-space: pre-wrap; overflow: auto; }
  </style>
</head>
<body>
<button id="side-panel-toggle" class="side-panel-toggle" data-allow-busy="true" onclick="toggleSidePanel()" aria-controls="side-panel" aria-expanded="false" title="Panel boczny">☰</button>
<div id="side-panel-scrim" class="side-panel-scrim" data-allow-busy="true" onclick="setSidePanelOpen(false)"></div>
<main>
  <aside id="side-panel" aria-hidden="true">
    <div class="side-panel-head">
      <h2 id="scenario">Scenariusz</h2>
      <button class="side-panel-close" data-allow-busy="true" onclick="setSidePanelOpen(false)" aria-label="Zamknij panel">×</button>
    </div>
    <div class="card"><b>Lokacja</b><div id="zone"></div></div>
    <div class="card"><b>Wyzwanie</b><div id="challenge"></div></div>
    <div class="card"><b>Jawne elementy sceny</b><div id="visible-environment"></div></div>
    <div class="card"><b>Zasoby</b><div id="resources"></div></div>
    <div class="card">
      <b>Plansza</b>
      <div id="board-status" class="muted"></div>
      <label>Tryb
        <select id="board-backend">
          <option value="none">brak</option>
          <option value="simulator">symulator</option>
          <option value="hardware">hardware</option>
        </select>
      </label>
      <label>URL symulatora <input id="board-url" class="wide-input" value="http://127.0.0.1:5000"></label>
      <label>Port hardware <input id="board-serial-port" class="wide-input" placeholder="/dev/ttyUSB0"></label>
      <label>WLED URL <input id="wled-url" class="wide-input" placeholder="http://adres-wled"></label>
      <label>Timeout skanu <input id="scan-timeout" type="number" min="1" max="120" value="30"></label>
      <div class="row" style="margin-top:8px">
        <button onclick="configureBoard()">Zastosuj</button>
        <button class="secondary" onclick="scanBoard()">Skanuj planszę</button>
        <button class="secondary" data-allow-busy="true" onclick="resetBoardScan()">Reset skanu</button>
      </div>
    </div>
    <button class="secondary" onclick="resetSession()">Reset</button>
  </aside>
  <section>
    <h1 id="page-title">Eksploracja</h1>
    <div id="status" class="status" hidden></div>
    <div class="card" id="flow-panel"></div>
    <div class="card scene-description" id="scene-description-card">
      <h3>Opis sceny</h3>
      <div id="scene-description"></div>
    </div>
    <div class="card" id="result-panel">
      <h3>Wynik</h3>
      <div id="result"></div>
      <button onclick="ackResult()">Dalej</button>
    </div>
    <div class="card" id="encounter-panel">
      <h3 id="encounter-title">Zaczyna się encounter</h3>
      <div id="encounter"></div>
    </div>
    <div class="card" id="travel-panel">
      <h3>Dostępne przejścia</h3>
      <div id="travel-options"></div>
    </div>
    <div class="card" id="points-panel">
      <h3>Odkryte punkty</h3>
      <div id="point-options"></div>
    </div>
    <div class="card" id="pending-panel">
      <h3>Decyzja MG</h3>
      <div id="pending"></div>
      <div id="lead-actor-choice"></div>
      <div class="row" style="margin-top:8px">
        <button onclick="decision('accept')">Akceptuj</button>
        <button class="danger" onclick="decision('reject')">Odrzuć</button>
        <button class="secondary" onclick="decision('explain')">Wyjaśnij</button>
      </div>
    </div>
    <div class="card" id="action-panel">
      <h3 id="action-title">Co robi drużyna?</h3>
      <textarea id="action"></textarea>
      <div class="row" style="margin-top:8px">
        <button onclick="sendAction()">Wyślij</button>
      </div>
    </div>
    <div class="card" id="roll-panel">
      <h3>Rzuty</h3>
      <div id="roll-prompt"></div>
      <div id="rolls"></div>
      <button onclick="sendRolls()">Rozstrzygnij rzuty</button>
    </div>
    <details class="card debug-panel">
      <summary>Historia komunikatów</summary>
      <div id="messages"></div>
    </details>
    <details class="card debug-panel" id="session-log-panel">
      <summary>Log sesji</summary>
      <div class="log-meta" id="session-log-meta"></div>
      <div class="log-toolbar">
        <label>Filtr event type <input id="session-log-filter" data-allow-busy="true" placeholder="np. ui_effect_applied" oninput="renderSessionLog()"></label>
        <button class="secondary" data-allow-busy="true" onclick="refreshSessionLog()">Odśwież log</button>
      </div>
      <div id="session-log-events" class="muted">Log nie został jeszcze wczytany.</div>
    </details>
    <details class="card debug-panel">
      <summary>Debug payload</summary>
      <pre id="debug-payload"></pre>
    </details>
  </section>
</main>
<script>
let state = null;
let busy = false;
let resultAck = null;
let playerTurnScanLoop = false;
let boardScanInFlight = false;
let boardScanToken = 0;
let sessionLog = null;
let sidePanelOpen = localStorage.getItem('explorationSidePanelOpen') === 'true';
function setSidePanelOpen(open) {
  sidePanelOpen = Boolean(open);
  localStorage.setItem('explorationSidePanelOpen', sidePanelOpen ? 'true' : 'false');
  document.body.classList.toggle('side-panel-open', sidePanelOpen);
  const panel = document.getElementById('side-panel');
  const toggle = document.getElementById('side-panel-toggle');
  if (panel) panel.setAttribute('aria-hidden', sidePanelOpen ? 'false' : 'true');
  if (toggle) toggle.setAttribute('aria-expanded', sidePanelOpen ? 'true' : 'false');
}
function toggleSidePanel() {
  setSidePanelOpen(!sidePanelOpen);
}
function setBusy(message) {
  busy = Boolean(message);
  const status = document.getElementById('status');
  status.hidden = !busy;
  status.textContent = message || '';
  document.querySelectorAll('button, textarea, input').forEach(el => {
    if (el.closest('details.debug-panel')) return;
    if (el.dataset.allowBusy === 'true') return;
    el.disabled = busy;
  });
}
async function api(path, body, busyMessage) {
  setBusy(busyMessage || 'Czekam na odpowiedź...');
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
    const data = await res.json();
    if (!res.ok) alert(data.error || 'Błąd');
    state = data.state || data;
  if (path === '/api/rolls' && res.ok) {
      resultAck = state.flow && state.flow.stage === 'interaction_result' ? null : latestResultMessage(state);
    } else if (path !== '/api/decision') {
      resultAck = null;
    }
    render();
    refreshSessionLog();
  } finally {
    setBusy('');
  }
}
async function loadState() {
  const res = await fetch('/api/state');
  state = await res.json();
  render();
  refreshSessionLog();
}
function render() {
  const inCombat = Boolean(state.combat);
  document.getElementById('page-title').textContent = inCombat ? 'Walka' : 'Eksploracja';
  document.getElementById('encounter-title').textContent = inCombat ? 'Walka' : 'Zaczyna się encounter';
  document.getElementById('scenario').textContent = state.scenario.name;
  document.getElementById('zone').textContent = state.current_zone.name;
  document.getElementById('challenge').textContent = state.active_challenge ? `${state.active_challenge.name}: ${state.active_challenge.current_progress}/${state.active_challenge.progress_required}, hałas ${state.active_challenge.noise}` : 'Brak';
  document.getElementById('visible-environment').innerHTML = visibleEnvironmentHtml();
  document.getElementById('resources').innerHTML = state.resources.map(r => `<div>${r.label}</div>`).join('') || 'Brak';
  renderBoardPanel();
  document.getElementById('flow-panel').innerHTML = flowPanelHtml();
  const sceneHtml = sceneDescriptionHtml(state);
  document.getElementById('scene-description').innerHTML = sceneHtml;
  document.getElementById('scene-description-card').hidden = !sceneHtml;
  document.getElementById('messages').innerHTML = state.messages.map(m => `<div class="message"><b>${m.title}</b><br>${m.body}</div>`).join('');
  document.getElementById('pending').innerHTML = pendingHtml(state.pending);
  document.getElementById('lead-actor-choice').innerHTML = leadActorChoiceHtml();
  document.getElementById('result').innerHTML = resultAck ? `<div class="result"><b>${esc(resultAck.title)}</b><br>${esc(resultAck.body)}</div>` : '';
  document.getElementById('encounter').innerHTML = encounterHtml();
  document.getElementById('travel-options').innerHTML = travelOptionsHtml();
  document.getElementById('point-options').innerHTML = pointOptionsHtml();
  document.getElementById('roll-prompt').innerHTML = rollPromptHtml();
  document.getElementById('rolls').innerHTML = state.required_rolls.map(r => {
    const sides = Number(r.die_sides || 20);
    const value = sides === 100 ? 50 : 10;
    return `<label>${esc(r.actor_name)} ${esc(r.label || `d${sides}`)}: <input data-actor="${esc(r.actor_id)}" type="number" min="1" max="${sides}" value="${value}"></label>`;
  }).join(' ');
  document.getElementById('debug-payload').textContent = JSON.stringify(state, null, 2);
  renderSessionLogMeta();
  document.getElementById('action-title').textContent = state.active_point && state.active_point.has_npc ? 'Co robicie wobec NPC?' : 'Co robi drużyna?';
  updateActivePanel();
}
function renderBoardPanel() {
  const board = state.board || {};
  document.getElementById('board-status').textContent = `${board.message || 'Plansza niepodłączona.'} Domyślny backend z configu: ${board.configured_backend || '-'}.`;
  document.getElementById('board-backend').value = board.backend || 'none';
  document.getElementById('board-url').value = board.board_url || 'http://127.0.0.1:5000';
  document.getElementById('board-serial-port').value = board.board_serial_port || '';
  document.getElementById('wled-url').value = board.wled_url || '';
  document.getElementById('scan-timeout').value = board.scan_timeout_s || 30;
}
function esc(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
async function refreshSessionLog() {
  const res = await fetch('/api/session-log');
  sessionLog = await res.json();
  renderSessionLog();
}
function renderSessionLogMeta() {
  const meta = document.getElementById('session-log-meta');
  if (!meta || !state || !state.session_log) return;
  meta.innerHTML = `Session: <code>${esc(state.session_log.session_id)}</code><br>Plik: <code>${esc(state.session_log.path)}</code>`;
}
function renderSessionLog() {
  renderSessionLogMeta();
  const container = document.getElementById('session-log-events');
  if (!container) return;
  if (!sessionLog) {
    container.innerHTML = '<span class="muted">Log nie został jeszcze wczytany.</span>';
    return;
  }
  const filter = (document.getElementById('session-log-filter')?.value || '').trim().toLowerCase();
  const events = (sessionLog.events || []).filter(event => !filter || String(event.event_type || '').toLowerCase().includes(filter));
  if (!events.length) {
    container.innerHTML = '<span class="muted">Brak eventów dla aktualnego filtra.</span>';
    return;
  }
  container.innerHTML = events.slice().reverse().map(event => sessionLogEventHtml(event)).join('');
}
function sessionLogEventHtml(event) {
  const type = String(event.event_type || '');
  const payload = event.payload || {};
  const classes = ['log-event'];
  if (type === 'ui_effect_applied') classes.push('effect');
  if (['ui_action_submitted','ui_npc_proposal_validated','ui_gm_proposal_validated','ui_rolls_resolved','ui_effect_applied','ui_challenge_resolved'].includes(type)) {
    classes.push('important');
  }
  const summary = sessionLogSummary(type, payload);
  return `
    <div class="${classes.join(' ')}">
      <div class="event-head">
        <div><code>${esc(type)}</code> <span class="muted">#${esc(event.seq)}</span></div>
        <div class="muted">${esc(event.ts || '')}</div>
      </div>
      ${summary ? `<div>${summary}</div>` : ''}
      <details><summary>Payload JSON</summary><pre>${esc(JSON.stringify(payload, null, 2))}</pre></details>
    </div>
  `;
}
function sessionLogSummary(type, payload) {
  if (type === 'ui_action_submitted') return `Deklaracja: ${esc(payload.text || '')}`;
  if (type === 'ui_effect_applied') {
    const effect = payload.effect || {};
    return `Efekt: ${esc(payload.effect_type || effect.type || '')}; źródło: ${esc(payload.source || '')}; zmiana stanu: ${payload.changed ? 'tak' : 'nie'}`;
  }
  if (type === 'ui_npc_proposal_validated') return `NPC point: ${esc(payload.point_id || '')}`;
  if (type === 'ui_gm_proposal_validated') return `Challenge: ${esc(payload.challenge_id || '')}`;
  if (type === 'ui_rolls_resolved') return `Rzuty dla: ${esc(payload.pending_kind || '')}`;
  if (type === 'ui_challenge_resolved') return `Challenge: ${esc(payload.challenge_id || '')}; completed: ${payload.completed ? 'tak' : 'nie'}`;
  if (type === 'ui_message_added') return `${esc(payload.title || '')}: ${esc(payload.body || '')}`;
  return '';
}
function listHtml(items) {
  if (!items || !items.length) return '';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}
function sceneStatusHtml() {
  const items = state.scene_status || [];
  if (!items.length) return '<span class="muted">Brak zmian.</span>';
  return `<div class="status-list">${items.map(item => `
    <div class="status-item"><b>${esc(item.label)}</b><span>${esc(item.value)}</span></div>
  `).join('')}</div>`;
}
function flowPanelHtml() {
  const flow = state.flow || {};
  const stage = flow.stage || 'waiting_for_board';
  if (stage === 'waiting_for_board') {
    return `
      <div class="start-panel"><div class="inner">
        <h2>Wybierz planszę</h2>
        <p>Najpierw wybierz backend planszy w panelu po lewej: <b>symulator</b> albo <b>hardware</b>, a potem kliknij <b>Zastosuj</b>.</p>
        <p class="muted">Tryb „brak” zostaje tylko do testów technicznych i nie uruchamia normalnej sesji gracza.</p>
        <button class="start-button" disabled>Start</button>
      </div></div>
    `;
  }
  if (stage === 'ready_to_start') {
    return `
      <div class="start-panel"><div class="inner">
        <h2>Plansza gotowa</h2>
        <p>Backend planszy jest podłączony. Kliknij Start, żeby pokazać jawne elementy sceny na planszy.</p>
        <button class="start-button" onclick="startSession()">Start</button>
      </div></div>
    `;
  }
  if (stage === 'party_setup') {
    const setup = state.exploration_setup;
    if (setup && setup.current_step) {
      const step = setup.current_step || {};
      const hasPositions = Boolean(step.has_positions);
      const positions = (step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
      return `
        <h3>Setup mapy ${Number(setup.current_index) + 1}/${setup.step_count}</h3>
        <p><b>${esc(step.label || '')}</b></p>
        <p>${esc(step.message || '')}</p>
        ${hasPositions ? `<p><b>Kolor:</b> ${esc(step.color || '-')}</p><p><b>Pola:</b> ${esc(positions)}</p>` : '<p class="muted">Ten krok jest tylko instrukcją i nie podświetla pól na planszy.</p>'}
        <p class="muted">${hasPositions ? 'Rozstaw elementy na fizycznej planszy. Jeśli potwierdzasz planszą, najpierw kliknij Skanuj planszę.' : 'Potwierdź, żeby przejść do pierwszego podświetlanego elementu mapy.'}</p>
        <div class="row"><button onclick="confirmExplorationSetup()">Potwierdź setup</button>${hasPositions ? '<button class="secondary" data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>' : ''}</div>
      `;
    }
    return `
      <h3>Setup drużyny</h3>
      <p>Ustaw figurkę drużyny na podświetlonym polu.</p>
      <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      <p class="muted">Po uruchomieniu skanu kliknij podświetlone pole.</p>
    `;
  }
  if (stage === 'location_preview') {
    const preview = flow.preview_zone;
    if (!preview) {
      return `
        <h3>Jawne elementy sceny</h3>
        ${availableLocationsHtml(flow.available_locations || [])}
        <p>Kliknij Skanuj planszę, a potem wskaż element sceny.</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    const image = preview.image_url ? `<img class="location-preview-image" src="${esc(preview.image_url)}" alt="${esc(preview.name)}">` : '';
    if (preview.available === false) {
      return `
        <h3>Podgląd elementu</h3>
        ${image}
        <p><b>${esc(preview.name)}</b></p>
        <p>${esc(preview.description || preview.summary || '')}</p>
        <div class="status">${esc(preview.locked_reason || 'Ten element jest jeszcze zablokowany.')}</div>
        <button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wróć do wyboru elementów</button>
      `;
    }
    return `
      <h3>Podgląd elementu</h3>
      ${image}
      <p><b>${esc(preview.name)}</b></p>
      <p>${esc(preview.description || preview.summary || '')}</p>
      <p><b>Czy chcesz wejść w interakcję?</b> Potwierdź Enterem albo przyciskiem.</p>
      <div class="row"><button onclick="confirmLocationPreview()">Wejdź w eksplorację</button><button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wróć do wyboru elementów</button></div>
    `;
  }
  if (stage === 'interaction_result') {
    const result = flow.interaction_result || {};
    const unlocked = result.unlocked_zones || [];
    const points = result.revealed_points || [];
    return `
      <h3>${esc(result.title || 'Wynik interakcji')}</h3>
      <div class="result">${esc(result.body || '')}</div>
      ${unlocked.length ? `<p><b>Odblokowano lokacje:</b></p><ul>${unlocked.map(zone => `<li>${esc(zone.name)}</li>`).join('')}</ul>` : ''}
      ${points.length ? `<p><b>Ujawniono punkty:</b></p><ul>${points.map(point => `<li>${esc(point.name)}</li>`).join('')}</ul>` : ''}
      <p class="muted">${esc(result.next_instruction || 'Zakończ interakcję, aby wrócić do wyboru lokacji.')}</p>
      <button onclick="finishInteraction()">Zakończ interakcję</button>
    `;
  }
  return '';
}
function availableLocationsHtml(locations) {
  if (!locations.length) return '<p>Brak jawnych elementów sceny.</p>';
  return `<ul>${locations.map(zone => {
    const status = zone.available === false ? `zablokowane: ${esc(zone.locked_reason || '')}` : 'dostępne';
    return `<li><b>${esc(zone.name)}</b>: kolor ${esc(colorNameForZone(zone))}, ${status}</li>`;
  }).join('')}</ul>`;
}
function colorNameForZone(zone) {
  return zone.color || 'kolor specjalny';
}
function visibleEnvironmentHtml() {
  const entries = state.visible_environment || [];
  if (!entries.length) return '<div class="muted">Brak jawnych elementów.</div>';
  return entries.map(entry => {
    const positions = (entry.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
    const blocked = entry.blocks_movement ? 'blokuje ruch' : 'można wejść';
    return `
      <div class="status-item" style="margin:6px 0">
        <b>${esc(entry.name)}</b>
        <span>${esc(entry.label || entry.type || '')}${entry.color ? ` | ${esc(entry.color)}` : ''}</span>
        <span>${positions ? `pola ${esc(positions)} | ` : ''}${esc(blocked)}</span>
      </div>
    `;
  }).join('');
}
function sceneDescriptionHtml(state) {
  const zone = state.current_zone || {};
  const challenge = state.active_challenge;
  const stage = state.flow ? state.flow.stage : 'location_active';
  if (stage !== 'location_active') {
    return '';
  }
  const parts = [
    `<p><b>${esc(zone.name)}</b></p>`,
    zone.image_url ? `<img class="scene-thumb" src="${esc(zone.image_url)}" alt="${esc(zone.name)}">` : '',
    zone.description ? `<p>${esc(zone.description)}</p>` : '',
    zone.summary ? `<p>${esc(zone.summary)}</p>` : '',
  ];
  if (zone.available_materials && zone.available_materials.length) {
    parts.push(`<p><b>Widoczne elementy otoczenia:</b></p>${listHtml(zone.available_materials)}`);
  }
    if (challenge) {
    parts.push(`<p><b>${esc(challenge.name)}</b></p>`);
    if (challenge.summary) parts.push(`<p>${esc(challenge.summary)}</p>`);
    parts.push(`<p><b>Postęp:</b> ${challenge.current_progress}/${challenge.progress_required}. <b>Hałas:</b> ${challenge.noise}.</p>`);
    if (challenge.complications && challenge.complications.length) {
      parts.push(`<p><b>Komplikacje:</b> ${challenge.complications.map(esc).join(', ')}</p>`);
    }
    if (challenge.options && challenge.options.length) {
      parts.push(challengeOptionsHtml(challenge.options));
    }
    const hasHints = (challenge.reasonable_approaches && challenge.reasonable_approaches.length)
      || (challenge.risk_notes && challenge.risk_notes.length);
    if (hasHints) {
      const hints = [];
      if (challenge.reasonable_approaches && challenge.reasonable_approaches.length) {
        hints.push(`<p><b>Sensowne podejścia:</b></p>${listHtml(challenge.reasonable_approaches)}`);
      }
      if (challenge.risk_notes && challenge.risk_notes.length) {
        hints.push(`<p><b>Ryzyka:</b></p>${listHtml(challenge.risk_notes)}`);
      }
      parts.push(`
        <button class="secondary" type="button" onclick="toggleHints()">Pokaż wskazówki MG</button>
        <div id="gm-hints" class="hint-panel" hidden>${hints.join('')}</div>
      `);
    }
  }
  if (state.active_point) {
    const point = state.active_point;
    parts.push(`<p><b>${esc(point.name)}</b></p>`);
    parts.push(point.description ? `<p>${esc(point.description)}</p>` : '');
    if (point.npc) {
      parts.push(`<p>${esc(point.npc.public_description)}</p>`);
      if (point.npc.current_state) parts.push(`<p><b>Stan NPC:</b> ${esc(point.npc.current_state)}</p>`);
    }
  }
  if (!challenge && state.travel_options && state.travel_options.length) {
    parts.push(`<p><b>Droga dalej jest otwarta.</b> Zakończ interakcję albo wybierz lokację na planszy.</p>`);
  }
  const html = parts.filter(Boolean).join('');
  return html.trim() ? html : '';
}
function challengeOptionsHtml(options) {
  return `
    <div class="status-list">
      ${options.map(option => {
        const skill = option.skill ? `/${esc(option.skill)}` : '';
        const requirements = challengeOptionRequirementsText(option);
        const actors = (option.eligible_actors || []).map(actor => actor.name).join(', ');
        return `
          <div class="status-item">
            <b>${esc(option.label)}</b>
            <div>${esc(option.description || '')}</div>
            <div class="muted">Test: ${esc(option.ability)}${skill}, ST ${esc(option.dc)}. Sukces +${esc(option.progress_on_success)}, porażka +${esc(option.progress_on_failure)}.</div>
            ${requirements ? `<div class="muted">Wymaga: ${requirements}</div>` : ''}
            ${challengeOptionBonusesText(option) ? `<div class="muted">Premie: ${challengeOptionBonusesText(option)}</div>` : ''}
            ${actors ? `<div class="muted">Może wykonać: ${esc(actors)}</div>` : ''}
          </div>
        `;
      }).join('')}
    </div>
  `;
}
function challengeOptionRequirementsText(option) {
  const parts = [];
  if (option.requires_item_ids && option.requires_item_ids.length) parts.push(`item ${option.requires_item_ids.map(esc).join(', ')}`);
  if (option.requires_spell_ids && option.requires_spell_ids.length) parts.push(`czar ${option.requires_spell_ids.map(esc).join(', ')}`);
  if (option.requires_ability_scores && option.requires_ability_scores.length) {
    parts.push(option.requires_ability_scores.map(req => `${esc(req.ability)} ${esc(req.minimum)}`).join(', '));
  }
  return parts.join('; ');
}
function challengeOptionBonusesText(option) {
  const bonuses = option.bonuses || [];
  return bonuses.map(bonus => {
    const mod = Number(bonus.modifier || 0);
    const breakage = bonus.breakage_risk ? `, ryzyko uszkodzenia ${esc(bonus.breakage_risk.chance_percent)}% przy krytycznej porażce` : '';
    const spellLevel = Number(bonus.spell_level || 0);
    const spellCost = bonus.source_type === 'spell' ? (spellLevel > 0 ? `, zużywa slot ${spellLevel}. poziomu` : ', cantrip bez slota') : '';
    return `${esc(bonus.label || bonus.source_id)} ${signedNumber(mod)}${spellCost}${breakage}`;
  }).join('; ');
}
function toggleHints() {
  const panel = document.getElementById('gm-hints');
  if (!panel) return;
  panel.hidden = !panel.hidden;
  const button = panel.previousElementSibling;
  if (button) button.textContent = panel.hidden ? 'Pokaż wskazówki MG' : 'Ukryj wskazówki MG';
}
function pendingHtml(pending) {
  if (!pending) return '';
  const proposal = pending.proposal || {};
  const option = pending.option || {};
  const lines = [];
  if (proposal.player_narration) lines.push(`<p>${esc(proposal.player_narration)}</p>`);
  if (proposal.npc_response) lines.push(`<p><b>NPC:</b> ${esc(proposal.npc_response)}</p>`);
  if (option.label) {
    const skill = option.skill ? `/${esc(option.skill)}` : '';
    lines.push(`<p><b>Podejście:</b> ${esc(option.label)}. Test: ${esc(option.ability)}${skill}, ST ${esc(option.dc)}.</p>`);
    lines.push(`<p><b>Postęp:</b> sukces +${esc(option.progress_on_success)}, porażka +${esc(option.progress_on_failure)}.</p>`);
  } else if (proposal.action_type) {
    if (proposal.requires_roll) {
      const skill = proposal.skill ? `/${esc(proposal.skill)}` : '';
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Test: ${esc(proposal.ability)}${skill}, ST ${esc(proposal.dc)}.</p>`);
    } else {
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Bez rzutu.</p>`);
    }
  }
  return lines.join('') || '<p>MG proponuje interpretację deklaracji.</p>';
}
function leadActorChoiceHtml() {
  if (!state.pending || state.pending.stage !== 'decision' || !state.actors || state.actors.length < 2) return '';
  const options = state.actors.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)}</option>`).join('');
  return `<label><b>Kto prowadzi test?</b> <select id="lead-actor">${options}</select></label>`;
}
function rollPromptHtml() {
  if (!state.pending) return '';
  if (state.pending.stage === 'breakage') {
    const info = state.pending.breakage || {};
    return `<p><b>Test trwałości:</b> rzuć k100 dla ${esc(info.item_label || info.item_id || 'przedmiotu')}. Wynik ${esc(info.chance_percent || 0)} lub mniej oznacza uszkodzenie.</p>`;
  }
  if (state.pending.stage !== 'roll') return '';
  const plan = state.pending.check_plan || {};
  const participants = {
    single_actor: 'rzuca jeden wybrany bohater',
    lead_with_help: 'rzuca prowadzący z pomocą',
    whole_party: 'rzuca cała drużyna',
    selected_actors: 'rzucają wybrani bohaterowie'
  }[plan.participants] || plan.participants || 'rzut eksploracyjny';
  const aggregation = {
    lead_result: 'liczy się wynik prowadzącego',
    highest: 'liczy się najwyższy wynik',
    lowest: 'liczy się najniższy wynik',
    majority_success: 'sukces, jeśli zda co najmniej połowa'
  }[plan.aggregation] || plan.aggregation || '';
  const names = (state.required_rolls || []).map(r => r.actor_name).join(', ');
  const bonuses = (plan.option_bonuses || []).filter(bonus => Number(bonus.modifier || 0) !== 0);
  const bonusHtml = bonuses.length
    ? `<p><b>Aktywne premie:</b> ${bonuses.map(bonus => {
        const spellLevel = Number(bonus.spell_level || 0);
        const spellCost = bonus.source_type === 'spell' ? (spellLevel > 0 ? `, zużyje slot ${spellLevel}. poziomu` : ', cantrip bez slota') : '';
        return `${esc(bonus.actor_name || '')}: ${esc(bonus.label || bonus.source_id)} ${signedNumber(Number(bonus.modifier || 0))}${spellCost}`;
      }).join('; ')}</p>`
    : '';
  return `<p><b>Format rzutu:</b> ${esc(participants)}${aggregation ? `, ${esc(aggregation)}` : ''}.</p><p><b>Rzucają:</b> ${esc(names || '-')}</p>${bonusHtml}`;
}
function latestResultMessage(state) {
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].title && messages[i].title.startsWith('Wynik')) return messages[i];
  }
  return messages[messages.length - 1] || null;
}
function travelOptionsHtml() {
  const zones = state.travel_options || [];
  if (!zones.length) return '<p>Brak dostępnych przejść z tej lokacji.</p>';
  return zones.map(zone => `
    <div class="row" style="justify-content:space-between; margin: 6px 0">
      <div><b>${esc(zone.name)}</b><br><span class="muted">${esc(zone.description)}</span></div>
      <button onclick="travel('${esc(zone.id)}')">Przejdź</button>
    </div>
  `).join('');
}
function encounterHtml() {
  const encounter = state.pending_encounter;
  if (!encounter) return '';
  if (state.combat) return combatStartHtml();
  const setup = state.encounter_setup;
  const initiative = state.encounter_initiative;
  const setupHtml = encounterSetupHtml(setup);
  const initiativeHtml = encounterInitiativeHtml(setup, initiative);
  const combatHtml = combatStartHtml();
  return `
    <p><b>${esc(encounter.name)}</b></p>
    <p>${esc(encounter.description)}</p>
    <p><b>Powód:</b> ${esc(encounter.reason)}</p>
    <p><b>Scenariusz encountera:</b> ${esc(encounter.encounter_scenario)}</p>
    ${setupHtml}
    ${initiativeHtml}
    ${combatHtml}
    ${state.combat ? '' : `<details class="debug-panel"><summary>Komenda awaryjna terminala</summary><pre>${esc(encounter.command)}</pre></details>`}
  `;
}
function encounterSetupHtml(setup) {
  if (!setup) {
    return `
      <div class="message"><b>Setup przed walką</b><br>Rozpocznijcie setup encountera. Jawne elementy sceny są już na planszy.</div>
      <button onclick="startEncounterSetup()">Rozpocznij setup</button>
    `;
  }
  if (setup.status === 'completed') {
    return '<div class="result"><b>Setup zakończony</b><br>Plansza jest przygotowana do inicjatywy i walki.</div>';
  }
  const step = setup.current_step || {};
  const hasPositions = Boolean(step.has_positions);
  const requiresBoardAssignment = Boolean(step.requires_board_assignment);
  const positions = (step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
  const availablePositions = (step.available_positions || step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
  const assignmentButtons = (step.available_positions || []).map(pos =>
    `<button class="secondary" onclick="selectBoardPosition(${Number(pos[0])}, ${Number(pos[1])})">(${Number(pos[0])},${Number(pos[1])})</button>`
  ).join('');
  return `
    <div class="message">
      <b>Krok ${Number(setup.current_index) + 1}/${setup.step_count}: ${esc(step.label || '')}</b><br>
      ${esc(step.message || '')}
      ${requiresBoardAssignment ? `<p><b>Aktualnie ustaw:</b> ${esc(step.assignment_actor_name || '-')}</p><p><b>Wolne pola:</b> ${esc(availablePositions || '-')}</p>` : ''}
      ${hasPositions && !requiresBoardAssignment ? `<p><b>Kolor:</b> ${esc(step.color || '-')}</p><p><b>Pola:</b> ${esc(positions)}</p>` : ''}
      ${!hasPositions ? '<p class="muted">Ten krok jest tylko instrukcją i nie podświetla pól na planszy.</p>' : ''}
    </div>
    ${requiresBoardAssignment
      ? `<div class="row"><button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>${assignmentButtons}</div><p class="muted">Postaw figurkę wskazanego bohatera na podświetlonym polu i uruchom skan. Przyciski pól są awaryjnym wyborem bez skanu planszy. Po ostatnim bohaterze gra przejdzie dalej.</p>`
      : '<button onclick="confirmEncounterSetup()">Potwierdź krok setupu</button>'}
  `;
}
function encounterInitiativeHtml(setup, initiative) {
  if (!setup || setup.status !== 'completed' || state.combat) return '';
  if (!initiative) {
    return `
      <div class="message"><b>Inicjatywa</b><br>Setup zakończony. Teraz ustalcie kolejność tur.</div>
      <button onclick="startEncounterInitiative()">Rozpocznij inicjatywę</button>
    `;
  }
  if (initiative.status === 'completed') return '';
  const prompt = initiative.current_prompt || {};
  return `
    <div class="message">
      <b>Rzut inicjatywy ${Number(initiative.current_prompt_index) + 1}/${initiative.prompt_count}</b><br>
      ${esc(prompt.message || 'Wpisz naturalny wynik d20.')}
    </div>
    <div class="row">
      <label>Wynik d20: <input id="encounter-initiative-roll" type="number" min="1" max="20" value="10"></label>
      <button onclick="submitEncounterInitiativeRoll()">Zapisz rzut</button>
    </div>
  `;
}
function combatStartHtml() {
  const combat = state.combat;
  if (!combat) return '';
  const order = state.encounter_initiative && state.encounter_initiative.order ? state.encounter_initiative.order : [];
  const actors = combat.actors || [];
  const finished = combat.status === 'finished';
  const actor = combat.current_actor || {};
  const isAllyTurn = actor.faction === 'ally';
  const isEnemyTurn = actor.faction === 'enemy';
  return `
    <div class="combat-stage">
      ${combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn)}
      ${combatActiveEffectsHtml(combat)}
      ${combatLastResultHtml()}
    </div>
    <details class="combat-details">
      <summary>Szczegóły walki</summary>
      <section class="combat-section">
        <h4>Aktualny aktor</h4>
        ${combatActorStatusHtml(combat)}
      </section>
      <section class="combat-section">
        <h4>Szczegóły aktualnego kroku</h4>
        ${combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn)}
      </section>
      <section class="combat-section">
        <h4>Wszystkie aktywne efekty</h4>
        ${combatAllEffectsHtml(combat)}
      </section>
      <p><b>Kolejność inicjatywy:</b> ${order.map(entry => `${esc(entry.actor_name)} (${entry.total})`).join(', ')}</p>
      <div class="status-list">
        ${actors.map(actor => `
          <div class="status-item${actor.defeated ? ' defeated' : ''}">
            <b>${esc(actor.name)} ${actor.id === combat.current_actor.id ? '(tura)' : ''}</b>
            <span>${esc(actor.faction)} | HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)} | pole (${esc(actor.position[0])},${esc(actor.position[1])})</span>
            ${statusChipsHtml(actor.status_chips || actorEffectChips(actor), 'Brak aktywnych statusów.')}
          </div>
        `).join('')}
      </div>
    </details>
  `;
}
function combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn) {
  return `
    <div class="combat-current-step">
      ${combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn)}
      ${combatMiniStatusHtml(combat)}
      <div class="combat-action-card">
        ${finished ? '<button onclick="resolveCombatOutcome()">Zastosuj wynik walki</button>' : combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn)}
      </div>
    </div>
  `;
}
function combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn) {
  return `
    <div class="combat-prompt">
      <b>${esc(combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn))}</b>
      <span>${esc(combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn))}</span>
    </div>
  `;
}
function combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn) {
  if (finished) return 'Walka zakończona';
  const actor = combat.current_actor || {};
  if (combat.pending_concentration_check) {
    const pendingActor = combat.pending_concentration_check.actor || {};
    return `${pendingActor.name || 'Bohater'}: test koncentracji`;
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) return `Tura ${actor.name || 'przeciwnika'}: Ready`;
    if (combat.pending_enemy_opportunity_attack) return `Tura ${actor.name || 'przeciwnika'}: reakcja bohatera`;
    if (combat.enemy_turn_result) return `Tura ${actor.name || 'przeciwnika'}: potwierdź wynik`;
    if (combat.enemy_turn_intent) return `Tura ${actor.name || 'przeciwnika'}: zamiar`;
    if (combat.enemy_turn_preview) return `Tura ${actor.name || 'przeciwnika'}: potwierdź planszą`;
    return `Tura ${actor.name || 'przeciwnika'}: rozegraj zamiar`;
  }
  if (isAllyTurn && combat.pending_player_attack) {
    if (combat.pending_player_attack.stage === 'confirm_attack') return `Tura ${actor.name || 'gracza'}: potwierdź atak`;
    return combat.pending_player_attack.stage === 'damage_roll'
      ? `Tura ${actor.name || 'gracza'}: wpisz obrażenia`
      : `Tura ${actor.name || 'gracza'}: rzuć d20`;
  }
  if (isAllyTurn && combat.pending_player_healing) return `Tura ${actor.name || 'gracza'}: wpisz leczenie`;
  if (isAllyTurn && combat.pending_area_spell) {
    return combat.pending_area_spell.stage === 'damage_roll'
      ? `Tura ${actor.name || 'gracza'}: obrażenia obszarowe`
      : `Tura ${actor.name || 'gracza'}: potwierdź obszar`;
  }
  if (isAllyTurn && combat.pending_opportunity_movement) return `Tura ${actor.name || 'gracza'}: atak okazyjny`;
  if (isAllyTurn && combat.pending_combat_help) return `Tura ${actor.name || 'gracza'}: Help`;
  if (isAllyTurn && combat.pending_concentration_action) return `Tura ${actor.name || 'gracza'}: koncentracja`;
  if (isAllyTurn && combat.pending_combat_ready) return `Tura ${actor.name || 'gracza'}: Ready`;
  if (isAllyTurn && combat.pending_combat_interaction) return `Tura ${actor.name || 'gracza'}: wybierz interakcję`;
  if (isAllyTurn && combat.movement_preview) return `Tura ${actor.name || 'gracza'}: potwierdź ruch`;
  if (isAllyTurn) return `Tura ${actor.name || 'gracza'}: wybierz ruch, cel albo obiekt`;
  return `Tura ${actor.name || '-'}`;
}
function combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn) {
  if (finished) return 'Zastosuj wynik walki, żeby wrócić do eksploracji.';
  const actor = combat.current_actor || {};
  if (combat.pending_concentration_check) {
    return combat.pending_concentration_check.instruction || 'Rzuć CON save, żeby utrzymać koncentrację.';
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) {
      const pendingReady = combat.pending_ready_attack;
      const attacker = pendingReady.attacker || {};
      const target = pendingReady.target || {};
      if (pendingReady.stage === 'choice') return `Warunek Ready został spełniony. ${attacker.name || 'Bohater'} może zaatakować ${target.name || 'przeciwnika'}.`;
      if (pendingReady.stage === 'damage_roll') return `Trafienie przygotowaną akcją. Rzuć obrażenia ${pendingReady.damage_instruction || ''} i wpisz wynik.`;
      return `${attacker.name || 'Bohater'} używa przygotowanej akcji. Rzuć d20 i wpisz naturalny wynik.`;
    }
    if (combat.pending_enemy_opportunity_attack) {
      const pendingOpportunity = combat.pending_enemy_opportunity_attack;
      const attacker = pendingOpportunity.attacker || {};
      const target = pendingOpportunity.target || {};
      if (pendingOpportunity.stage === 'choice') return `${target.name || 'Przeciwnik'} opuszcza zasięg ${attacker.name || 'bohatera'}. Wykonaj atak okazyjny albo pomiń reakcję.`;
      if (pendingOpportunity.stage === 'damage_roll') return `Trafienie atakiem okazyjnym. Rzuć obrażenia ${pendingOpportunity.damage_instruction || ''} i wpisz wynik.`;
      return `${attacker.name || 'Bohater'} wykonuje atak okazyjny. Rzuć d20 i wpisz naturalny wynik.`;
    }
    if (combat.enemy_turn_result) return 'Przeczytaj wynik tury przeciwnika i potwierdź go Enterem albo przyciskiem.';
    const intent = combat.enemy_turn_intent || null;
    if (intent) return `${intent.message || 'Przeciwnik deklaruje zamiar.'} Potwierdź, żeby przejść do wykonania na planszy.`;
    const preview = combat.enemy_turn_preview || null;
    if (preview && preview.kind === 'movement') {
      return `Przestaw ${preview.enemy_name} na pole (${preview.destination[0]},${preview.destination[1]}), uruchom skan i kliknij pole docelowe.`;
    }
    if (preview && preview.kind === 'attack') {
      return `${preview.enemy_name} atakuje ${preview.target_name}. Uruchom skan i kliknij podświetlony cel.`;
    }
    return 'Naciśnij Enter albo przycisk, żeby gra pokazała zamiar przeciwnika.';
  }
  if (!isAllyTurn) return 'Ten aktor nie ma automatycznych kontrolek w MVP. Możesz zakończyć turę.';
  if (combat.pending_opportunity_movement) {
    const pendingOpportunity = combat.pending_opportunity_movement;
    const names = (pendingOpportunity.threats || []).map(actor => actor.name).join(', ') || 'wróg';
    return `Ten ruch opuszcza zasięg: ${names}. Potwierdź, żeby rozstrzygnąć ataki okazyjne i wykonać ruch.`;
  }
  if (combat.pending_combat_help) {
    return 'Wybierz sojusznika i przeciwnika. Sojusznik dostanie przewagę na następny atak przeciw temu celowi.';
  }
  if (combat.pending_concentration_action) {
    return 'Wybierz sojusznika. Czar zużyje akcję i slot, a wcześniejsza koncentracja tego aktora zostanie zakończona.';
  }
  if (combat.pending_combat_ready) {
    return 'Wybierz warunek. Akcja zostanie zużyta teraz, a atak będzie można wykonać później reakcją.';
  }
  const pending = combat.pending_player_attack || null;
  if (pending) {
    const target = pending.target || {};
    const source = pending.source || {};
    if (pending.stage === 'confirm_attack') {
      if (source.save_ability) {
        return `Wybrano ${target.name || '-'}. Potwierdź czar, żeby przeciwnik wykonał automatyczny rzut obronny.`;
      }
      return `Wybrano ${target.name || '-'}. Potwierdź atak, żeby przejść do rzutu d20.`;
    }
    if (pending.stage === 'damage_roll') {
      return `Trafiono ${target.name || 'cel'}. Rzuć obrażenia ${pending.damage_instruction || source.damage_hint || ''} i wpisz wynik.`;
    }
    return `Wybrano cel ${target.name || '-'}. Rzuć d20 na atak ${source.name || ''} i wpisz naturalny wynik.`;
  }
  const pendingHealing = combat.pending_player_healing || null;
  if (pendingHealing) {
    const target = pendingHealing.target || {};
    const source = pendingHealing.source || {};
    return `Wybrano ${target.name || '-'}. Rzuć leczenie ${source.healing_hint || ''} i wpisz sumę.`;
  }
  const pendingArea = combat.pending_area_spell || null;
  if (pendingArea) {
    const source = pendingArea.source || {};
    const targets = (pendingArea.targets || []).map(target => target.name).join(', ') || 'brak celów';
    if (pendingArea.stage === 'damage_roll') return `Rzuć obrażenia ${source.damage_hint || ''} i wpisz sumę dla celów w obszarze.`;
    return `Wybrano obszar ${source.name || 'czaru'}. Cele: ${targets}. Potwierdź Enterem albo przyciskiem.`;
  }
  if (combat.pending_combat_interaction) {
    const pendingInteraction = combat.pending_combat_interaction;
    return `Wybrano obiekt ${pendingInteraction.object_name || '-'}. Wybierz interakcję i potwierdź przyciskiem albo Enterem.`;
  }
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  if (preview) {
    return `Wybrano ruch na (${preview.destination[0]},${preview.destination[1]}). Uruchom skan i kliknij pole docelowe, żeby zatwierdzić.`;
  }
  if (actionUsed && remaining > 0) return `Akcja zużyta. Możesz jeszcze ruszyć się (${remaining} ft) albo zakończyć turę.`;
  if (actionUsed) return 'Akcja zużyta. Możesz zakończyć turę.';
  if (remaining > 0) return `Kliknij Skanuj planszę, a potem wybierz niebieskie pole ruchu, czerwony cel, turkusowego rannego sojusznika albo zielony obiekt.`;
  return 'Ruch wykorzystany. Możesz zaatakować czerwony cel, uleczyć turkusowego sojusznika, użyć zielonego obiektu albo zakończyć turę.';
}
function combatMiniStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const position = actor.position || ['-', '-'];
  return `
    <div class="combat-mini-status">
      <span>Runda ${esc(combat.round_number || '-')}</span>
      <span>${esc(actor.name || '-')}</span>
      <span>HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)}</span>
      <span>Pole (${esc(position[0])},${esc(position[1])})</span>
      ${actor.faction === 'ally' ? `<span>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'}</span><span>Bonus: ${bonusActionUsed ? 'zużyta' : 'dostępna'}</span><span>Reakcja: ${reactionAvailable ? 'dostępna' : 'zużyta'}</span><span>Ruch: ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</span>` : ''}
    </div>
    ${statusChipsHtml(actor.status_chips || [], 'Brak statusów aktywnego aktora.')}
  `;
}
function combatActorStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  return `
    <p><b>${esc(actor.name || '-')}</b> (${esc(actor.faction || '-')})</p>
    <p>Runda ${esc(combat.round_number || '-')}, pole (${esc(actor.position ? actor.position[0] : '-')},${esc(actor.position ? actor.position[1] : '-')})</p>
    <p>HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)}</p>
    ${actorInventoryHtml(actor)}
    ${actor.faction === 'ally' ? `<p>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'} | Bonus action: ${bonusActionUsed ? 'zużyta' : 'dostępna'} | Reakcja: ${reactionAvailable ? 'dostępna' : 'zużyta'} | Ruch: ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</p>` : ''}
    ${statusChipsHtml(actor.status_chips || [], 'Brak statusów aktywnego aktora.')}
  `;
}
function actorInventoryHtml(actor) {
  const items = actor && actor.inventory ? actor.inventory : [];
  if (!items.length) return '';
  return `<p><b>Ekwipunek:</b> ${items.map(item => `${esc(item.name || item.id)}${item.quantity !== undefined ? ` x${esc(item.quantity)}` : ''}${item.equipped === false ? ' (niezałożone)' : ''}`).join(', ')}</p>`;
}
function statusChipsHtml(chips, emptyText) {
  const items = chips || [];
  if (!items.length) return emptyText ? `<p class="combat-empty">${esc(emptyText)}</p>` : '';
  return `<div class="status-chips">${items.map(chip => {
    const tone = chip.tone || 'neutral';
    const title = chip.title ? ` title="${esc(chip.title)}"` : '';
    return `<span class="status-chip ${esc(tone)}"${title}>${esc(chip.label || '')}</span>`;
  }).join('')}</div>`;
}
function actorEffectChips(actor) {
  const chips = [];
  if (actor.defeated) chips.push({label: 'Pokonany', tone: 'danger'});
  (actor.effects || []).forEach(effect => {
    const label = `${effect.label || effect.kind || 'Efekt'}${effect.value_label ? `: ${effect.value_label}` : ''}`;
    chips.push({label, tone: effectChipTone(effect.kind), title: effect.expires || ''});
  });
  if (actor.concentration) chips.push({label: `Koncentracja: ${actor.concentration.label || '-'}`, tone: 'magic', title: actor.concentration.expires || ''});
  return chips;
}
function effectChipTone(kind) {
  if (kind === 'grant_ac_bonus_until_move' || kind === 'dodge_until_next_turn' || kind === 'disengage_until_turn_end') return 'defense';
  if (kind === 'grant_attack_bonus_while_on_object' || kind === 'help_attack_advantage' || kind === 'strength_potion' || kind === 'concentration_attack_bonus') return 'offense';
  if (kind === 'grant_next_attack_penalty') return 'penalty';
  if (kind === 'ready_attack') return 'ready';
  return 'neutral';
}
function combatActiveEffectsHtml(combat) {
  const effects = relevantCombatEffects(combat);
  return `
    <div class="combat-effects">
      <h4>Aktywne efekty</h4>
      ${effects.length ? `<div class="combat-effect-list">${effects.map(item => combatEffectHtml(item)).join('')}</div>` : '<p class="combat-empty">Brak aktywnych efektów dla aktualnego kroku.</p>'}
    </div>
  `;
}
function combatAllEffectsHtml(combat) {
  const actors = combat.actors || [];
  const items = [];
  actors.forEach(actor => {
    (actor.effects || []).forEach(effect => items.push({actor, effect, role: actor.name || 'Aktor'}));
  });
  if (!items.length) return '<p class="combat-empty">Brak aktywnych efektów.</p>';
  return `<div class="combat-effect-list">${items.map(item => combatEffectHtml(item)).join('')}</div>`;
}
function relevantCombatEffects(combat) {
  const actors = combat.actors || [];
  const current = combat.current_actor || {};
  const items = [];
  const seen = new Set();
  const addActorEffects = (actorId, role) => {
    if (!actorId) return;
    const actor = actors.find(candidate => candidate.id === actorId);
    if (!actor) return;
    (actor.effects || []).forEach(effect => {
      const key = `${actor.id}:${effect.id}`;
      if (seen.has(key)) return;
      seen.add(key);
      items.push({actor, effect, role});
    });
  };
  addActorEffects(current.id, 'Aktywny aktor');
  const pending = combat.pending_player_attack || null;
  if (pending && pending.target) addActorEffects(pending.target.id, 'Cel ataku');
  if (pending && pending.attacker) addActorEffects(pending.attacker.id, 'Atakujący');
  const intent = combat.enemy_turn_intent || combat.enemy_turn_preview || combat.enemy_turn_result || null;
  if (intent && intent.target_id) addActorEffects(intent.target_id, 'Cel przeciwnika');
  if (intent && intent.enemy_id) addActorEffects(intent.enemy_id, 'Przeciwnik');
  return items;
}
function combatEffectHtml(item) {
  const effect = item.effect || {};
  const actor = item.actor || {};
  const value = effect.value_label || signedNumber(effect.value || 0);
  const expires = effect.expires || 'czas trwania zależy od efektu';
  return `
    <div class="combat-effect">
      <b>${esc(item.role || 'Efekt')}: ${esc(actor.name || '-')}</b>
      <span>${esc(effect.label || effect.kind || '-')} | ${esc(value)} | ${esc(expires)}</span>
    </div>
  `;
}
function actorHpLabel(actor) {
  if (!actor) return '-';
  const maxHp = actor.max_hp !== null && actor.max_hp !== undefined ? actor.max_hp : actor.hp;
  const temp = Number(actor.temp_hp || 0);
  return `${actor.hp} / ${maxHp}${temp > 0 ? ` + ${temp} temp` : ''}${actor.defeated ? ' (pokonany)' : ''}`;
}
function combatLastResultHtml() {
  return `
    <div class="combat-last-result">
      <h4>Ostatni rezultat</h4>
      ${latestCombatMessageHtml()}
    </div>
  `;
}
function latestCombatMessageHtml() {
  const combatTitles = new Set(['Atak', 'Obrażenia', 'Ruch', 'Koniec tury', 'Atak przeciwnika', 'Obrażenia przeciwnika', 'Ruch przeciwnika', 'Tura przeciwnika', 'Atak okazyjny', 'Pomoc', 'Ready', 'Leczenie', 'Eliksir']);
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (!combatTitles.has(messages[i].title)) continue;
    return `<p><b>${esc(messages[i].title)}</b></p><p>${esc(messages[i].body)}</p>`;
  }
  return '<p class="combat-empty">Brak rezultatu w tej walce.</p>';
}
function combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.pending_concentration_check) {
    return pendingConcentrationCheckHtml(combat.pending_concentration_check);
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) {
      return pendingReadyAttackHtml(combat.pending_ready_attack);
    }
    if (combat.pending_enemy_opportunity_attack) {
      return pendingEnemyOpportunityAttackHtml(combat.pending_enemy_opportunity_attack);
    }
    if (combat.enemy_turn_intent) {
      return enemyTurnIntentHtml(combat.enemy_turn_intent);
    }
    if (combat.enemy_turn_result) {
      return enemyTurnResultHtml(combat.enemy_turn_result);
    }
    const preview = combat.enemy_turn_preview || null;
    if (preview && preview.kind === 'movement') {
      return `
        <p>Oczekiwane pole: (${esc(preview.destination[0])},${esc(preview.destination[1])})</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    if (preview && preview.kind === 'attack') {
      return `
        <p>Oczekiwany cel: ${esc(preview.target_name)}</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    return `
      <button data-allow-busy="true" onclick="resolveEnemyTurn()">Rozegraj turę przeciwnika</button>
    `;
  }
  if (!isAllyTurn) {
    return '<p class="muted">Ten aktor nie ma automatycznych kontrolek w MVP.</p><button data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>';
  }
  if (combat.pending_opportunity_movement) {
    return pendingOpportunityMovementHtml(combat.pending_opportunity_movement);
  }
  if (combat.pending_combat_help) {
    return pendingCombatHelpHtml(combat.pending_combat_help);
  }
  if (combat.pending_concentration_action) {
    return pendingConcentrationActionHtml(combat.pending_concentration_action);
  }
  if (combat.pending_combat_ready) {
    return pendingCombatReadyHtml(combat.pending_combat_ready);
  }
  if (combat.pending_player_attack) {
    return pendingPlayerAttackHtml(combat.pending_player_attack);
  }
  if (combat.pending_player_healing) {
    return pendingPlayerHealingHtml(combat.pending_player_healing);
  }
  if (combat.pending_area_spell) {
    return pendingAreaSpellHtml(combat.pending_area_spell);
  }
  if (combat.pending_combat_interaction) {
    return pendingCombatInteractionHtml(combat.pending_combat_interaction);
  }
  const movement = combat.movement || {remaining_feet: 0, destinations: []};
  const preview = combat.movement_preview || null;
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  return `
    ${preview ? `<p>Potwierdź pole: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : `<p>Ruch dostępny: ${esc(movement.remaining_feet || 0)} ft.</p>`}
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      ${!actionUsed ? combatSourceButtonsHtml(combat) : ''}
      ${!actionUsed ? '<button class="secondary" data-allow-busy="true" onclick="startCombatReady()">Ready</button><button class="secondary" data-allow-busy="true" onclick="startCombatHelp()">Help</button><button class="secondary" data-allow-busy="true" onclick="useCombatDash()">Dash</button><button class="secondary" data-allow-busy="true" onclick="useCombatDodge()">Unik</button><button class="secondary" data-allow-busy="true" onclick="useCombatDisengage()">Odwrót</button>' : ''}
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
}
function combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.pending_concentration_check) return pendingConcentrationCheckDetailsHtml(combat.pending_concentration_check);
  if (isEnemyTurn) return enemyTurnDetailsHtml(combat);
  if (!isAllyTurn) return '<p class="muted">Brak dodatkowych szczegółów dla tego aktora.</p>';
  if (combat.pending_opportunity_movement) return pendingOpportunityMovementDetailsHtml(combat.pending_opportunity_movement);
  if (combat.pending_combat_help) return pendingCombatHelpDetailsHtml(combat.pending_combat_help);
  if (combat.pending_concentration_action) return pendingConcentrationActionDetailsHtml(combat.pending_concentration_action);
  if (combat.pending_combat_ready) return pendingCombatReadyDetailsHtml(combat.pending_combat_ready);
  if (combat.pending_player_attack) return pendingPlayerAttackDetailsHtml(combat.pending_player_attack);
  if (combat.pending_player_healing) return pendingPlayerHealingDetailsHtml(combat.pending_player_healing);
  if (combat.pending_area_spell) return pendingAreaSpellDetailsHtml(combat.pending_area_spell);
  if (combat.pending_combat_interaction) return pendingCombatInteractionDetailsHtml(combat.pending_combat_interaction);
  return playerTurnDetailsHtml(combat);
}
function combatSourceButtonsHtml(combat) {
  const attacks = combat.available_attack_sources || [];
  const selectedAttack = combat.selected_attack_source_id || '';
  const actor = combat.current_actor || {};
  const attackButtons = attacks.map(source => {
    const selected = source.id === selectedAttack ? ' selected' : '';
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const label = sourceButtonLabel(source);
    return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatAttackSource('${esc(source.id)}')">${label}</button>`;
  }).join('');
  const healing = combat.available_healing_sources || [];
  const selectedHealing = combat.selected_healing_source_id || '';
  const healingButtons = healing.map(source => {
    const selected = source.id === selectedHealing ? ' selected' : '';
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const label = sourceButtonLabel(source);
    return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatHealingSource('${esc(source.id)}')">${label}</button>`;
  }).join('');
  const actionButtons = (combat.combat_actions || []).map(action => {
    if (action.action_type === 'strength_potion') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = sourceButtonLabel(action);
      return `<button class="secondary"${disabled} data-allow-busy="true" onclick="useStrengthPotion('${esc(action.id)}')">${label}</button>`;
    }
    if (action.action_type === 'concentration_attack_bonus') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = sourceButtonLabel(action);
      return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startConcentrationAction('${esc(action.id)}')">${label}</button>`;
    }
    return '';
  }).join('');
  return `${attackButtons}${healingButtons}${actionButtons}`;
}
function sourceButtonLabel(source) {
  const resource = source.resource_label ? ` · ${esc(source.resource_label)}` : '';
  return `${esc(source.name)}${resource}`;
}
function sourceUnavailableReason(source, actor) {
  if (source.prepared === false) return 'Ten czar nie jest przygotowany.';
  if (source.available === false) {
    if (source.source_item_id) return 'Ten przedmiot został zużyty.';
    return 'Ta opcja nie jest dostępna.';
  }
  const spellLevel = Number(source.spell_level || 0);
  if (spellLevel <= 0) return '';
  const slots = actor.spell_slots || [];
  const slot = slots.find(item => Number(item.level) === spellLevel);
  if (!slot || Number(slot.remaining || 0) <= 0) return `Brak slotów czaru ${spellLevel}. poziomu.`;
  return '';
}
function spellSlotSummaryHtml(actor) {
  const slots = actor.spell_slots || [];
  if (!slots.length) return '';
  return slots.map(slot => `slot ${esc(slot.level)}: ${esc(slot.remaining)}/${esc(slot.maximum)}`).join(', ');
}
function sourceSummaryText(source) {
  const parts = [source.name || '-'];
  if (source.resource_label) parts.push(source.resource_label);
  if (source.prepared === false) parts.push('nieprzygotowany');
  if (source.save_ability) parts.push(`save ${abilityLabel(source.save_ability)} ST ${source.save_dc || '-'}`);
  if (source.area) parts.push(`obszar ${areaShapeLabel(source.area.shape)}`);
  if (source.range_feet) parts.push(`${source.range_feet} ft`);
  return parts.join(' · ');
}
function playerTurnDetailsHtml(combat) {
  const source = combat.available_attack || {};
  const attackSources = combat.available_attack_sources || [];
  const healingSources = combat.available_healing_sources || [];
  const targets = combat.legal_targets || [];
  const healingTargets = combat.legal_healing_targets || [];
  const areaPositions = combat.legal_area_positions || [];
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const moveCount = (movement.destinations || []).length;
  const slotSummary = spellSlotSummaryHtml(actor);
  const concentration = actor.concentration || null;
  const inventory = actorInventoryHtml(actor);
  const targetText = targets.length
    ? targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ')
    : 'brak';
  return `
    <p><b>Tura gracza:</b> ${esc(actor.name || '-')}</p>
    <p><b>Akcja:</b> ${actionUsed ? 'zużyta' : 'dostępna'} | <b>Bonus action:</b> ${bonusActionUsed ? 'zużyta' : 'dostępna'} | <b>Reakcja:</b> ${reactionAvailable ? 'dostępna' : 'zużyta'} | <b>Ruch:</b> ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</p>
    ${inventory}
    ${slotSummary || concentration ? `<p><b>Magia:</b> ${slotSummary ? `ST czarów ${esc(actor.spell_save_dc || '-')}; ${slotSummary}` : ''}${concentration ? ` | Koncentracja: ${esc(concentration.label || '-')}` : ''}</p>` : ''}
    <p>Niebieskie pola: ruch (${esc(moveCount)} pól). Czerwone pola: legalne cele ataku. Turkusowe pola: legalne cele leczenia. Zielone pola: interakcje sceny. Żółte pola: środek albo kierunek czaru obszarowego.</p>
    ${preview ? `<p>Wybrana ścieżka: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : ''}
    <p><b>Atak:</b> ${esc(source.name || '-')}${source.damage_hint ? `, po trafieniu rzuć ${esc(source.damage_hint)}` : ''}</p>
    <p><b>Źródła ataku:</b> ${attackSources.map(sourceSummaryText).map(esc).join(', ') || 'brak'}</p>
    <p><b>Leczenie:</b> ${healingSources.map(item => `${sourceSummaryText(item)}${item.healing_hint ? ` · ${item.healing_hint}` : ''}`).map(esc).join(', ') || 'brak'}</p>
    <p><b>Cele w zasięgu:</b> ${esc(targetText)}</p>
    <p><b>Pola czaru obszarowego:</b> ${areaPositions.map(position => `(${esc(position[0])},${esc(position[1])})`).join(', ') || 'brak'}</p>
    <p><b>Ranni sojusznicy w zasięgu:</b> ${healingTargets.map(target => `${esc(target.name)} (${esc(target.position[0])},${esc(target.position[1])})`).join(', ') || 'brak'}</p>
  `;
}
function enemyTurnDetailsHtml(combat) {
  const pendingReady = combat.pending_ready_attack || null;
  if (pendingReady) {
    return pendingReadyAttackDetailsHtml(pendingReady);
  }
  const pendingOpportunity = combat.pending_enemy_opportunity_attack || null;
  if (pendingOpportunity) {
    return pendingEnemyOpportunityAttackDetailsHtml(pendingOpportunity, combat.enemy_turn_preview || null);
  }
  const intent = combat.enemy_turn_intent || null;
  if (intent) {
    const source = intent.source || {};
    const targetText = intent.target_name ? ` przeciwko ${esc(intent.target_name)}` : '';
    const moveText = intent.kind === 'movement'
      ? `<p><b>Ruch:</b> (${esc(intent.destination[0])},${esc(intent.destination[1])}), koszt ${esc(intent.cost_feet)} ft.</p>`
      : '';
    const attackText = intent.target_name
      ? `<p><b>Atak:</b> ${esc(source.name || '-')} ${targetText}. Premia do rzutu: ${esc(signedNumber(intent.attack_modifier || 0))}.</p>`
      : '';
    return `
      <p><b>Zamiar przeciwnika:</b> ${esc(intent.message || '')}</p>
      ${combatActiveEffectsHtml(combat)}
      ${moveText}
      ${attackText}
    `;
  }
  const result = combat.enemy_turn_result || null;
  if (result) {
    const target = result.target_name ? ` przeciwko ${esc(result.target_name)}` : '';
    const hitText = result.hit === true ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : (result.hit === false ? 'PUDŁO' : 'BRAK ATAKU');
    const rollHtml = result.natural_roll !== null && result.natural_roll !== undefined
      ? `<p><b>Rzut d20:</b> ${d20RollResultText(result)} | <b>Wynik końcowy:</b> ${esc(result.total)}</p>`
      : '';
    const damageHtml = result.damage !== null && result.damage !== undefined
      ? `<p><b>Obrażenia:</b> ${esc(result.damage)}</p>`
      : '';
    const damageResult = result.damage_result || null;
    const hpHtml = damageResult
      ? `<p><b>HP celu:</b> ${esc(damageResult.hp_before)} -> ${esc(damageResult.hp_after)}${damageResult.defeated_by_damage ? ' | cel pokonany' : ''}</p>`
      : '';
    return `
      <p><b>Wynik tury przeciwnika:</b> ${hitText}</p>
      <p>${esc(result.enemy_name || 'Przeciwnik')}${target}</p>
      ${rollHtml}
      ${damageHtml}
      ${hpHtml}
      <p class="muted">${esc(result.message || '')}</p>
    `;
  }
  const preview = combat.enemy_turn_preview || null;
  if (preview && preview.kind === 'movement') {
    return `<p><b>Ruch przeciwnika:</b> ${esc(preview.enemy_name)} porusza się na (${esc(preview.destination[0])},${esc(preview.destination[1])}). Przestaw figurkę po ścieżce i potwierdź pole planszą.${enemyRollSummaryHtml(preview)}</p>${combatActiveEffectsHtml(combat)}`;
  }
  if (preview && preview.kind === 'attack') {
    return `<p><b>Atak przeciwnika:</b> ${esc(preview.enemy_name)} atakuje ${esc(preview.target_name)}. Potwierdź podświetlony cel planszą.${enemyRollSummaryHtml(preview)}</p>${combatActiveEffectsHtml(combat)}`;
  }
  return '<p>Enter albo przycisk wyliczy zamiar przeciwnika. Potem potwierdzisz ruch lub atak kliknięciem na planszy.</p>';
}
function enemyTurnIntentHtml(intent) {
  return `
    <button data-allow-busy="true" onclick="resolveEnemyTurn()">Potwierdź zamiar przeciwnika</button>
  `;
}
function enemyTurnResultHtml(result) {
  return `
    <button data-allow-busy="true" onclick="confirmEnemyTurnResult()">Potwierdź wynik przeciwnika</button>
  `;
}
function pendingEnemyOpportunityAttackHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'choice') {
    return `
      <p>${esc(target.name || 'Przeciwnik')} opuszcza zasięg: ${esc(attacker.name || 'bohater')}.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="startEnemyOpportunityAttack()">Wykonaj atak okazyjny</button>
        <button class="secondary" data-allow-busy="true" onclick="skipEnemyOpportunityAttack()">Pomiń reakcję</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      <div class="row">
        <label>Obrażenia: <input id="enemy-opportunity-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitEnemyOpportunityDamageRoll()">Zapisz obrażenia</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('enemy-opportunity-natural-roll', pending.attack_mode)}
      <button onclick="submitEnemyOpportunityAttackRoll()">Zapisz rzut</button>
    </div>
  `;
}
function pendingEnemyOpportunityAttackDetailsHtml(pending, preview) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const active = pending.active_modifiers || [];
  const ignored = pending.ignored_modifiers || [];
  const path = preview && preview.path ? preview.path.map(position => `(${position[0]},${position[1]})`).join(' -> ') : '';
  return `
    <p><b>Atak okazyjny bohatera:</b> ${esc(attacker.name || '-')} przeciwko ${esc(target.name || '-')}</p>
    ${path ? `<p><b>Ruch przeciwnika:</b> ${esc(path)}</p>` : ''}
    <p><b>Premia do rzutu:</b> ${esc(signedNumber(pending.attack_modifier || 0))} | <b>AC celu:</b> ${esc(pending.target_ac || '-')}</p>
    <p><b>Aktywne modyfikatory:</b> ${active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') || 'brak'}</p>
    ${ignored.length ? `<p><b>Pominięte modyfikatory:</b> ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}</p>` : ''}
    <p><b>Obrażenia:</b> ${esc(pending.damage_instruction || '-')}</p>
  `;
}
function pendingCombatHelpHtml(pending) {
  const allies = pending.allies || [];
  const targets = pending.targets || [];
  const allyOptions = allies.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  const targetOptions = targets.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  return `
    <p>Wybierz sojusznika i przeciwnika dla akcji Help.</p>
    <div class="row">
      <label>Sojusznik: <select id="combat-help-ally">${allyOptions}</select></label>
      <label>Cel: <select id="combat-help-target">${targetOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmCombatHelp()">Potwierdź Help</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelCombatHelp()">Anuluj</button>
    </div>
  `;
}
function pendingCombatHelpDetailsHtml(pending) {
  const helper = pending.helper || {};
  const allies = pending.allies || [];
  const targets = pending.targets || [];
  return `
    <p><b>Pomagający:</b> ${esc(helper.name || '-')}</p>
    <p><b>Legalni sojusznicy:</b> ${allies.map(actor => esc(actor.name)).join(', ') || 'brak'}</p>
    <p><b>Cele w zasięgu 5 ft pomagającego:</b> ${targets.map(actor => `${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})`).join(', ') || 'brak'}</p>
    <p>Efekt: wybrany sojusznik ma przewagę na następny atak przeciw wybranemu celowi.</p>
  `;
}
function pendingConcentrationActionHtml(pending) {
  const action = pending.action || {};
  const targets = pending.targets || [];
  const targetOptions = targets.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  return `
    <p>${esc(action.label || action.name || 'Czar koncentracyjny')}: wybierz sojusznika dla efektu.</p>
    <div class="row">
      <label>Cel: <select id="combat-concentration-target">${targetOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmConcentrationAction()">Potwierdź czar</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelConcentrationAction()">Anuluj</button>
    </div>
  `;
}
function pendingConcentrationActionDetailsHtml(pending) {
  const caster = pending.caster || {};
  const action = pending.action || {};
  const targets = pending.targets || [];
  return `
    <p><b>Rzucający:</b> ${esc(caster.name || '-')}</p>
    <p><b>Czar:</b> ${esc(action.label || action.name || '-')} ${action.resource_label ? `(${esc(action.resource_label)})` : ''}</p>
    <p><b>Koncentracja:</b> ${action.concentration ? 'tak' : 'nie'} | <b>Efekt:</b> ${esc(signedNumber(action.value || 0))} do ataku celu</p>
    <p><b>Legalni sojusznicy:</b> ${targets.map(actor => `${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})`).join(', ') || 'brak'}</p>
  `;
}
function pendingConcentrationCheckHtml(pending) {
  const actor = pending.actor || {};
  const modifier = Number(pending.modifier || 0);
  return `
    <p>${esc(actor.name || 'Bohater')} utrzymuje koncentrację: ST ${esc(pending.dc)}.</p>
    <div class="row">
      <label>Wynik d20: <input id="concentration-check-roll" type="number" min="1" max="20" value="10"></label>
      <button onclick="submitConcentrationCheck()">Zapisz rzut</button>
    </div>
    <p class="muted">Premia CON: ${esc(signedNumber(modifier))}. Sukces utrzymuje efekt, porażka go kończy.</p>
  `;
}
function pendingConcentrationCheckDetailsHtml(pending) {
  const actor = pending.actor || {};
  const effects = pending.effects || [];
  return `
    <p><b>Koncentrujący:</b> ${esc(actor.name || '-')}</p>
    <p><b>Obrażenia:</b> ${esc(pending.damage)} | <b>ST:</b> ${esc(pending.dc)} | <b>Premia CON:</b> ${esc(signedNumber(pending.modifier || 0))}</p>
    <p><b>Efekty zagrożone:</b> ${effects.map(effect => esc(effect.label || effect.kind || effect.id)).join(', ') || 'brak'}</p>
  `;
}
function pendingCombatReadyHtml(pending) {
  const triggerOptions = (pending.triggers || []).map(trigger => `<option value="${esc(trigger.id)}">${esc(trigger.label)}</option>`).join('');
  return `
    <p>Przygotuj atak jako reakcję na wybrany warunek.</p>
    <div class="row">
      <label>Warunek: <select id="combat-ready-trigger">${triggerOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmCombatReady()">Potwierdź Ready</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelCombatReady()">Anuluj</button>
    </div>
  `;
}
function pendingCombatReadyDetailsHtml(pending) {
  const actor = pending.actor || {};
  return `
    <p><b>Przygotowujący:</b> ${esc(actor.name || '-')}</p>
    <p>Ready zużywa akcję główną teraz. Jeśli wybrany warunek zajdzie przed następną turą aktora, gracz może użyć reakcji i wykonać przygotowany atak.</p>
  `;
}
function pendingReadyAttackHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'choice') {
    return `
      <p>${esc(pending.trigger_label || 'Warunek Ready')} | ${esc(attacker.name || 'Bohater')} może zaatakować ${esc(target.name || 'przeciwnika')}.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="startReadyAttack()">Użyj przygotowanej akcji</button>
        <button class="secondary" data-allow-busy="true" onclick="skipReadyAttack()">Pomiń reakcję</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      <div class="row">
        <label>Obrażenia: <input id="ready-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitReadyDamageRoll()">Zapisz obrażenia</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('ready-natural-roll', pending.attack_mode)}
      <button onclick="submitReadyAttackRoll()">Zapisz rzut</button>
    </div>
  `;
}
function pendingReadyAttackDetailsHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const active = pending.active_modifiers || [];
  return `
    <p><b>Ready:</b> ${esc(attacker.name || '-')} przeciwko ${esc(target.name || '-')}</p>
    <p><b>Warunek:</b> ${esc(pending.trigger_label || '-')}</p>
    <p><b>Premia do rzutu:</b> ${esc(signedNumber(pending.attack_modifier || 0))} | <b>AC celu:</b> ${esc(pending.target_ac || '-')}</p>
    <p><b>Aktywne modyfikatory:</b> ${active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') || 'brak'}</p>
  `;
}
function pendingOpportunityMovementHtml(pending) {
  const names = (pending.threats || []).map(actor => actor.name).join(', ') || 'wróg';
  return `
    <p>Ruch na (${esc(pending.destination[0])},${esc(pending.destination[1])}) prowokuje: ${esc(names)}.</p>
    <div class="row">
      <button data-allow-busy="true" onclick="confirmOpportunityMovement()">Potwierdź ruch mimo ryzyka</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelOpportunityMovement()">Anuluj ruch</button>
    </div>
  `;
}
function pendingOpportunityMovementDetailsHtml(pending) {
  const threats = pending.threats || [];
  const threatText = threats.length
    ? threats.map(actor => `${actor.name} (${actor.position[0]},${actor.position[1]})`).join(', ')
    : 'brak';
  return `
    <p><b>Atak okazyjny:</b> wybrany ruch opuszcza zasięg wroga.</p>
    <p><b>Zagrożenia:</b> ${esc(threatText)}</p>
    <p><b>Ścieżka:</b> ${(pending.path || []).map(position => `(${position[0]},${position[1]})`).join(' -> ')}</p>
  `;
}
function pendingPlayerAttackHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'confirm_attack') {
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    if (source.save_ability) {
      return `
        <p>Cel: ${esc(target.name || '-')} | rzut obronny ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}</p>
        <div class="row">
          <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź czar</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
        </div>
      `;
    }
    return `
      <p>Cel: ${esc(target.name || '-')} | AC ${esc(target.ac || '-')} | premia ${esc(modifierLabel)}</p>
      <div class="row">
        <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź atak</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      ${spellSavesHtml(pending.saving_throws || [])}
      <div class="row">
        <label>Obrażenia: <input id="combat-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitPlayerDamageRoll()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('combat-attack-natural-roll', pending.attack_mode)}
      <button onclick="submitPlayerAttackRoll()">Zapisz rzut</button>
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
}
function d20RollInputsHtml(baseId, mode) {
  const second = mode === 'advantage' || mode === 'disadvantage';
  const label = mode === 'advantage' ? 'Przewaga' : (mode === 'disadvantage' ? 'Utrudnienie' : 'Wynik d20');
  return `
    <label>${esc(second ? `${label} 1` : label)}: <input id="${esc(baseId)}" type="number" min="1" max="20" value="10"></label>
    ${second ? `<label>${esc(label)} 2: <input id="${esc(baseId)}-2" type="number" min="1" max="20" value="10"></label>` : ''}
  `;
}
function d20RollPayload(baseId) {
  const roll = document.getElementById(baseId);
  const roll2 = document.getElementById(`${baseId}-2`);
  const payload = {natural_roll: Number(roll ? roll.value : 0)};
  if (roll2) payload.natural_roll_2 = Number(roll2.value || 0);
  return payload;
}
function d20RollResultText(result) {
  const rolls = result && result.natural_rolls ? result.natural_rolls : [];
  if (rolls.length > 1) return `${rolls.map(esc).join(' / ')} -> ${esc(result.natural_roll || '')}`;
  return result && result.natural_roll !== null && result.natural_roll !== undefined ? esc(result.natural_roll) : '';
}
function pendingAreaSpellHtml(pending) {
  const source = pending.source || {};
  const targets = pending.targets || [];
  const targetText = targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ') || 'brak celów';
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia czaru obszarowego.')}</p>
      <p>Cele w obszarze: ${esc(targetText)}</p>
      ${spellSavesHtml(pending.saving_throws || [])}
      <div class="row">
        <label>Obrażenia: <input id="area-spell-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitAreaSpellDamage()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    <p>Obszar: ${esc((pending.area_positions || []).map(position => `(${position[0]},${position[1]})`).join(', ') || '-')}</p>
    <p>Cele w obszarze: ${esc(targetText)}</p>
    ${source.save_ability ? `<p>Rzut obronny: ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')} | ${esc(saveSuccessLabel(source.save_damage_on_success))}</p>` : ''}
    <div class="row">
      <button data-allow-busy="true" onclick="confirmAreaSpell()">Potwierdź czar</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelAreaSpell()">Anuluj czar</button>
    </div>
  `;
}
function pendingAreaSpellDetailsHtml(pending) {
  const source = pending.source || {};
  const targets = pending.targets || [];
  return `
    <p><b>Czar:</b> ${esc(source.name || '-')} | ${esc(source.damage_hint || '-')}</p>
    <p><b>Zakotwiczenie:</b> (${esc(pending.anchor ? pending.anchor[0] : '-')},${esc(pending.anchor ? pending.anchor[1] : '-')})</p>
    <p><b>Obszar:</b> ${esc((pending.area_positions || []).map(position => `(${position[0]},${position[1]})`).join(', ') || '-')}</p>
    <p><b>Cele:</b> ${targets.map(target => `${esc(target.name)} (${esc(target.position[0])},${esc(target.position[1])})`).join(', ') || 'brak'}</p>
    ${spellSavesHtml(pending.saving_throws || [])}
  `;
}
function pendingPlayerHealingHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  return `
    <p>${esc(pending.healing_instruction || 'Rzuć leczenie i wpisz wynik.')}</p>
    <div class="row">
      <label>Leczenie: <input id="combat-healing-roll" type="number" min="0" value="${esc(defaultHealingValue(source))}"></label>
      <button onclick="submitPlayerHealingRoll()">Zapisz leczenie</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelPlayerHealing()">Anuluj</button>
    </div>
    <p class="muted">Cel: ${esc(target.name || '-')}.</p>
  `;
}
function pendingPlayerHealingDetailsHtml(pending) {
  const healer = pending.healer || {};
  const target = pending.target || {};
  const source = pending.source || {};
  return `
    <p><b>Leczenie:</b> ${esc(healer.name || '-')} używa ${esc(source.name || '-')} na ${esc(target.name || '-')}</p>
    <p><b>HP celu:</b> ${esc(actorHpLabel(target))}</p>
    <p><b>Rzut:</b> ${esc(pending.healing_instruction || '-')}</p>
  `;
}
function pendingCombatInteractionHtml(pending) {
  const options = pending.options || [];
  if (!options.length) return '<p>Brak dostępnych opcji interakcji.</p>';
  const primary = options[0];
  const buttons = options.map(option => `<button data-allow-busy="true" onclick="confirmCombatInteraction('${esc(option.id)}')">${esc(option.label)}</button>`).join('');
  return `
    <p>Obiekt: ${esc(pending.object_name || '-')} | pole (${esc(pending.target_position ? pending.target_position[0] : '-')},${esc(pending.target_position ? pending.target_position[1] : '-')})</p>
    <p>${esc(primary.description || 'Interakcja zużywa akcję główną.')}</p>
    <div class="row">${buttons}<button class="secondary" data-allow-busy="true" onclick="cancelCombatInteraction()">Anuluj</button></div>
  `;
}
function pendingCombatInteractionDetailsHtml(pending) {
  const options = pending.options || [];
  if (!options.length) return '<p>Brak szczegółów interakcji.</p>';
  return options.map(option => `
    <p><b>${esc(option.label)}</b></p>
    <p>${esc(option.description || '')}</p>
    <p><b>Warunki:</b> ${(option.conditions || []).map(condition => esc(condition)).join(', ') || 'brak'}</p>
  `).join('');
}
function pendingPlayerAttackDetailsHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'confirm_attack') {
    const active = pending.active_modifiers || [];
    const ignored = pending.ignored_modifiers || [];
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    return `
      <p><b>Potwierdzenie ataku</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>AC celu:</b> ${esc(target.ac || '-')} | <b>Pole:</b> (${esc(target.position ? target.position[0] : '-')},${esc(target.position ? target.position[1] : '-')})</p>
      <p><b>Atak:</b> ${esc(source.name || '-')} | <b>Zasięg:</b> ${esc(source.range_feet || 0)} ft | <b>Premia końcowa:</b> ${esc(modifierLabel)}</p>
      <p><b>Aktywne premie/kary:</b> ${active.length ? active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') : 'brak'}</p>
      ${attackEffectsDetailsHtml(pending)}
      ${ignored.length ? `<p><b>Odrzucone duplikaty:</b> ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}</p>` : ''}
      <p><b>Rzut:</b> ${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
      <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
    `;
  }
  if (pending.stage === 'damage_roll') {
    if (pending.saving_throws && pending.saving_throws.length) {
      return `
        <p><b>Tura gracza: wpisz obrażenia czaru</b></p>
        <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Czar:</b> ${esc(source.name || '-')}</p>
        ${spellSavesHtml(pending.saving_throws || [])}
        <p><b>Co teraz:</b> ${esc(pending.damage_instruction || '')}</p>
      `;
    }
    return `
      <p><b>Tura gracza: wpisz obrażenia</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Trafienie:</b> ${pending.critical ? 'krytyczne' : 'zwykłe'}</p>
      ${attackEffectsDetailsHtml(pending)}
      <p><b>Rzut d20:</b> ${d20RollResultText(pending)} | <b>Wynik końcowy:</b> ${esc(pending.total || '')}</p>
      <p><b>Co teraz:</b> ${esc(pending.damage_instruction || '')}</p>
    `;
  }
  return `
    <p><b>Tura gracza: wybrano cel</b></p>
    <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Atak:</b> ${esc(source.name || '-')}</p>
    ${attackEffectsDetailsHtml(pending)}
    <p><b>Co teraz:</b> ${source.save_ability ? `Potwierdź czar. Cel wykona automatyczny rzut obronny na ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}.` : esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
  `;
}
function attackEffectsDetailsHtml(pending) {
  const items = [];
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  (attacker.effects || []).forEach(effect => items.push({actor: attacker, effect, role: 'Atakujący'}));
  (target.effects || []).forEach(effect => items.push({actor: target, effect, role: 'Cel'}));
  if (!items.length) return '<p><b>Efekty ataku:</b> brak</p>';
  return `
    <div>
      <p><b>Efekty ataku:</b></p>
      <div class="combat-effect-list">${items.map(item => combatEffectHtml(item)).join('')}</div>
    </div>
  `;
}
function enemyRollSummaryHtml(preview) {
  if (!preview || preview.natural_roll === null || preview.natural_roll === undefined) return '';
  const outcome = preview.hit ? (preview.critical ? 'trafienie krytyczne' : 'trafienie') : 'pudło';
  const damage = preview.damage !== null && preview.damage !== undefined ? `<br>Obrażenia: ${esc(preview.damage)}.` : '';
  return `<br>Automatyczny rzut przeciwnika: d20 ${d20RollResultText(preview)}, razem ${esc(preview.total)} (${outcome}).${damage}`;
}
function spellSavesHtml(saves) {
  if (!saves || !saves.length) return '';
  return `
    <div class="combat-effect-list">
      ${saves.map(save => `
        <span class="combat-effect">
          ${esc(save.actor_name || save.actor_id)}: ${esc(abilityLabel(save.ability))} d20 ${esc(save.natural_roll)}, mod ${esc(signedNumber(save.modifier || 0))}, razem ${esc(save.total)} / ST ${esc(save.dc)} - ${save.success ? 'sukces' : 'porażka'}${save.success ? `, ${esc(saveSuccessLabel(save.damage_multiplier === 0.5 ? 'half' : 'none'))}` : ', pełne obrażenia'}
        </span>
      `).join('')}
    </div>
  `;
}
function abilityLabel(ability) {
  const labels = {
    strength: 'Siła',
    dexterity: 'Zręczność',
    constitution: 'Kondycja',
    intelligence: 'Inteligencja',
    wisdom: 'Mądrość',
    charisma: 'Charyzma'
  };
  return labels[ability] || ability || '-';
}
function saveSuccessLabel(value) {
  if (value === 'half') return 'połowa obrażeń przy sukcesie';
  return 'brak obrażeń przy sukcesie';
}
function areaShapeLabel(shape) {
  const labels = {
    line: 'linia',
    cone: 'stożek',
    radius: 'okrąg'
  };
  return labels[shape] || shape || '-';
}
function defaultDamageValue(source) {
  if (!source) return 0;
  if (source.damage_fixed !== null && source.damage_fixed !== undefined) return Number(source.damage_fixed) + Number(source.damage_modifier || 0);
  return Math.max(0, Number(source.damage_modifier || 0));
}
function defaultHealingValue(source) {
  if (!source) return 0;
  if (source.healing_fixed !== null && source.healing_fixed !== undefined) return Number(source.healing_fixed) + Number(source.healing_modifier || 0);
  return Math.max(0, Number(source.healing_modifier || 0));
}
function signedNumber(value) {
  const number = Number(value || 0);
  return number >= 0 ? `+${number}` : `${number}`;
}
function pointOptionsHtml() {
  const points = state.current_zone_points || [];
  if (!points.length) return '<p>Brak odkrytych punktów w tej lokacji.</p>';
  const rows = points.map(point => {
    const active = state.active_point && state.active_point.id === point.id;
    const positions = (point.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
    return `
      <div class="status-item" style="margin: 6px 0">
        <b>${esc(point.name)}${active ? ' (aktywny)' : ''}</b>
        <div class="muted">${esc(point.description)}</div>
        <div>LED: ${esc(point.color || 'kolor specjalny')}${positions ? `, pole ${esc(positions)}` : ''}. Przestaw pionek drużyny na to pole, kliknij Skanuj planszę i wskaż pole.</div>
      </div>
    `;
  });
  if (state.active_point) {
    rows.push('<button class="secondary" onclick="selectPoint(&quot;&quot;)">Wróć do lokacji</button>');
  }
  rows.unshift('<button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>');
  return rows.join('');
}
function updateActivePanel() {
  const stage = state.flow ? state.flow.stage : 'location_active';
  const flowActive = stage !== 'location_active';
  const hasPendingDecision = state.pending && state.pending.stage === 'decision';
  const hasRolls = state.required_rolls && state.required_rolls.length > 0;
  const hasResult = Boolean(resultAck);
  const hasEncounter = Boolean(state.pending_encounter);
  const hasTravel = false;
  const hasPoints = !flowActive && !hasEncounter && !hasResult && !hasPendingDecision && !hasRolls && state.current_zone_points && state.current_zone_points.length > 0;
  const flowPanel = document.getElementById('flow-panel');
  flowPanel.hidden = hasEncounter || !flowPanel.innerHTML.trim();
  document.getElementById('result-panel').hidden = !hasResult;
  document.getElementById('encounter-panel').hidden = !hasEncounter || hasResult;
  document.getElementById('travel-panel').hidden = !hasTravel;
  document.getElementById('points-panel').hidden = !hasPoints;
  document.getElementById('pending-panel').hidden = !hasPendingDecision;
  document.getElementById('roll-panel').hidden = !hasRolls;
  document.getElementById('action-panel').hidden = flowActive || hasEncounter || hasResult || hasTravel || hasPendingDecision || hasRolls;
}
function sendAction() { api('/api/action', {text: document.getElementById('action').value}, 'Czekam na decyzję MG...'); }
function decision(value) {
  const labels = {
    accept: 'Przyjmuję decyzję MG...',
    reject: 'Odrzucam decyzję MG...',
    explain: 'Proszę MG o wyjaśnienie...'
  };
  const leadActor = document.getElementById('lead-actor');
  api('/api/decision', {decision:value, lead_actor_id: leadActor ? leadActor.value : null}, labels[value] || 'Czekam na MG...');
}
function sendRolls() {
  const rolls = {};
  document.querySelectorAll('#rolls input').forEach(input => rolls[input.dataset.actor] = Number(input.value));
  api('/api/rolls', {rolls}, 'Rozstrzygam wynik rzutu...');
}
function resetSession() { api('/api/reset', {}, 'Resetuję scenę...'); }
function travel(zoneId) { api('/api/travel', {zone_id: zoneId}, 'Przechodzę do wybranej lokacji...'); }
function selectPoint(pointId) { api('/api/point', {point_id: pointId}, pointId ? 'Otwieram punkt eksploracji...' : 'Wracam do lokacji...'); }
function finishInteraction() { api('/api/interaction/finish', {}, 'Wracam do wyboru lokacji...'); }
function cancelLocationPreview() { api('/api/location/cancel-preview', {}, 'Wracam do wyboru lokacji...'); }
function confirmLocationPreview() { api('/api/location/confirm-preview', {}, 'Wchodzę w eksplorację...'); }
function confirmExplorationSetup() { api('/api/exploration/setup/confirm', {}, 'Potwierdzam setup mapy...'); }
function configureBoard() {
  api('/api/board/configure', {
    backend: document.getElementById('board-backend').value,
    board_url: document.getElementById('board-url').value,
    board_serial_port: document.getElementById('board-serial-port').value,
    wled_url: document.getElementById('wled-url').value,
    scan_timeout_s: Number(document.getElementById('scan-timeout').value || 30)
  }, 'Łączę z planszą...');
}
function startSession() { api('/api/start', {}, 'Rozpoczynam sesję...'); }
function isAllyCombatTurnActive() {
  const combat = state && state.combat ? state.combat : null;
  const actor = combat && combat.current_actor ? combat.current_actor : {};
  return Boolean(combat && combat.status === 'active' && actor.faction === 'ally' && !combat.enemy_turn_preview && !combat.pending_player_attack && !combat.pending_player_healing && !combat.pending_area_spell && !combat.pending_combat_interaction && !combat.pending_combat_help && !combat.pending_concentration_action && !combat.pending_concentration_check && !combat.pending_combat_ready);
}
async function scanBoard() {
  if (boardScanInFlight) return;
  const continuous = isAllyCombatTurnActive();
  if (continuous) playerTurnScanLoop = true;
  await scanBoardOnce();
}
async function scanBoardOnce() {
  if (boardScanInFlight) return;
  const token = boardScanToken;
  boardScanInFlight = true;
  setBusy('Czekam na kliknięcie pola na planszy...');
  try {
    const res = await fetch('/api/board/scan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
    const data = await res.json();
    if (token !== boardScanToken) return;
    if (!res.ok) {
      playerTurnScanLoop = false;
      alert(data.error || 'Błąd');
    }
    state = data.state || data;
    if (!isAllyCombatTurnActive()) playerTurnScanLoop = false;
    render();
    refreshSessionLog();
  } finally {
    if (token === boardScanToken) {
      boardScanInFlight = false;
      setBusy('');
    }
  }
  if (token === boardScanToken && playerTurnScanLoop && isAllyCombatTurnActive()) {
    setTimeout(scanBoardOnce, 50);
  }
}
async function stopBoardScanLoop() {
  playerTurnScanLoop = false;
  boardScanToken += 1;
  if (boardScanInFlight) {
    try {
      await fetch('/api/board/reset-scan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
    } catch (_error) {
      // Best effort: the next stale scan response is ignored by boardScanToken.
    }
    boardScanInFlight = false;
    setBusy('');
  }
}
function selectBoardPosition(col, row) { api('/api/board/select', {col, row}, 'Wybieram pole planszy...'); }
function resetBoardScan() { api('/api/board/reset-scan', {}, 'Resetuję oczekiwanie planszy...'); }
function startEncounterSetup() { api('/api/encounter/setup/start', {}, 'Przygotowuję kroki setupu encountera...'); }
function confirmEncounterSetup() { api('/api/encounter/setup/confirm', {}, 'Potwierdzam krok setupu...'); }
function startEncounterInitiative() { api('/api/encounter/initiative/start', {}, 'Rozpoczynam inicjatywę...'); }
function submitEncounterInitiativeRoll() {
  const input = document.getElementById('encounter-initiative-roll');
  api('/api/encounter/initiative/roll', {natural_roll: Number(input ? input.value : 0)}, 'Zapisuję rzut inicjatywy...');
}
function submitPlayerAttackRoll() {
  api('/api/combat/player-attack-roll', d20RollPayload('combat-attack-natural-roll'), 'Rozstrzygam rzut ataku...');
}
function selectCombatAttackSource(sourceId) { api('/api/combat/attack-source', {source_id: sourceId}, 'Wybieram źródło ataku...'); }
function selectCombatHealingSource(sourceId) { api('/api/combat/healing-source', {source_id: sourceId}, 'Wybieram leczenie...'); }
function confirmPlayerAttackTarget() { api('/api/combat/player-attack-confirm', {}, 'Potwierdzam atak...'); }
function cancelPlayerAttackTarget() { api('/api/combat/player-attack-cancel', {}, 'Anuluję wybór celu...'); }
function confirmCombatInteraction(interactionId) { api('/api/combat/interaction/confirm', {interaction_id: interactionId}, 'Potwierdzam interakcję...'); }
function cancelCombatInteraction() { api('/api/combat/interaction/cancel', {}, 'Anuluję interakcję...'); }
function submitPlayerDamageRoll() {
  const damage = document.getElementById('combat-damage-roll');
  api('/api/combat/player-damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia...');
}
function submitPlayerHealingRoll() {
  const healing = document.getElementById('combat-healing-roll');
  api('/api/combat/player-healing', {healing: Number(healing ? healing.value : 0)}, 'Zapisuję leczenie...');
}
function cancelPlayerHealing() { api('/api/combat/player-healing-cancel', {}, 'Anuluję leczenie...'); }
function confirmAreaSpell() { api('/api/combat/area-spell/confirm', {}, 'Potwierdzam czar obszarowy...'); }
function submitAreaSpellDamage() {
  const damage = document.getElementById('area-spell-damage-roll');
  api('/api/combat/area-spell/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia obszarowe...');
}
function cancelAreaSpell() { api('/api/combat/area-spell/cancel', {}, 'Anuluję czar obszarowy...'); }
function useStrengthPotion(actionId) { api('/api/combat/strength-potion', {action_id: actionId}, 'Używam eliksiru...'); }
function startConcentrationAction(actionId) { api('/api/combat/concentration/start', {action_id: actionId}, 'Przygotowuję czar koncentracyjny...'); }
function confirmConcentrationAction() {
  const target = document.getElementById('combat-concentration-target');
  api('/api/combat/concentration/confirm', {target_id: target ? target.value : ''}, 'Potwierdzam czar koncentracyjny...');
}
function cancelConcentrationAction() { api('/api/combat/concentration/cancel', {}, 'Anuluję czar koncentracyjny...'); }
function submitConcentrationCheck() {
  const roll = document.getElementById('concentration-check-roll');
  api('/api/combat/concentration-check', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam koncentrację...');
}
function submitCombatMove() {
  const destination = document.getElementById('combat-move-destination');
  const parts = destination && destination.value ? destination.value.split(',') : ['0', '0'];
  api('/api/combat/move', {col: Number(parts[0]), row: Number(parts[1])}, 'Wykonuję ruch...');
}
function confirmOpportunityMovement() { api('/api/combat/opportunity-movement/confirm', {}, 'Rozstrzygam ataki okazyjne...'); }
function cancelOpportunityMovement() { api('/api/combat/opportunity-movement/cancel', {}, 'Anuluję ryzykowny ruch...'); }
function useCombatDash() { api('/api/combat/dash', {}, 'Wykonuję Dash...'); }
function useCombatDodge() { api('/api/combat/dodge', {}, 'Wykonuję Unik...'); }
function useCombatDisengage() { api('/api/combat/disengage', {}, 'Wykonuję Odwrót...'); }
function startCombatHelp() { api('/api/combat/help/start', {}, 'Przygotowuję Help...'); }
function confirmCombatHelp() {
  const ally = document.getElementById('combat-help-ally');
  const target = document.getElementById('combat-help-target');
  api('/api/combat/help/confirm', {ally_id: ally ? ally.value : '', target_id: target ? target.value : ''}, 'Potwierdzam Help...');
}
function cancelCombatHelp() { api('/api/combat/help/cancel', {}, 'Anuluję Help...'); }
function startCombatReady() { api('/api/combat/ready/start', {}, 'Przygotowuję Ready...'); }
function confirmCombatReady() {
  const trigger = document.getElementById('combat-ready-trigger');
  api('/api/combat/ready/confirm', {trigger: trigger ? trigger.value : ''}, 'Potwierdzam Ready...');
}
function cancelCombatReady() { api('/api/combat/ready/cancel', {}, 'Anuluję Ready...'); }
function resolveEnemyTurn() { api('/api/combat/enemy-turn', {}, 'Rozgrywam turę przeciwnika...'); }
function startEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/start', {}, 'Rozpoczynam atak okazyjny...'); }
function skipEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/skip', {}, 'Pomijam reakcję...'); }
function submitEnemyOpportunityAttackRoll() {
  api('/api/combat/enemy-opportunity/roll', d20RollPayload('enemy-opportunity-natural-roll'), 'Rozstrzygam atak okazyjny...');
}
function submitEnemyOpportunityDamageRoll() {
  const damage = document.getElementById('enemy-opportunity-damage-roll');
  api('/api/combat/enemy-opportunity/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia ataku okazyjnego...');
}
function startReadyAttack() { api('/api/combat/ready-attack/start', {}, 'Używam przygotowanej akcji...'); }
function skipReadyAttack() { api('/api/combat/ready-attack/skip', {}, 'Pomijam przygotowaną akcję...'); }
function submitReadyAttackRoll() {
  api('/api/combat/ready-attack/roll', d20RollPayload('ready-natural-roll'), 'Rozstrzygam przygotowaną akcję...');
}
function submitReadyDamageRoll() {
  const damage = document.getElementById('ready-damage-roll');
  api('/api/combat/ready-attack/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia przygotowanej akcji...');
}
function confirmEnemyTurnResult() { api('/api/combat/enemy-turn/confirm', {}, 'Potwierdzam wynik przeciwnika...'); }
async function finishCombatTurn() {
  await stopBoardScanLoop();
  api('/api/combat/end-turn', {}, 'Kończę turę...');
}
function resolveCombatOutcome() { api('/api/encounter/combat/resolve', {}, 'Zastosowuję wynik walki w eksploracji...'); }
function ackResult() {
  resultAck = null;
  render();
}
function isVisible(id) {
  const el = document.getElementById(id);
  return Boolean(el && !el.hidden && el.offsetParent !== null);
}
function visiblePrimaryScanButton() {
  const containers = ['flow-panel', 'encounter-panel', 'points-panel'];
  for (const id of containers) {
    const container = document.getElementById(id);
    if (!container || container.hidden || container.offsetParent === null) continue;
    const button = container.querySelector('button[data-primary-scan="true"]');
    if (button && !button.disabled && button.offsetParent !== null) return button;
  }
  return null;
}
function triggerPrimaryAction() {
  if (busy) return false;
  if (isVisible('result-panel')) { ackResult(); return true; }
  if (isVisible('pending-panel')) { decision('accept'); return true; }
  if (isVisible('roll-panel')) { sendRolls(); return true; }
  if (isVisible('action-panel')) { sendAction(); return true; }
  const scanButton = visiblePrimaryScanButton();
  if (scanButton) { scanButton.click(); return true; }
  const setup = state.encounter_setup;
  const initiative = state.encounter_initiative;
  const combat = state.combat;
    if (isVisible('encounter-panel')) {
    if (combat && combat.status === 'finished') { resolveCombatOutcome(); return true; }
    if (combat && combat.status === 'active') {
      if (combat.pending_concentration_check) { submitConcentrationCheck(); return true; }
      if (combat.enemy_turn_result) { confirmEnemyTurnResult(); return true; }
      if (combat.pending_ready_attack) {
        if (combat.pending_ready_attack.stage === 'choice') startReadyAttack();
        else if (combat.pending_ready_attack.stage === 'damage_roll') submitReadyDamageRoll();
        else submitReadyAttackRoll();
        return true;
      }
      if (combat.pending_enemy_opportunity_attack) {
        if (combat.pending_enemy_opportunity_attack.stage === 'choice') startEnemyOpportunityAttack();
        else if (combat.pending_enemy_opportunity_attack.stage === 'damage_roll') submitEnemyOpportunityDamageRoll();
        else submitEnemyOpportunityAttackRoll();
        return true;
      }
      if (combat.pending_opportunity_movement) { confirmOpportunityMovement(); return true; }
      if (combat.pending_combat_help) { confirmCombatHelp(); return true; }
      if (combat.pending_concentration_action) { confirmConcentrationAction(); return true; }
      if (combat.pending_combat_ready) { confirmCombatReady(); return true; }
      if (combat.pending_combat_interaction) {
        const options = combat.pending_combat_interaction.options || [];
        if (options.length) confirmCombatInteraction(options[0].id);
        return true;
      }
      if (combat.pending_player_attack) {
        if (combat.pending_player_attack.stage === 'confirm_attack') confirmPlayerAttackTarget();
        else if (combat.pending_player_attack.stage === 'damage_roll') submitPlayerDamageRoll();
        else submitPlayerAttackRoll();
        return true;
      }
      if (combat.pending_player_healing) { submitPlayerHealingRoll(); return true; }
      if (combat.pending_area_spell) {
        if (combat.pending_area_spell.stage === 'damage_roll') submitAreaSpellDamage();
        else confirmAreaSpell();
        return true;
      }
      if (combat.enemy_turn_preview) return false;
      const actor = combat.current_actor || {};
      if (actor.faction === 'enemy') { resolveEnemyTurn(); return true; }
      return false;
    }
    if (initiative && initiative.status !== 'completed') { submitEncounterInitiativeRoll(); return true; }
    if (setup && setup.status === 'completed' && !initiative) { startEncounterInitiative(); return true; }
    if (setup && setup.current_step && setup.current_step.requires_board_assignment) return false;
    if (setup && setup.status === 'active') { confirmEncounterSetup(); return true; }
    if (!setup) { startEncounterSetup(); return true; }
  }
  if (isVisible('flow-panel')) {
    const stage = state.flow ? state.flow.stage : '';
    const preview = state.flow ? state.flow.preview_zone : null;
    if (stage === 'location_preview' && preview && preview.available !== false) { confirmLocationPreview(); return true; }
    if (stage === 'party_setup' && state.exploration_setup) { confirmExplorationSetup(); return true; }
    if (stage === 'interaction_result') { finishInteraction(); return true; }
    if (stage === 'ready_to_start') { startSession(); return true; }
  }
  return false;
}
document.addEventListener('keydown', event => {
  if (event.key !== 'Enter') return;
  const target = event.target;
  if (target && target.tagName === 'TEXTAREA' && event.shiftKey) return;
  if (target && target.closest && target.closest('details.debug-panel')) return;
  if (triggerPrimaryAction()) {
    event.preventDefault();
  }
});
setSidePanelOpen(sidePanelOpen);
loadState();
</script>
</body>
</html>
"""
