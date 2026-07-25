import json
import sys
import time

from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import ExplorationState, reveal_exploration_points
from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType, NpcInteractionProposal
from dnd_board_game.runtime import demo_exploration_scene
from dnd_board_game.runtime.demo_exploration_scene import build_parser, run_demo
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario
from dnd_board_game.runtime.session_observer import SessionObserver
from dnd_board_game.world import Coordinate


class FakeConnection:
    def __init__(self, scanned=None):
        self.events = []
        self.scanned = list(scanned or [])

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        self.events.append(("scan_board", list(acceptable_responses or [])))
        if not self.scanned:
            return None
        return self.scanned.pop(0)

    def cancel_scan(self):
        self.events.append(("cancel_scan",))


def _gm_analysis(analysis_type=GmDeclarationAnalysisType.PLAUSIBLE, message="", normalized_intent="Testowa interpretacja deklaracji."):
    return GmDeclarationAnalysis(
        analysis_type=analysis_type,
        player_message=message,
        normalized_intent=normalized_intent,
        reason="Testowy analyzer.",
        confidence=1.0,
    )


class FakeGmClient:
    model = "fake-gm"

    def __init__(self, proposal, analysis=None):
        self.proposals = list(proposal if isinstance(proposal, list) else [proposal])
        self.analyses = list(analysis if isinstance(analysis, list) else [analysis or _gm_analysis()])
        self.requests = []
        self.analysis_requests = []

    def analyze(self, request):
        self.analysis_requests.append(request)
        if len(self.analyses) > 1:
            return self.analyses.pop(0)
        return self.analyses[0]

    def classify(self, request):
        self.requests.append(request)
        if len(self.proposals) > 1:
            return self.proposals.pop(0)
        return self.proposals[0]


class FakeNpcClient:
    model = "fake-npc"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def interact_npc(self, request):
        self.requests.append(request)
        return self.proposal


def test_npc_interaction_proposal_accepts_null_optional_messages():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "player_narration": None,
            "npc_response": None,
            "requires_roll": False,
            "success_message": None,
            "failure_message": None,
            "gm_notes": None,
        }
    )

    assert proposal.player_narration == ""
    assert proposal.npc_response == ""
    assert proposal.success_message == ""
    assert proposal.failure_message == ""
    assert proposal.gm_notes == ""


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "none",
            "--session-id",
            "exploration_test",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            "--max-steps",
            "6",
            *extra,
        ]
    )


def _scenario_args(tmp_path, scenario, *extra):
    return _args(tmp_path, "--scenario", scenario, *extra)


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _gm_rope_proposal():
    return GmClassifierProposal.model_validate(
        {
            "intent_type": "challenge_attempt",
            "target_challenge_id": "closed_gate",
            "approach_label": "Przejście górą z liną",
            "approach_tags": ["climbing", "quiet"],
            "ability": "dexterity",
            "skill": "acrobatics",
            "difficulty_tier": "medium",
            "difficulty_reason": "Wspinaczka po starej bramie jest możliwa, ale wymaga sprawności.",
            "dc": 15,
            "progress_on_success": 2,
            "progress_on_failure": 1,
            "used_resource_ids": ["rope"],
            "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
            "player_narration": "Lina łapie o występ muru.",
        }
    )


def _gm_force_gate_completion_proposal():
    return GmClassifierProposal.model_validate(
        {
            "intent_type": "challenge_attempt",
            "target_challenge_id": "closed_gate",
            "approach_label": "Wyważenie bramy",
            "approach_tags": ["heavy_force", "noise"],
            "ability": "strength",
            "skill": "athletics",
            "difficulty_tier": "medium",
            "difficulty_reason": "Stara brama może ustąpić pod mocnym naporem, ale będzie głośno.",
            "dc": 15,
            "progress_on_success": 3,
            "progress_on_failure": 1,
            "used_resource_ids": [],
            "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
            "player_narration": "Napieracie na skrzydła bramy, próbując złamać stary rygiel.",
        }
    )


