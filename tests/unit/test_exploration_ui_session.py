import random
from dataclasses import replace

from dnd_board_game.actors import Faction
from dnd_board_game.combat import EnemyAutoTurnResult, replace_actor, set_scene_flag
from dnd_board_game.combat.damage import DamageComponentInput, DamageType, apply_damage_result, resolve_damage
from dnd_board_game.hardware import LedColor
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.rules import RollMode
from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession,
    PendingInteraction,
    PendingKind,
    PendingStage,
    PendingEnemyOpportunityAttack,
    UiFlowStage,
    create_app,
)
from dnd_board_game.world import Coordinate, find_path


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
            while session.encounter_setup_flow.is_player_start_step:
                position = session.encounter_setup_flow.remaining_player_start_positions()[0]
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    session.submit_encounter_initiative_roll(19)
    session.submit_encounter_initiative_roll(18)
    assert session.combat_state is not None
    return session.combat_state


def _start_gate_skirmish(session: ExplorationUiSession):
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "gate_passed", True))
    session.state_payload()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            while session.encounter_setup_flow.is_player_start_step:
                position = session.encounter_setup_flow.remaining_player_start_positions()[0]
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    session.submit_encounter_initiative_roll(19)
    session.submit_encounter_initiative_roll(18)
    assert session.combat_state is not None
    return session.combat_state


def _prepare_enemy_opportunity_preview(session: ExplorationUiSession):
    assert session.combat_state is not None
    while session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy = session.combat_state.initiative_order.current_actor
    hero = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ALLY)
    session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(8, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(hero, position=Coordinate(7, 7)))
    enemy = session.combat_state.initiative_order.current_actor
    moved_enemy = replace(enemy, position=Coordinate(9, 7))
    path = find_path(session.encounter_setup_flow.encounter.board, enemy, session.combat_state.actors, moved_enemy.position)
    moved_state = replace_actor(session.combat_state, moved_enemy)
    session.pending_enemy_turn_result = EnemyAutoTurnResult(
        state=moved_state,
        enemy=enemy,
        target=None,
        message=f"{enemy.name} rusza się na {moved_enemy.position.as_tuple()}.",
        movement_path=path,
        moved_enemy=moved_enemy,
    )
    session.pending_enemy_opportunity_attack = PendingEnemyOpportunityAttack(
        target_id=str(enemy.id),
        threat_actor_ids=(str(hero.id),),
    )
    return hero, enemy


def _prepare_ready_attack_trigger(session: ExplorationUiSession, trigger: str = "enemy_moves"):
    assert session.combat_state is not None
    readied_actor = session.combat_state.initiative_order.current_actor
    target = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(readied_actor, position=Coordinate(8, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(10, 7)))
    readied_actor = session.combat_state.initiative_order.current_actor
    target = next(actor for actor in session.combat_state.actors if actor.id == target.id)
    session.confirm_combat_ready(trigger=trigger)
    moved_target = replace(target, position=Coordinate(9, 7))
    path = find_path(session.encounter_setup_flow.encounter.board, target, session.combat_state.actors, moved_target.position)
    result_state = replace_actor(session.combat_state, moved_target)
    result = EnemyAutoTurnResult(
        state=result_state,
        enemy=target,
        target=None,
        message=f"{target.name} rusza się na {moved_target.position.as_tuple()}.",
        movement_path=path,
        moved_enemy=moved_target,
    )
    pending = session._pending_ready_attack_for_enemy_result(result)
    assert pending is not None
    session.pending_enemy_turn_result = result
    session.pending_ready_attack = pending
    return readied_actor, target


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
    assert state["required_rolls"] == [{"actor_id": "hero", "actor_name": "Bohater", "die_sides": 20, "label": "d20"}]

    state = session.resolve_rolls({"hero": 16})

    assert state["pending"] is None
    assert state["active_challenge"] is None
    assert state["flow"]["stage"] == "interaction_result"
    assert state["exploration_setup"] is None


