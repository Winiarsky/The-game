from dataclasses import replace

from dnd_board_game.actors import Faction
from dnd_board_game.combat import replace_actor, set_scene_flag
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage, create_app


class FakeGmClient:
    model = "fake-gm"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def analyze(self, request):
        return GmDeclarationAnalysis(
            analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
            player_message="",
            normalized_intent=request.player_action,
            reason="test",
            confidence=1.0,
        )

    def classify(self, request):
        self.requests.append(request)
        return self.proposal


class FakeNpcClient:
    model = "fake-npc"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def interact_npc(self, request):
        self.requests.append(request)
        return self.proposal


class FakeBoardConnection:
    def __init__(self, clicks=None):
        self.led_calls = []
        self.clicks = list(clicks or [])
        self.reset_calls = []

    def set_leds(self, positions, rgb_color):
        self.led_calls.append((positions, rgb_color))

    def leds_off(self):
        self.led_calls.append(("off", None))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
        if not self.clicks:
            return None
        click = self.clicks.pop(0)
        if acceptable_responses and click not in acceptable_responses:
            return None
        return click

    def reset_connection(self):
        self.reset_calls.append("reset_connection")


def _challenge_proposal(**overrides):
    data = {
        "intent_type": "challenge_attempt",
        "target_challenge_id": "closed_gate",
        "approach_label": "Wyważenie bramy",
        "approach_tags": ["heavy_force", "noise"],
        "ability": "strength",
        "skill": "athletics",
        "difficulty_tier": "medium",
        "difficulty_reason": "Stara brama może ustąpić pod mocnym naporem.",
        "dc": 15,
        "progress_on_success": 3,
        "progress_on_failure": 1,
        "used_resource_ids": [],
        "check_participants": "single_actor",
        "check_aggregation": "lead_result",
        "consequence_targets": ["lead_actor", "scene"],
        "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
        "player_narration": "Napieracie na skrzydła bramy.",
    }
    data.update(overrides)
    return GmClassifierProposal.model_validate(data)


def _start_combat_from_scout_alarm(session: ExplorationUiSession):
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))
    session.state_payload()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            for position in session.encounter_setup_flow.current_step.positions[:2]:
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    session.submit_encounter_initiative_roll(19)
    assert session.combat_state is not None
    return session.combat_state


def test_exploration_ui_session_resolves_gate_challenge():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Wyważamy bramę.")
    assert state["pending"]["stage"] == "decision"
    assert state["active_challenge"]["current_progress"] == 0

    state = session.decide("accept")
    assert state["pending"]["stage"] == "roll"
    assert state["required_rolls"] == [{"actor_id": "hero", "actor_name": "Bohater"}]

    state = session.resolve_rolls({"hero": 16})

    assert state["pending"] is None
    assert state["active_challenge"] is None
    assert state["flow"]["stage"] == "interaction_result"
    assert state["exploration_setup"] is None
    assert state["pending_encounter"] is None

    state = session.finish_interaction_result()

    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["label"] == "przewrócona brama"
    assert state["exploration_setup"]["current_step"]["positions"] == [[8, 5], [9, 5]]

    state = session.confirm_exploration_setup_step()

    assert state["travel_options"][0]["id"] == "courtyard"
    assert state["pending_encounter"]["trigger_id"] == "gate_open_skirmish"
    assert any(message["title"] == "Nowy punkt odkryty" for message in state["messages"])


def test_exploration_ui_session_pending_encounter_waits_for_ui_setup_not_board_click():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    session.submit_action("Wyważamy bramę.")
    session.decide("accept")
    session.resolve_rolls({"hero": 16})
    session.finish_interaction_result()
    state = session.confirm_exploration_setup_step()

    assert state["pending_encounter"]["trigger_id"] == "gate_open_skirmish"
    assert state["board"]["message"] == "Encounter gotowy. Potwierdź rozpoczęcie setupu w UI albo Enterem."
    assert board.led_calls[-1] == ("off", None)

    client = create_app(session).test_client()
    response = client.post("/api/board/scan", json={})

    assert response.status_code == 400
    assert "Encounter czeka na rozpoczęcie setupu" in response.get_json()["error"]


def test_exploration_ui_session_starts_with_map_setup_before_location_preview():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    state = session.start_session()

    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["label"] == "elementy mapy"
    assert state["exploration_setup"]["current_step"]["has_positions"] is False
    assert state["exploration_setup"]["current_step"]["color"] is None

    while session.exploration_setup_flow is not None:
        state = session.confirm_exploration_setup_step()

    assert state["flow"]["stage"] == "location_preview"
    assert state["exploration_setup"] is None