def _gm_quiet_party_proposal():
    return GmClassifierProposal.model_validate(
        {
            "intent_type": "challenge_attempt",
            "target_challenge_id": "closed_gate",
            "approach_label": "Ciche przejście przy bramie",
            "approach_tags": ["quiet", "climbing"],
            "ability": "dexterity",
            "skill": "acrobatics",
            "difficulty_tier": "medium",
            "difficulty_reason": "Cała drużyna próbuje przejść cicho, więc ryzykiem jest najgorszy wynik.",
            "dc": 15,
            "progress_on_success": 2,
            "progress_on_failure": 1,
            "used_resource_ids": [],
            "check_participants": "whole_party",
            "check_aggregation": "lowest",
            "consequence_targets": ["scene", "failed_actors"],
            "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
            "player_narration": "Próbujecie przejść bardzo cicho, pilnując każdego kroku.",
        }
    )


def _gm_unsupported_proposal():
    return GmClassifierProposal.model_validate(
        {
            "intent_type": "unsupported",
            "target_challenge_id": None,
            "player_narration": "Lina nie pozwoli przelecieć nad bramą. Spróbujcie opisać realne podejście.",
        }
    )


def _gm_preparation_proposal():
    return GmClassifierProposal.model_validate(
        {
            "intent_type": "challenge_attempt",
            "target_challenge_id": "closed_gate",
            "approach_label": "Przygotowanie liny",
            "approach_tags": ["climbing"],
            "used_resource_ids": [],
            "action_flow": "preparation",
            "requires_roll_now": False,
            "preparation_effect": {
                "type": "modifier",
                "label": "Lina stabilizuje wspinaczkę",
                "target_tags": ["climbing"],
                "value": 2,
                "duration": "next_attempt",
                "source": "freeform",
            },
            "player_narration": "Mocujecie linę tak, żeby następne wejście było łatwiejsze.",
        }
    )


def _gm_advantage_preparation_proposal():
    data = _gm_preparation_proposal().model_dump(mode="json")
    data.update(
        {
            "preparation_effect": {
                "type": "advantage",
                "label": "Lina daje pewne oparcie",
                "target_tags": ["climbing"],
                "value": 1,
                "duration": "next_attempt",
                "source": "freeform",
            }
        }
    )
    return GmClassifierProposal.model_validate(data)


def _gm_disadvantage_preparation_proposal():
    data = _gm_preparation_proposal().model_dump(mode="json")
    data.update(
        {
            "preparation_effect": {
                "type": "disadvantage",
                "label": "Śliskie przęsła utrudniają wejście",
                "target_tags": ["climbing"],
                "value": 1,
                "duration": "next_attempt",
                "source": "freeform",
            }
        }
    )
    return GmClassifierProposal.model_validate(data)


def _gm_effect_boost_preparation_proposal():
    data = _gm_preparation_proposal().model_dump(mode="json")
    data.update(
        {
            "approach_label": "Przygotowanie mocniejszej dźwigni",
            "approach_tags": ["lever"],
            "preparation_effect": {
                "type": "effect_boost",
                "label": "Lepszy punkt podważenia",
                "target_tags": ["lever"],
                "value": 1,
                "duration": "next_attempt",
                "source": "freeform",
            },
        }
    )
    return GmClassifierProposal.model_validate(data)


def _gm_grant_saw_preparation_proposal():
    data = _gm_preparation_proposal().model_dump(mode="json")
    data.update(
        {
            "approach_label": "Znalezienie starej piły",
            "approach_tags": ["scouting", "saw"],
            "preparation_effect": {
                "type": "grant_resource",
                "label": "Stara piła w obozowisku",
                "target_tags": ["saw", "picket"],
                "value": 1,
                "duration": "next_attempt",
                "source": "freeform",
                "resource_id": "saw",
            },
        }
    )
    return GmClassifierProposal.model_validate(data)


def _gm_unlock_saw_option_preparation_proposal():
    data = _gm_preparation_proposal().model_dump(mode="json")
    data.update(
        {
            "approach_label": "Odkrycie słabego miejsca",
            "approach_tags": ["scouting", "picket"],
            "preparation_effect": {
                "type": "unlock_option",
                "label": "Słabe miejsce w sztachetach",
                "target_tags": ["picket"],
                "value": 1,
                "duration": "next_attempt",
                "source": "freeform",
                "option_id": "saw_picket",
            },
        }
    )
    return GmClassifierProposal.model_validate(data)


def _gm_climb_without_resource_proposal():
    return _gm_rope_proposal().model_copy(update={"used_resource_ids": ()})


