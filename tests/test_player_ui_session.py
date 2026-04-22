import itertools
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import player_ui.app as player_ui_app_module  # noqa: E402


@pytest.fixture()
def ui_client(monkeypatch):
    monkeypatch.setattr(player_ui_app_module, "events_history", [])
    monkeypatch.setattr(player_ui_app_module, "prompts", {})
    monkeypatch.setattr(player_ui_app_module, "subscribers", set())
    monkeypatch.setattr(player_ui_app_module, "event_ids", itertools.count(1))
    monkeypatch.setattr(player_ui_app_module, "prompt_ids", itertools.count(1))
    monkeypatch.setattr(player_ui_app_module, "session_ids", itertools.count(2))
    monkeypatch.setattr(player_ui_app_module, "current_session_id", "ui-session-1")

    with player_ui_app_module.app.test_client() as client:
        yield client


def test_session_reset_rotates_session_and_hides_old_prompts(ui_client):
    create = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Wybierz akcję",
            "kind": "choice",
            "choices": ["Move", "End"],
            "session_id": "ui-session-1",
        },
    )
    assert create.status_code == 200
    prompt_id = create.get_json()["id"]

    reset = ui_client.post("/api/session/reset", json={"reason": "manual"})
    assert reset.status_code == 200
    payload = reset.get_json()
    assert payload["previous_session_id"] == "ui-session-1"
    assert payload["retired_prompts"] == 1
    assert payload["session"]["id"] == "ui-session-2"

    listed = ui_client.get("/api/prompts")
    assert listed.status_code == 200
    listed_payload = listed.get_json()
    assert listed_payload["session"]["id"] == "ui-session-2"
    assert listed_payload["prompts"] == []

    old_prompt = ui_client.get(f"/api/prompts/{prompt_id}")
    assert old_prompt.status_code == 200
    old_payload = old_prompt.get_json()
    assert old_payload["session_id"] == "ui-session-1"
    assert old_payload["status"] == "answered"
    assert old_payload["answer"] == player_ui_app_module.SESSION_RESET_COMMAND

    assert len(player_ui_app_module.events_history) == 1
    assert player_ui_app_module.events_history[0]["type"] == "session_reset"


def test_prompt_api_rejects_stale_session_id(ui_client):
    create = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Stary prompt",
            "kind": "info",
            "session_id": "ui-session-stale",
        },
    )
    assert create.status_code == 409
    payload = create.get_json()
    assert payload["ok"] is False
    assert payload["error"] == "session mismatch"
    assert payload["current_session_id"] == "ui-session-1"


def test_late_response_to_reset_prompt_is_ignored(ui_client):
    create = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Rzut obronny",
            "kind": "roll",
            "session_id": "ui-session-1",
        },
    )
    assert create.status_code == 200
    prompt_id = create.get_json()["id"]

    reset = ui_client.post("/api/session/reset", json={"reason": "manual"})
    assert reset.status_code == 200

    late = ui_client.post(f"/api/prompts/{prompt_id}/response", json={"answer": 17})
    assert late.status_code == 200
    late_payload = late.get_json()
    assert late_payload["ignored"] is True
    assert late_payload["session_id"] == "ui-session-1"
    assert late_payload["answer"] == player_ui_app_module.SESSION_RESET_COMMAND

    fetched = ui_client.get(f"/api/prompts/{prompt_id}")
    assert fetched.status_code == 200
    fetched_payload = fetched.get_json()
    assert fetched_payload["answer"] == player_ui_app_module.SESSION_RESET_COMMAND

    assert len(player_ui_app_module.events_history) == 1
    assert player_ui_app_module.events_history[0]["type"] == "session_reset"


def test_prompt_api_returns_normalized_communication_envelope(ui_client):
    create = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Tura przeciwnika: Bandit Sharpshot",
            "kind": "info",
            "title": "Tura przeciwnika: Bandit Sharpshot",
            "prompt_long": "Przeciwnik rozpoczyna turę.\nAkcje pozostałe: **3**/**3**.",
            "source": "enemy_turn_start",
            "communication": {
                "blocking": True,
                "semantic_type": "required_action",
                "priority": "action",
                "cta": "Enter po przygotowaniu się do obserwacji.",
            },
        },
    )
    assert create.status_code == 200
    prompt_id = create.get_json()["id"]

    fetched = ui_client.get(f"/api/prompts/{prompt_id}")
    assert fetched.status_code == 200
    payload = fetched.get_json()
    comm = payload["communication"]
    assert comm["blocking"] is True
    assert comm["semantic_type"] == "required_action"
    assert comm["priority"] == "action"
    assert comm["body_markdown"].startswith("Przeciwnik rozpoczyna turę.")
    assert comm["cta"] == "Enter po przygotowaniu się do obserwacji."
    assert comm["dedupe_key"]


def test_event_api_returns_normalized_debug_communication(ui_client):
    resp = ui_client.post(
        "/api/events",
        json={
            "type": "log",
            "payload": {
                "message": "Krawędzie: [{'a': [0, 1], 'b': [0, 2]}]",
                "tag": "Debug",
            },
        },
    )
    assert resp.status_code == 200
    event = resp.get_json()["event"]
    comm = event["payload"]["communication"]
    assert comm["priority"] == "debug"
    assert comm["debug_only"] is True
    assert comm["details_markdown"].startswith("Krawędzie:")