def test_exploration_ui_session_rejects_pending_interpretation():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    session.submit_action("Wyważamy bramę.")
    state = session.decide("reject")

    assert state["pending"] is None
    assert any("Odrzucono interpretację" in message["body"] for message in state["messages"])


def test_exploration_ui_session_debug_npc_sets_flags_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Mówicie spokojnie i trzymacie ręce widocznie.",
            "npc_response": "Zwiadowca oddycha wolniej.",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
            ],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    state = session.submit_action("Uspokajamy zwiadowcę.")
    assert state["pending"]["kind"] == "npc"

    state = session.decide("accept")

    assert state["pending"] is None
    assert {"key": "scout_calmed", "value": True} in state["flags"]


def test_exploration_ui_session_npc_information_sets_flags_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "player_narration": "Opatrujecie ranę zwiadowcy.",
            "npc_response": "Zwiadowca odzyskuje oddech i wskazuje ślady.",
            "requires_roll": False,
            "flag_changes_on_success": [{"key": "scout_stabilized", "value": True}],
            "revealed_information_ids": ["tower_hint"],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    session.submit_action("Opatrujemy zwiadowcę.")
    state = session.decide("accept")

    assert {"key": "scout_stabilized", "value": True} in state["flags"]
    assert {"key": "tower_hint_learned", "value": True} in state["flags"]
    assert any(message["title"] == "Informacja: Wskazówka o wieży" for message in state["messages"])


def test_exploration_ui_session_writes_debug_log_for_npc_effects(tmp_path):
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Mówicie spokojnie.",
            "npc_response": "Zwiadowca przestaje się szarpać.",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
            ],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
        session_id="ui_log_test",
        observation_dir=tmp_path,
    )

    session.submit_action("Uspokajamy zwiadowcę.")
    session.decide("accept")

    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    event_types = [event["event_type"] for event in events]
    effect_event = next(event for event in events if event["event_type"] == "ui_effect_applied")

    assert event_types[:1] == ["ui_session_started"]
    assert "ui_action_submitted" in event_types
    assert "ui_npc_proposal_validated" in event_types
    assert effect_event["payload"]["source"] == "npc_proposal"
    assert effect_event["payload"]["effect"]["parameters"]["key"] == "scout_calmed"
    assert {"key": "scout_calmed", "value": True} in effect_event["payload"]["flags"]

    client = create_app(session).test_client()
    payload = client.get("/api/session-log").get_json()
    assert payload["session_id"] == "ui_log_test"
    assert payload["path"] == str(session.observer.path)
    assert any(event["event_type"] == "ui_effect_applied" for event in payload["events"])


def test_exploration_ui_session_applies_victory_outcome_after_combat():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))

    state = session.state_payload()
    assert state["pending_encounter"]["trigger_id"] == "scout_panic_alarm"

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            for position in session.encounter_setup_flow.current_step.positions[:2]:
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(15)
    session.submit_encounter_initiative_roll(14)

    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, hp=0))

    state = session.resolve_active_combat()

    assert state["combat"] is None
    assert state["pending_encounter"] is None
    assert state["flow"]["stage"] == "interaction_result"
    assert {"key": "courtyard_cleared", "value": True} in state["flags"]
    assert any(point["id"] == "wounded_scout" for point in state["flow"]["interaction_result"]["revealed_points"])
    assert any(point["id"] == "wounded_scout" for point in state["visible_points"])

    state = session.finish_interaction_result()
    assert state["pending_encounter"] is None


def test_exploration_ui_session_player_attack_applies_damage_and_uses_action():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    state = session.state_payload()
    assert state["combat"]["current_actor"]["faction"] == "ally"
    assert state["combat"]["legal_targets"]
    target_id = state["combat"]["legal_targets"][0]["id"]

    state = session.submit_player_attack(target_id=target_id, natural_roll=20, damage=5)

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target_id)
    assert damaged["hp"] < 7
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Atak" and "trafia krytycznie" in message["body"] for message in state["messages"])


def test_exploration_ui_session_board_click_on_enemy_prompts_manual_attack_and_damage_rolls():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]
    session.attach_board_connection(FakeBoardConnection(clicks=[tuple(target["position"])]), backend="simulator")

    selected = session.scan_board_selection()

    assert selected["combat"]["pending_player_attack"]["stage"] == "attack_roll"
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert "Rzuć 1d20" in selected["combat"]["pending_player_attack"]["attack_instruction"]
    assert selected["combat"]["turn_action"]["action_use"] == "action_available"

    attack_roll = session.submit_player_attack_roll(natural_roll=20)
    pending = attack_roll["combat"]["pending_player_attack"]
    assert pending["stage"] == "damage_roll"
    assert pending["hit"] is True
    assert pending["critical"] is True
    assert "Rzuć obrażenia" in pending["damage_instruction"]
    assert attack_roll["combat"]["turn_action"]["action_use"] == "action_used"

    state = session.submit_player_damage_roll(damage=5)

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target["id"])
    assert damaged["hp"] < target["hp"]
    assert state["combat"]["pending_player_attack"] is None
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Obrażenia" for message in state["messages"])