def test_exploration_ui_session_applies_item_bonus_and_breaks_item_after_critical_failure():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "lockpick_gate")
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        proposal=_challenge_proposal(),
        challenge=challenge,
        option=option,
    )

    accepted = session.decide("accept", lead_actor_id="hero")

    assert accepted["required_rolls"] == [{"actor_id": "rogue", "actor_name": "Łotrzyca", "die_sides": 20, "label": "d20"}]
    plan = accepted["pending"]["check_plan"]
    assert plan["option_bonuses"][0]["source_id"] == "thieves_tools"
    assert plan["option_bonuses"][0]["modifier"] == 2

    after_roll = session.resolve_rolls({"rogue": 1})

    assert after_roll["pending"]["stage"] == "breakage"
    assert after_roll["required_rolls"] == [{"actor_id": "rogue", "actor_name": "Łotrzyca", "die_sides": 100, "label": "k100 trwałości"}]
    assert after_roll["pending"]["breakage"]["chance_percent"] == 25

    after_breakage = session.resolve_rolls({"rogue": 12})

    assert after_breakage["pending"] is None
    rogue = next(actor for actor in after_breakage["actors"] if actor["id"] == "rogue")
    thieves_tools = next(item for item in rogue["inventory"] if item["id"] == "thieves_tools")
    assert thieves_tools["broken"] is True
    assert thieves_tools["available"] is False


def test_exploration_ui_session_consumes_leveled_spell_slot_for_exploration_bonus():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "reveal_bolt_with_flame")
    option = replace(option, bonuses=(replace(option.bonuses[0], spell_level=1),))
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        proposal=_challenge_proposal(),
        challenge=challenge,
        option=option,
    )

    accepted = session.decide("accept", lead_actor_id="hero")

    assert accepted["required_rolls"] == [{"actor_id": "cleric", "actor_name": "Kapłan", "die_sides": 20, "label": "d20"}]
    assert accepted["pending"]["check_plan"]["option_bonuses"][0]["spell_level"] == 1

    resolved = session.resolve_rolls({"cleric": 12})

    cleric = next(actor for actor in resolved["actors"] if actor["id"] == "cleric")
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert any(message["title"] == "Zużyty slot czaru" for message in resolved["messages"])


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
    assert session.combat_state is not None
    for index, actor in enumerate(tuple(session.combat_state.actors)):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, position=Coordinate(10, index)))

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
    assert session.combat_state is not None
    for index, actor in enumerate(tuple(session.combat_state.actors)):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, position=Coordinate(10, index)))
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


def test_exploration_ui_session_dash_uses_action_and_extends_movement_pool():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    dashed = session.use_combat_dash()

    assert dashed["combat"]["turn_action"]["action_use"] == "action_used"
    assert dashed["combat"]["turn_action"]["extra_movement_feet"] == 30
    assert dashed["combat"]["movement"]["remaining_feet"] == 60
    assert dashed["combat"]["movement"]["extra_movement_feet"] == 30
    assert any(message["title"] == "Dash" and "dodatkowe 30 feet" in message["body"] for message in dashed["messages"])


def test_exploration_ui_session_can_select_attack_source_and_strength_potion_modifies_strength_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "hero":
        session.finish_combat_turn()

    state = session.state_payload()
    source_ids = {source["id"] for source in state["combat"]["available_attack_sources"]}
    assert {"longsword_slash", "crossbow_shot"} <= source_ids
    hero_payload = state["combat"]["current_actor"]
    assert {item["id"] for item in hero_payload["inventory"]} >= {"longsword", "crossbow", "strength_potion"}
    potion_action = next(action for action in state["combat"]["combat_actions"] if action["id"] == "drink_strength_potion")
    assert potion_action["source_item_id"] == "strength_potion"
    assert potion_action["source_item_quantity"] == 1
    assert potion_action["available"] is True
    longsword_payload = next(source for source in state["combat"]["available_attack_sources"] if source["id"] == "longsword_slash")
    crossbow_payload = next(source for source in state["combat"]["available_attack_sources"] if source["id"] == "crossbow_shot")
    assert longsword_payload["mechanic"]["type"] == "MeleeAttack"
    assert crossbow_payload["mechanic"]["type"] == "RangedAttack"

    selected = session.select_combat_attack_source("longsword_slash")
    assert selected["combat"]["selected_attack_source_id"] == "longsword_slash"

    boosted = session.use_combat_strength_potion("drink_strength_potion")
    assert boosted["combat"]["turn_action"]["action_use"] == "action_used"
    actor = next(candidate for candidate in boosted["combat"]["actors"] if candidate["id"] == "hero")
    assert any(effect["kind"] == "strength_potion" for effect in actor["effects"])
    strength_potion = next(item for item in actor["inventory"] if item["id"] == "strength_potion")
    assert strength_potion["quantity"] == 0
    spent_action = next(action for action in boosted["combat"]["combat_actions"] if action["id"] == "drink_strength_potion")
    assert spent_action["available"] is False

    hero = next(candidate for candidate in session.combat_state.actors if str(candidate.id) == "hero")
    base_source = next(source for source in session._attack_sources_for_actor(hero) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero, base_source)
    assert any(modifier.label == "Wypij napój siły" and modifier.value == 2 for modifier in modified.attack_roll_request.modifiers)
    assert modified.damage_modifier == base_source.damage_modifier + 2


