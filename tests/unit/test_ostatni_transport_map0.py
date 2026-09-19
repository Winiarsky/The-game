from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import ActorId
from dnd_board_game.combat import (
    CombatStatus,
    SceneFlags,
    replace_actor,
    scene_flag,
    set_scene_flag,
)
from dnd_board_game.application import NpcGoalExecutionPlanner, resolve_encounter_opening
from dnd_board_game.exploration import (
    EncounterOpeningOutcome,
    ExplorationState,
    NpcOutcomeTier,
    visible_exploration_points,
)
from dnd_board_game.llm import (
    NpcInteractionProposal,
    build_npc_interaction_request,
    validate_npc_interaction_proposal,
)
from dnd_board_game.rules import RollMode
from dnd_board_game.scenarios import (
    build_encounter_from_scenario,
    build_exploration_from_scenario,
    encounter_for_party_size,
    load_scenario,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate, find_path


SCENARIO_PATH = "content/scenarios/ostatni_transport_00_gildia.json"
MAP1_SCENARIO_PATH = "content/scenarios/ostatni_transport_01_zawalona_droga.json"
MAP1_ENCOUNTER_PATH = "content/scenarios/ostatni_transport_01_glodne_cienie.json"


class FakeBoardConnection:
    def __init__(self, clicks=()) -> None:
        self.clicks = list(clicks)

    def set_leds(self, positions, rgb_color) -> None:  # noqa: ARG002
        pass

    def leds_off(self) -> None:
        pass

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
        return self.clicks.pop(0) if self.clicks else None

    def reset_connection(self) -> None:
        pass


def _exploration():
    return build_exploration_from_scenario(load_scenario(SCENARIO_PATH))


def _resolve_map1_opening(session: ExplorationUiSession) -> None:
    session.state_payload()
    if (
        session.pending_encounter is not None
        and session.pending_encounter.opening_resolution is None
    ):
        session.resolve_encounter_opening()


def test_map0_loads_with_seven_heroes_nessa_and_departure_gate() -> None:
    exploration = _exploration()
    nessa = exploration.points[0].npc_interaction

    assert {str(actor.id) for actor in exploration.actors} == {
        "brakka", "lorian", "dagna", "garran", "mira", "erynd", "nimra"
    }
    assert {actor.level for actor in exploration.actors} == {3}
    assert nessa is not None
    assert len(nessa.goals) == 7
    assert exploration.continuation is not None
    assert exploration.continuation.available_if_flags == ("guild_departure_unlocked",)
    assert exploration.continuation.travel_minutes == 60
    assert exploration.continuation.travel_policy.navigation_dc is None
    assert exploration.continuation.travel_policy.pace_details == ()
    review = next(goal for goal in nessa.goals if goal.id == "review_transport_documents")
    assert review.required_party_actor_id == "erynd"
    assert review.assigned_actor_id == "erynd"

    without_erynd = tuple(
        actor for actor in exploration.actors if str(actor.id) != "erynd"
    )
    visible_without_erynd = NpcGoalExecutionPlanner().available_goals(
        npc=nessa,
        flows=exploration.flows,
        flags=SceneFlags(),
        actors=without_erynd,
    )
    assert "review_transport_documents" not in {
        goal.id for goal in visible_without_erynd
    }
    assert "finish_nessa_briefing" in {
        goal.id for goal in visible_without_erynd
    }


def test_map0_assigned_erynd_goal_exposes_only_erynd_as_eligible_actor() -> None:
    session = ExplorationUiSession(SCENARIO_PATH, debug_point_id="nessa_desk")

    goals = {
        goal["id"]: goal
        for goal in session.state_payload()["active_point"]["npc"]["goals"]
    }

    assert goals["review_transport_documents"]["assigned_actor_id"] == "erynd"
    assert goals["review_transport_documents"]["eligible_actor_ids"] == ["erynd"]
    assert goals["negotiate_nessa_reward"]["social_skill_options"] == [
        "persuasion",
        "deception",
        "intimidation",
    ]


def test_map0_opens_spread_hotspots_without_placing_nessa() -> None:
    session = ExplorationUiSession(SCENARIO_PATH)
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    started = session.start_session()
    assert started["exploration_setup"]["current_step"]["label"] == (
        "papierowa mapa: Siedziba Gildii"
    )

    placed = session.confirm_exploration_setup_step()
    assert placed["exploration_setup"] is None
    assert placed["flow"]["stage"] == "location_active"
    nessa = next(
        point for point in placed["current_zone_points"] if point["id"] == "nessa_desk"
    )
    assert nessa["positions"] == [[5, 21]]
    assert nessa["image"] == "assets/nessa_portrait.png"

    pads = placed["flow"]["board_interaction"]["pads"]
    hotspot_positions = {
        pad["target_id"]: pad["position"]
        for pad in pads
        if pad["action_kind"] in {"point", "zone_option"}
    }
    assert hotspot_positions == {
        "nessa_desk": [5, 21],
        "guild_archive_placeholder": [16, 7],
        "guild_quartermaster_placeholder": [5, 7],
        "guild_training_placeholder": [15, 21],
    }

    preview = session.select_board_position(Coordinate(5, 21))
    assert preview["active_point"] is None
    assert preview["flow"]["board_interaction"]["selected_action_kind"] == "point"
    assert preview["flow"]["board_interaction"]["selected_action_id"] == "nessa_desk"

    switched = session.select_board_position(Coordinate(16, 7))
    assert switched["active_point"] is None
    assert switched["flow"]["board_interaction"]["selected_action_id"] == (
        "guild_archive_placeholder"
    )
    preview = session.select_board_position(Coordinate(5, 21))
    assert preview["active_point"] is None

    accepted = session.select_board_position(Coordinate(5, 21))
    assert accepted["active_point"]["id"] == "nessa_desk"
    assert accepted["active_point"]["image"] == "assets/nessa_portrait.png"
    assert accepted["flow"]["board_interaction"]["anchor_position"] == [5, 21]
    assert [
        pad["position"] for pad in accepted["flow"]["board_interaction"]["pads"]
    ] == [
        [4, 20], [5, 20], [6, 20], [6, 21],
        [6, 22], [5, 22], [4, 22], [4, 21],
    ]
    nessa_target = session._current_board_scan_target()
    assert nessa_target.positions == ()
    assert nessa_target.feedback.frames == ()
    assert "pozostaje wygaszona" in nessa_target.empty_message

    session.select_point("")
    archive_preview = session.select_board_position(Coordinate(16, 7))
    assert archive_preview["flow"]["board_interaction"]["selected_action_id"] == (
        "guild_archive_placeholder"
    )
    archive_result = session.select_board_position(Coordinate(16, 7))
    assert archive_result["flow"]["board_interaction"]["selected_action_id"] is None
    assert any(
        message["title"] == "Archiwum konsekwencji"
        for message in archive_result["messages"]
    )


def test_map0_hotspot_preview_rearms_scan_and_second_board_click_enters() -> None:
    session = ExplorationUiSession(SCENARIO_PATH)
    board = FakeBoardConnection(clicks=((5, 21), (5, 21)))
    session.attach_board_connection(board, backend="simulator")
    session.start_session()
    session.confirm_exploration_setup_step()

    initial_revision = session.state_payload()["board_selection"]["revision"]
    preview = session.scan_board_selection(
        expected_revision=initial_revision,
        automatic=True,
    )

    assert preview["active_point"] is None
    assert preview["board_selection"]["auto_arm"] is True
    assert preview["board_selection"]["confirmation_policy"] == "immediate"
    assert preview["board_selection"]["revision"] != initial_revision

    entered = session.scan_board_selection(
        expected_revision=preview["board_selection"]["revision"],
        automatic=True,
    )

    assert entered["active_point"]["id"] == "nessa_desk"
    assert board.clicks == []


def test_map0_message_hotspot_rearms_scan_and_resolves_on_second_click() -> None:
    session = ExplorationUiSession(SCENARIO_PATH)
    board = FakeBoardConnection(clicks=((16, 7), (16, 7)))
    session.attach_board_connection(board, backend="simulator")
    session.start_session()
    session.confirm_exploration_setup_step()

    preview = session.scan_board_selection(automatic=True)
    assert preview["board_selection"]["auto_arm"] is True
    assert preview["flow"]["board_interaction"]["selected_action_id"] == (
        "guild_archive_placeholder"
    )

    resolved = session.scan_board_selection(
        expected_revision=preview["board_selection"]["revision"],
        automatic=True,
    )
    assert any(
        message["title"] == "Archiwum konsekwencji"
        for message in resolved["messages"]
    )
    assert resolved["flow"]["board_interaction"]["selected_action_id"] is None


def test_map1_direct_start_also_keeps_every_hero_at_level_three() -> None:
    exploration = build_exploration_from_scenario(load_scenario(MAP1_SCENARIO_PATH))

    assert len(exploration.actors) == 7
    assert {actor.level for actor in exploration.actors} == {3}


def test_map1_starts_with_an_immediate_encounter_and_hidden_exploration() -> None:
    exploration = build_exploration_from_scenario(load_scenario(MAP1_SCENARIO_PATH))
    trigger = exploration.encounter_triggers[0]

    assert trigger.condition.value == "always"
    assert trigger.defeat_policy.value == "game_over"
    assert visible_exploration_points(exploration.points) == ()

    session = ExplorationUiSession(MAP1_SCENARIO_PATH)
    payload = session.state_payload()

    assert payload["pending_encounter"]["trigger_id"] == "hungry_shadows_ambush"
    assert payload["visible_points"] == []


def test_map1_first_encounter_setup_includes_figures_and_tactical_terrain() -> None:
    session = ExplorationUiSession(MAP1_SCENARIO_PATH)
    session.configure_custom_party((session.exploration.actors[0],))
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    _resolve_map1_opening(session)

    session.start_encounter_setup()

    assert session.encounter_setup_flow is not None
    assert [step.label for step in session.encounter_setup_flow.steps] == [
        "Start walki", "Wrak i skarpa", "Osłony kierunkowe", "Błoto i strumień",
        "pola startowe bohaterów", "jawnych przeciwników i NPC", "Cel i zasady starcia",
    ]
    payload = session.encounter_setup_flow.as_payload()
    assert payload["map_asset_url"].endswith("glodne_cienie_battlemap_v6.svg")
    steps = {step.label: step for step in session.encounter_setup_flow.steps}
    assert len(steps["pola startowe bohaterów"].positions) == 40
    assert any("Samo stanie" in rule for rule in steps["Osłony kierunkowe"].mechanics)
    assert tuple(payload["battle_briefing"]) == steps["Cel i zasady starcia"].mechanics
    while session.encounter_setup_flow.current_step.label != "Błoto i strumień":
        session.confirm_encounter_setup_step()
    payload = session.state_payload()
    assert payload["encounter_setup"]["current_step"]["positions"] == [[9, 17], [1, 7]]
    assert payload["encounter_setup"]["current_step"]["mechanics"]
    assert payload["board_selection"]["legal_position_count"] == 0
    assert payload["board_selection"]["auto_arm"] is False


@pytest.mark.parametrize(
    ("party_size", "enemy_ids", "hit_point_overrides"),
    (
        (1, {"hungry_shadow_solo"}, {"hungry_shadow_solo": 12}),
        (2, {"hungry_shadow_leader", "hungry_shadow_s2"}, {"hungry_shadow_leader": 24}),
        (3, {"hungry_shadow_leader", "hungry_shadow_s1", "hungry_shadow_s2"}, {}),
        (4, {"hungry_shadow_leader", "hungry_shadow_s1", "hungry_shadow_s2", "hungry_shadow_s3"}, {}),
        (5, {"hungry_shadow_leader", "hungry_shadow_s1", "hungry_shadow_s2", "hungry_shadow_s3", "hungry_shadow_s4"}, {}),
    ),
)
def test_map1_encounter_selects_authored_party_size_variant(
    party_size: int,
    enemy_ids: set[str],
    hit_point_overrides: dict[str, int],
) -> None:
    base = build_encounter_from_scenario(load_scenario(MAP1_ENCOUNTER_PATH))

    encounter = encounter_for_party_size(base, party_size)
    enemies = {
        str(actor.id): actor
        for actor in encounter.actors
        if actor.faction.value == "enemy"
    }

    assert set(enemies) == enemy_ids
    for actor_id, expected_hit_points in hit_point_overrides.items():
        assert enemies[actor_id].hp == expected_hit_points
        assert enemies[actor_id].max_hp == expected_hit_points
    assert set(encounter.attack_sources_by_actor) >= {
        actor.id for actor in enemies.values()
    }


def test_map1_heroes_choose_their_formation_inside_a_ten_by_four_zone() -> None:
    encounter = build_encounter_from_scenario(load_scenario(MAP1_ENCOUNTER_PATH))

    assert len(encounter.player_start_zones) == 1
    assert {position.as_tuple() for position in encounter.player_start_zones[0]} == {
        (col, row)
        for row in range(19, 23)
        for col in range(5, 15)
    }
    assert all(
        not encounter.board.terrain_at(position).blocks_movement
        for position in encounter.player_start_zones[0]
    )
    assert dict(encounter.enemy_ai_roles) == {
        "hungry_shadow_s1": "skirmisher",
        "hungry_shadow_s2": "flanker",
        "hungry_shadow_s3": "flanker",
        "hungry_shadow_s4": "harrier",
        "hungry_shadow_leader": "leader",
        "hungry_shadow_solo": "skirmisher",
    }


def test_map1_setup_keeps_the_whole_start_zone_available_for_each_hero() -> None:
    session = ExplorationUiSession(MAP1_SCENARIO_PATH)
    party = tuple(session.exploration.actors[:4])
    session.configure_custom_party(party)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    _resolve_map1_opening(session)

    session.start_encounter_setup()
    flow = session.encounter_setup_flow
    assert flow is not None
    while flow.current_step is not None and not flow.is_player_start_step:
        session.confirm_encounter_setup_step()

    assert flow.current_step is not None
    assert flow.current_step.label == "pola startowe bohaterów"
    assert len(flow.remaining_player_start_positions()) == 40
    first = Coordinate(14, 22)
    session.assign_encounter_player_start_position(first)

    assert len(flow.remaining_player_start_positions()) == 39
    assert Coordinate(5, 19) in flow.remaining_player_start_positions()
    assert first not in flow.remaining_player_start_positions()


def test_hungry_shadows_use_coordinated_pack_attack_statblocks() -> None:
    encounter = encounter_for_party_size(
        build_encounter_from_scenario(load_scenario(MAP1_ENCOUNTER_PATH)),
        3,
    )
    leader_sources = encounter.attack_source_options_by_actor[ActorId("hungry_shadow_leader")]
    assert {
        source.id: (sum(modifier.value for modifier in source.attack_roll_request.modifiers), source.damage_components[0].formula())
        for source in leader_sources
    } == {
        "hungry_shadow_leader_life_drain": (3, "1d4 + 2"),
        "hungry_shadow_leader_spirit_bolt": (5, "1d6 + 2"),
    }
    assert {
        str(actor_id): source.damage_components[0].formula()
        for actor_id, source in encounter.attack_sources_by_actor.items()
        if str(actor_id).startswith("hungry_shadow_s")
    } == {
        "hungry_shadow_s1": "1d4 + 2",
        "hungry_shadow_s2": "1d4 + 2",
    }


@pytest.mark.parametrize(
    ("party_size", "enemy_positions"),
    (
        (1, {(10, 17)}),
        (2, {(11, 10), (13, 17)}),
        (3, {(11, 10), (6, 17), (13, 17)}),
        (4, {(11, 10), (6, 17), (13, 17), (17, 15)}),
        (5, {(11, 10), (6, 17), (13, 17), (17, 15), (3, 14)}),
    ),
)
def test_map1_runtime_setup_lights_only_selected_enemy_variant(
    party_size: int,
    enemy_positions: set[tuple[int, int]],
) -> None:
    session = ExplorationUiSession(MAP1_SCENARIO_PATH)
    session.configure_custom_party(tuple(session.exploration.actors[:party_size]))
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    _resolve_map1_opening(session)

    session.start_encounter_setup()

    assert session.encounter_setup_flow is not None
    flow = session.encounter_setup_flow
    enemies = tuple(
        actor
        for actor in flow.encounter.actors
        if actor.faction.value == "enemy"
    )
    enemy_step = next(
        step
        for step in flow.steps
        if step.label == "jawnych przeciwników i NPC"
    )
    assert len(enemies) == party_size
    assert {
        position.as_tuple()
        for position in enemy_step.positions
    } == enemy_positions
    assert all(
        not flow.encounter.board.terrain_at(actor.position).blocks_movement
        for actor in enemies
    )


def test_map1_layout_applies_difficult_terrain_and_blocking_wagon_to_pathfinding() -> None:
    encounter = build_encounter_from_scenario(load_scenario(MAP1_ENCOUNTER_PATH))
    hero = next(actor for actor in encounter.actors if actor.faction.value == "ally")

    muddy_hero = replace(hero, position=Coordinate(9, 19))
    muddy_path = find_path(
        encounter.board,
        muddy_hero,
        (muddy_hero,),
        Coordinate(9, 17),
    )
    blocked_path = find_path(
        encounter.board,
        replace(hero, position=Coordinate(6, 13), speed_feet=200),
        (),
        Coordinate(9, 13),
    )
    route_around_wagon = find_path(
        encounter.board,
        replace(hero, position=Coordinate(6, 16), speed_feet=200),
        (),
        Coordinate(13, 10),
    )

    assert muddy_path.valid is True
    assert muddy_path.cost_feet == 20
    assert blocked_path.valid is False
    assert route_around_wagon.valid is True
    assert all(
        not encounter.board.terrain_at(position).blocks_movement
        for position in route_around_wagon.path
    )


def _start_map1_combat(session: ExplorationUiSession) -> None:
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    _resolve_map1_opening(session)
    session.start_encounter_setup()
    while (
        session.encounter_setup_flow is not None
        and not session.encounter_setup_flow.completed
    ):
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.current_step.positions[0]
            )
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    while (
        session.encounter_initiative_flow is not None
        and not session.encounter_initiative_flow.completed
    ):
        session.submit_encounter_initiative_roll(10)


