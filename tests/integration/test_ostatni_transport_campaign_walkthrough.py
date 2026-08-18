from dataclasses import replace

from dnd_board_game.combat import CombatStatus, replace_actor, scene_flag
from dnd_board_game.llm import NpcInteractionProposal, NpcOutcomeRenderProposal
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate


START_SCENARIO = "content/scenarios/ostatni_transport_00_gildia.json"


class FakeBoardConnection:
    def set_leds(self, positions, rgb_color) -> None:  # noqa: ARG002
        pass

    def leds_off(self) -> None:
        pass

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
        return None

    def reset_connection(self) -> None:
        pass


class WalkthroughNessaClient:
    model = "walkthrough-nessa"

    def interact_npc(self, request):
        return NpcInteractionProposal.model_validate(
            {
                "action_type": "contract_negotiation",
                "target_id": "fair_request",
                "argument_intent_fit": 1,
                "argument_specificity": 1,
                "argument_credibility": 0,
                "argument_leverages": [
                    {"id": "nessa_true_priority", "strength": 2}
                ],
                "declaration_class": "valid_argument",
                "requires_roll": False,
            }
        )

    def render_npc_outcome(self, request):
        return NpcOutcomeRenderProposal(
            gm_narration="Nessa waży argument i poprawia kontrakt czerwonym ołówkiem.",
            npc_response="Macie lepsze warunki, kochaniutcy. Nie każcie mi tego żałować.",
            acknowledged_mechanical_summary=request.mechanical_summary,
        )


def _complete_guild_setup(session: ExplorationUiSession) -> None:
    started = session.start_session()
    assert started["flow"]["stage"] == "party_setup"
    assert started["exploration_setup"]["paper_map"]["id"] == "guild_hall_overview"
    nessa_setup = session.confirm_exploration_setup_step()
    assert nessa_setup["flow"]["stage"] == "party_setup"
    assert nessa_setup["exploration_setup"]["current_step"]["assignment_point_id"] == (
        "nessa_desk"
    )
    assert session.select_board_position(Coordinate(8, 3))["flow"]["stage"] == (
        "location_active"
    )
    preview = session.select_board_position(Coordinate(8, 3))
    assert preview["active_point"] is None
    assert preview["flow"]["board_interaction"]["selected_action_id"] == "nessa_desk"
    session.select_point("nessa_desk")


def _resolve_checked_goal(
    session: ExplorationUiSession,
    *,
    goal_id: str,
    actor_id: str,
    declaration: str,
    social_skill: str | None = None,
) -> None:
    pending = session.submit_action(
        declaration,
        selected_goal_id=goal_id,
        selected_check_participants="single_actor",
        participant_actor_ids=(actor_id,),
        selected_social_skill=social_skill,
    )
    assert pending["pending"] is not None
    session.decide("accept")
    resolved = session.resolve_rolls(
        {actor_id: {"natural_roll": 20, "natural_roll_2": 19}}
    )
    assert resolved["pending"] is None


def _start_map1_combat(session: ExplorationUiSession) -> None:
    session.state_payload()
    assert session.pending_encounter is not None
    if session.pending_encounter.opening_resolution is None:
        session.resolve_encounter_opening()
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.start_encounter_setup()
    while (
        session.encounter_setup_flow is not None
        and not session.encounter_setup_flow.completed
    ):
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    while (
        session.encounter_initiative_flow is not None
        and not session.encounter_initiative_flow.completed
    ):
        session.submit_encounter_initiative_roll(10, 9)


