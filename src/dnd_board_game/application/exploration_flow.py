from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.combat import SetupStep, scene_flag
from dnd_board_game.exploration import (
    ExplorationEncounterTrigger,
    ExplorationPoint,
    ExplorationState,
    ExplorationZone,
    PendingEncounter,
    ScenarioClockEvent,
    TimedMagicEffect,
    challenge_state_for,
    set_party_zone,
    visible_exploration_points,
    zone_is_available,
    advance_exploration_time,
)


class ExplorationFlowStage(StrEnum):
    SPELL_PREPARATION = "spell_preparation"
    WAITING_FOR_BOARD = "waiting_for_board"
    READY_TO_START = "ready_to_start"
    PARTY_SETUP = "party_setup"
    LOCATION_PREVIEW = "location_preview"
    LOCATION_ACTIVE = "location_active"
    SHORT_REST = "short_rest"
    INTERACTION_RESULT = "interaction_result"
    GAME_OVER = "game_over"
    SCENARIO_COMPLETE = "scenario_complete"


@dataclass(frozen=True, slots=True)
class StartSessionTransition:
    stage: ExplorationFlowStage
    setup_steps: tuple[SetupStep, ...]
    board_message: str


@dataclass(frozen=True, slots=True)
class FinishInteractionTransition:
    stage: ExplorationFlowStage
    setup_steps: tuple[SetupStep, ...]
    board_message: str


@dataclass(frozen=True, slots=True)
class CancelPreviewTransition:
    preview_zone_id: str
    board_message: str