def test_exploration_ui_session_cleric_can_heal_wounded_ally():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    wounded = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    session.combat_state = replace_actor(session.combat_state, replace(wounded, hp=10))

    selected = session.select_combat_healing_source("healing_word")
    assert selected["combat"]["selected_healing_source_id"] == "healing_word"
    healing_payload = next(source for source in selected["combat"]["available_healing_sources"] if source["id"] == "healing_word")
    assert healing_payload["mechanic"]["type"] == "SpellHealing"
    assert healing_payload["casting_kind"] == "leveled"
    assert healing_payload["resource_label"] == "slot 1. poziomu"
    assert healing_payload["prepared"] is True
    assert any(target["id"] == "hero" for target in selected["combat"]["legal_healing_targets"])

    target_position = next(actor.position for actor in session.combat_state.actors if str(actor.id) == "hero")
    pending = session.select_player_healing_target_at_position(target_position)
    assert pending["combat"]["pending_player_healing"]["target"]["id"] == "hero"

    healed = session.submit_player_healing_roll(healing=6)
    hero = next(actor for actor in healed["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in healed["combat"]["actors"] if actor["id"] == "cleric")
    assert hero["hp"] == 16
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert healed["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Leczenie" and "HP 10 -> 16" in message["body"] for message in healed["messages"])


def test_exploration_ui_session_cleric_concentration_spell_grants_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()

    started = session.start_combat_concentration_action("bless_attack_bonus")
    pending = started["combat"]["pending_concentration_action"]
    assert pending["action"]["id"] == "bless_attack_bonus"
    assert pending["action"]["resource_label"] == "slot 1. poziomu"
    assert pending["action"]["concentration"] is True
    assert any(target["id"] == "hero" for target in pending["targets"])

    confirmed = session.confirm_combat_concentration_action(target_id="hero")
    hero = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric")

    assert confirmed["combat"]["pending_concentration_action"] is None
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_used"
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert cleric["concentration"]["kind"] == "concentration_attack_bonus"
    assert cleric["concentration"]["target_actor_id"] == "hero"
    assert any(effect["kind"] == "concentration_attack_bonus" and effect["value"] == 1 for effect in hero["effects"])

    hero_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    source = next(source for source in session._attack_sources_for_actor(hero_actor) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero_actor, source)
    assert any(modifier.label == "Błogosławieństwo" and modifier.value == 1 for modifier in modified.attack_roll_request.modifiers)


def _cleric_casts_bless_on_hero(session: ExplorationUiSession) -> None:
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.start_combat_concentration_action("bless_attack_bonus")
    session.confirm_combat_concentration_action(target_id="hero")


def _apply_test_damage(session: ExplorationUiSession, actor_id: str, damage_amount: int) -> None:
    assert session.combat_state is not None
    actor = next(candidate for candidate in session.combat_state.actors if str(candidate.id) == actor_id)
    damage = resolve_damage((DamageComponentInput(damage_amount, DamageType.SLASHING, "test"),))
    applied = apply_damage_result(actor, damage)
    session.combat_state = replace_actor(session.combat_state, applied.actor_after)
    session._maybe_prompt_concentration_check(applied)


def test_exploration_ui_session_concentration_check_failure_removes_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _cleric_casts_bless_on_hero(session)

    _apply_test_damage(session, "cleric", 12)
    payload = session.state_payload()
    pending = payload["combat"]["pending_concentration_check"]

    assert pending["actor"]["id"] == "cleric"
    assert pending["damage"] == 12
    assert pending["dc"] == 10
    assert pending["modifier"] == 1
    assert pending["effects"][0]["kind"] == "concentration_attack_bonus"

    resolved = session.submit_concentration_check(natural_roll=1)
    hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "cleric")

    assert resolved["combat"]["pending_concentration_check"] is None
    assert hero["effects"] == []
    assert cleric["concentration"] is None

    hero_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    source = next(source for source in session._attack_sources_for_actor(hero_actor) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero_actor, source)
    assert not any(modifier.label == "Błogosławieństwo" for modifier in modified.attack_roll_request.modifiers)


def test_exploration_ui_session_concentration_check_success_keeps_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _cleric_casts_bless_on_hero(session)

    _apply_test_damage(session, "cleric", 12)
    resolved = session.submit_concentration_check(natural_roll=20)
    hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "cleric")

    assert resolved["combat"]["pending_concentration_check"] is None
    assert cleric["concentration"]["kind"] == "concentration_attack_bonus"
    assert any(effect["kind"] == "concentration_attack_bonus" and effect["value"] == 1 for effect in hero["effects"])


