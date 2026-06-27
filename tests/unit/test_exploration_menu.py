from dnd_board_game.exploration import (
    ExplorationMenuOptionKind,
    ExplorationState,
    PartyCheckInput,
    build_exploration_menu,
    menu_option_for_position,
    resolve_zone_search,
)
from dnd_board_game.rules import D20RollRequest
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


def test_menu_contains_all_gate_options_and_cancel():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")

    menu = build_exploration_menu(state, gate)

    option_ids = {option.id for option in menu.options}
    assert {"force_gate", "vault_gate", "lever_gate", "find_way_around", "break_picket"} <= option_ids
    assert "inspect_gate_area" in option_ids
    assert "look_around" in option_ids
    assert "cancel" in option_ids


def test_menu_assigns_unique_positions_inside_zone():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")

    menu = build_exploration_menu(state, gate)

    positions = [option.slot_position for option in menu.options]
    assert len(positions) == len(set(positions))
    assert set(positions).issubset(set(gate.positions))
    assert gate.marker_position not in positions


def test_menu_assigns_unique_colors_for_visible_options():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")

    menu = build_exploration_menu(state, gate)

    colors = [option.color for option in menu.options]
    assert len(colors) == len(set(colors))


def test_completed_search_option_is_removed_from_menu():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")
    actors = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json")).actors
    searched = resolve_zone_search(
        state,
        gate,
        tuple(PartyCheckInput(actor, 15, D20RollRequest()) for actor in actors),
    ).state

    menu = build_exploration_menu(searched, gate)

    assert "inspect_gate_area" not in {option.id for option in menu.options}


def test_option_color_stays_stable_after_other_option_is_removed():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")
    actors = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json")).actors
    before = build_exploration_menu(state, gate)
    before_look_around = next(option for option in before.options if option.id == "look_around")
    searched = resolve_zone_search(
        state,
        gate,
        tuple(PartyCheckInput(actor, 15, D20RollRequest()) for actor in actors),
    ).state

    after = build_exploration_menu(searched, gate)
    after_look_around = next(option for option in after.options if option.id == "look_around")

    assert after_look_around.color == before_look_around.color


def test_menu_option_for_position_returns_selected_option():
    state = _state()
    gate = next(zone for zone in state.zones if zone.id == "gate")
    menu = build_exploration_menu(state, gate)
    selected = next(option for option in menu.options if option.kind == ExplorationMenuOptionKind.LOOK_AROUND)

    assert menu_option_for_position(menu, selected.slot_position) == selected