def _gm_lever_without_resource_proposal():
    return _gm_rope_proposal().model_copy(
        update={
            "approach_label": "Podważenie mechanizmu",
            "approach_tags": ("lever", "quiet"),
            "ability": "intelligence",
            "skill": "crafting",
            "difficulty_tier": "medium",
            "difficulty_reason": "Precyzyjne podważanie wymaga pracy przy mechanizmie.",
            "dc": 15,
            "progress_on_success": 2,
            "progress_on_failure": 1,
            "used_resource_ids": (),
            "player_narration": "Podważacie mechanizm spokojnie i metodycznie.",
        }
    )


def _gm_picket_without_resource_proposal():
    return _gm_rope_proposal().model_copy(
        update={
            "approach_label": "Praca przy sztachetach",
            "approach_tags": ("picket",),
            "ability": "strength",
            "skill": "athletics",
            "difficulty_tier": "medium",
            "difficulty_reason": "Poszerzenie szpary wymaga siły i ostrożności.",
            "dc": 15,
            "progress_on_success": 2,
            "progress_on_failure": 1,
            "used_resource_ids": (),
            "player_narration": "Pracujecie przy słabych sztachetach, próbując poszerzyć przejście.",
        }
    )


def _gm_picket_with_saw_resource_proposal():
    return _gm_picket_without_resource_proposal().model_copy(update={"used_resource_ids": ("saw",)})


def test_demo_exploration_scene_partial_gate_progress_keeps_courtyard_locked(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Próbujemy poszerzyć szparę w sztachetach.",
            "--gm-accept",
            "yes",
            "--exploration-script",
            "zone:gate",
            "--challenge-roll",
            "gm_generated=10",
        ),
        gm_client=FakeGmClient(_gm_picket_without_resource_proposal()),
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "challenge_progress_updated" in event_types
    assert [zone.id for zone in demo_exploration_scene.available_exploration_zones(result.final_state)] == ["gate"]


def test_demo_exploration_scene_shows_new_locations_after_gate_completion(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Wyważamy starą bramę.",
            "--gm-accept",
            "yes",
            "--exploration-script",
            "zone:gate",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "3",
        ),
        gm_client=FakeGmClient(_gm_force_gate_completion_proposal()),
    )

    events = _events(result.observation_path)
    assert any("Lokacje dostępne teraz" in message and "Dziedziniec" in message for message in result.messages)
    assert any(event["event_type"] == "exploration_available_locations_shown" for event in events)


def test_demo_exploration_scene_challenge_can_use_lowest_party_check(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Próbujemy przejść przy bramie bardzo cicho.",
            "--gm-accept",
            "yes",
            "--exploration-script",
            "zone:gate",
            "--party-check-roll",
            "hero=17",
            "--party-check-roll",
            "rogue=5",
            "--max-steps",
            "1",
        ),
        gm_client=FakeGmClient(_gm_quiet_party_proposal()),
    )

    events = _events(result.observation_path)
    check_events = [event for event in events if event["event_type"] == "check_resolved" and event["payload"]["phase"] == "challenge"]
    assert check_events
    assert check_events[0]["payload"]["plan"]["participants"] == "whole_party"
    assert check_events[0]["payload"]["plan"]["aggregation"] == "lowest"
    assert check_events[0]["payload"]["success"] is False
    assert check_events[0]["payload"]["selected_actor_id"] == "rogue"
    assert check_events[0]["payload"]["consequence_actor_ids"] == ["rogue", "cleric"]


def test_demo_exploration_scene_zone_travel_preview_uses_only_markers(tmp_path):
    connection = FakeConnection(scanned=[(9, 10), (9, 10)])
    result = run_demo(
        _args(
            tmp_path,
            "--board-backend",
            "simulator",
            "--show-leds",
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Wyważamy starą bramę.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "3",
        ),
        connection_factory=lambda args: connection,
        gm_client=FakeGmClient(_gm_force_gate_completion_proposal()),
    )

    events = _events(result.observation_path)
    assert any(event["event_type"] == "zone_travel_previewed" for event in events)
    assert any("Wybrana lokacja: Dziedziniec" in message for message in result.messages)
    assert any("Pusty dziedziniec" in message for message in result.messages)
    set_led_positions = [event[1] for event in connection.events if event[0] == "set_leds"]
    assert [(9, 2)] in set_led_positions
    assert [(9, 10)] in set_led_positions


