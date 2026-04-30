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
    monkeypatch.setattr(player_ui_app_module, "subscribers", set())
    monkeypatch.setattr(player_ui_app_module, "event_ids", itertools.count(1))
    monkeypatch.setattr(player_ui_app_module, "session_ids", itertools.count(2))
    monkeypatch.setattr(player_ui_app_module, "current_session_id", "ui-session-1")
    prompt_director = player_ui_app_module.PromptDirector(session_id="ui-session-1")
    prompt_director.set_publisher(player_ui_app_module._publish)
    monkeypatch.setattr(player_ui_app_module, "prompt_director", prompt_director)
    monkeypatch.setattr(
        player_ui_app_module,
        "runtime_state",
        {
            "process": None,
            "state": "idle",
            "scenario_id": None,
            "hero_ids": [],
            "session_id": "ui-session-1",
            "started_at": None,
            "stopped_at": None,
            "returncode": None,
            "command": [],
            "base_url": None,
            "error": None,
            "board_backend": None,
            "board_url": None,
        },
    )

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
            "prompt_id": "enemy.turn.start",
        },
    )
    assert create.status_code == 200
    prompt_id = create.get_json()["id"]
    assert create.get_json()["prompt_key"] == "enemy.turn.start"

    fetched = ui_client.get(f"/api/prompts/{prompt_id}")
    assert fetched.status_code == 200
    payload = fetched.get_json()
    assert payload["prompt_key"] == "enemy.turn.start"
    comm = payload["communication"]
    assert comm["blocking"] is True
    assert comm["semantic_type"] == "required_action"
    assert comm["priority"] == "action"
    assert comm["body_markdown"].startswith("Przeciwnik rozpoczyna turę.")
    assert comm["cta"] == "Enter po przygotowaniu się do obserwacji."
    assert comm["dedupe_key"]
    assert comm["context"]["prompt_key"] == "enemy.turn.start"


def test_catalog_exposes_bandit_cave_asset_manifest_and_audio_cues(ui_client):
    response = ui_client.get("/api/catalog")

    assert response.status_code == 200
    scenario = response.get_json()["catalog"]["scenarios"][0]
    assert scenario["id"] == "bandit_cave"
    assert scenario["asset_manifest"] == "/assets/ui_v2/bandit_cave/manifest.json"
    assert scenario["audio_cues"]["briefing_intro"]["kind"] == "voiceover"
    dog_hint = scenario["audio_cues"]["hint_dog_barking"]["audio"]
    assert dog_hint.endswith("hint_dog_barking_001.mp3")
    assert ui_client.get(dog_hint).status_code == 200


def test_asset_route_serves_manifest_and_draft_svg(ui_client):
    manifest = ui_client.get("/assets/ui_v2/bandit_cave/manifest.json")
    assert manifest.status_code == 200
    payload = manifest.get_json()
    assert payload["scenario_id"] == "bandit_cave"
    assert payload["spells"]["acid_splash"]["image"].endswith("acid_splash.svg")

    image = ui_client.get("/assets/ui_v2/bandit_cave/images/spells/acid_splash.svg")
    assert image.status_code == 200
    assert image.data.startswith(b"<svg")


def test_choice_meta_can_carry_image_and_spell_asset_hints(ui_client):
    create = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Wybierz czar",
            "kind": "choice",
            "choices": ["Acid Splash"],
            "session_id": "ui-session-1",
            "choice_meta": [
                {
                    "raw": "acid_splash",
                    "label": "Acid Splash",
                    "spell_id": "acid_splash",
                    "spell_tier": "cantrip",
                    "image": "/assets/ui_v2/bandit_cave/images/spells/acid_splash.svg",
                }
            ],
        },
    )
    assert create.status_code == 200
    prompt_id = create.get_json()["id"]

    fetched = ui_client.get(f"/api/prompts/{prompt_id}")
    assert fetched.status_code == 200
    meta = fetched.get_json()["choice_meta"][0]
    assert meta["spell_id"] == "acid_splash"
    assert meta["spell_tier"] == "cantrip"
    assert meta["image"].endswith("acid_splash.svg")


def test_player_card_and_ack_prompt_expose_prompt_key(ui_client):
    response = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "title": "Setup bohaterów",
                "summary": "Co robić teraz",
                "body_markdown": "Ustaw figurkę Cedrica.",
                "prompt_id": "setup.hero_setup_place_figure",
            },
        },
    )
    assert response.status_code == 200

    view_state = ui_client.get("/api/view-state").get_json()["view_state"]
    assert view_state["active_prompt"]["prompt_key"] == "setup.hero_setup_place_figure"
    assert view_state["journal"][0]["prompt_key"] == "setup.hero_setup_place_figure"