def test_map1_victory_is_the_only_gate_to_aftermath_exploration(tmp_path) -> None:
    session = ExplorationUiSession(
        MAP1_SCENARIO_PATH,
        save_dir=tmp_path,
        automatic_checkpoints=True,
    )
    session.configure_custom_party((session.exploration.actors[0],))
    _start_map1_combat(session)
    assert session.combat_state is not None
    assert session.encounter_checkpoint_path.is_file()
    for actor in tuple(session.combat_state.actors):
        if actor.faction.value == "enemy":
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0, uses_death_saves=False),
            )

    resolved = session.resolve_active_combat()

    assert resolved["flow"]["stage"] == "interaction_result"
    assert {point["id"] for point in resolved["visible_points"]} == {
        "road_aftermath",
        "teren",
    }
    assert scene_flag(session.state.flags, "map1_encounter_cleared", False) is True


def test_map1_defeat_enters_game_over_without_revealing_exploration(tmp_path) -> None:
    session = ExplorationUiSession(
        MAP1_SCENARIO_PATH,
        save_dir=tmp_path,
        automatic_checkpoints=True,
    )
    session.configure_custom_party((session.exploration.actors[0],))
    _start_map1_combat(session)
    assert session.combat_state is not None
    initial_combat_state = session.combat_state
    assert session.encounter_checkpoint_path.is_file()
    for actor in tuple(session.combat_state.actors):
        if actor.faction.value == "ally":
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0, uses_death_saves=False),
            )

    resolved = session.resolve_active_combat()

    assert resolved["flow"]["stage"] == "game_over"
    assert resolved["visible_points"] == []
    assert scene_flag(session.state.flags, "map1_encounter_cleared", False) is False

    session.save_snapshot()
    restored = ExplorationUiSession(MAP1_SCENARIO_PATH, save_dir=tmp_path)
    loaded = restored.load_snapshot()

    assert loaded["flow"]["stage"] == "game_over"
    assert loaded["visible_points"] == []

    response = create_app(
        restored,
        character_dir=tmp_path / "characters",
    ).test_client().post("/api/encounter/retry", json={})
    retried = response.get_json()

    assert response.status_code == 200
    assert retried["flow"]["stage"] == "location_active"
    assert retried["combat"] is None
    assert retried["pending_encounter"]["trigger_id"] == (
        "hungry_shadows_ambush"
    )
    assert retried["visible_points"] == []
    assert retried["encounter_setup"]["is_retry"] is True

    setup_labels = []
    while (
        restored.encounter_setup_flow is not None
        and not restored.encounter_setup_flow.completed
    ):
        step = restored.encounter_setup_flow.current_step
        assert step is not None
        assert restored.encounter_setup_flow.is_player_start_step is False
        setup_labels.append(step.label)
        restored.confirm_encounter_setup_step()

    assert setup_labels == [
        "Start walki",
        "Wrak i skarpa", "Osłony kierunkowe", "Błoto i strumień",
        "bohater: Brakka",
        "przeciwnik lub NPC: Osłabiony Głodny Cień",
        "Cel i zasady starcia",
    ]
    assert restored.combat_state is not None
    assert restored.combat_state.status == CombatStatus.ACTIVE
    assert restored.combat_state.actors == initial_combat_state.actors
    assert restored.combat_state.initiative_order.current_index == (
        initial_combat_state.initiative_order.current_index
    )
    assert [
        (str(entry.actor.id), entry.roll.total)
        for entry in restored.combat_state.initiative_order.entries
    ] == [
        (str(entry.actor.id), entry.roll.total)
        for entry in initial_combat_state.initiative_order.entries
    ]


