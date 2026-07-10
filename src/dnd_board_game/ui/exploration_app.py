from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request, send_from_directory

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActorSetupEntry,
    ActionUse,
    AttackDeclaration,
    CombatState,
    EncounterSetup,
    InitiativeEntry,
    InitiativeOrder,
    DamageComponentInput,
    DamageType,
    InitiativePrompt,
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
    finish_turn,
    active_actor_led_feedback,
    apply_damage,
    initiative_prompt_led_feedback,
    replace_actor,
    resolve_attack,
    resolve_damage,
    resolve_enemy_auto_turn,
    roll_enemy_initiative,
    plan_enemy_turn,
    scene_flag,
    select_attack_target,
    setup_led_feedback,
    start_combat,
    start_attack_action,
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
    apply_exploration_effect,
    available_exploration_zones,
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
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, ability_modifier, resolve_d20_roll, roll_instruction
from dnd_board_game.scenarios import (
    LoadedEncounter,
    LoadedExploration,
    build_encounter_from_scenario,
    build_exploration_from_scenario,
    load_scenario,
)
from dnd_board_game.runtime.session_observer import SessionObserver
from dnd_board_game.world import Coordinate, MovementRangeResult, find_path, movement_range


class PendingKind(StrEnum):
    CHALLENGE = "challenge"
    NPC = "npc"


