from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType, NpcInteractionProposal
from dnd_board_game.ui.exploration_app import ExplorationUiSession, UiFlowStage, create_app


class FakeGmClient:
    model = "fake-gm"

    def analyze(self, request):
        return GmDeclarationAnalysis(
            analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
            player_message="",
            normalized_intent=request.player_action,
            reason="test",
            confidence=1.0,
        )

    def classify(self, request):
        if "hałas" in request.player_action.lower():
            return GmClassifierProposal.model_validate(
                {
                    "intent_type": "challenge_attempt",
                    "target_challenge_id": "closed_gate",
                    "approach_label": "Głośne wyważenie bramy",
                    "approach_tags": ["heavy_force", "noise"],
                    "ability": "strength",
                    "skill": "athletics",
                    "difficulty_tier": "medium",
                    "difficulty_reason": "Test.",
                    "dc": 15,
                    "progress_on_success": 3,
                    "progress_on_failure": 1,
                    "used_resource_ids": [],
                    "consequences": [{"trigger": "success", "type": "add_noise", "value": 3}],
                    "player_narration": "Uderzacie w bramę bardzo głośno.",
                }
            )
        if request.state.party_position.zone_id == "courtyard":
            return GmClassifierProposal.model_validate(
                {
                    "intent_type": "challenge_attempt",
                    "target_challenge_id": "courtyard_search",
                    "approach_label": "Ostrożne przeszukanie wozu",
                    "approach_tags": ["search", "careful"],
                    "ability": "wisdom",
                    "skill": "perception",
                    "difficulty_tier": "easy",
                    "difficulty_reason": "Test.",
                    "dc": 12,
                    "progress_on_success": 2,
                    "progress_on_failure": 1,
                    "used_resource_ids": [],
                    "consequences": [],
                    "player_narration": "Sprawdzacie naruszony wóz i ślady na błocie.",
                }
            )
        return GmClassifierProposal.model_validate(
            {
                "intent_type": "challenge_attempt",
                "target_challenge_id": "closed_gate",
                "approach_label": "Wyważenie bramy",
                "approach_tags": ["heavy_force", "noise"],
                "ability": "strength",
                "skill": "athletics",
                "difficulty_tier": "medium",
                "difficulty_reason": "Test.",
                "dc": 15,
                "progress_on_success": 3,
                "progress_on_failure": 1,
                "used_resource_ids": [],
                "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
                "player_narration": "Napieracie na skrzydła bramy.",
            }
        )


class FakeNpcClient:
    model = "fake-npc"

    def interact_npc(self, request):
        return NpcInteractionProposal.model_validate(
            {
                "action_type": "social",
                "player_narration": "Podchodzicie spokojnie i mówicie, że chcecie pomóc.",
                "npc_response": "Zwiadowca oddycha płycej, ale przestaje się szarpać.",
                "requires_roll": False,
                "flag_changes_on_success": [{"key": "scout_calmed", "value": True}],
            }
        )


def _client(*, active: bool = True):
    return create_app(_session(active=active)).test_client()


def _session(*, active: bool = True):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(),
        npc_client=FakeNpcClient(),
    )
    if active:
        session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    return session


def test_exploration_ui_page_includes_session_log_panel():
    client = _client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="session-log-panel"' in html
    assert 'id="session-log-filter"' in html
    assert "/api/session-log" in html


def test_exploration_ui_session_log_endpoint_returns_events():
    client = _client()

    data = client.get("/api/session-log").get_json()

    assert data["session_id"].startswith("exploration_ui_")
    assert data["path"].endswith(".jsonl")
    assert data["events"][0]["event_type"] == "ui_session_started"


class FakeBoardConnection:
    def __init__(self, clicks=None):
        self.clicks = list(clicks or [])
        self.led_calls = []
        self.clear_calls = 0

    def set_leds(self, positions, rgb_color):
        self.led_calls.append((tuple(tuple(position) for position in positions), tuple(rgb_color)))

    def leds_off(self):
        self.clear_calls += 1

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        if not self.clicks:
            return None
        return self.clicks.pop(0)


def test_exploration_ui_state_endpoint_returns_json():
    client = _client()

    response = client.get("/api/state")

    assert response.status_code == 200
    assert response.get_json()["scenario"]["id"] == "abandoned_watchtower"


def test_exploration_ui_initial_payload_waits_for_board_and_hides_actions():
    client = _client(active=False)

    data = client.get("/api/state").get_json()

    assert data["flow"]["stage"] == "waiting_for_board"
    assert data["flow"]["can_start"] is False
    assert data["active_challenge"] is None
    assert data["current_zone"]["image_url"].endswith("/scenario-assets/assets/gate_preview.png")


def test_exploration_ui_serves_gate_preview_asset():
    client = _client(active=False)

    response = client.get("/scenario-assets/assets/gate_preview.png")

    assert response.status_code == 200
    assert response.content_type == "image/png"


def test_exploration_ui_prefills_board_settings_from_shared_config():
    client = _client()

    board = client.get("/api/state").get_json()["board"]

    assert board["configured_backend"] == "hardware"
    assert board["backend"] == "none"
    assert board["board_serial_port"] == "/dev/ttyUSB0"
    assert board["wled_url"] == "http://192.168.0.165"