def test_nessa_briefing_has_complete_authored_information_and_optional_topics() -> None:
    exploration = _exploration()
    nessa = exploration.points[0].npc_interaction
    assert nessa is not None
    goals = {goal.id: goal for goal in nessa.goals}

    assert "odnajdziecie wozy" in nessa.dialogue_intro.casefold()
    assert "sprowadzicie ocalałych" in nessa.dialogue_intro.casefold()
    assert "ustalicie, co się wydarzyło" in nessa.dialogue_intro.casefold()
    assert goals["finish_nessa_briefing"].required_flags == ()

    disappearance = goals["ask_nessa_about_disappearance"].grounded_response
    cargo = goals["ask_nessa_about_cargo"].grounded_response
    people = goals["ask_nessa_about_people"].grounded_response
    priorities = goals["read_nessa_priorities"].grounded_response
    documents = goals["review_transport_documents"].grounded_response
    assert disappearance is not None
    assert "trzema ukośnymi nacięciami" in disappearance.npc_response
    assert "lewej stronie drogi" in disappearance.npc_response
    assert cargo is not None
    assert "cztery zabezpieczone skrzynie" in cargo.npc_response
    assert "miedzianym gwoździu" in cargo.npc_response
    assert people is not None
    assert "sześciu strażników" in people.npc_response
    assert "Alven Rost" in people.npc_response
    assert priorities is not None
    assert "wyjątkowo cenne" in priorities.success_message
    assert "Nie potraficie uczciwie wskazać" in priorities.failure_message
    assert documents is not None
    assert "prawdopodobnie działa magia" in documents.success_message
    assert "ten sam odcinek lasu" in documents.failure_message


