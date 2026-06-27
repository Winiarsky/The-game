import pytest

from dnd_board_game.exploration import (
    available_exploration_zones,
    ExplorationState,
    SceneMode,
    SearchResult,
    resolve_zone_search,
    set_party_zone,
    visible_exploration_points,
    visible_exploration_zones,
    zone_for_position,
)
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario
from dnd_board_game.exploration import PartyCheckInput
from dnd_board_game.world import Coordinate


def _exploration():
    return build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))


def test_loader_loads_exploration_mode_zones_and_party_start():
    loaded = load_scenario("content/scenarios/abandoned_watchtower.json")
    exploration = build_exploration_from_scenario(loaded)

    assert loaded.definition.scene_mode == SceneMode.EXPLORATION
    assert exploration.party_position.zone_id == "gate"
    assert {zone.id for zone in exploration.zones} == {"gate", "courtyard", "barracks", "tower"}
    assert zone_for_position(exploration.zones, Coordinate(4, 5)).id == "courtyard"


def test_visible_setup_excludes_hidden_points():
    exploration = _exploration()

    assert {zone.id for zone in visible_exploration_zones(exploration.zones)} == {"gate", "courtyard", "barracks", "tower"}
    assert visible_exploration_points(exploration.points) == ()


def test_only_gate_is_available_before_gate_is_passed():
    exploration = _exploration()
    state = ExplorationState(exploration.zones, exploration.points, exploration.party_position)

    assert [zone.id for zone in available_exploration_zones(state)] == ["gate"]


def test_party_position_updates_after_zone_travel():
    exploration = _exploration()
    state = ExplorationState(exploration.zones, exploration.points, exploration.party_position)
    courtyard = next(zone for zone in exploration.zones if zone.id == "courtyard")

    updated = set_party_zone(state, courtyard)

    assert updated.party_position.zone_id == "courtyard"
    assert updated.party_position.marker_position == courtyard.marker_position


def test_zone_search_reveals_hidden_point_and_blocks_second_attempt():
    exploration = _exploration()
    state = ExplorationState(exploration.zones, exploration.points, exploration.party_position)
    courtyard = next(zone for zone in exploration.zones if zone.id == "courtyard")
    inputs = tuple(PartyCheckInput(actor, 15, D20RollRequest()) for actor in exploration.actors)

    result = resolve_zone_search(state, courtyard, inputs)

    assert isinstance(result, SearchResult)
    assert result.party_check.success is True
    assert [point.id for point in result.revealed_points] == ["hidden_cache"]
    assert "courtyard" in result.state.exhausted_search_zones
    with pytest.raises(ValueError, match="already been searched"):
        resolve_zone_search(result.state, courtyard, inputs)