def test_exploration_ui_session_cleric_area_spell_previews_line_and_consumes_slot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(goblin, position=Coordinate(11, 6)))

    selected = session.select_combat_attack_source("radiant_line")

    assert selected["combat"]["selected_attack_source_id"] == "radiant_line"
    source_payload = next(source for source in selected["combat"]["available_attack_sources"] if source["id"] == "radiant_line")
    assert source_payload["mechanic"]["type"] == "AreaSpellAttack"
    assert source_payload["casting_kind"] == "leveled"
    assert source_payload["resource_label"] == "slot 1. poziomu"
    cantrip_payload = next(source for source in selected["combat"]["available_attack_sources"] if source["id"] == "sacred_flame")
    assert cantrip_payload["casting_kind"] == "cantrip"
    assert cantrip_payload["resource_label"] == "cantrip"
    assert [10, 6] in selected["combat"]["legal_area_positions"]
    assert selected["combat"]["legal_targets"] == []

    pending = session.select_player_area_spell_at_position(Coordinate(10, 6))

    area_spell = pending["combat"]["pending_area_spell"]
    assert area_spell["source"]["id"] == "radiant_line"
    assert [11, 6] in area_spell["area_positions"]
    assert [target["id"] for target in area_spell["targets"]] == ["goblin_b"]

    confirmed = session.confirm_player_area_spell()
    cleric_after_confirm = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric")

    assert confirmed["combat"]["pending_area_spell"]["stage"] == "damage_roll"
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_used"
    assert cleric_after_confirm["spell_slots"][0]["remaining"] == 1
    save = confirmed["combat"]["pending_area_spell"]["saving_throws"][0]
    assert save["actor_id"] == "goblin_b"
    assert save["ability"] == "dexterity"
    assert save["dc"] == 13
    assert save["success"] is True

    damaged = session.submit_player_area_spell_damage(damage=5)
    damaged_goblin = next(actor for actor in damaged["combat"]["actors"] if actor["id"] == "goblin_b")

    assert damaged["combat"]["pending_area_spell"] is None
    assert damaged_goblin["hp"] == 8
    assert any(message["title"] == "Obrażenia obszarowe" and "HP 10 -> 8" in message["body"] for message in damaged["messages"])


def test_exploration_ui_session_sacred_flame_uses_enemy_save_instead_of_attack_roll():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.encounter_rng = random.Random(0)

    selected = session.select_combat_attack_source("sacred_flame")
    target_position = next(actor.position for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    pending = session.select_player_attack_target_at_position(target_position)

    assert pending["combat"]["pending_player_attack"]["source"]["save_ability"] == "dexterity"
    assert pending["combat"]["pending_player_attack"]["spell_save_dc"] == 13

    resolved = session.confirm_player_attack_target()
    goblin = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "goblin_b")

    assert resolved["combat"]["pending_player_attack"] is None
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"
    assert goblin["hp"] == 10
    assert any(message["title"] == "Czar" and "Sukces: brak obrażeń" in message["body"] for message in resolved["messages"])