def test_map0_generated_art_paths_are_bound_to_authored_goals() -> None:
    exploration = _exploration()
    nessa_point = exploration.points[0]
    assert nessa_point.npc_interaction is not None
    goals = {goal.id: goal for goal in nessa_point.npc_interaction.goals}

    assert exploration.zones[0].image == "assets/guild_hall_map_isometric.png"
    assert exploration.zones[0].paper_map is not None
    assert exploration.zones[0].paper_map.id == "guild_hall_overview"
    assert nessa_point.image == "assets/nessa_portrait.png"
    assert {
        option.id: option.image for option in exploration.zones[0].options
    } == {
        "guild_archive_placeholder": "assets/placeholder_archive.png",
        "guild_quartermaster_placeholder": "assets/placeholder_quartermaster.png",
        "guild_training_placeholder": "assets/placeholder_training.png",
    }
    assert {
        goal_id: goals[goal_id].image
        for goal_id in (
            "ask_nessa_about_disappearance",
            "ask_nessa_about_cargo",
            "ask_nessa_about_people",
            "read_nessa_priorities",
            "review_transport_documents",
            "negotiate_nessa_reward",
            "finish_nessa_briefing",
        )
    } == {
        "ask_nessa_about_disappearance": "assets/tile_disappearance.png",
        "ask_nessa_about_cargo": "assets/tile_cargo.png",
        "ask_nessa_about_people": "assets/tile_people_alven.png",
        "read_nessa_priorities": "assets/tile_insight.png",
        "review_transport_documents": "assets/tile_erynd_documents.png",
        "negotiate_nessa_reward": "assets/tile_negotiation.png",
        "finish_nessa_briefing": "assets/tile_departure.png",
    }


