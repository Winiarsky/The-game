import json
import sys
import time

from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType
from dnd_board_game.runtime import demo_exploration_scene
from dnd_board_game.runtime.demo_exploration_scene import build_parser, run_demo
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
            "dc": 13,
            "progress_on_success": 2,
            "progress_on_failure": 1,
            "used_resource_ids": ["rope"],
            "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
            "player_narration": "Lina łapie o występ muru.",
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


def test_demo_exploration_scene_runs_scripted_zone_travel_and_search(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "confirm",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "confirm",
            "--party-check-roll",
            "hero=10",
            "--party-check-roll",
            "rogue=10",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "courtyard"
    assert any("kolor czerwony" in message for message in result.messages)
    assert not any("RGB" in message for message in result.messages)
    assert "party_zone_changed" in event_types
    assert "party_check_resolved" in event_types
    assert "zone_search_revealed" in event_types
    assert any(point.visibility.value == "visible" for point in result.final_state.points if point.id == "hidden_cache")
    party_check = [event for event in events if event["event_type"] == "party_check_resolved"][-1]
    assert party_check["payload"]["winning_total"] == 12


def test_demo_exploration_scene_partial_gate_progress_keeps_courtyard_locked(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "option:break_picket",
            "--challenge-roll",
            "break_picket=10",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "challenge_progress_updated" in event_types
    assert [zone.id for zone in demo_exploration_scene.available_exploration_zones(result.final_state)] == ["gate"]


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
    assert any("postęp przy sukcesie: +2, postęp przy porażce: +1" in message for message in result.messages)
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 2


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
    assert demo_exploration_scene.challenge_state_for(result.final_state, "closed_gate").current_progress == 2


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


def test_demo_exploration_scene_search_can_reveal_saw_resource(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "option:inspect_gate_area",
            "--exploration-script",
            "point:old_camp_tools",
            "--max-steps",
            "8",
            "--party-check-roll",
            "hero=15",
            "--party-check-roll",
            "rogue=15",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "resource_found" in event_types
    assert "saw" in result.final_state.inventory_resource_ids


def test_demo_exploration_scene_village_message_option_sets_flag_and_completes_objective(tmp_path):
    result = run_demo(
        _scenario_args(
            tmp_path,
            "content/scenarios/village_square_mvp.json",
            "--exploration-script",
            "zone:market",
            "--exploration-script",
            "option:talk_to_elder",
            "--max-steps",
            "4",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert ("quest_hook_found", True) in result.final_state.flags.values
    assert "scene_flag_set" in event_types
    assert "objective_completed" in event_types
    assert "exploration_finished" in event_types
    assert any("Cel eksploracji" in message for message in result.messages)


def test_demo_exploration_scene_rejects_non_adjacent_zone_travel(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "confirm",
            "--exploration-script",
            "zone:tower",
            "--exploration-script",
            "end",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "zone_travel_rejected" in event_types


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
    assert "exploration_menu_opened" not in event_types
    assert any("Aby przejść dalej" in message for message in result.messages)
    assert any("Aktualny postęp: 0/3" in message for message in result.messages)


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


def test_demo_exploration_menu_clears_anchor_before_showing_options(tmp_path):
    connection = FakeConnection(scanned=[(9, 2), (8, 1)])
    args = _args(
        tmp_path,
        "--board-backend",
        "simulator",
        "--show-leds",
        "--legacy-option-menu",
        "--max-steps",
        "1",
    )

    run_demo(args, connection_factory=lambda args: connection)

    menu_start_indexes = [
        index
        for index, event in enumerate(connection.events)
        if event[0] == "set_leds" and event[1] == [(9, 1)]
    ]
    assert menu_start_indexes
    menu_start = menu_start_indexes[-1]
    assert connection.events[menu_start - 1] == ("leds_off",)
    menu_events = [event for event in connection.events[menu_start:] if event[0] == "set_leds"]
    assert all(event[1] != [(9, 2)] for event in menu_events)


def test_demo_exploration_clears_revealed_point_before_next_map_state(tmp_path):
    connection = FakeConnection(scanned=[(9, 2), (10, 3), (9, 2), (8, 1)])
    args = _args(
        tmp_path,
        "--board-backend",
        "simulator",
        "--show-leds",
        "--legacy-option-menu",
        "--max-steps",
        "2",
        "--party-check-roll",
        "hero=15",
        "--party-check-roll",
        "rogue=15",
    )

    run_demo(args, connection_factory=lambda args: connection)

    revealed_indexes = [
        index
        for index, event in enumerate(connection.events)
        if event[0] == "set_leds" and event[1] == [(11, 3)]
    ]
    assert revealed_indexes
    revealed_index = revealed_indexes[-1]
    assert ("leds_off",) in connection.events[revealed_index + 1 :]


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