def test_debug_player_card_does_not_create_hidden_ack_prompt(ui_client):
    created = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Setup encounteru",
            "kind": "info",
            "title": "Setup encounteru",
            "prompt_long": "Przygotuj obszar mapy: Bandit Cave.",
            "source": "encounter_setup",
            "scope_key": "setup",
            "dedupe_key": "setup:1/7",
            "session_id": "ui-session-1",
        },
    )
    assert created.status_code == 200
    first_prompt_id = created.get_json()["id"]

    answered = ui_client.post(f"/api/prompts/{first_prompt_id}/answer", json={"answer": "ok"})
    assert answered.status_code == 200

    debug_card = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "kind": "debug",
                "title": "Krawędzie setupu",
                "body_markdown": "Dane techniczne ścian dostępne w szczegółach.",
                "details_markdown": "Krawędzie: ...",
                "priority": "debug",
                "scope_key": "setup",
                "dedupe_key": "setup_edges:2",
            },
        },
    )
    assert debug_card.status_code == 200

    interim = ui_client.get("/api/view-state").get_json()["view_state"]
    assert interim["active_prompt"] is None
    assert interim["debug_feed"][0]["title"] == "Krawędzie setupu"

    next_prompt = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Setup encounteru",
            "kind": "info",
            "title": "Setup encounteru",
            "prompt_long": "Ustaw ściany zgodnie z podświetlonymi krawędziami i potwierdź w UI.",
            "source": "encounter_setup",
            "scope_key": "setup",
            "dedupe_key": "setup:2/7",
            "session_id": "ui-session-1",
        },
    )
    assert next_prompt.status_code == 200
    assert next_prompt.get_json()["id"] == "2"


def test_view_state_separates_active_prompt_from_journal_cards(ui_client):
    created = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Wybierz akcję",
            "kind": "choice",
            "choices": ["Move", "End"],
            "source": "intent_menu",
            "scope_key": "hero_turn:intent",
            "session_id": "ui-session-1",
        },
    )
    assert created.status_code == 200

    card_event = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "kind": "result",
                "title": "Wynik akcji",
                "body_markdown": "Bohater przygotowuje się do ruchu.",
                "scope_key": "hero_turn:resolution",
            },
        },
    )
    assert card_event.status_code == 200

    response = ui_client.get("/api/view-state")
    assert response.status_code == 200
    payload = response.get_json()["view_state"]
    assert payload["active_prompt"]["title"] == "Wybierz akcję"
    assert payload["active_prompt"]["scope_key"] == "hero_turn:intent"
    assert payload["focus_card"]["title"] == "Wynik akcji"
    assert payload["focus_card"]["kind"] == "result"
    assert payload["journal"][0]["title"] == "Wynik akcji"


def test_prompt_supersedes_previous_prompt_in_same_scope(ui_client):
    first = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Pierwszy prompt",
            "kind": "info",
            "source": "setup",
            "scope_key": "setup",
            "session_id": "ui-session-1",
        },
    )
    assert first.status_code == 200
    first_id = first.get_json()["id"]

    second = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Drugi prompt",
            "kind": "info",
            "source": "setup",
            "scope_key": "setup",
            "session_id": "ui-session-1",
        },
    )
    assert second.status_code == 200
    second_id = second.get_json()["id"]

    first_payload = ui_client.get(f"/api/prompts/{first_id}").get_json()
    second_payload = ui_client.get(f"/api/prompts/{second_id}").get_json()
    view_state = ui_client.get("/api/view-state").get_json()["view_state"]

    assert first_payload["status"] == "superseded"
    assert second_payload["status"] == "pending"
    assert second_payload["replaces_prompt_id"] == first_id
    assert view_state["active_prompt"]["id"] == second_id


def test_journal_endpoint_returns_incremental_cards(ui_client):
    first = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "kind": "narration",
                "title": "Start",
                "body_markdown": "Rozpoczyna się tura.",
            },
        },
    )
    second = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "kind": "result",
                "title": "Wynik",
                "body_markdown": "Rzut zakończony sukcesem.",
            },
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    snapshot = ui_client.get("/api/view-state").get_json()["view_state"]
    older_seq = snapshot["journal"][-1]["seq"]

    journal = ui_client.get(f"/api/journal?after={older_seq}")
    assert journal.status_code == 200
    payload = journal.get_json()
    assert [entry["title"] for entry in payload["journal"]] == ["Wynik"]