def test_map0_print_package_exists_and_uses_physical_board_dimensions() -> None:
    paper_map = _exploration().zones[0].paper_map
    assert paper_map is not None
    assert (paper_map.width_cm, paper_map.height_cm) == (50.0, 75.0)
    for relative_path in (
        paper_map.preview_path,
        paper_map.a4_pdf_path,
        paper_map.full_size_pdf_path,
    ):
        path = Path("assets") / relative_path
        assert path.is_file()
        assert path.stat().st_size > 0


def test_map0_initial_setup_matches_mvp_map_and_hotspot_flow() -> None:
    session = ExplorationUiSession(SCENARIO_PATH)
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    setup = session.start_session()
    assert setup["flow"]["stage"] == "party_setup"
    assert setup["exploration_setup"]["current_step"]["label"] == (
        "papierowa mapa: Siedziba Gildii"
    )
    assert "Usuń poprzednią papierową mapę" in (
        setup["exploration_setup"]["current_step"]["message"]
    )
    assert setup["exploration_setup"]["paper_map"]["id"] == (
        "guild_hall_overview"
    )
    assert setup["exploration_setup"]["paper_map"]["a4_pdf_url"].endswith(
        "/guild_hall_overview.pdf"
    )

    active = session.confirm_exploration_setup_step()
    assert active["exploration_setup"] is None
    assert active["flow"]["stage"] == "location_active"
    pads = active["flow"]["board_interaction"]["pads"]
    assert [pad["target_id"] for pad in pads] == [
        "nessa_desk",
        "guild_archive_placeholder",
        "guild_quartermaster_placeholder",
        "guild_training_placeholder",
        "continuation",
        "guild_hall",
    ]
    assert next(
        option
        for option in active["flow"]["zone_options"]
        if option["id"] == "guild_archive_placeholder"
    )["image"] == "assets/placeholder_archive.png"