def test_exploration_ui_session_board_scan_shows_feedback_once_before_waiting_for_click():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]
    board = FakeBoardConnection(clicks=[tuple(target["position"])])
    session.attach_board_connection(board, backend="simulator")

    session.scan_board_selection()

    assert board.led_calls[0] == ("off", None)
    assert board.led_calls[1] != ("off", None)


def test_exploration_ui_session_player_movement_updates_position_and_remaining_speed():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    state = session.state_payload()
    actor_id = state["combat"]["current_actor"]["id"]
    destination = next(tile for tile in state["combat"]["movement"]["destinations"] if tile["cost_feet"] == 5)

    state = session.submit_combat_movement(col=destination["col"], row=destination["row"])

    moved = next(actor for actor in state["combat"]["actors"] if actor["id"] == actor_id)
    assert moved["position"] == [destination["col"], destination["row"]]
    assert state["combat"]["movement"]["remaining_feet"] == 25
    assert any(message["title"] == "Ruch" for message in state["messages"])


def test_exploration_ui_session_board_movement_requires_second_click_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    actor_id = state["combat"]["current_actor"]["id"]
    destination = next(tile for tile in state["combat"]["movement"]["destinations"] if tile["cost_feet"] == 5)
    clicked = (destination["col"], destination["row"])
    session.attach_board_connection(FakeBoardConnection(clicks=[clicked, clicked]), backend="simulator")

    preview = session.scan_board_selection()

    actor_after_preview = next(actor for actor in preview["combat"]["actors"] if actor["id"] == actor_id)
    assert actor_after_preview["position"] == state["combat"]["current_actor"]["position"]
    assert preview["combat"]["movement_preview"]["destination"] == [destination["col"], destination["row"]]

    moved = session.scan_board_selection()

    actor_after_move = next(actor for actor in moved["combat"]["actors"] if actor["id"] == actor_id)
    assert actor_after_move["position"] == [destination["col"], destination["row"]]
    assert moved["combat"]["movement_preview"] is None


def test_exploration_ui_session_enemy_turn_waits_for_board_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    while session.combat_state is not None and session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy_id = str(session.combat_state.initiative_order.current_actor.id)

    preview = session.resolve_enemy_turn()

    assert preview["combat"]["current_actor"]["id"] == enemy_id
    assert preview["combat"]["enemy_turn_preview"] is not None
    assert any(message["title"] in {"Ruch przeciwnika", "Atak przeciwnika"} for message in preview["messages"])

    enemy_preview = preview["combat"]["enemy_turn_preview"]
    if enemy_preview["kind"] == "movement":
        click = tuple(enemy_preview["destination"])
    else:
        click = tuple(enemy_preview["target_position"])
    if "natural_roll" in enemy_preview:
        assert isinstance(enemy_preview["natural_roll"], int)
        assert isinstance(enemy_preview["total"], int)
        assert "hit" in enemy_preview
    board = FakeBoardConnection(clicks=[click])
    session.attach_board_connection(board, backend="simulator")

    state = session.scan_board_selection()

    assert any(message["title"] == "Tura przeciwnika" for message in state["messages"])
    if "natural_roll" in enemy_preview:
        assert any(
            message["title"] == "Tura przeciwnika" and "Rzut d20:" in message["body"] and "wynik końcowy:" in message["body"]
            for message in state["messages"]
        )
    assert state["combat"]["enemy_turn_preview"] is None
    assert state["combat"]["current_actor"]["id"] != enemy_id or state["combat"]["status"] == "finished"


def test_exploration_ui_session_can_reset_board_scan():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    state = session.reset_board_scan()

    assert board.reset_calls == ["reset_connection"]
    assert state["board"]["message"] == "Zresetowano oczekiwanie na kliknięcie planszy."


def test_exploration_ui_session_reset_restores_initial_state():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Wyważamy bramę.")
    session.decide("accept")
    session.resolve_rolls({"hero": 16})

    session.reset()
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    state = session.state_payload()

    assert state["active_challenge"]["current_progress"] == 0
    assert state["flags"] == []