def test_cards_require_enter_before_next_transition(ui_client):
    first = ui_client.post(
        "/api/events",
        json={
            "type": "narration",
            "session_id": "ui-session-1",
            "payload": {
                "message": "Krok pierwszy.",
                "source": "scenario_flow",
            },
        },
    )
    second = ui_client.post(
        "/api/events",
        json={
            "type": "narration",
            "session_id": "ui-session-1",
            "payload": {
                "message": "Krok drugi.",
                "source": "scenario_flow",
            },
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    initial_view = ui_client.get("/api/view-state").get_json()["view_state"]
    first_prompt = initial_view["active_prompt"]
    assert first_prompt["body_markdown"] == "Krok pierwszy."
    assert first_prompt["input_mode"] == "confirm"
    assert first_prompt["communication"]["cta"] == "Enter, aby przejść do kolejnego kroku."

    answered = ui_client.post(f"/api/prompts/{first_prompt['id']}/answer", json={"answer": "ok"})
    assert answered.status_code == 200

    next_view = ui_client.get("/api/view-state").get_json()["view_state"]
    assert next_view["active_prompt"]["body_markdown"] == "Krok drugi."


def test_plain_logs_do_not_create_player_facing_prompt(ui_client):
    logged = ui_client.post(
        "/api/events",
        json={
            "type": "log",
            "session_id": "ui-session-1",
            "payload": {
                "message": "Techniczny log bez semantyki promptu.",
            },
        },
    )
    assert logged.status_code == 200

    view_state = ui_client.get("/api/view-state").get_json()["view_state"]
    assert view_state["active_prompt"] is None
    assert view_state["journal"] == []


def test_player_card_can_opt_out_of_ack_prompt(ui_client):
    posted = ui_client.post(
        "/api/events",
        json={
            "type": "player_card",
            "session_id": "ui-session-1",
            "payload": {
                "kind": "narration",
                "title": "Krótki status",
                "body_markdown": "Drużyna czeka przy wejściu.",
                "communication": {
                    "ack_required": False,
                    "pause_policy": "passive",
                },
            },
        },
    )
    assert posted.status_code == 200

    view_state = ui_client.get("/api/view-state").get_json()["view_state"]
    assert view_state["active_prompt"] is None
    assert view_state["journal"][0]["title"] == "Krótki status"
    assert view_state["journal"][0]["communication"]["ack_required"] is False
    assert view_state["journal"][0]["communication"]["pause_policy"] == "passive"


def test_duplicate_consecutive_cards_are_deduplicated(ui_client):
    first = ui_client.post(
        "/api/events",
        json={
            "type": "narration",
            "session_id": "ui-session-1",
            "payload": {
                "message": "Ten sam krok.",
                "source": "scenario_flow",
            },
        },
    )
    second = ui_client.post(
        "/api/events",
        json={
            "type": "narration",
            "session_id": "ui-session-1",
            "payload": {
                "message": "Ten sam krok.",
                "source": "scenario_flow",
            },
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    view_state = ui_client.get("/api/view-state").get_json()["view_state"]
    assert len(view_state["journal"]) == 1
    assert view_state["active_prompt"]["body_markdown"] == "Ten sam krok."

    prompt_id = view_state["active_prompt"]["id"]
    answered = ui_client.post(f"/api/prompts/{prompt_id}/answer", json={"answer": "ok"})
    assert answered.status_code == 200

    after = ui_client.get("/api/view-state").get_json()["view_state"]
    assert after["active_prompt"] is None


def test_duplicate_api_prompts_are_deduplicated(ui_client):
    first = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Atak dystansowy: analiza strzału",
            "kind": "choice",
            "title": "Atak dystansowy: analiza strzału",
            "prompt_long": "Cel: Wróg\nMożesz potwierdzić strzał albo wrócić do wyboru celu.",
            "choices": ["Potwierdź strzał", "Wybierz inny cel"],
            "source": "attack_ranged_analysis",
            "scope_key": "hero_turn:targeting",
            "dedupe_key": "attack_ranged_analysis:Atak dystansowy: analiza strzału",
            "session_id": "ui-session-1",
        },
    )
    second = ui_client.post(
        "/api/prompts",
        json={
            "prompt": "Atak dystansowy: analiza strzału",
            "kind": "choice",
            "title": "Atak dystansowy: analiza strzału",
            "prompt_long": "Cel: Wróg\nMożesz potwierdzić strzał albo wrócić do wyboru celu.",
            "choices": ["Potwierdź strzał", "Wybierz inny cel"],
            "source": "attack_ranged_analysis",
            "scope_key": "hero_turn:targeting",
            "dedupe_key": "attack_ranged_analysis:Atak dystansowy: analiza strzału",
            "session_id": "ui-session-1",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    first_id = first.get_json()["id"]
    second_id = second.get_json()["id"]
    prompts = ui_client.get("/api/prompts").get_json()["prompts"]

    assert first_id == second_id
    assert len(prompts) == 1


def test_catalog_returns_bandit_cave_and_hero_cards(ui_client):
    response = ui_client.get("/api/catalog")
    assert response.status_code == 200
    payload = response.get_json()
    catalog = payload["catalog"]
    assert catalog["heroes"]
    assert catalog["scenarios"]
    scenario = catalog["scenarios"][0]
    assert scenario["id"] == "bandit_cave"
    assert scenario["primary_objectives"]
    first_hero = catalog["heroes"][0]
    assert first_hero["id"]
    assert first_hero["portrait"]
    assert "summary" in first_hero