def test_exploration_ui_state_includes_player_facing_scene_description():
    client = _client()

    response = client.get("/api/state")

    data = response.get_json()
    assert "Zarośnięta" in data["current_zone"]["description"]
    assert "stara drewniana brama" in data["current_zone"]["summary"]
    assert "wspinaczka" in data["active_challenge"]["reasonable_approaches"]
    assert data["active_challenge"]["risk_notes"]


def test_exploration_ui_start_and_double_click_location_flow_updates_leds():
    session = _session(active=False)
    board = FakeBoardConnection(clicks=[(9, 2), (9, 2)])
    session.attach_board_connection(board, backend="simulator")
    app = create_app(session)
    client = app.test_client()

    ready = client.get("/api/state").get_json()
    assert ready["flow"]["stage"] == "ready_to_start"

    started = client.post("/api/start", json={}).get_json()
    assert started["flow"]["stage"] == "location_preview"
    assert started["flow"]["preview_zone"] is None
    assert [zone["id"] for zone in started["flow"]["available_locations"]] == ["gate", "courtyard", "tower"]
    assert [zone["available"] for zone in started["flow"]["available_locations"]] == [True, False, False]

    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "gate"
    assert preview["active_challenge"] is None

    active = client.post("/api/board/scan", json={}).get_json()
    assert active["flow"]["stage"] == "location_active"
    assert active["active_challenge"]["id"] == "closed_gate"


def test_exploration_ui_blocked_visible_location_shows_locked_preview():
    session = _session(active=False)
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    client.post("/api/start", json={})
    preview = client.post("/api/board/scan", json={}).get_json()

    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "courtyard"
    assert preview["flow"]["preview_zone"]["available"] is False
    assert "Najpierw trzeba otworzyć bramę" in preview["flow"]["preview_zone"]["locked_reason"]
    assert preview["active_challenge"] is None


def test_exploration_ui_action_rejects_empty_text():
    client = _client()

    response = client.post("/api/action", json={"text": ""})

    assert response.status_code == 400
    assert "Deklaracja nie może być pusta" in response.get_json()["error"]


def test_exploration_ui_decision_without_pending_is_controlled_error():
    client = _client()

    response = client.post("/api/decision", json={"decision": "accept"})

    assert response.status_code == 400
    assert "Brak propozycji" in response.get_json()["error"]


def test_exploration_ui_action_accept_and_roll_flow():
    client = _client()

    action_response = client.post("/api/action", json={"text": "Wyważamy bramę."})
    assert action_response.status_code == 200
    assert action_response.get_json()["pending"]["stage"] == "decision"

    decision_response = client.post("/api/decision", json={"decision": "accept"})
    assert decision_response.status_code == 200
    assert decision_response.get_json()["required_rolls"][0]["actor_id"] == "hero"

    rolls_response = client.post("/api/rolls", json={"rolls": {"hero": 16}})
    assert rolls_response.status_code == 200
    data = rolls_response.get_json()
    assert data["flow"]["stage"] == "interaction_result"
    assert data["flow"]["interaction_result"]["unlocked_zones"][0]["id"] == "courtyard"
    assert data["active_challenge"] is None
    assert data["travel_options"][0]["id"] == "courtyard"
    assert {"label": "Brama", "value": "otwarta"} in data["scene_status"]


def test_exploration_ui_accept_can_select_lead_actor():
    client = _client()

    client.post("/api/action", json={"text": "Wyważamy bramę."})
    response = client.post("/api/decision", json={"decision": "accept", "lead_actor_id": "rogue"})

    assert response.status_code == 200
    assert response.get_json()["required_rolls"] == [{"actor_id": "rogue", "actor_name": "Łotrzyca"}]


