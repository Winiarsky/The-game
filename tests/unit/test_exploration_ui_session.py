import random
from dataclasses import replace

from dnd_board_game.actors import Faction
from dnd_board_game.combat import replace_actor, set_scene_flag
from dnd_board_game.hardware import LedColor
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage, create_app
from dnd_board_game.world import Coordinate


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


def _start_gate_skirmish(session: ExplorationUiSession):
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "gate_passed", True))
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
    assert state["combat"]["current_actor"]["max_hp"] >= state["combat"]["current_actor"]["hp"]
    assert "temp_hp" in state["combat"]["current_actor"]
    assert "defeated" in state["combat"]["current_actor"]
    assert state["combat"]["turn_action"]["bonus_action_use"] == "action_available"
    assert state["combat"]["turn_action"]["reaction_available"] is True
    target_id = state["combat"]["legal_targets"][0]["id"]

    state = session.submit_player_attack(target_id=target_id, natural_roll=20, damage=5)

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target_id)
    assert damaged["hp"] < 7
    assert damaged["max_hp"] >= damaged["hp"]
    assert damaged["defeated"] is False
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Atak" and "trafia krytycznie" in message["body"] for message in state["messages"])
    assert any(message["title"] == "Atak" and "HP" in message["body"] for message in state["messages"])


def test_exploration_ui_session_board_click_on_enemy_prompts_manual_attack_and_damage_rolls():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]
    session.attach_board_connection(FakeBoardConnection(clicks=[tuple(target["position"])]), backend="simulator")

    selected = session.scan_board_selection()

    assert selected["combat"]["pending_player_attack"]["stage"] == "confirm_attack"
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert selected["combat"]["pending_player_attack"]["target"]["ac"] == target["ac"]
    assert selected["combat"]["pending_player_attack"]["attack_modifier"] > 0
    assert selected["combat"]["pending_player_attack"]["active_modifiers"]
    assert "Rzuć 1d20" in selected["combat"]["pending_player_attack"]["attack_instruction"]
    assert selected["combat"]["turn_action"]["action_use"] == "action_available"

    confirmed = session.confirm_player_attack_target()
    assert confirmed["combat"]["pending_player_attack"]["stage"] == "attack_roll"
    assert confirmed["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_available"

    attack_roll = session.submit_player_attack_roll(natural_roll=20)
    pending = attack_roll["combat"]["pending_player_attack"]
    assert pending["stage"] == "damage_roll"
    assert pending["hit"] is True
    assert pending["critical"] is True
    assert pending["target_ac"] == target["ac"]
    assert "Rzuć obrażenia" in pending["damage_instruction"]
    assert attack_roll["combat"]["turn_action"]["action_use"] == "action_used"

    state = session.submit_player_damage_roll(damage=5)

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target["id"])
    assert damaged["hp"] < target["hp"]
    assert damaged["max_hp"] == target["max_hp"]
    assert state["combat"]["pending_player_attack"] is None
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Obrażenia" and "HP" in message["body"] for message in state["messages"])


def test_exploration_ui_session_player_damage_can_finish_combat_and_remove_target():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]

    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY and str(actor.id) != target["id"]:
            session.combat_state = replace_actor(session.combat_state, replace(actor, hp=0))

    state = session.submit_player_attack(target_id=target["id"], natural_roll=20, damage=999)

    defeated = next(actor for actor in state["combat"]["actors"] if actor["id"] == target["id"])
    assert defeated["hp"] == 0
    assert defeated["defeated"] is True
    assert state["combat"]["status"] == "finished"
    assert state["combat"]["winner"] == "ally"
    assert state["combat"]["legal_targets"] == []
    assert any(message["title"] == "Atak" and "Cel zostaje pokonany" in message["body"] for message in state["messages"])


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