def test_demo_exploration_scene_gate_completion_keeps_wounded_scout_hidden_until_encounter(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Wyważamy bramę.",
            "--gm-accept",
            "yes",
            "--exploration-script",
            "zone:gate",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "3",
        ),
        gm_client=FakeGmClient(_gm_force_gate_completion_proposal()),
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    visible_points = {point.id for point in demo_exploration_scene.visible_exploration_points(result.final_state.points)}
    assert "wounded_scout" not in visible_points
    assert "exploration_point_revealed" not in event_types
    assert not any("Ranny zwiadowca" in message for message in result.messages)


def test_demo_exploration_scene_npc_interaction_sets_flags_and_reveals_info(tmp_path):
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    state, _revealed = reveal_exploration_points(state, ("wounded_scout",))
    point = next(point for point in state.points if point.id == "wounded_scout")
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "player_narration": "Klękacie przy zwiadowcy i odsuwacie deski, starając się nie szarpać rany.",
            "npc_response": "Zwiadowca syczy z bólu, ale przestaje się cofać.",
            "requires_roll": True,
            "ability": "wisdom",
            "skill": "medicine",
            "dc": 10,
            "success_message": "Stabilizujecie zwiadowcę. Może już mówić spokojniej.",
            "failure_message": "Zwiadowca wpada w panikę i potrzebuje więcej czasu.",
            "flag_changes_on_success": [
                {"key": "scout_treated", "value": True},
                {"key": "scout_stabilized", "value": True},
            ],
            "flag_changes_on_failure": [{"key": "scout_panicked", "value": True}],
            "revealed_information_ids": ["tower_hint"],
        }
    )
    args = _args(
        tmp_path,
        "--gm-classifier",
        "gemini",
        "--freeform-action",
        "opatrujemy rannego zwiadowcę i pytamy, co widział",
        "--gm-accept",
        "yes",
        "--party-check-roll",
        "hero=12",
        "--party-check-roll",
        "rogue=12",
    )
    observer = SessionObserver("npc_test", tmp_path)

    new_state, messages, _sent = demo_exploration_scene._handle_exploration_point(
        args,
        exploration,
        state,
        point,
        None,
        observer,
        FakeNpcClient(proposal),
    )

    events = _events(observer.path)
    assert any("Stabilizujecie zwiadowcę" in message for message in messages)
    assert any("ktoś przeciągnął coś ciężkiego w stronę wieży obserwacyjnej" in message for message in messages)
    assert ("scout_stabilized", True) in new_state.flags.values
    assert ("tower_hint_learned", True) in new_state.flags.values
    assert "npc_check_resolved" in [event["event_type"] for event in events]
    assert "npc_information_revealed" in [event["event_type"] for event in events]
    check_events = [event for event in events if event["event_type"] == "check_resolved" and event["payload"]["phase"] == "npc"]
    assert check_events
    assert check_events[0]["payload"]["plan"]["participants"] == "lead_with_help"
    assert check_events[0]["payload"]["plan"]["aggregation"] == "lead_result"
    assert check_events[0]["payload"]["plan"]["consequence_targets"] == ["npc"]


def test_demo_exploration_scene_npc_interaction_rejects_blocked_intent(tmp_path):
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    state, _revealed = reveal_exploration_points(state, ("wounded_scout",))
    point = next(point for point in state.points if point.id == "wounded_scout")
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "trade",
            "player_narration": "Próbujecie ubić z nim targ, ale zwiadowca nie jest kupcem.",
            "requires_roll": False,
        }
    )
    args = _args(
        tmp_path,
        "--gm-classifier",
        "gemini",
        "--freeform-action",
        "chcemy kupić od niego informacje",
        "--gm-accept",
        "yes",
    )
    observer = SessionObserver("npc_blocked_test", tmp_path)

    new_state, messages, _sent = demo_exploration_scene._handle_exploration_point(
        args,
        exploration,
        state,
        point,
        None,
        observer,
        FakeNpcClient(proposal),
    )

    assert new_state == state
    assert any("NPC intent is blocked here: trade" in message for message in messages)
    assert "npc_interaction_rejected" in [event["event_type"] for event in _events(observer.path)]


