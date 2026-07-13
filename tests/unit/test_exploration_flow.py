import pytest

from dnd_board_game.application import ExplorationFlowService, ExplorationFlowStage
from dnd_board_game.combat import SceneFlags, SetupStep, SetupStepKind, set_scene_flag
from dnd_board_game.exploration import (
    EncounterTriggerCondition,
    ExplorationEncounterTrigger,
    ExplorationPoint,
    ExplorationState,
    ExplorationZone,
    PartyPosition,
)
from dnd_board_game.world import Coordinate


def _zone(
    zone_id: str,
    col: int,
    *,
    available_if_flag: str | None = None,
) -> ExplorationZone:
    return ExplorationZone(
        id=zone_id,
        name=zone_id.title(),
        positions=(Coordinate(col, 0),),
        color=(10, 20, 30),
        available_if_flag=available_if_flag,
    )


def _state(*, unlocked: bool = False, points: tuple[ExplorationPoint, ...] = ()) -> ExplorationState:
    gate = _zone("gate", 0)
    courtyard = _zone("courtyard", 1, available_if_flag="gate_passed")
    flags = SceneFlags()
    if unlocked:
        flags = set_scene_flag(flags, "gate_passed", True)
    return ExplorationState(
        zones=(gate, courtyard),
        points=points,
        party_position=PartyPosition(gate.id, gate.marker_position),
        flags=flags,
    )


def _setup_step(label: str = "przeszkody") -> SetupStep:
    return SetupStep(
        kind=SetupStepKind.ENVIRONMENT,
        label=label,
        positions=(Coordinate(2, 2),),
        color=(1, 2, 3),
        message="Ustaw element.",
    )


def test_start_session_requires_board_and_selects_setup_stage() -> None:
    service = ExplorationFlowService()

    with pytest.raises(ValueError, match="Najpierw wybierz"):
        service.start_session(
            board_connected=False,
            board_backend="none",
            current_stage=ExplorationFlowStage.WAITING_FOR_BOARD,
            setup_steps=(),
        )

    transition = service.start_session(
        board_connected=True,
        board_backend="simulator",
        current_stage=ExplorationFlowStage.READY_TO_START,
        setup_steps=(_setup_step(),),
    )

    assert transition is not None
    assert transition.stage == ExplorationFlowStage.PARTY_SETUP
    assert transition.setup_steps[0].label == "przeszkody"


def test_confirm_location_preview_updates_party_and_emits_existing_event() -> None:
    service = ExplorationFlowService()
    state = _state(unlocked=True)
    gate, courtyard = state.zones

    transition = service.confirm_location_preview(
        current_stage=ExplorationFlowStage.LOCATION_PREVIEW,
        state=state,
        current_zone=gate,
        preview_zone=courtyard,
        active_point_id="old_point",
    )

    assert transition is not None
    assert transition.state.party_position.zone_id == "courtyard"
    assert transition.active_point_id == ""
    assert transition.stage == ExplorationFlowStage.LOCATION_ACTIVE
    assert transition.event_type == "ui_location_preview_confirmed"
    assert dict(transition.event_payload) == {"zone_id": "courtyard"}


def test_confirm_location_preview_rejects_locked_zone() -> None:
    service = ExplorationFlowService()
    state = _state()

    with pytest.raises(ValueError, match="Najpierw trzeba otworzyć bramę"):
        service.confirm_location_preview(
            current_stage=ExplorationFlowStage.LOCATION_PREVIEW,
            state=state,
            current_zone=state.zones[0],
            preview_zone=state.zones[1],
            active_point_id="",
        )


def test_setup_and_finish_interaction_transitions_are_explicit() -> None:
    service = ExplorationFlowService()
    first = _setup_step("pierwszy")
    second = _setup_step("drugi")

    next_step = service.advance_setup_step(steps=(first, second), current_index=0)
    finished = service.advance_setup_step(steps=(first, second), current_index=1)
    after_interaction = service.finish_interaction(
        current_stage=ExplorationFlowStage.INTERACTION_RESULT,
        post_interaction_setup_steps=(first,),
    )

    assert next_step is not None and next_step.current_index == 1 and not next_step.completed
    assert finished is not None and finished.completed
    assert finished.stage == ExplorationFlowStage.LOCATION_PREVIEW
    assert after_interaction is not None
    assert after_interaction.stage == ExplorationFlowStage.PARTY_SETUP
    assert after_interaction.setup_steps == (first,)


def test_travel_and_point_selection_return_transport_neutral_results() -> None:
    service = ExplorationFlowService()
    point = ExplorationPoint(
        id="scout",
        name="Zwiadowca",
        zone_id="gate",
        positions=(Coordinate(0, 1),),
        color=(1, 2, 3),
    )
    state = _state(unlocked=True, points=(point,))
    gate, courtyard = state.zones

    travel = service.travel(
        state=state,
        current_zone=gate,
        travel_options=(courtyard,),
        zone_id="courtyard",
    )
    selection = service.select_point(
        current_stage=ExplorationFlowStage.LOCATION_ACTIVE,
        current_points=(point,),
        point_id="scout",
    )

    assert travel.state.party_position.zone_id == "courtyard"
    assert travel.event_type == "ui_zone_traveled"
    assert selection.active_point_id == "scout"
    assert selection.point is point


def test_encounter_detection_respects_blocking_and_resolved_ids() -> None:
    service = ExplorationFlowService()
    state = _state(unlocked=True)
    trigger = ExplorationEncounterTrigger(
        id="gate_alarm",
        name="Alarm",
        description="Nadchodzą gobliny.",
        encounter_scenario="content/scenarios/gate_skirmish.json",
        condition=EncounterTriggerCondition.FLAG_EQUALS,
        flag_key="gate_passed",
        flag_value=True,
    )

    assert service.detect_encounter(
        state=state,
        triggers=(trigger,),
        resolved_trigger_ids=set(),
        blocked=True,
        current_encounter=None,
    ) is None
    detection = service.detect_encounter(
        state=state,
        triggers=(trigger,),
        resolved_trigger_ids=set(),
        blocked=False,
        current_encounter=None,
    )

    assert detection is not None
    assert detection.encounter.trigger_id == "gate_alarm"
    assert detection.encounter.reason == "Flaga gate_passed ma wartość True."
    assert service.detect_encounter(
        state=state,
        triggers=(trigger,),
        resolved_trigger_ids={"gate_alarm"},
        blocked=False,
        current_encounter=None,
    ) is None
