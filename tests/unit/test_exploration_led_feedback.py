from dnd_board_game.exploration import (
    ExplorationState,
    build_exploration_menu,
    exploration_menu_feedback,
    exploration_zone_feedback,
    look_around_feedback,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    return ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )


def _positions(feedback):
    return {position for frame in feedback.frames for position in frame.positions}


def _frame_for(feedback, position):
    return next(frame for frame in feedback.frames if position in frame.positions)


def test_default_exploration_feedback_shows_only_zone_anchors():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")

    feedback = exploration_zone_feedback(state)

    assert _positions(feedback) == {gate.marker_position}
    assert _frame_for(feedback, gate.marker_position).color == gate.color


def test_menu_feedback_shows_only_option_slots():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")
    menu = build_exploration_menu(state, gate)

    feedback = exploration_menu_feedback(menu)

    expected = {option.slot_position for option in menu.options}
    assert _positions(feedback) == expected
    assert gate.marker_position not in _positions(feedback)


def test_look_around_feedback_shows_whole_zone():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")

    feedback = look_around_feedback(gate)

    assert set(gate.positions).issubset(_positions(feedback))