def test_demo_exploration_scene_debug_point_starts_npc_interaction_without_map_flow(tmp_path):
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "player_narration": "Mówicie spokojnie i pokazujecie puste dłonie.",
            "npc_response": "Zwiadowca oddycha wolniej i opuszcza rękę.",
            "requires_roll": False,
            "flag_changes_on_success": [{"key": "scout_calmed", "value": True}],
        }
    )

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "gemini",
            "--freeform-action",
            "uspokajamy zwiadowcę i pytamy, czy jest bezpieczny",
            "--gm-accept",
            "yes",
            "--debug-point",
            "wounded_scout",
            "--max-steps",
            "1",
        ),
        gm_client=FakeNpcClient(proposal),
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert ("scout_calmed", True) in result.final_state.flags.values
    assert "debug_point_interaction_started" in event_types
    assert "npc_interaction_started" in event_types
    assert not any(event["event_type"] == "exploration_setup_started" for event in events)


def test_demo_exploration_scene_gm_classifier_dry_run_does_not_change_progress(tmp_path):
    client = FakeGmClient(_gm_rope_proposal())

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--gm-dry-run",
            "--freeform-action",
            "Próbujemy wejść górą z liną.",
            "--max-steps",
            "2",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.requests) == 1
    assert "gm_classifier_requested" in event_types
    assert "gm_declaration_analyzed" in event_types
    assert "gm_classifier_proposal_validated" in event_types
    assert "challenge_progress_updated" not in event_types
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_freeform_defaults_to_gemini(tmp_path):
    client = FakeGmClient(_gm_rope_proposal())

    result = run_demo(
        _args(
            tmp_path,
            "--gm-dry-run",
            "--freeform-action",
            "Próbujemy wejść górą z liną.",
            "--max-steps",
            "2",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    request_event = next(event for event in events if event["event_type"] == "gm_classifier_requested")
    assert request_event["payload"]["provider"] == "gemini"
    assert len(client.requests) == 1


def test_demo_exploration_scene_gm_classifier_resolves_generated_option(tmp_path):
    client = FakeGmClient(_gm_rope_proposal())

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Próbujemy wejść górą z liną.",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "2",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "resource_used" in event_types
    assert "gm_classifier_option_resolved" in event_types
    assert "challenge_progress_updated" in event_types
    assert any("Zamek nadal może trzymać bramę" in message for message in result.messages)
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_gm_classifier_retries_after_rejection(tmp_path, monkeypatch):
    client = FakeGmClient([_gm_unsupported_proposal(), _gm_rope_proposal()])
    answers = iter(["Próbujemy wejść górą z liną."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Wsiadam na linę i przelatuję nad bramą.",
            "--challenge-roll",
            "gm_generated=14",
            "--gm-accept",
            "yes",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.requests) == 2
    assert "gm_classifier_proposal_rejected" in event_types
    assert "gm_classifier_option_resolved" in event_types
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True


def test_demo_exploration_scene_interactive_gm_auto_selects_single_zone(tmp_path, monkeypatch):
    client = FakeGmClient(_gm_rope_proposal())
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "Próbujemy wejść górą z liną.")

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--challenge-roll",
            "gm_generated=14",
            "--gm-accept",
            "yes",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.requests) == 1
    assert len(client.analysis_requests) == 1
    assert "exploration_zone_auto_selected" in event_types
    assert "gm_classifier_option_resolved" in event_types
    assert any("przechodzę do niej automatycznie" in message for message in result.messages)


def test_demo_exploration_scene_gm_accept_no_skips_roll_and_progress(tmp_path):
    client = FakeGmClient(_gm_rope_proposal())

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Próbujemy wejść górą z liną.",
            "--gm-accept",
            "no",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "gm_interpretation_rejected" in event_types
    assert "challenge_progress_updated" not in event_types
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_player_question_does_not_classify_or_roll(tmp_path):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=_gm_analysis(
            GmDeclarationAnalysisType.PLAYER_QUESTION,
            "Najciszej wygląda manipulowanie mechanizmem albo szukanie obejścia.",
        ),
    )

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--freeform-action",
            "Jak przejść bez hałasu?",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.requests) == 0
    assert "player_question_answered" in event_types
    assert "challenge_progress_updated" not in event_types
    assert any("Najciszej wygląda" in message for message in result.messages)