def test_exploration_ui_session_cart_cover_uses_action_and_expires_after_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    state = session.submit_combat_movement(col=7, row=7)
    actor_id = state["combat"]["current_actor"]["id"]
    base_ac = state["combat"]["current_actor"]["ac"]

    selected = session.select_board_position(Coordinate(7, 8))

    assert selected["combat"]["pending_combat_interaction"]["object_id"] == "broken_cart"
    assert {option["id"] for option in selected["combat"]["pending_combat_interaction"]["options"]} == {
        "take_cover_cart",
        "climb_cart",
    }

    covered = session.confirm_combat_interaction("take_cover_cart")
    actor = next(candidate for candidate in covered["combat"]["actors"] if candidate["id"] == actor_id)

    assert covered["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor["ac"] == base_ac + 2
    assert actor["effects"][0]["kind"] == "grant_ac_bonus_until_move"
    assert any(message["title"] == "Interakcja" and "AC +2" in message["body"] for message in covered["messages"])

    moved = session.submit_combat_movement(col=6, row=7)
    moved_actor = next(candidate for candidate in moved["combat"]["actors"] if candidate["id"] == actor_id)

    assert moved_actor["position"] == [6, 7]
    assert moved_actor["ac"] == base_ac
    assert moved_actor["effects"] == []


def test_exploration_ui_session_cart_climb_moves_actor_and_adds_attack_bonus_next_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    state = session.submit_combat_movement(col=7, row=7)
    actor_id = state["combat"]["current_actor"]["id"]
    session.select_board_position(Coordinate(7, 8))

    climbed = session.confirm_combat_interaction("climb_cart")
    actor = next(candidate for candidate in climbed["combat"]["actors"] if candidate["id"] == actor_id)

    assert actor["position"] == [7, 8]
    assert actor["effects"][0]["kind"] == "grant_attack_bonus_while_on_object"
    assert climbed["combat"]["turn_action"]["action_use"] == "action_used"

    session.finish_combat_turn()
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != actor_id:
        session.finish_combat_turn()

    selected = session.select_player_attack_target_at_position(Coordinate(7, 9))
    modifiers = selected["combat"]["pending_player_attack"]["active_modifiers"]

    assert any(modifier["label"] == "Pozycja na wozie" and modifier["value"] == 2 for modifier in modifiers)


def test_exploration_ui_session_cart_interactions_are_shown_with_interactive_leds():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.scan_board_selection()

    colored_positions = {}
    for positions, rgb_color in board.led_calls:
        if positions == "off":
            continue
        if rgb_color and all(isinstance(channel, int) for channel in rgb_color):
            colored_positions.update({position: rgb_color for position in positions})
        else:
            colored_positions.update(dict(zip(positions, rgb_color, strict=True)))

    assert colored_positions[(7, 8)] == list(LedColor.INTERACTIVE_OBJECT)
    assert colored_positions[(8, 8)] == list(LedColor.INTERACTIVE_OBJECT)


def test_exploration_ui_session_rubble_interaction_penalizes_adjacent_enemy_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    session.encounter_rng = random.Random(1)
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    selected = session.select_board_position(Coordinate(10, 7))

    assert selected["combat"]["pending_combat_interaction"]["object_id"] == "rubble_patch"
    assert [option["id"] for option in selected["combat"]["pending_combat_interaction"]["options"]] == ["throw_rubble"]

    applied = session.confirm_combat_interaction("throw_rubble")
    enemy = next(actor for actor in applied["combat"]["actors"] if actor["id"] == "goblin_b")

    assert applied["combat"]["turn_action"]["action_use"] == "action_used"
    assert enemy["effects"][0]["kind"] == "grant_next_attack_penalty"
    assert enemy["effects"][0]["value"] == -2
    assert any(message["title"] == "Interakcja" and "Gruz w oczach" in message["body"] for message in applied["messages"])
    assert any(message["title"] == "Interakcja" and "rzut obronny na Zręczność" in message["body"] for message in applied["messages"])
    assert any(message["title"] == "Interakcja" and "ST 12" in message["body"] for message in applied["messages"])

    enemy_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    source = session.encounter_setup_flow.encounter.attack_sources_by_actor[enemy_actor.id]
    modified_source = session._effective_attack_source(enemy_actor, source)

    assert any(
        modifier.label == "Gruz w oczach" and modifier.value == -2
        for modifier in modified_source.attack_roll_request.modifiers
    )


def test_exploration_ui_session_rubble_tile_is_interactive_when_actor_stands_on_it():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.scan_board_selection()

    colored_positions = {}
    for positions, rgb_color in board.led_calls:
        if positions == "off":
            continue
        if rgb_color and all(isinstance(channel, int) for channel in rgb_color):
            colored_positions.update({position: rgb_color for position in positions})
        else:
            colored_positions.update(dict(zip(positions, rgb_color, strict=True)))

    assert colored_positions[(10, 7)] == list(LedColor.INTERACTIVE_OBJECT)


def test_exploration_ui_session_enemy_turn_waits_for_board_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    while session.combat_state is not None and session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy_id = str(session.combat_state.initiative_order.current_actor.id)
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    intent = session.resolve_enemy_turn()

    assert intent["combat"]["current_actor"]["id"] == enemy_id
    assert intent["combat"]["enemy_turn_intent"] is not None
    assert intent["combat"]["enemy_turn_preview"] is None
    assert any(message["title"] == "Zamiar przeciwnika" for message in intent["messages"])
    intent_payload = intent["combat"]["enemy_turn_intent"]
    highlighted_positions = {
        tuple(position)
        for positions, _color in board.led_calls
        if positions != "off"
        for position in positions
    }
    if intent_payload["kind"] == "movement":
        assert tuple(intent_payload["destination"]) in highlighted_positions
    if intent_payload.get("target_position"):
        assert tuple(intent_payload["target_position"]) in highlighted_positions

    preview = session.resolve_enemy_turn()

    assert preview["combat"]["current_actor"]["id"] == enemy_id
    assert preview["combat"]["enemy_turn_intent"] is None
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
    board.clicks.append(click)

    result = session.scan_board_selection()

    assert result["combat"]["enemy_turn_preview"] is None
    assert result["combat"]["enemy_turn_result"] is not None
    assert result["combat"]["current_actor"]["id"] == enemy_id
    if "natural_roll" in enemy_preview:
        assert "Rzut d20:" in result["combat"]["enemy_turn_result"]["message"]
        assert "wynik końcowy:" in result["combat"]["enemy_turn_result"]["message"]

    state = session.confirm_enemy_turn_result()

    assert any(message["title"] == "Tura przeciwnika" for message in state["messages"])
    if "natural_roll" in enemy_preview:
        assert any(
            message["title"] == "Tura przeciwnika" and "Rzut d20:" in message["body"] and "wynik końcowy:" in message["body"]
            for message in state["messages"]
        )
    assert state["combat"]["enemy_turn_preview"] is None
    assert state["combat"]["enemy_turn_result"] is None
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