def test_information_tiles_and_briefing_end_apply_authored_knowledge_flags() -> None:
    session = ExplorationUiSession(SCENARIO_PATH, debug_point_id="nessa_desk")

    disappearance_state = session.submit_action(
        "Pytamy o zaginięcie.",
        selected_goal_id="ask_nessa_about_disappearance",
        selected_check_participants="no_actor",
    )
    assert any(
        "trzema ukośnymi nacięciami" in message["body"]
        for message in disappearance_state["messages"]
    )
    assert scene_flag(
        session.state.flags,
        "knowledge.transport_last_contact_details",
        False,
    ) is True
    assert scene_flag(
        session.state.flags,
        "knowledge.convoy_route_marks",
        False,
    ) is True

    finish_session = ExplorationUiSession(
        SCENARIO_PATH,
        debug_point_id="nessa_desk",
    )
    finish_state = finish_session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    assert any(
        "Wracacie i mówicie mi prawdę" in message["body"]
        for message in finish_state["messages"]
    )
    assert scene_flag(
        finish_session.state.flags,
        "black_ford_transport_quest_active",
        False,
    ) is True
    assert scene_flag(
        finish_session.state.flags,
        "guild_departure_unlocked",
        False,
    ) is True


def test_nessa_argument_assessment_is_converted_to_a_bounded_roll_adjustment() -> None:
    exploration = _exploration()
    point = exploration.points[0]
    assert point.npc_interaction is not None
    zone = exploration.zones[0]
    flags = set_scene_flag(SceneFlags(), "knowledge.nessa_true_priority_known", True)
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        flags,
        resources=exploration.resources,
    )
    request = build_npc_interaction_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action="Pył jest dla ciebie ważniejszy niż przyznajesz, więc ryzyko kosztuje.",
        selected_goal_id="negotiate_nessa_reward",
        routed_intent_id="contract_negotiation",
        selected_social_skill="persuasion",
        participant_actor_ids=("lorian",),
    )
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "contract_negotiation",
            "target_id": "fair_request",
            "argument_intent_fit": 1,
            "argument_specificity": 1,
            "argument_credibility": 0,
            "argument_leverages": [{"id": "nessa_true_priority", "strength": 2}],
            "declaration_class": "valid_argument",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request)

    assert validated.proposal.requires_roll is True
    assert validated.proposal.dc == 14
    assert validated.proposal.skill == "persuasion"
    assert validated.proposal.argument_score == 4
    assert validated.proposal.argument_roll_mode == RollMode.ADVANTAGE.value