def test_demo_exploration_scene_clarification_acceptance_uses_normalized_intent(tmp_path, monkeypatch):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=_gm_analysis(
            GmDeclarationAnalysisType.NEEDS_CLARIFICATION,
            "Czy chcesz wyważyć bramę z całej siły?",
            "Wyważenie bramy z rozbiegu.",
        ),
    )
    answers = iter(["+"])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-action",
            "Biorę długi rozbieg.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.analysis_requests) == 1
    assert len(client.requests) == 1
    assert client.requests[0].player_action == "Wyważenie bramy z rozbiegu."
    assert "gm_declaration_clarification_accepted" in event_types
    assert "gm_classifier_option_resolved" in event_types


def test_demo_exploration_scene_clarification_reprompts_unknown_terminal_command(tmp_path, monkeypatch):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=_gm_analysis(
            GmDeclarationAnalysisType.NEEDS_CLARIFICATION,
            "Czy chcesz wyważyć bramę z całej siły?",
            "Wyważenie bramy z rozbiegu.",
        ),
    )
    answers = iter(["moze", "+"])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-action",
            "Biorę długi rozbieg.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "gm_declaration_clarification_accepted" in event_types
    assert "gm_classifier_option_resolved" in event_types


def test_demo_exploration_scene_unsupported_analysis_retries_without_classifying(tmp_path):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=[
            _gm_analysis(
                GmDeclarationAnalysisType.UNSUPPORTED,
                "Laserowy pistolet nie pasuje do tej sceny fantasy.",
            ),
            _gm_analysis(),
        ],
    )

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Strzelamy laserowym pistoletem.",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "gm_declaration_unsupported" in event_types
    assert len(client.requests) == 0
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_correction_attempt_gets_declaration_thread(tmp_path, monkeypatch):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=[
            _gm_analysis(
                GmDeclarationAnalysisType.UNSUPPORTED,
                "Drużyna nie ma skocznych butów.",
            ),
            _gm_analysis(),
        ],
    )
    answers = iter(["Dobra, to bez butów, próbujemy przeskoczyć z rozbiegu."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Przeskakujemy bramę w skocznych butach.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.analysis_requests) == 2
    assert client.analysis_requests[1].declaration_thread[0].content == "Przeskakujemy bramę w skocznych butach."
    assert "Drużyna nie ma skocznych butów" in client.analysis_requests[1].declaration_thread[0].outcome
    assert client.analysis_requests[1].player_action == "Dobra, to bez butów, próbujemy przeskoczyć z rozbiegu."
    assert "gm_declaration_thread_updated" in event_types
    assert "gm_classifier_option_resolved" in event_types


def test_demo_exploration_scene_interpretation_help_does_not_change_state_before_accept(tmp_path, monkeypatch):
    proposal = _gm_rope_proposal().model_copy(update={"gm_notes": "Test dexterity/acrobatics, bo deklaracja opisuje wspinaczkę."})
    client = FakeGmClient(proposal)
    answers = iter(["?", "+"])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-action",
            "Wchodzimy górą po bramie.",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "gm_interpretation_explained" in event_types
    assert "gm_interpretation_accepted" in event_types
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True


def test_demo_exploration_scene_reclassifies_same_declaration_with_context(tmp_path, monkeypatch):
    first = _gm_rope_proposal().model_copy(update={"approach_label": "Pierwsza interpretacja"})
    second = _gm_rope_proposal().model_copy(update={"approach_label": "Druga interpretacja"})
    client = FakeGmClient([first, second])
    answers = iter(["r", "+"])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-action",
            "Wchodzimy górą po bramie.",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert len(client.requests) == 2
    assert "Poprzednia interpretacja" in client.requests[1].declaration_thread[-1].content
    assert "gm_interpretation_reclassify_requested" in event_types
    assert "gm_interpretation_reclassified" in event_types
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True


def test_demo_exploration_scene_rejected_interpretation_records_correction(tmp_path, monkeypatch):
    client = FakeGmClient([_gm_rope_proposal(), _gm_rope_proposal()])
    answers = iter(["-", "Nie, chodzi nam o wspinaczkę bez użycia klina.", "+"])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Próbujemy przejść po bramie.",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "gm_interpretation_rejected" in event_types
    assert "gm_interpretation_corrected" in event_types
    assert client.analysis_requests[1].player_action == "Nie, chodzi nam o wspinaczkę bez użycia klina."
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True


def test_demo_exploration_scene_preparation_then_attempt_applies_effect(tmp_path, monkeypatch):
    client = FakeGmClient(
        [_gm_preparation_proposal(), _gm_climb_without_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Przygotowanie liny."),
            _gm_analysis(normalized_intent="Wejście górą."),
        ],
    )
    answers = iter(["Wchodzimy górą po bramie."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Owijamy linę wokół belki, żeby łatwiej wejść.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=11",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "preparation_effect_created" in event_types
    assert "preparation_effect_applied" in event_types
    assert "preparation_effect_expired" in event_types
    assert "gm_classifier_option_resolved" in event_types
    assert scene_flag(result.final_state.flags, "gate_bolt_cleared") is True


def test_demo_exploration_scene_advantage_preparation_changes_roll_instruction(tmp_path, monkeypatch, capsys):
    client = FakeGmClient(
        [_gm_advantage_preparation_proposal(), _gm_climb_without_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Przygotowanie liny."),
            _gm_analysis(normalized_intent="Wejście górą."),
        ],
    )
    answers = iter(["Wchodzimy górą po bramie."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Mocujemy linę pod wspinaczkę.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    output = capsys.readouterr().out
    assert "Rzuć 2d20 z przewagą i wpisz oba wyniki" in output


def test_demo_exploration_scene_disadvantage_preparation_changes_roll_instruction(tmp_path, monkeypatch, capsys):
    client = FakeGmClient(
        [_gm_disadvantage_preparation_proposal(), _gm_climb_without_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Śliskie przęsła."),
            _gm_analysis(normalized_intent="Wejście górą."),
        ],
    )
    answers = iter(["Wchodzimy górą po bramie."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Śliskie deski utrudniają wejście.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=14",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    output = capsys.readouterr().out
    assert "Rzuć 2d20 z utrudnieniem i wpisz oba wyniki" in output


def test_demo_exploration_scene_effect_boost_increases_success_progress(tmp_path, monkeypatch):
    client = FakeGmClient(
        [_gm_effect_boost_preparation_proposal(), _gm_lever_without_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Przygotowanie dźwigni."),
            _gm_analysis(normalized_intent="Podważenie mechanizmu."),
        ],
    )
    answers = iter(["Podważamy mechanizm."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Ustawiamy lepszy punkt podważenia.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    assert scene_flag(result.final_state.flags, "gate_structure_weakened") is True
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_grant_resource_effect_adds_resource_after_success(tmp_path, monkeypatch):
    client = FakeGmClient(
        [_gm_grant_saw_preparation_proposal(), _gm_picket_with_saw_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Szukamy piły."),
            _gm_analysis(normalized_intent="Próbujemy użyć odkrytego narzędzia."),
        ],
    )
    answers = iter(["Próbujemy użyć odkrytego narzędzia."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Rozglądamy się za narzędziem.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "saw" in result.final_state.inventory_resource_ids
    assert "resource_granted" in event_types
    assert "gm_classifier_proposal_rejected" not in event_types
    assert "resource_used" in event_types


def test_demo_exploration_scene_unlock_option_effect_sets_unlock_flag_after_success(tmp_path, monkeypatch):
    client = FakeGmClient(
        [_gm_unlock_saw_option_preparation_proposal(), _gm_picket_without_resource_proposal()],
        analysis=[
            _gm_analysis(normalized_intent="Szukamy słabego miejsca."),
            _gm_analysis(normalized_intent="Wykorzystujemy słabe miejsce."),
        ],
    )
    answers = iter(["Wykorzystujemy słabe miejsce."])
    monkeypatch.setattr(demo_exploration_scene.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-retries",
            "2",
            "--freeform-action",
            "Szukamy słabego miejsca w sztachetach.",
            "--gm-accept",
            "yes",
            "--challenge-roll",
            "gm_generated=15",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert ("llm_unlocked_option:saw_picket", True) in result.final_state.flags.values
    assert "option_unlocked" in event_types


def test_demo_exploration_scene_declared_missing_resource_does_not_roll(tmp_path):
    client = FakeGmClient(
        _gm_rope_proposal(),
        analysis=_gm_analysis(
            message="Drużyna nie ma słoika z kwasem.",
            normalized_intent="Użycie kwasu na zawiasach.",
        ).model_copy(update={"declared_resources": ("słoik z kwasem",)}),
    )

    result = run_demo(
        _args(
            tmp_path,
            "--gm-classifier",
            "groq",
            "--interactive-freeform",
            "--freeform-action",
            "Wyciągam słoik z kwasem i polewam zawiasy.",
            "--max-steps",
            "1",
        ),
        gm_client=client,
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "declaration_fact_rejected" in event_types
    assert "gm_classifier_option_resolved" not in event_types
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_inspects_non_anchor_tile_without_options(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "tile:gate",
            "--exploration-script",
            "end",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "zone_tile_inspected" in event_types
    assert "zone_option_previewed" not in event_types


def test_demo_exploration_scene_setup_sends_leds_with_fake_connection(tmp_path):
    connection = FakeConnection(scanned=[(9, 2), (8, 1)])
    args = _args(tmp_path, "--board-backend", "simulator", "--show-leds", "--max-steps", "1")

    result = run_demo(args, connection_factory=lambda args: connection)

    assert result.feedback_events > 0
    assert any(event[0] == "set_leds" for event in connection.events)
    assert any("Dostępne lokacje" in message for message in result.messages)
    assert sum(message.count("Kliknij odpowiednią lokację") for message in result.messages) == 1
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "exploration_setup_started" in event_types
    assert "party_position_set" in event_types


def test_demo_exploration_scene_gate_click_shows_challenge_prompt_by_default(tmp_path):
    connection = FakeConnection(scanned=[(9, 2)])
    args = _args(tmp_path, "--board-backend", "simulator", "--show-leds", "--max-steps", "1")

    result = run_demo(args, connection_factory=lambda args: connection)

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "challenge_freeform_prompted" in event_types
    assert any("konkretnych zmian stanu przeszkody" in message for message in result.messages)
    assert not any("Aktualny postęp" in message for message in result.messages)


def test_demo_exploration_scene_pending_scripts_do_not_open_challenge_menu_by_default(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "unused_script_command",
            "--max-steps",
            "1",
        )
    )

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "challenge_freeform_prompted" in event_types
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 0


def test_demo_exploration_scene_village_setup_confirms_visible_points_with_fake_connection(tmp_path):
    connection = FakeConnection(scanned=[(8, 5), (8, 4), (8, 1)])
    args = _scenario_args(
        tmp_path,
        "content/scenarios/village_square_mvp.json",
        "--board-backend",
        "simulator",
        "--show-leds",
        "--max-steps",
        "1",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    scan_events = [event for event in connection.events if event[0] == "scan_board"]
    assert scan_events[0][1] == [(8, 5), (7, 4), (3, 12)]
    assert any("Setup jawnych elementów 1" in message for message in result.messages)
    assert any("Dostępne lokacje" in message for message in result.messages)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "exploration_setup_step_confirmed" in event_types


def test_wait_for_scan_or_enter_returns_click():
    connection = FakeConnection(scanned=[(2, 3)])

    event, position = demo_exploration_scene._wait_for_scan_or_enter(
        BoardLedAdapter(connection),
        [(2, 3)],
        timeout_s=1,
    )

    assert event == "click"
    assert position == Coordinate(2, 3)


def test_wait_for_scan_or_enter_cancels_scan_on_enter(monkeypatch):
    class BlockingConnection(FakeConnection):
        def scan_board(self, acceptable_responses=None, *, timeout_s=None):
            self.events.append(("scan_board", list(acceptable_responses or [])))
            time.sleep(0.2)
            return None

    connection = BlockingConnection()

    class _ReadableStdin:
        def fileno(self):
            return sys.stdin.fileno()

        def readline(self):
            return "\n"

    monkeypatch.setattr(demo_exploration_scene.select, "select", lambda *_args, **_kwargs: ([_ReadableStdin()], [], []))
    monkeypatch.setattr(demo_exploration_scene.sys, "stdin", _ReadableStdin())

    event, position = demo_exploration_scene._wait_for_scan_or_enter(
        BoardLedAdapter(connection),
        [(2, 3)],
        timeout_s=1,
    )

    assert event == "enter"
    assert position is None
    assert ("cancel_scan",) in connection.events