def test_exploration_ui_reset_endpoint_restores_state():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})

    response = client.post("/api/reset", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "waiting_for_board"
    assert data["active_challenge"] is None


def test_exploration_ui_shows_and_handles_travel_after_completed_challenge():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    completed = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()

    assert completed["active_challenge"] is None
    assert completed["travel_options"][0]["id"] == "courtyard"

    response = client.post("/api/travel", json={"zone_id": "courtyard"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["current_zone"]["id"] == "courtyard"
    assert data["active_challenge"]["id"] == "courtyard_search"


def test_exploration_ui_finish_interaction_returns_to_location_selection():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    completed = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()
    assert completed["flow"]["stage"] == "interaction_result"

    response = client.post("/api/interaction/finish", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"] is None
    assert [zone["id"] for zone in data["flow"]["available_locations"]] == ["gate", "courtyard", "tower"]
    assert [zone["color"] for zone in data["flow"]["available_locations"]] == ["żółty", "niebieski", "pomarańczowy"]


def test_exploration_ui_can_cancel_location_preview():
    session = _session()
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    client.post("/api/interaction/finish")
    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "courtyard"

    response = client.post("/api/location/cancel-preview", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"] is None


def test_exploration_ui_reveals_selects_and_resolves_npc_point():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    client.post("/api/travel", json={"zone_id": "courtyard"})

    point_response = client.post("/api/point", json={"point_id": "wounded_scout"})
    assert point_response.status_code == 200
    point_state = point_response.get_json()
    assert point_state["active_point"]["id"] == "wounded_scout"
    assert point_state["active_point"]["npc"]["name"] == "Ranny zwiadowca"
    assert {"label": "Ranny zwiadowca", "value": "odkryty, ranny"} in point_state["scene_status"]

    action_response = client.post("/api/action", json={"text": "Uspokajamy zwiadowcę."})
    assert action_response.status_code == 200
    assert action_response.get_json()["pending"]["kind"] == "npc"

    accepted = client.post("/api/decision", json={"decision": "accept"}).get_json()
    assert {"key": "scout_calmed", "value": True} in accepted["flags"]
    assert {"label": "Ranny zwiadowca", "value": "uspokojony"} in accepted["scene_status"]


def test_exploration_ui_points_are_board_first_and_text_redirects_to_point_led():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    client.post("/api/travel", json={"zone_id": "courtyard"})

    state = client.get("/api/state").get_json()
    wounded = next(point for point in state["current_zone_points"] if point["id"] == "wounded_scout")
    assert wounded["color"] == "fioletowy"
    assert wounded["positions"] == [[8, 8]]

    response = client.post("/api/action", json={"text": "Chcemy zbadać rannego zwiadowcę."})

    assert response.status_code == 200
    data = response.get_json()
    assert data["pending"] is None
    assert "podświetlone na fioletowy" in data["messages"][-1]["body"]


def test_exploration_ui_sets_pending_encounter_after_noise_trigger():
    client = _client()
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    data = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()

    assert data["pending_encounter"]["trigger_id"] == "gate_noise_alarm"
    assert data["pending_encounter"]["encounter_scenario"] == "content/scenarios/multi_actor_skirmish.json"
    assert {"label": "Encounter", "value": "Alarm na dziedzińcu"} in data["scene_status"]


def test_exploration_ui_runs_guided_encounter_setup_after_trigger():
    client = _client()
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})

    setup_started = client.post("/api/encounter/setup/start").get_json()
    setup = setup_started["encounter_setup"]
    assert setup["scenario_id"] == "multi_actor_skirmish"
    assert setup["status"] == "active"
    assert setup["current_step"]["label"] == "Start walki"
    assert setup["step_count"] >= 4

    next_step = client.post("/api/encounter/setup/confirm").get_json()["encounter_setup"]
    assert next_step["current_step"]["label"] == "bohaterów"
    assert next_step["current_step"]["positions"] == [[0, 0], [0, 1]]

    enemy_step = client.post("/api/encounter/setup/confirm").get_json()["encounter_setup"]
    assert enemy_step["current_step"]["label"] == "jawnych przeciwników i NPC"
    assert enemy_step["current_step"]["positions"] == [[1, 0], [1, 1], [1, 2]]

    while True:
        state = client.post("/api/encounter/setup/confirm").get_json()
        setup = state["encounter_setup"]
        if setup["status"] == "completed":
            break

    assert setup["current_step"] is None
    assert any(message["title"] == "Setup zakończony" for message in state["messages"])


def test_exploration_ui_starts_combat_after_setup_and_initiative():
    client = _client()
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    client.post("/api/encounter/setup/start")
    while True:
        setup_state = client.post("/api/encounter/setup/confirm").get_json()
        if setup_state["encounter_setup"]["status"] == "completed":
            break

    initiative_state = client.post("/api/encounter/initiative/start").get_json()
    assert initiative_state["encounter_initiative"]["current_prompt"]["actor_id"] == "hero"

    after_hero = client.post("/api/encounter/initiative/roll", json={"natural_roll": 14}).get_json()
    assert after_hero["encounter_initiative"]["current_prompt"]["actor_id"] == "rogue"

    after_rogue = client.post("/api/encounter/initiative/roll", json={"natural_roll": 10}).get_json()
    initiative = after_rogue["encounter_initiative"]
    combat = after_rogue["combat"]

    assert initiative["status"] == "completed"
    assert [entry["actor_id"] for entry in initiative["order"]] == [
        combat["current_actor"]["id"],
        *[entry["actor_id"] for entry in initiative["order"][1:]],
    ]
    assert combat["status"] == "active"
    assert combat["round_number"] == 1
    assert len(combat["actors"]) == 5
    assert any(message["title"] == "Kolejność inicjatywy" for message in after_rogue["messages"])


def test_exploration_ui_board_scan_selects_travel_zone_and_updates_leds():
    session = _session()
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    app = create_app(session)
    client = app.test_client()

    client.post("/api/action", json={"text": "Wyważamy bramę głośno."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    client.post("/api/interaction/finish")

    assert board.led_calls

    response = client.post("/api/board/scan")
    data = response.get_json()

    assert response.status_code == 200
    assert data["current_zone"]["id"] == "gate"
    assert data["board"]["connected"] is True
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"]["id"] == "courtyard"
    assert "Dziedziniec" in data["board"]["message"]
