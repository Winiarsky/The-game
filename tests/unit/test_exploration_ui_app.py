from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app


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


def _client():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(),
    )
    return create_app(session).test_client()


def test_exploration_ui_state_endpoint_returns_json():
    client = _client()

    response = client.get("/api/state")

    assert response.status_code == 200
    assert response.get_json()["scenario"]["id"] == "abandoned_watchtower"


def test_exploration_ui_state_includes_player_facing_scene_description():
    client = _client()

    response = client.get("/api/state")

    data = response.get_json()
    assert "Zarośnięta" in data["current_zone"]["description"]
    assert "stara drewniana brama" in data["current_zone"]["summary"]
    assert "wspinaczka" in data["active_challenge"]["reasonable_approaches"]
    assert data["active_challenge"]["risk_notes"]


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
    assert data["active_challenge"] is None
    assert data["travel_options"][0]["id"] == "courtyard"


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
    assert response.get_json()["active_challenge"]["current_progress"] == 0


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