def test_exploration_ui_session_dodge_adds_defensive_effect_until_next_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    dodged = session.use_combat_dodge()
    actor_payload = next(candidate for candidate in dodged["combat"]["actors"] if candidate["id"] == str(actor.id))
    current_actor_payload = dodged["combat"]["current_actor"]
    enemy_actor = next(candidate for candidate in session.combat_state.actors if candidate.faction == Faction.ENEMY)
    source = session.encounter_setup_flow.encounter.attack_sources_by_actor[enemy_actor.id]
    modified_source = session._effective_attack_source(enemy_actor, source, actor)

    assert dodged["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor_payload["effects"][0]["kind"] == "dodge_until_next_turn"
    assert actor_payload["effects"][0]["label"] == "Unik"
    assert actor_payload["effects"][0]["value_label"] == "ataki przeciwko aktorowi mają utrudnienie"
    assert actor_payload["effects"][0]["expires"] == "znika na początku następnej tury aktora"
    chip_labels = {chip["label"] for chip in current_actor_payload["status_chips"]}
    assert "Akcja zużyta" in chip_labels
    assert "Reakcja dostępna" in chip_labels
    assert "Unik: ataki przeciwko aktorowi mają utrudnienie" in chip_labels
    assert modified_source.attack_roll_request.mode == RollMode.DISADVANTAGE

    session.finish_combat_turn()
    assert any(effect.actor_id == str(actor.id) and effect.kind == "dodge_until_next_turn" for effect in session.active_combat_effects)
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != str(actor.id):
        session.finish_combat_turn()

    assert not any(effect.actor_id == str(actor.id) and effect.kind == "dodge_until_next_turn" for effect in session.active_combat_effects)
    assert any(message.title == "Efekty" and "Unik" in message.body for message in session.messages)


def test_exploration_ui_session_disengage_adds_effect_until_turn_end():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    disengaged = session.use_combat_disengage()
    actor_payload = next(candidate for candidate in disengaged["combat"]["actors"] if candidate["id"] == str(actor.id))

    assert disengaged["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor_payload["effects"][0]["kind"] == "disengage_until_turn_end"
    assert actor_payload["effects"][0]["label"] == "Odwrót"
    assert actor_payload["effects"][0]["value_label"] == "bezpieczne odejście"
    assert actor_payload["effects"][0]["expires"] == "znika na końcu tury"
    assert any(message["title"] == "Odwrót" and "bezpiecznie odejść" in message["body"] for message in disengaged["messages"])

    ended = session.finish_combat_turn()

    assert not any(effect.actor_id == str(actor.id) and effect.kind == "disengage_until_turn_end" for effect in session.active_combat_effects)
    assert not any(
        effect["kind"] == "disengage_until_turn_end"
        for candidate in ended["combat"]["actors"]
        for effect in candidate["effects"]
    )


def test_exploration_ui_session_movement_leaving_reach_requires_opportunity_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    state = session.submit_combat_movement(col=9, row=7)

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [10, 7]
    assert state["combat"]["pending_opportunity_movement"]["destination"] == [9, 7]
    assert [threat["id"] for threat in state["combat"]["pending_opportunity_movement"]["threats"]] == ["goblin_b"]
    assert any(message["title"] == "Atak okazyjny" for message in state["messages"])


def test_exploration_ui_session_confirming_opportunity_movement_resolves_reaction_then_moves():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    session.encounter_rng = random.Random(1)
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    session.submit_combat_movement(col=9, row=7)
    state = session.confirm_opportunity_movement()

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [9, 7]
    assert state["combat"]["pending_opportunity_movement"] is None
    assert any(message["title"] == "Atak okazyjny" and "Goblin przy rumowisku" in message["body"] for message in state["messages"])
    assert session.combat_state is not None
    assert str(next(iter(session.combat_state.spent_reaction_actor_ids))) == "goblin_b"


def test_exploration_ui_session_disengage_prevents_opportunity_movement_prompt():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))
    session.use_combat_disengage()

    state = session.submit_combat_movement(col=9, row=7)

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [9, 7]
    assert state["combat"]["pending_opportunity_movement"] is None


def test_exploration_ui_session_help_grants_advantage_to_ally_attack_against_target():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    helper = session.combat_state.initiative_order.current_actor
    ally = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ALLY and actor.id != helper.id)
    target = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(helper, position=Coordinate(10, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(ally, position=Coordinate(10, 8)))
    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(11, 7)))
    ally = next(actor for actor in session.combat_state.actors if actor.id == ally.id)
    target = next(actor for actor in session.combat_state.actors if actor.id == target.id)

    pending = session.start_combat_help()
    helped = session.confirm_combat_help(ally_id=str(ally.id), target_id=str(target.id))

    ally_payload = next(actor for actor in helped["combat"]["actors"] if actor["id"] == str(ally.id))
    assert pending["combat"]["pending_combat_help"]["helper"]["id"] == str(helper.id)
    assert helped["combat"]["turn_action"]["action_use"] == "action_used"
    assert ally_payload["effects"][0]["kind"] == "help_attack_advantage"
    assert ally_payload["effects"][0]["target_actor_id"] == str(target.id)

    session.finish_combat_turn()
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != str(ally.id):
        session.finish_combat_turn()

    selected = session.select_player_attack_target_at_position(target.position)
    assert selected["combat"]["pending_player_attack"]["attack_mode"] == "advantage"

    session.confirm_player_attack_target()
    rolled = session.submit_player_attack_roll(natural_roll=10, natural_roll_2=15)

    assert not any(effect.kind == "help_attack_advantage" for effect in session.active_combat_effects)
    assert rolled["combat"]["pending_player_attack"] is not None
    assert rolled["combat"]["pending_player_attack"]["natural_rolls"] == [10, 15]
    assert rolled["combat"]["pending_player_attack"]["natural_roll"] == 15