@dataclass(frozen=True, slots=True)
class LocationTransition:
    state: ExplorationState
    stage: ExplorationFlowStage
    preview_zone_id: str
    active_point_id: str
    board_message: str
    message_title: str = ""
    message_body: str = ""
    event_type: str = ""
    event_payload: tuple[tuple[str, object], ...] = ()
    elapsed_minutes: int = 0
    expired_magic_effects: tuple[TimedMagicEffect, ...] = ()
    triggered_clock_events: tuple[ScenarioClockEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class SetupStepTransition:
    current_index: int
    completed: bool
    stage: ExplorationFlowStage
    board_message: str
    confirmed_label: str


@dataclass(frozen=True, slots=True)
class PointSelection:
    active_point_id: str
    point: ExplorationPoint | None


@dataclass(frozen=True, slots=True)
class EncounterDetection:
    encounter: PendingEncounter
    message_title: str
    message_body: str


class ExplorationFlowService:
    """Deterministic state transitions for the web exploration flow."""

    def start_session(
        self,
        *,
        board_connected: bool,
        board_backend: str,
        current_stage: ExplorationFlowStage,
        setup_steps: tuple[SetupStep, ...],
        spell_preparation_pending: bool = False,
    ) -> StartSessionTransition | None:
        if not board_connected or board_backend not in {"simulator", "hardware"}:
            raise ValueError("Najpierw wybierz i zastosuj backend planszy: symulator albo hardware.")
        if current_stage not in {
            ExplorationFlowStage.READY_TO_START,
            ExplorationFlowStage.WAITING_FOR_BOARD,
        }:
            return None
        if setup_steps:
            return StartSessionTransition(
                stage=ExplorationFlowStage.PARTY_SETUP,
                setup_steps=setup_steps,
                board_message="Najpierw rozstaw widoczne elementy mapy i potwierdź kroki setupu.",
            )
        return StartSessionTransition(
            stage=(
                ExplorationFlowStage.SPELL_PREPARATION
                if spell_preparation_pending
                else ExplorationFlowStage.LOCATION_PREVIEW
            ),
            setup_steps=(),
            board_message=(
                "Fizyczny setup zakończony. Przygotuj czary przed rozpoczęciem eksploracji."
                if spell_preparation_pending
                else "Wybierz jawny element sceny na planszy."
            ),
        )

    def finish_interaction(
        self,
        *,
        current_stage: ExplorationFlowStage,
        post_interaction_setup_steps: tuple[SetupStep, ...],
    ) -> FinishInteractionTransition | None:
        if current_stage != ExplorationFlowStage.INTERACTION_RESULT:
            return None
        if post_interaction_setup_steps:
            return FinishInteractionTransition(
                stage=ExplorationFlowStage.PARTY_SETUP,
                setup_steps=post_interaction_setup_steps,
                board_message="Rozstaw nowy element mapy wynikający z interakcji.",
            )
        return FinishInteractionTransition(
            stage=ExplorationFlowStage.LOCATION_PREVIEW,
            setup_steps=(),
            board_message="Wybierz kolejną dostępną lokację na planszy.",
        )

    def cancel_location_preview(
        self,
        *,
        current_stage: ExplorationFlowStage,
    ) -> CancelPreviewTransition | None:
        if current_stage != ExplorationFlowStage.LOCATION_PREVIEW:
            return None
        return CancelPreviewTransition(
            preview_zone_id="",
            board_message="Wrócono do wyboru dostępnych lokacji.",
        )

    def confirm_location_preview(
        self,
        *,
        current_stage: ExplorationFlowStage,
        state: ExplorationState,
        current_zone: ExplorationZone,
        preview_zone: ExplorationZone | None,
        active_point_id: str,
    ) -> LocationTransition | None:
        if current_stage != ExplorationFlowStage.LOCATION_PREVIEW:
            return None
        if preview_zone is None:
            raise ValueError("Najpierw wybierz element sceny na planszy.")
        if not zone_is_available(state, preview_zone):
            raise ValueError(_locked_zone_message(preview_zone))
        updated_state = state
        updated_active_point_id = active_point_id
        if preview_zone.id != current_zone.id:
            updated_state = set_party_zone(state, preview_zone)
            updated_active_point_id = ""
        return LocationTransition(
            state=updated_state,
            stage=ExplorationFlowStage.LOCATION_ACTIVE,
            preview_zone_id="",
            active_point_id=updated_active_point_id,
            board_message=f"Drużyna wchodzi do lokacji: {preview_zone.name}.",
            event_type="ui_location_preview_confirmed",
            event_payload=(("zone_id", preview_zone.id),),
        )

    def advance_setup_step(
        self,
        *,
        steps: tuple[SetupStep, ...],
        current_index: int,
        spell_preparation_pending: bool = False,
    ) -> SetupStepTransition | None:
        if not steps or current_index >= len(steps):
            return None
        step = steps[current_index]
        completed = current_index + 1 >= len(steps)
        return SetupStepTransition(
            current_index=current_index if completed else current_index + 1,
            completed=completed,
            stage=(
                ExplorationFlowStage.SPELL_PREPARATION
                if completed and spell_preparation_pending
                else ExplorationFlowStage.LOCATION_PREVIEW
                if completed
                else ExplorationFlowStage.PARTY_SETUP
            ),
            board_message=(
                "Elementy mapy ustawione. Przygotuj czary przed rozpoczęciem eksploracji."
                if completed and spell_preparation_pending
                else "Elementy mapy ustawione. Wybierz jawny element sceny na planszy."
                if completed
                else "Potwierdź kolejny element mapy."
            ),
            confirmed_label=step.label,
        )

    def travel(
        self,
        *,
        state: ExplorationState,
        current_zone: ExplorationZone,
        travel_options: tuple[ExplorationZone, ...],
        zone_id: str,
    ) -> LocationTransition:
        destination = next((zone for zone in travel_options if zone.id == zone_id), None)
        if destination is None:
            raise ValueError("Ta lokacja nie jest teraz dostępna.")
        time_advance = advance_exploration_time(
            set_party_zone(state, destination),
            destination.travel_minutes,
        )
        return LocationTransition(
            state=time_advance.state,
            stage=ExplorationFlowStage.LOCATION_ACTIVE,
            preview_zone_id="",
            active_point_id="",
            board_message=(
                f"Drużyna przechodzi do lokacji: {destination.name}. "
                "Wybierzcie punkt albo działanie dostępne w tej lokacji."
            ),
            message_title="Przejście",
            message_body=(
                f"Drużyna przechodzi z {current_zone.name} do lokacji: "
                f"{destination.name}."
                + (
                    f" Mija {destination.travel_minutes} min."
                    if destination.travel_minutes
                    else ""
                )
            ),
            event_type="ui_zone_traveled",
            event_payload=(
                ("from_zone_id", current_zone.id),
                ("to_zone_id", destination.id),
                ("elapsed_minutes", destination.travel_minutes),
            ),
            elapsed_minutes=destination.travel_minutes,
            expired_magic_effects=time_advance.expired_effects,
            triggered_clock_events=time_advance.triggered_clock_events,
        )

    def select_point(
        self,
        *,
        current_stage: ExplorationFlowStage,
        current_points: tuple[ExplorationPoint, ...],
        point_id: str,
    ) -> PointSelection:
        if current_stage != ExplorationFlowStage.LOCATION_ACTIVE:
            raise ValueError("Najpierw potwierdź wejście do lokacji.")
        if not point_id:
            return PointSelection(active_point_id="", point=None)
        point = next((candidate for candidate in current_points if candidate.id == point_id), None)
        if point is None:
            raise ValueError("Ten punkt nie jest dostępny w aktualnej lokacji.")
        return PointSelection(active_point_id=point.id, point=point)

    def detect_encounter(
        self,
        *,
        state: ExplorationState,
        triggers: tuple[ExplorationEncounterTrigger, ...],
        resolved_trigger_ids: set[str],
        blocked: bool,
        current_encounter: PendingEncounter | None,
    ) -> EncounterDetection | None:
        if blocked or current_encounter is not None:
            return None
        for trigger in triggers:
            if trigger.id in resolved_trigger_ids:
                continue
            reason = self.trigger_reason(state, trigger)
            if not reason:
                continue
            encounter = PendingEncounter(
                trigger_id=trigger.id,
                name=trigger.name,
                description=trigger.description,
                encounter_scenario=trigger.encounter_scenario,
                reason=reason,
            )
            return EncounterDetection(
                encounter=encounter,
                message_title="Encounter",
                message_body=f"{trigger.name}. {trigger.description}".strip(),
            )
        return None

    @staticmethod
    def trigger_reason(state: ExplorationState, trigger: ExplorationEncounterTrigger) -> str:
        if trigger.condition.value == "always":
            return "Encounter rozpoczyna się natychmiast po wejściu do sceny."
        if trigger.condition.value == "noise_at_least" and trigger.challenge_id is not None and trigger.noise is not None:
            noise = challenge_state_for(state, trigger.challenge_id).noise
            if noise >= trigger.noise:
                return f"Hałas osiągnął {noise}, próg: {trigger.noise}."
        if trigger.condition.value == "flag_equals" and trigger.flag_key:
            value = scene_flag(state.flags, trigger.flag_key, None)
            if value == trigger.flag_value:
                return f"Flaga {trigger.flag_key} ma wartość {trigger.flag_value}."
        if trigger.condition.value == "point_revealed" and trigger.point_id:
            visible_ids = {point.id for point in visible_exploration_points(state.points)}
            if trigger.point_id in visible_ids:
                return f"Ujawniono punkt: {trigger.point_id}."
        return ""


def _locked_zone_message(zone: ExplorationZone) -> str:
    if zone.available_if_flag == "gate_passed":
        return f"{zone.name} jest jeszcze niedostępna. Najpierw trzeba otworzyć bramę."
    return f"{zone.name} jest jeszcze niedostępna."