def test_unsupported_factual_claim_forces_maximum_credibility_penalty() -> None:
    exploration = _exploration()
    point = exploration.points[0]
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        resources=exploration.resources,
    )
    request = build_npc_interaction_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        zone=exploration.zones[0],
        point=point,
        state=state,
        player_action="Inna gildia już jedzie po transport.",
        selected_goal_id="negotiate_nessa_reward",
        routed_intent_id="contract_negotiation",
        selected_social_skill="deception",
        participant_actor_ids=("lorian",),
    )
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "contract_negotiation",
            "target_id": "calculated_lie",
            "argument_intent_fit": 1,
            "argument_specificity": 1,
            "argument_credibility": 0,
            "argument_unsupported_claims": [
                "Inna gildia już jedzie po transport."
            ],
            "declaration_class": "valid_argument",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request)

    assert validated.proposal.argument_score == 0
    assert validated.proposal.argument_modifier == 0


def test_guild_hotspots_match_the_isometric_map_and_gate_keeps_its_slot() -> None:
    session = ExplorationUiSession(SCENARIO_PATH, debug_point_id="nessa_desk")
    session.select_point("")

    locked_pads = session._board_interaction_pads()
    locked_gate = next(
        pad for pad in locked_pads if pad.target_id == "continuation"
    )
    assert [pad.label for pad in locked_pads[:-1]] == [
        "Rozpocznij odprawę z Nessą",
        "Archiwum konsekwencji",
        "Magazyn i kwatermistrz",
        "Pole treningowe",
        "Wyruszcie śladem transportu",
    ]
    assert [pad.position.as_tuple() for pad in locked_pads[:-1]] == [
        (5, 21), (16, 7), (5, 7), (15, 21), (10, 3)
    ]
    assert locked_gate.enabled is False
    assert locked_gate.inspectable is True

    locked_state = session._activate_board_interaction_pad(locked_gate)
    assert locked_state["flow"]["board_interaction"]["selected_panel"] == "continuation"
    assert locked_state["flow"]["continuation"]["available"] is False

    session.select_point("nessa_desk")
    session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    session.select_point("")
    unlocked_gate = next(
        pad for pad in session._board_interaction_pads()
        if pad.target_id == "continuation"
    )
    assert unlocked_gate.symbol == locked_gate.symbol
    assert unlocked_gate.position == locked_gate.position
    assert unlocked_gate.color == locked_gate.color
    assert unlocked_gate.enabled is True


def test_departure_opens_screen_confirmation_without_pace_board_tiles() -> None:
    session = ExplorationUiSession(SCENARIO_PATH, debug_point_id="nessa_desk")
    session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    session.select_point("")
    root_pads = session._board_interaction_pads()
    departure = next(pad for pad in root_pads if pad.target_id == "continuation")
    session._activate_board_interaction_pad(departure)
    pace_pads = tuple(
        pad
        for pad in session._board_interaction_pads()
        if pad.action_kind == "continuation_pace"
    )
    assert pace_pads == ()
    selected = session.state_payload()
    interaction = selected["flow"]["board_interaction"]
    assert interaction["selected_panel"] == "continuation"
    assert interaction["selected_action_kind"] is None
    assert interaction["selected_action_id"] is None
    assert selected["board_selection"]["auto_arm"] is False


def test_departure_summary_contains_only_information_the_party_learned() -> None:
    session = ExplorationUiSession(SCENARIO_PATH, debug_point_id="nessa_desk")
    session.submit_action(
        "Pytamy o zaginięcie.",
        selected_goal_id="ask_nessa_about_disappearance",
        selected_check_participants="no_actor",
    )
    session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )

    summary = session.state_payload()["flow"]["continuation"]["departure_summary"]
    known = [item["label"] for item in summary if item["known"]]
    unknown = [item["label"] for item in summary if not item["known"]]
    assert any("Cel: odnaleźć transport" in label for label in known)
    assert any("Kamienny Słup" in label for label in known)
    assert any("trzema ukośnymi nacięciami" in label for label in known)
    assert any("miedzianym gwoździem" in label for label in unknown)


def test_contract_defines_level_three_scale_base_pay_and_preparation_resources() -> None:
    exploration = _exploration()
    nessa = exploration.points[0].npc_interaction
    assert nessa is not None
    permission = nessa.policy.intent_permission("contract_negotiation")
    assert permission is not None
    hard = permission.target("hard_terms")
    request = permission.target("fair_request")
    lie = permission.target("calculated_lie")
    assert hard is not None and request is not None and lie is not None
    assert hard.branch(NpcOutcomeTier.SUCCESS).message.startswith("Kontrakt: 5 gp")
    assert hard.branch(NpcOutcomeTier.CRITICAL_SUCCESS).currency_reward_cp_per_actor == 300
    assert request.branch(NpcOutcomeTier.SUCCESS).message.startswith("Kontrakt: 5 gp do wspólnej puli")
    assert any(
        effect.get("parameters", {}).get("resource_id") == "guild_medical_pack"
        for effect in request.branch(NpcOutcomeTier.CRITICAL_SUCCESS).effects
    )
    assert lie.branch(NpcOutcomeTier.SUCCESS).currency_reward_cp_per_actor == 300
    assert lie.branch(NpcOutcomeTier.CRITICAL_SUCCESS).currency_reward_cp_per_actor == 500
    assert {resource.id for resource in exploration.resources} == {
        "guild_medical_pack", "guild_supply_pack"
    }