class PendingStage(StrEnum):
    DECISION = "decision"
    ROLL = "roll"


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
    stage: str = "confirm_attack"
    natural_roll: int | None = None
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
            "active_challenge": _challenge_payload(self.state, active_challenge) if active_challenge else None,
            "active_point": _point_payload(self.active_point) if self.active_point else None,
            "resources": [_resource_payload(resource) for resource in self.state.resources if resource.id in self.state.inventory_resource_ids],
            "actors": [{"id": str(actor.id), "name": actor.name} for actor in self.exploration.actors],
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

    def submit_player_attack(self, *, target_id: str, natural_roll: int, damage: int = 0) -> dict[str, object]:
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
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=target_id)
        assert selected.selected_target is not None
        declaration = AttackDeclaration(attacker=attacker, target=selected.selected_target, source=source)
        attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, natural_roll))
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        resolution = resolve_attack(declaration, attack_roll, selected.action_use)
        updated_state = action_result.state
        message = _player_attack_message(attacker.name, selected.selected_target.name, attack_roll.total, resolution.hit, resolution.critical)
        if resolution.hit:
            damage_amount = max(0, int(damage))
            damage_result = resolve_damage((DamageComponentInput(damage_amount, DamageType(source.damage_type), source.name),))
            target_actor = next((actor for actor in updated_state.actors if str(actor.id) == selected.selected_target.id), None)
            if target_actor is None:
                raise ValueError(f"Nieznany cel ataku: {selected.selected_target.id}.")
            updated_target = apply_damage(target_actor, damage_result)
            updated_state = replace_actor(updated_state, updated_target)
            message = f"{message} Obrażenia: {damage_result.total_applied}. {target_actor.name}: HP {target_actor.hp} -> {updated_target.hp}."
        self.combat_state = updated_state
        self.pending_player_attack = None
        self.selected_combat_movement_path = None
        self._add_message("Atak", message)
        self._record(
            "ui_combat_player_attack",
            {
                "attacker_id": str(attacker.id),
                "target_id": selected.selected_target.id,
                "natural_roll": attack_roll.natural_roll,
                "total": attack_roll.total,
                "hit": resolution.hit,
                "critical": resolution.critical,
                "damage": int(damage) if resolution.hit else 0,
            },
        )
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
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, position=position)
        assert selected.selected_target is not None
        self.pending_player_attack = PendingPlayerAttack(
            attacker_id=str(attacker.id),
            target_id=selected.selected_target.id,
        )
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
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=pending.target_id)
        assert selected.selected_target is not None
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

    def submit_player_attack_roll(self, *, natural_roll: int) -> dict[str, object]:
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
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        action = start_attack_action(encounter.board, attacker, self.combat_state.actors, source)
        selected = select_attack_target(action, target_id=pending.target_id)
        assert selected.selected_target is not None
        declaration = AttackDeclaration(attacker=attacker, target=selected.selected_target, source=source)
        attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, int(natural_roll)))
        action_result = use_turn_action(self.combat_state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        resolution = resolve_attack(declaration, attack_roll, selected.action_use)
        self.combat_state = action_result.state
        self.selected_combat_movement_path = None
        message = _player_attack_message(attacker.name, selected.selected_target.name, attack_roll.total, resolution.hit, resolution.critical)
        if not resolution.hit:
            self.pending_player_attack = None
            self._add_message("Atak", message)
            self._record(
                "ui_combat_player_attack_roll",
                {
                    "attacker_id": str(attacker.id),
                    "target_id": selected.selected_target.id,
                    "natural_roll": attack_roll.natural_roll,
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
        source = encounter.attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        target_actor = next((actor for actor in self.combat_state.actors if str(actor.id) == pending.target_id), None)
        if target_actor is None:
            raise ValueError(f"Nieznany cel ataku: {pending.target_id}.")
        damage_amount = max(0, int(damage))
        damage_result = resolve_damage((DamageComponentInput(damage_amount, DamageType(source.damage_type), source.name),))
        updated_target = apply_damage(target_actor, damage_result)
        self.combat_state = replace_actor(self.combat_state, updated_target)
        self.pending_player_attack = None
        self._add_message(
            "Obrażenia",
            f"{attacker.name} zadaje {damage_result.total_applied} obrażeń. {target_actor.name}: HP {target_actor.hp} -> {updated_target.hp}.",
        )
        self._record(
            "ui_combat_player_damage_roll",
            {
                "attacker_id": str(attacker.id),
                "target_id": str(target_actor.id),
                "damage": damage_result.total_applied,
            },
        )
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
        path = find_path(encounter.board, actor, self.combat_state.actors, destination)
        if not path.valid:
            raise ValueError("Nie można dojść do wskazanego pola.")
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
        path = find_path(encounter.board, actor, self.combat_state.actors, destination)
        result = use_movement(self.combat_state, actor, path)
        if not result.accepted:
            raise ValueError(result.message)
        self.combat_state = result.state
        self.selected_combat_movement_path = None
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
        self.pending_enemy_turn_intent = None
        result = resolve_enemy_auto_turn(encounter.board, self.combat_state, enemy, source, self.encounter_rng)
        if result.movement_path is not None and result.movement_path.valid and result.movement_path.destination != enemy.position:
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
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
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
        self._sync_board_leds()
        return self.state_payload()

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
        self.combat_state = finish_turn(result.state)
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
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
        self.combat_state = finish_turn(self.combat_state)
        self.selected_combat_movement_path = None
        self.pending_enemy_turn_intent = None
        self.pending_enemy_turn_result = None
        self.pending_enemy_turn_ack_result = None
        self.pending_player_attack = None
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
            if encounter is not None and actor.faction == Faction.ALLY and self.combat_state.status.value == "active":
                movement = _remaining_movement_range(encounter.board, self.combat_state, actor)
                attack_targets = _legal_combat_targets(encounter, self.combat_state, actor)
                return BoardScanTarget(
                    positions=tuple(sorted(movement.reachable_tiles | frozenset(target.position for target in attack_targets))),
                    feedback=_combat_choice_led_feedback(movement, attack_targets, self.selected_combat_movement_path, encounter.board),
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
                    if encounter is not None and _combat_target_at_position(encounter, self.combat_state, actor, selected) is not None:
                        self.board_message = f"Atak bohatera: {actor.name} -> {selected.as_tuple()}."
                        return self.select_player_attack_target_at_position(selected)
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
        plan = _challenge_check_plan(option, self.lead_actor_id)
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
            },
        )
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
        if self.pending is None or self.pending.stage != PendingStage.ROLL or self.pending.check_plan is None:
            return []
        return [
            {"actor_id": str(actor.id), "actor_name": actor.name}
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
            return jsonify(session.submit_player_attack_roll(natural_roll=int(data.get("natural_roll", 0))))
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

    @app.post("/api/combat/move")
    def api_combat_move():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_combat_movement(col=int(data.get("col", 0)), row=int(data.get("row", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-turn")
    def api_combat_enemy_turn():
        try:
            return jsonify(session.resolve_enemy_turn())
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


def _combat_payload(
    state: CombatState | None,
    encounter: LoadedEncounter | None = None,
    selected_movement_path=None,
    pending_enemy_turn_intent=None,
    pending_enemy_turn_result=None,
    pending_enemy_turn_ack_result=None,
    pending_player_attack: PendingPlayerAttack | None = None,
) -> dict[str, object] | None:
    if state is None:
        return None
    actor = combat_current_actor(state)
    attack_source = encounter.attack_sources_by_actor.get(actor.id) if encounter is not None else None
    targets = ()
    movement = None
    if (
        encounter is not None
        and attack_source is not None
        and state.status.value == "active"
        and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    ):
        targets = start_attack_action(encounter.board, actor, state.actors, attack_source).legal_targets
    if encounter is not None and actor.faction == Faction.ALLY and state.status.value == "active":
        movement = _remaining_movement_range(encounter.board, state, actor)
    return {
        "status": state.status.value,
        "round_number": state.round_number,
        "current_actor": _combat_actor_payload(actor),
        "actors": [_combat_actor_payload(candidate) for candidate in state.actors],
        "winner": state.winner.value if state.winner is not None else None,
        "turn_action": {
            "action_use": state.turn_action.action_use.value,
            "movement_used_feet": state.turn_action.movement_used_feet,
        },
        "available_attack": _attack_source_payload(attack_source) if attack_source is not None else None,
        "legal_targets": [_combat_target_payload(target) for target in targets],
        "movement": _movement_payload(movement, state, actor) if movement is not None else None,
        "movement_preview": _movement_preview_payload(selected_movement_path),
        "enemy_turn_intent": _enemy_turn_intent_payload(pending_enemy_turn_intent, encounter),
        "enemy_turn_preview": _enemy_turn_preview_payload(pending_enemy_turn_result, encounter),
        "enemy_turn_result": _enemy_turn_result_payload(pending_enemy_turn_ack_result, encounter),
        "pending_player_attack": _pending_player_attack_payload(pending_player_attack, state, encounter),
    }


def _combat_actor_payload(actor: Actor) -> dict[str, object]:
    return {
        "id": str(actor.id),
        "name": actor.name,
        "faction": actor.faction.value,
        "hp": actor.hp,
        "temp_hp": actor.temp_hp,
        "ac": actor.ac,
        "position": [actor.position.col, actor.position.row],
        "defeated": actor.is_defeated(),
    }


def _attack_source_payload(source) -> dict[str, object]:
    return {
        "name": source.name,
        "range_feet": source.range_feet,
        "damage_hint": source.damage_hint,
        "damage_fixed": source.damage_fixed,
        "damage_die_sides": source.damage_die_sides,
        "damage_modifier": source.damage_modifier,
        "damage_type": source.damage_type,
    }


def _pending_player_attack_payload(
    pending: PendingPlayerAttack | None,
    state: CombatState,
    encounter: LoadedEncounter | None,
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
    instruction = roll_instruction(source.attack_roll_request)
    return {
        "stage": pending.stage,
        "attacker": _combat_actor_payload(attacker),
        "target": _combat_actor_payload(target),
        "source": _attack_source_payload(source),
        "attack_instruction": instruction.message,
        "attack_modifier": instruction.breakdown.modifier_total,
        "attack_mode": instruction.mode.value,
        "active_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_roll_modifier_payload(modifier) for modifier in instruction.breakdown.ignored_modifiers],
        "damage_instruction": _damage_roll_instruction(source),
        "natural_roll": pending.natural_roll,
        "total": pending.total,
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
        "position": [target.position.col, target.position.row],
    }


def _remaining_movement_range(board, state: CombatState, actor: Actor) -> MovementRangeResult:
    result = movement_range(board, actor, state.actors)
    remaining = max(0, actor.speed_feet - state.turn_action.movement_used_feet)
    reachable = frozenset(tile for tile in result.reachable_tiles if result.costs_by_tile.get(tile, 999) <= remaining)
    costs = {tile: cost for tile, cost in result.costs_by_tile.items() if tile in reachable}
    paths = {tile: path for tile, path in result.paths_by_tile.items() if tile in reachable}
    return MovementRangeResult(origin=result.origin, reachable_tiles=reachable, costs_by_tile=costs, paths_by_tile=paths)


def _legal_combat_targets(encounter: LoadedEncounter, state: CombatState, actor: Actor):
    if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
        return ()
    source = encounter.attack_sources_by_actor.get(actor.id)
    if source is None:
        return ()
    return start_attack_action(encounter.board, actor, state.actors, source).legal_targets


def _combat_target_at_position(encounter: LoadedEncounter, state: CombatState, actor: Actor, position: Coordinate):
    for target in _legal_combat_targets(encounter, state, actor):
        if target.position == position:
            return target
    return None


def _combat_choice_led_feedback(movement: MovementRangeResult, attack_targets, selected_path=None, board=None) -> LedFeedback:
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


def _enemy_turn_intent_payload(intent, encounter: LoadedEncounter | None = None) -> dict[str, object] | None:
    if intent is None:
        return None
    payload: dict[str, object] = {
        "enemy_id": str(intent.enemy.id),
        "enemy_name": intent.enemy.name,
        "message": _enemy_turn_intent_message(intent),
    }
    source = encounter.attack_sources_by_actor.get(intent.enemy.id) if encounter is not None else None
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


def _enemy_turn_preview_payload(result, encounter: LoadedEncounter | None = None) -> dict[str, object] | None:
    if result is None:
        return None
    payload: dict[str, object] = {"enemy_id": str(result.enemy.id), "enemy_name": result.enemy.name}
    source = encounter.attack_sources_by_actor.get(result.enemy.id) if encounter is not None else None
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
        payload["total"] = result.attack_roll.total
    if result.attack_resolution is not None:
        payload["hit"] = result.attack_resolution.hit
        payload["critical"] = result.attack_resolution.critical
    if result.damage is not None:
        payload["damage"] = result.damage.total_applied
    if result.movement_path is not None and result.movement_path.valid:
        payload["kind"] = "movement"
        payload["destination"] = [result.movement_path.destination.col, result.movement_path.destination.row]
        payload["path"] = [[position.col, position.row] for position in result.movement_path.path]
        payload["cost_feet"] = result.movement_path.cost_feet
    elif result.target is not None:
        payload["kind"] = "attack"
    return payload


def _enemy_turn_result_payload(result, encounter: LoadedEncounter | None = None) -> dict[str, object] | None:
    payload = _enemy_turn_preview_payload(result, encounter)
    if payload is None:
        return None
    payload["message"] = _enemy_turn_message(result)
    payload["summary"] = _enemy_roll_summary(result)
    return payload


def _enemy_roll_summary(result) -> str:
    if result.attack_roll is None or result.target is None:
        return ""
    parts = [
        f"Rzut d20: {result.attack_roll.natural_roll}",
        f"wynik końcowy: {result.attack_roll.total}",
    ]
    if result.attack_resolution is not None:
        parts.append("trafienie" if result.attack_resolution.hit else "pudło")
        if result.attack_resolution.critical:
            parts.append("krytyk")
    if result.damage is not None:
        parts.append(f"obrażenia: {result.damage.total_applied}")
    return ". ".join(parts) + "."


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
    remaining = max(0, actor.speed_feet - state.turn_action.movement_used_feet)
    destinations = tuple(sorted(tile for tile in result.reachable_tiles if tile != result.origin))
    return {
        "remaining_feet": remaining,
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


def _challenge_check_plan(option: ExplorationChallengeOption, lead_actor_id: str) -> ExplorationCheckPlan:
    return ExplorationCheckPlan(
        participants=option.check_participants or CheckParticipants.SINGLE_ACTOR,
        aggregation=option.check_aggregation or CheckAggregation.LEAD_RESULT,
        consequence_targets=option.consequence_targets or (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.SCENE),
        ability=option.ability_check.ability,
        skill=option.ability_check.skill,
        dc=option.ability_check.dc,
        lead_actor_id=lead_actor_id,
        reason_for_players=option.description,
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
        request = D20RollRequest(modifiers=_ability_roll_modifiers(actor, plan.ability, plan.skill))
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


def _challenge_payload(state: ExplorationState, challenge: ExplorationChallenge | None) -> dict[str, object] | None:
    if challenge is None:
        return None
    challenge_state = challenge_state_for(state, challenge.id)
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


def _challenge_option_payload(option: ExplorationChallengeOption) -> dict[str, object]:
    return {
        "id": option.id,
        "label": option.label,
        "ability": option.ability_check.ability,
        "skill": option.ability_check.skill,
        "dc": option.ability_check.dc,
        "progress_on_success": option.progress_on_success,
        "progress_on_failure": option.progress_on_failure,
        "tags": list(option.tags),
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
    main { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
    aside { border-right: 1px solid #34383d; padding: 16px; background: #171a1e; overflow: auto; }
    section { padding: 18px; overflow: auto; }
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
    .status-item:last-child { border-bottom: 0; padding-bottom: 0; }
    .status-item b { display: block; }
    .combat-current-step { border: 1px solid #4b4227; border-radius: 6px; background: #181713; padding: 12px; }
    .combat-prompt { border-left: 4px solid #f5c542; background: #211f16; color: #f5e3a1; padding: 12px 14px; margin: 0 0 10px; }
    .combat-prompt b { display: block; font-size: 18px; margin-bottom: 4px; }
    .combat-mini-status { display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 10px; color: #d6d0c4; font-size: 13px; }
    .combat-mini-status span { border: 1px solid #34383d; border-radius: 999px; padding: 3px 8px; background: #111417; }
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
<main>
  <aside>
    <h2 id="scenario">Scenariusz</h2>
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
  document.getElementById('rolls').innerHTML = state.required_rolls.map(r => `<label>${r.actor_name}: <input data-actor="${r.actor_id}" type="number" min="1" max="20" value="10"></label>`).join(' ');
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
  if (!state.pending || state.pending.stage !== 'roll') return '';
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
  return `<p><b>Format rzutu:</b> ${esc(participants)}${aggregation ? `, ${esc(aggregation)}` : ''}.</p><p><b>Rzucają:</b> ${esc(names || '-')}</p>`;
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
      <p><b>Kolejność inicjatywy:</b> ${order.map(entry => `${esc(entry.actor_name)} (${entry.total})`).join(', ')}</p>
      <div class="status-list">
        ${actors.map(actor => `
          <div class="status-item">
            <b>${esc(actor.name)} ${actor.id === combat.current_actor.id ? '(tura)' : ''}</b>
            <span>${esc(actor.faction)} | HP ${esc(actor.hp)} / AC ${esc(actor.ac)} | pole (${esc(actor.position[0])},${esc(actor.position[1])})</span>
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
  if (isEnemyTurn) {
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
  if (isAllyTurn && combat.movement_preview) return `Tura ${actor.name || 'gracza'}: potwierdź ruch`;
  if (isAllyTurn) return `Tura ${actor.name || 'gracza'}: wybierz ruch albo cel`;
  return `Tura ${actor.name || '-'}`;
}
function combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn) {
  if (finished) return 'Zastosuj wynik walki, żeby wrócić do eksploracji.';
  const actor = combat.current_actor || {};
  if (isEnemyTurn) {
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
  const pending = combat.pending_player_attack || null;
  if (pending) {
    const target = pending.target || {};
    const source = pending.source || {};
    if (pending.stage === 'confirm_attack') {
      return `Wybrano ${target.name || '-'}. Potwierdź atak, żeby przejść do rzutu d20.`;
    }
    if (pending.stage === 'damage_roll') {
      return `Trafiono ${target.name || 'cel'}. Rzuć obrażenia ${pending.damage_instruction || source.damage_hint || ''} i wpisz wynik.`;
    }
    return `Wybrano cel ${target.name || '-'}. Rzuć d20 na atak ${source.name || ''} i wpisz naturalny wynik.`;
  }
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const remaining = Number(movement.remaining_feet || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  if (preview) {
    return `Wybrano ruch na (${preview.destination[0]},${preview.destination[1]}). Uruchom skan i kliknij pole docelowe, żeby zatwierdzić.`;
  }
  if (actionUsed && remaining > 0) return `Akcja zużyta. Możesz jeszcze ruszyć się (${remaining} ft) albo zakończyć turę.`;
  if (actionUsed) return 'Akcja zużyta. Możesz zakończyć turę.';
  if (remaining > 0) return `Kliknij Skanuj planszę, a potem wybierz niebieskie pole ruchu albo czerwony cel.`;
  return 'Ruch wykorzystany. Możesz zaatakować czerwony cel albo zakończyć turę.';
}
function combatMiniStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const position = actor.position || ['-', '-'];
  return `
    <div class="combat-mini-status">
      <span>Runda ${esc(combat.round_number || '-')}</span>
      <span>${esc(actor.name || '-')}</span>
      <span>HP ${esc(actor.hp)} / AC ${esc(actor.ac)}</span>
      <span>Pole (${esc(position[0])},${esc(position[1])})</span>
      ${actor.faction === 'ally' ? `<span>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'}</span><span>Ruch: ${esc(remaining)} ft</span>` : ''}
    </div>
  `;
}
function combatActorStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  return `
    <p><b>${esc(actor.name || '-')}</b> (${esc(actor.faction || '-')})</p>
    <p>Runda ${esc(combat.round_number || '-')}, pole (${esc(actor.position ? actor.position[0] : '-')},${esc(actor.position ? actor.position[1] : '-')})</p>
    <p>HP ${esc(actor.hp)} / AC ${esc(actor.ac)}</p>
    ${actor.faction === 'ally' ? `<p>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'} | Ruch: ${esc(remaining)} ft</p>` : ''}
  `;
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
  const combatTitles = new Set(['Atak', 'Obrażenia', 'Ruch', 'Koniec tury', 'Atak przeciwnika', 'Obrażenia przeciwnika', 'Ruch przeciwnika', 'Tura przeciwnika']);
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (!combatTitles.has(messages[i].title)) continue;
    return `<p><b>${esc(messages[i].title)}</b></p><p>${esc(messages[i].body)}</p>`;
  }
  return '<p class="combat-empty">Brak rezultatu w tej walce.</p>';
}
function combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn) {
  if (isEnemyTurn) {
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
  if (combat.pending_player_attack) {
    return pendingPlayerAttackHtml(combat.pending_player_attack);
  }
  const movement = combat.movement || {remaining_feet: 0, destinations: []};
  const preview = combat.movement_preview || null;
  return `
    ${preview ? `<p>Potwierdź pole: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : `<p>Ruch dostępny: ${esc(movement.remaining_feet || 0)} ft.</p>`}
    <div class="row"><button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button><button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button></div>
  `;
}
function combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn) {
  if (isEnemyTurn) return enemyTurnDetailsHtml(combat);
  if (!isAllyTurn) return '<p class="muted">Brak dodatkowych szczegółów dla tego aktora.</p>';
  if (combat.pending_player_attack) return pendingPlayerAttackDetailsHtml(combat.pending_player_attack);
  return playerTurnDetailsHtml(combat);
}
function playerTurnDetailsHtml(combat) {
  const source = combat.available_attack || {};
  const targets = combat.legal_targets || [];
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const remaining = Number(movement.remaining_feet || 0);
  const moveCount = (movement.destinations || []).length;
  const targetText = targets.length
    ? targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ')
    : 'brak';
  return `
    <p><b>Tura gracza:</b> ${esc(actor.name || '-')}</p>
    <p><b>Akcja:</b> ${actionUsed ? 'zużyta' : 'dostępna'} | <b>Ruch:</b> ${esc(remaining)} ft</p>
    <p>Niebieskie pola: ruch (${esc(moveCount)} pól). Czerwone pola: legalne cele ataku.</p>
    ${preview ? `<p>Wybrana ścieżka: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : ''}
    <p><b>Atak:</b> ${esc(source.name || '-')}${source.damage_hint ? `, po trafieniu rzuć ${esc(source.damage_hint)}` : ''}</p>
    <p><b>Cele w zasięgu:</b> ${esc(targetText)}</p>
  `;
}
function enemyTurnDetailsHtml(combat) {
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
      ${moveText}
      ${attackText}
    `;
  }
  const result = combat.enemy_turn_result || null;
  if (result) {
    const target = result.target_name ? ` przeciwko ${esc(result.target_name)}` : '';
    const hitText = result.hit === true ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : (result.hit === false ? 'PUDŁO' : 'BRAK ATAKU');
    const rollHtml = result.natural_roll !== null && result.natural_roll !== undefined
      ? `<p><b>Rzut d20:</b> ${esc(result.natural_roll)} | <b>Wynik końcowy:</b> ${esc(result.total)}</p>`
      : '';
    const damageHtml = result.damage !== null && result.damage !== undefined
      ? `<p><b>Obrażenia:</b> ${esc(result.damage)}</p>`
      : '';
    return `
      <p><b>Wynik tury przeciwnika:</b> ${hitText}</p>
      <p>${esc(result.enemy_name || 'Przeciwnik')}${target}</p>
      ${rollHtml}
      ${damageHtml}
      <p class="muted">${esc(result.message || '')}</p>
    `;
  }
  const preview = combat.enemy_turn_preview || null;
  if (preview && preview.kind === 'movement') {
    return `<p><b>Ruch przeciwnika:</b> ${esc(preview.enemy_name)} porusza się na (${esc(preview.destination[0])},${esc(preview.destination[1])}). Przestaw figurkę po ścieżce i potwierdź pole planszą.${enemyRollSummaryHtml(preview)}</p>`;
  }
  if (preview && preview.kind === 'attack') {
    return `<p><b>Atak przeciwnika:</b> ${esc(preview.enemy_name)} atakuje ${esc(preview.target_name)}. Potwierdź podświetlony cel planszą.${enemyRollSummaryHtml(preview)}</p>`;
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
function pendingPlayerAttackHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'confirm_attack') {
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
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
      <label>Wynik d20: <input id="combat-attack-natural-roll" type="number" min="1" max="20" value="10"></label>
      <button onclick="submitPlayerAttackRoll()">Zapisz rzut</button>
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
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
      ${ignored.length ? `<p><b>Odrzucone duplikaty:</b> ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}</p>` : ''}
      <p><b>Rzut:</b> ${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
      <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p><b>Tura gracza: wpisz obrażenia</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Trafienie:</b> ${pending.critical ? 'krytyczne' : 'zwykłe'}</p>
      <p><b>Rzut d20:</b> ${esc(pending.natural_roll || '')} | <b>Wynik końcowy:</b> ${esc(pending.total || '')}</p>
      <p><b>Co teraz:</b> ${esc(pending.damage_instruction || '')}</p>
    `;
  }
  return `
    <p><b>Tura gracza: wybrano cel</b></p>
    <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Atak:</b> ${esc(source.name || '-')}</p>
    <p><b>Co teraz:</b> ${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
  `;
}
function enemyRollSummaryHtml(preview) {
  if (!preview || preview.natural_roll === null || preview.natural_roll === undefined) return '';
  const outcome = preview.hit ? (preview.critical ? 'trafienie krytyczne' : 'trafienie') : 'pudło';
  const damage = preview.damage !== null && preview.damage !== undefined ? `<br>Obrażenia: ${esc(preview.damage)}.` : '';
  return `<br>Automatyczny rzut przeciwnika: d20 ${esc(preview.natural_roll)}, razem ${esc(preview.total)} (${outcome}).${damage}`;
}
function defaultDamageValue(source) {
  if (!source) return 0;
  if (source.damage_fixed !== null && source.damage_fixed !== undefined) return Number(source.damage_fixed) + Number(source.damage_modifier || 0);
  return Math.max(0, Number(source.damage_modifier || 0));
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
  return Boolean(combat && combat.status === 'active' && actor.faction === 'ally' && !combat.enemy_turn_preview && !combat.pending_player_attack);
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
  const roll = document.getElementById('combat-attack-natural-roll');
  api('/api/combat/player-attack-roll', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam rzut ataku...');
}
function confirmPlayerAttackTarget() { api('/api/combat/player-attack-confirm', {}, 'Potwierdzam atak...'); }
function cancelPlayerAttackTarget() { api('/api/combat/player-attack-cancel', {}, 'Anuluję wybór celu...'); }
function submitPlayerDamageRoll() {
  const damage = document.getElementById('combat-damage-roll');
  api('/api/combat/player-damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia...');
}
function submitCombatMove() {
  const destination = document.getElementById('combat-move-destination');
  const parts = destination && destination.value ? destination.value.split(',') : ['0', '0'];
  api('/api/combat/move', {col: Number(parts[0]), row: Number(parts[1])}, 'Wykonuję ruch...');
}
function resolveEnemyTurn() { api('/api/combat/enemy-turn', {}, 'Rozgrywam turę przeciwnika...'); }
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
      if (combat.enemy_turn_result) { confirmEnemyTurnResult(); return true; }
      if (combat.pending_player_attack) {
        if (combat.pending_player_attack.stage === 'confirm_attack') confirmPlayerAttackTarget();
        else if (combat.pending_player_attack.stage === 'damage_roll') submitPlayerDamageRoll();
        else submitPlayerAttackRoll();
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
loadState();
</script>
</body>
</html>
"""
