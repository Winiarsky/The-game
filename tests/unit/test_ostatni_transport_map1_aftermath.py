from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import scene_flag, set_scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    PartyPosition,
    apply_exploration_effect,
    available_exploration_zones,
)
from dnd_board_game.scenarios import (
    build_exploration_from_scenario,
    load_scenario,
    preflight_scenario,
)
from dnd_board_game.llm import NpcInteractionProposal
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage


MAP1_PATH = "content/scenarios/ostatni_transport_01_zawalona_droga.json"
MAP2_PATH = "content/scenarios/ostatni_transport_02_czarny_brod.json"


class TerenNpcClient:
    model = "teren-test"

    def interact_npc(self, request):
        action_by_goal = {
            "aid_teren": "aid",
            "question_teren": "question",
            "take_teren": "take_along",
            "shelter_teren": "leave_sheltered",
        }
        return NpcInteractionProposal(
            action_type=action_by_goal[str(request.selected_goal_id)]
        )


def _put_after_combat(
    session: ExplorationUiSession,
    zone_id: str,
    *flags_to_set: str,
) -> None:
    flags = session.state.flags
    for flag in ("map1_encounter_cleared", *flags_to_set):
        flags = set_scene_flag(flags, flag, True)
    session.state = replace(
        session.state,
        flags=flags,
        party_position=PartyPosition(zone_id),
        encounter_edges=tuple(
            replace(edge, consumed=True) for edge in session.state.encounter_edges
        ),
    )
    session.pending_encounter = None
    session.resolved_encounter_trigger_ids.add("hungry_shadows_ambush")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE


def test_map1_aftermath_uses_same_map_and_unlocks_all_postcombat_hotspots() -> None:
    loaded = load_scenario(MAP1_PATH)
    exploration = build_exploration_from_scenario(loaded)

    assert preflight_scenario(loaded, game_asset_root=Path("assets")) == ()
    assert loaded.definition.encounter_map_asset == (
        "maps/ostatni_transport_01/glodne_cienie_battlemap_base_v5.png"
    )
    initial_state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
    )
    assert {zone.id for zone in available_exploration_zones(initial_state)} == {
        "blocked_road"
    }

    cleared_state = replace(
        initial_state,
        flags=set_scene_flag(
            initial_state.flags,
            "map1_encounter_cleared",
            True,
        ),
    )
    assert {zone.id for zone in available_exploration_zones(cleared_state)} == {
        "blocked_road",
        "overturned_wagon",
        "western_culvert",
        "stream_tracks",
        "teren_shelter",
        "signal_tower",
        "black_ford_route",
    }
    teren = next(point for point in exploration.points if point.id == "teren")
    assert teren.npc_interaction is not None
    assert {goal.id for goal in teren.npc_interaction.goals} == {
        "aid_teren",
        "question_teren",
        "take_teren",
        "shelter_teren",
    }


def test_failed_wagon_search_is_fail_forward_and_sets_all_authored_flags() -> None:
    session = ExplorationUiSession(MAP1_PATH)
    _put_after_combat(session, "overturned_wagon")

    pending = session.select_exploration_option(
        "search_convoy_wagon",
        actor_id="brakka",
    )
    assert pending["pending"] is not None
    resolved = session.resolve_rolls({"brakka": 1})

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "map1_wagon_examined") is True
    assert scene_flag(session.state.flags, "knowledge.wagon_violent_looting") is True


def test_route_choice_sets_common_and_specific_flags_and_closes_other_choice() -> None:
    session = ExplorationUiSession(MAP1_PATH)
    _put_after_combat(session, "black_ford_route")

    selected = session.select_exploration_option("choose_forest_route")

    assert scene_flag(session.state.flags, "map1_route_selected") is True
    assert scene_flag(session.state.flags, "map1_route_forest") is True
    options = {option["id"]: option for option in selected["flow"]["zone_options"]}
    assert options["choose_main_route"]["completed"] is True
    assert options["choose_forest_route"]["completed"] is True
    with pytest.raises(ValueError, match="już rozstrzygnięte"):
        session.select_exploration_option("choose_main_route")


def test_teren_aid_question_and_fate_form_a_complete_guarded_sequence() -> None:
    session = ExplorationUiSession(MAP1_PATH, npc_client=TerenNpcClient())
    _put_after_combat(session, "teren_shelter")
    session.state = apply_exploration_effect(
        session.state,
        {"type": "reveal_point", "parameters": {"point_id": "teren"}},
    ).state
    session.select_point("teren")

    aid = session.submit_action(
        "Opatrujemy ranę i dajemy Terenowi wodę.",
        selected_goal_id="aid_teren",
        selected_check_participants="single_actor",
        participant_actor_ids=("dagna",),
    )
    assert aid["pending"] is not None
    session.decide("accept")
    session.resolve_rolls({"dagna": 15})
    assert scene_flag(session.state.flags, "teren_aid_resolved") is True

    questioned = session.submit_action(
        "Prosimy o pełną relację z ataku.",
        selected_goal_id="question_teren",
        selected_check_participants="single_actor",
        participant_actor_ids=("dagna",),
    )
    assert questioned["pending"] is not None
    session.decide("accept")
    session.resolve_rolls({"dagna": 15})
    assert scene_flag(session.state.flags, "map1_teren_questioned") is True
    assert scene_flag(session.state.flags, "knowledge.teren_truth") is True

    session.submit_action(
        "Teren idzie z nami.",
        selected_goal_id="take_teren",
        selected_check_participants="no_actor",
    )
    assert scene_flag(session.state.flags, "map1_teren_fate_decided") is True
    assert scene_flag(session.state.flags, "teren.traveling_with_party") is True


def test_completed_aftermath_handoff_reaches_black_ford_entry_shell(tmp_path) -> None:
    session = ExplorationUiSession(MAP1_PATH, save_dir=tmp_path)
    _put_after_combat(
        session,
        "black_ford_route",
        "map1_wagon_examined",
        "map1_route_clue_found",
        "map1_teren_fate_decided",
        "map1_young_beast_decided",
        "map1_route_selected",
        "map1_route_main",
    )

    completed = session.continue_scenario()
    assert completed["flow"]["scenario_handoff"]["target_scenario_id"] == (
        "ostatni_transport_02_czarny_brod"
    )
    started = session.start_scenario_handoff()

    assert started["scenario"]["id"] == "ostatni_transport_02_czarny_brod"
    assert scene_flag(session.state.flags, "arrival.route.main") is True
    target = build_exploration_from_scenario(load_scenario(MAP2_PATH))
    assert target.party_position.zone_id == "black_ford_approach"