def test_map0_full_quest_acceptance_and_gate_handoff_reaches_map1(tmp_path) -> None:
    session = ExplorationUiSession(
        SCENARIO_PATH,
        debug_point_id="nessa_desk",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.submit_action(
        "Pytamy o zaginięcie.",
        selected_goal_id="ask_nessa_about_disappearance",
        selected_check_participants="no_actor",
    )
    session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    session.select_point("")

    completed = session.continue_scenario()
    handoff = completed["flow"]["scenario_handoff"]
    assert completed["flow"]["stage"] == "scenario_complete"
    assert handoff["target_scenario_id"] == "ostatni_transport_01_zawalona_droga"
    propagated = {
        effect["parameters"]["key"]: effect["parameters"]["value"]
        for effect in handoff["outcome"]["target_effects"]
    }
    assert propagated["black_ford_transport_quest_active"] is True
    assert propagated["knowledge.convoy_route_marks"] is True
    assert propagated["contract.base_reward_gp_per_hero"] == 10

    started = session.start_scenario_handoff()
    assert started["scenario"]["id"] == "ostatni_transport_01_zawalona_droga"
    assert scene_flag(
        session.state.flags,
        "contract.base_reward_gp_per_hero",
    ) == 10
    assert scene_flag(session.state.flags, "travel.pace.normal") is None
    assert handoff["travel"] == {
        "mode": "fixed",
        "base_minutes": 60,
        "total_minutes": 60,
        "navigation": {"required": False, "success": True},
    }


def test_map0_legacy_travel_inputs_do_not_change_fixed_transition(tmp_path) -> None:
    session = ExplorationUiSession(
        SCENARIO_PATH,
        debug_point_id="nessa_desk",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    session.select_point("")

    completed = session.continue_scenario(
        pace="fast",
        navigator_actor_id="brakka",
        navigation_roll=1,
    )
    travel = completed["flow"]["scenario_handoff"]["travel"]

    assert travel["mode"] == "fixed"
    assert travel["total_minutes"] == 60
    assert travel["navigation"] == {"required": False, "success": True}

    from dnd_board_game.inventory import InventoryItem, LootBundle
    shared = LootBundle('party_loot', 'Wspólny zapas', (InventoryItem('found_ring', 'Nieznany pierścień', 'gear', equipped=False),))
    session.state = replace(session.state, party_loot=shared)
    session.start_scenario_handoff()
    assert session.state.party_loot == shared
    assert scene_flag(session.state.flags, "travel.pace.fast") is None
    assert scene_flag(session.state.flags, "travel.arrival.late") is None


def test_map1_opening_rewards_erynd_warning_without_travel_pace() -> None:
    exploration = build_exploration_from_scenario(load_scenario(MAP1_SCENARIO_PATH))
    trigger = exploration.encounter_triggers[0]
    assert trigger.opening_policy is not None
    flags = set_scene_flag(
        SceneFlags(), "knowledge.convoy_route_magic_suspected", True
    )
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        flags=flags,
    )

    result = resolve_encounter_opening(state, trigger.opening_policy)

    assert result.rule_id == "erynd_warned_party"
    assert result.outcome == EncounterOpeningOutcome.PARTY_INITIATIVE_ADVANTAGE


def test_map1_unwarned_approach_uses_default_opening() -> None:
    exploration = build_exploration_from_scenario(load_scenario(MAP1_SCENARIO_PATH))
    policy = exploration.encounter_triggers[0].opening_policy
    assert policy is not None
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        flags=SceneFlags(),
    )

    result = resolve_encounter_opening(state, policy)

    assert result.outcome == EncounterOpeningOutcome.NO_SURPRISE


def test_map1_battle_briefing_survives_loading_combat_checkpoint(tmp_path) -> None:
    session = ExplorationUiSession(MAP1_SCENARIO_PATH, save_dir=tmp_path)
    session.configure_custom_party((session.exploration.actors[0],))
    _start_map1_combat(session)
    expected = session.state_payload()["combat"]["battle_briefing"]
    session.save_snapshot()
    restored = ExplorationUiSession(MAP1_SCENARIO_PATH, save_dir=tmp_path)
    payload = restored.load_snapshot()
    assert restored.encounter_setup_flow is None
    assert payload["combat"]["battle_briefing"] == expected
    assert expected