def test_complete_new_game_to_first_encounter_victory_walkthrough(tmp_path) -> None:
    session = ExplorationUiSession(
        START_SCENARIO,
        npc_client=WalkthroughNessaClient(),
        save_dir=tmp_path / "saves",
        observation_dir=tmp_path / "observations",
        automatic_checkpoints=True,
    )
    client = create_app(session).test_client()

    # Launcher: only physical hero cards, then the single campaign entry.
    launcher = client.get("/new-game")
    assert launcher.status_code == 200
    html = launcher.get_data(as_text=True)
    assert 'value="ostatni_transport_00_gildia"' in html
    assert 'value="village_square_mvp"' not in html
    for actor_id in ("garran", "erynd"):
        scanned = client.post(
            "/api/new-game/card-scan",
            json={"payload": f"dndbg:v1:actor:{actor_id}"},
        )
        assert scanned.status_code == 200
    assert client.post(
        "/api/new-game/card-scan",
        json={"payload": "dndbg:v1:action:universal:accept"},
    ).get_json()["stage"] == "scenario"
    accepted = client.post(
        "/api/new-game/card-scan",
        json={
            "payload": "dndbg:v1:action:universal:accept",
            "scenario_id": "ostatni_transport_00_gildia",
        },
    )
    assert accepted.status_code == 200
    assert accepted.get_json()["redirect"] == "/play"
    assert {str(actor.id) for actor in session.exploration.actors} == {
        "garran",
        "erynd",
    }
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    # Physical Map 0 setup and the complete useful Nessa briefing.
    _complete_guild_setup(session)
    for goal_id, declaration in (
        ("ask_nessa_about_disappearance", "Pytamy o zaginięcie."),
        ("ask_nessa_about_cargo", "Pytamy o przewożony ładunek."),
        ("ask_nessa_about_people", "Pytamy, kto jechał z transportem."),
    ):
        state = session.submit_action(
            declaration,
            selected_goal_id=goal_id,
            selected_check_participants="no_actor",
        )
        assert state["pending"] is None

    _resolve_checked_goal(
        session,
        goal_id="read_nessa_priorities",
        actor_id="garran",
        declaration="Obserwuję, na czym Nessie zależy najbardziej.",
    )
    _resolve_checked_goal(
        session,
        goal_id="review_transport_documents",
        actor_id="erynd",
        declaration="Erynd porównuje trasę z ostrzeżeniami drwali.",
    )
    _resolve_checked_goal(
        session,
        goal_id="negotiate_nessa_reward",
        actor_id="erynd",
        declaration=(
            "Szary pył jest dla Gildii ważniejszy, niż przyznajesz, więc ryzyko "
            "powinno znaleźć odbicie w zapłacie."
        ),
        social_skill="persuasion",
    )
    finished = session.submit_action(
        "Jesteśmy gotowi wyruszyć.",
        selected_goal_id="finish_nessa_briefing",
        selected_check_participants="no_actor",
    )
    assert finished["pending"] is None
    assert scene_flag(session.state.flags, "black_ford_transport_quest_active") is True
    assert scene_flag(session.state.flags, "guild_departure_unlocked") is True
    assert scene_flag(session.state.flags, "knowledge.convoy_route_magic_suspected") is True
    assert scene_flag(session.state.flags, "nessa_contract_resolved") is True

    # Departure, travel and the same-session handoff to the ambush.
    session.select_point("")
    completed = session.continue_scenario(pace="normal")
    assert completed["flow"]["stage"] == "scenario_complete"
    assert completed["flow"]["scenario_handoff"]["target_scenario_id"] == (
        "ostatni_transport_01_zawalona_droga"
    )
    started_map1 = session.start_scenario_handoff()
    assert started_map1["scenario"]["id"] == "ostatni_transport_01_zawalona_droga"
    assert started_map1["pending_encounter"]["trigger_id"] == "hungry_shadows_ambush"
    assert started_map1["visible_points"] == []
    assert scene_flag(session.state.flags, "travel.pace.normal") is True

    # Encounter setup, initiative, authored scaling and victory handoff.
    _start_map1_combat(session)
    assert session.combat_state is not None
    assert session.combat_state.status == CombatStatus.ACTIVE
    assert session.encounter_checkpoint_path.is_file()
    enemies = tuple(
        actor
        for actor in session.combat_state.actors
        if actor.faction.value == "enemy"
    )
    assert {str(actor.id) for actor in enemies} == {
        "hungry_shadow_leader",
        "hungry_shadow_s2",
    }
    assert session.encounter_initiative_flow is not None
    encounter = session.encounter_initiative_flow.encounter
    assert {
        str(actor_id): sum(
            modifier.value for modifier in source.attack_roll_request.modifiers
        )
        for actor_id, source in encounter.attack_sources_by_actor.items()
        if str(actor_id).startswith("hungry_shadow")
    } == {
        "hungry_shadow_leader": 6,
        "hungry_shadow_s2": 5,
    }
    for actor in enemies:
        session.combat_state = replace_actor(
            session.combat_state,
            replace(actor, hp=0, uses_death_saves=False),
        )
    victory = session.resolve_active_combat()
    assert scene_flag(session.state.flags, "map1_encounter_cleared") is True
    assert {point["id"] for point in victory["visible_points"]} == {
        "road_aftermath"
    }