def test_exploration_ui_session_ready_prepares_attack_and_can_trigger_on_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    pending = session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    triggered = session.state_payload()

    assert pending["combat"]["pending_combat_ready"]["actor"]["id"] == str(readied_actor.id)
    assert triggered["combat"]["pending_ready_attack"]["stage"] == "choice"
    assert triggered["combat"]["pending_ready_attack"]["attacker"]["id"] == str(readied_actor.id)
    assert triggered["combat"]["pending_ready_attack"]["target"]["id"] == str(target.id)

    started = session.start_ready_attack()
    missed = session.submit_ready_attack_roll(natural_roll=1)

    assert started["combat"]["pending_ready_attack"]["stage"] == "attack_roll"
    assert missed["combat"]["pending_ready_attack"] is None
    assert missed["combat"]["enemy_turn_preview"]["kind"] == "movement"
    assert not any(effect.kind == "ready_attack" for effect in session.active_combat_effects)
    assert session.combat_state is not None
    assert readied_actor.id in session.pending_enemy_turn_result.state.spent_reaction_actor_ids


def test_exploration_ui_session_ready_attack_can_stop_enemy_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    session.start_ready_attack()
    rolled = session.submit_ready_attack_roll(natural_roll=20)
    stopped = session.submit_ready_damage_roll(damage=999)

    target_payload = next(actor for actor in stopped["combat"]["actors"] if actor["id"] == str(target.id))
    assert rolled["combat"]["pending_ready_attack"]["stage"] == "damage_roll"
    assert target_payload["defeated"] is True
    assert stopped["combat"]["pending_ready_attack"] is None
    assert stopped["combat"]["enemy_turn_preview"] is None
    assert any(
        message["title"] == "Ready" and "Tura przeciwnika zostaje przerwana" in message["body"]
        for message in stopped["messages"]
    )


def test_exploration_ui_session_hero_opportunity_attack_can_be_taken_during_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    hero, enemy = _prepare_enemy_opportunity_preview(session)

    started = session.start_enemy_opportunity_attack()

    assert started["combat"]["pending_enemy_opportunity_attack"]["stage"] == "attack_roll"
    assert started["combat"]["pending_enemy_opportunity_attack"]["attacker"]["id"] == str(hero.id)
    assert started["combat"]["pending_enemy_opportunity_attack"]["target"]["id"] == str(enemy.id)

    missed = session.submit_enemy_opportunity_attack_roll(natural_roll=1)

    assert missed["combat"]["pending_enemy_opportunity_attack"] is None
    assert missed["combat"]["enemy_turn_preview"]["kind"] == "movement"
    assert session.combat_state is not None
    assert hero.id in session.pending_enemy_turn_result.state.spent_reaction_actor_ids


def test_exploration_ui_session_hero_opportunity_attack_can_stop_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    hero, enemy = _prepare_enemy_opportunity_preview(session)

    session.start_enemy_opportunity_attack()
    rolled = session.submit_enemy_opportunity_attack_roll(natural_roll=20)
    stopped = session.submit_enemy_opportunity_damage_roll(damage=999)

    enemy_payload = next(actor for actor in stopped["combat"]["actors"] if actor["id"] == str(enemy.id))
    assert rolled["combat"]["pending_enemy_opportunity_attack"]["stage"] == "damage_roll"
    assert enemy_payload["defeated"] is True
    assert stopped["combat"]["pending_enemy_opportunity_attack"] is None
    assert stopped["combat"]["enemy_turn_preview"] is None
    assert any(
        message["title"] == "Atak okazyjny" and "Ruch przeciwnika zostaje przerwany" in message["body"]
        for message in stopped["messages"]
    )


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
    assert enemy["effects"][0]["value_label"] == "-2 do następnego ataku"
    assert enemy["effects"][0]["expires"] == "znika po następnym ataku"
    assert enemy["effects"][0]["summary"] == "Gruz w oczach | -2 do następnego ataku | znika po następnym ataku"
    assert any(chip["label"] == "Gruz w oczach: -2 do następnego ataku" and chip["tone"] == "penalty" for chip in enemy["status_chips"])
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
