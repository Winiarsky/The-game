from dataclasses import replace
from unittest.mock import Mock

from dnd_board_game.combat import set_scene_flag
from dnd_board_game.actors import ActorId
from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType, NpcInteractionProposal
from dnd_board_game.exploration import PartyPosition, reveal_exploration_points
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
                "request_risk": "no_risk",
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
        session.active_paper_map_id = "watchtower_overview"
    return session


def _submit_force_gate(
    client,
    text: str = "Wyważamy bramę.",
    *,
    check_participants: str | None = None,
    actor_ids: tuple[str, ...] = (),
):
    payload: dict[str, object] = {
        "text": text,
        "selected_goal_id": "force_entry",
    }
    if check_participants is not None:
        payload["check_participants"] = check_participants
    if actor_ids:
        payload["participant_actor_ids"] = list(actor_ids)
    return client.post(
        "/api/action",
        json=payload,
    )


def _page_assets(client) -> tuple[str, str, str]:
    html = client.get("/play").get_data(as_text=True)
    javascript = client.get("/static/exploration.js").get_data(as_text=True)
    stylesheet = client.get("/static/exploration.css").get_data(as_text=True)
    return html, javascript, stylesheet


def test_physical_control_card_scan_route_resolves_accept_and_decline() -> None:
    session = _session()
    client = create_app(session).test_client()

    accept = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:universal:accept"},
    )
    decline = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:universal:decline"},
    )

    assert accept.status_code == 200
    assert accept.get_json() == {
        "action": "accept",
        "applied": False,
        "label": "AKCEPTUJ",
        "payload": "dndbg:v1:action:universal:accept",
    }
    assert decline.status_code == 200
    assert decline.get_json()["action"] == "decline"
    card_events = [
        event
        for event in client.get("/api/session-log").get_json()["events"]
        if event["event_type"] == "ui_physical_card_declared"
    ]
    assert [event["payload"]["action"] for event in card_events] == [
        "accept",
        "decline",
    ]
    assert card_events[0]["payload"]["flow_stage"] == "location_active"


def test_exploration_action_cards_are_disabled_without_removing_combat_cards() -> None:
    session = _session()
    first, *remaining = session.exploration.actors
    session.exploration = replace(
        session.exploration,
        actors=(replace(first, id=ActorId("garran")), *remaining),
    )
    session.selected_lead_actor_id = "garran"
    client = create_app(session).test_client()

    declared = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg:v2:action:feature:tactical_assessment:garran",
        },
    )

    assert declared.status_code == 400
    payload = declared.get_json()
    assert "Karty eksploracji są obecnie wyłączone" in payload["error"]
    assert payload["state"]["exploration_card"]["enabled"] is False


def test_character_interaction_tile_is_party_gated_and_auto_assigns_actor() -> None:
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        gm_client=FakeGmClient(),
        npc_client=FakeNpcClient(),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.active_paper_map_id = "village_overview"
    first, second, *remaining = session.exploration.actors
    session.exploration = replace(
        session.exploration,
        actors=(
            replace(first, id=ActorId("brakka"), name="Brakka"),
            replace(second, id=ActorId("garran"), name="Garran"),
            *remaining,
        ),
    )
    session.selected_lead_actor_id = "brakka"
    session.travel_to("elder_house")

    options = {
        option["id"]: option
        for option in session.state_payload()["flow"]["zone_options"]
    }
    assert "brakka_bren_hard_truth" in options
    assert "mira_market_pickpocket_child" not in options
    brakka_tile = options["brakka_bren_hard_truth"]
    assert brakka_tile["character_moment"] is True
    assert brakka_tile["assigned_actor"] == {
        "id": "brakka",
        "name": "Brakka",
        "portrait": first.portrait,
    }

    pending = session.select_exploration_option(
        "brakka_bren_hard_truth",
        player_description="Brakka żąda od Brena szczerej odpowiedzi.",
    )
    assert pending["pending"]["check_plan"]["lead_actor_id"] == "brakka"

    resolved = session.resolve_rolls({"brakka": 20})
    flags = {item["key"]: item["value"] for item in resolved["flags"]}
    assert flags["brakka_bren_hard_truth_success"] is True


def test_every_mvp_character_moment_is_visible_only_for_its_assigned_hero() -> None:
    expected = {
        "content/scenarios/village_square_mvp.json": {
            "garran": ("tavern", "garran_wounded_soldiers"),
            "brakka": ("elder_house", "brakka_bren_hard_truth"),
            "mira": ("market", "mira_market_pickpocket_child"),
            "dagna": ("tavern", "dagna_injured_caravaner"),
            "lorian": ("tavern", "lorian_soldiers_song"),
            "nimra": ("elder_house", "nimra_map_arcane_correction"),
            "erynd": ("forest_road", "erynd_old_patrol_sign"),
        },
        "content/scenarios/abandoned_watchtower.json": {
            "garran": ("gate", "garran_gate_last_stand"),
            "brakka": ("barracks", "brakka_broken_manacles"),
            "mira": ("barracks", "mira_smugglers_mark"),
            "dagna": ("courtyard", "dagna_abandoned_wounded_signs"),
            "lorian": ("tower", "lorian_unfinished_watch_song"),
            "nimra": ("barracks", "nimra_arcane_burn"),
            "erynd": ("courtyard", "erynd_reconstructs_ambush"),
        },
    }

    for scenario_path, actor_moments in expected.items():
        session = ExplorationUiSession(scenario_path)
        original = session.exploration.actors
        for actor_id, (zone_id, option_id) in actor_moments.items():
            session.exploration = replace(
                session.exploration,
                actors=(
                    replace(original[0], id=ActorId(actor_id), name=actor_id.title()),
                    *original[1:],
                ),
            )
            session.state = replace(
                session.state,
                party_position=PartyPosition(zone_id),
            )
            options = session.state_payload()["flow"]["zone_options"]
            visible_moments = {
                option["id"]: option
                for option in options
                if option["character_moment"]
            }

            assert option_id in visible_moments
            assert {
                option["assigned_actor_id"] for option in visible_moments.values()
            } == {actor_id}


def test_player_ui_marks_character_moments_and_fixed_performer() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.exploration = replace(
        session.exploration,
        actors=(
            replace(session.exploration.actors[0], id=ActorId("mira"), name="Mira"),
            *session.exploration.actors[1:],
        ),
    )
    client = create_app(session).test_client()
    _html, javascript, _stylesheet = _page_assets(client)

    assert "character-moment-card" in javascript
    assert "Indywidualna interakcja" in javascript
    assert "automatyczny wykonawca" in javascript
    assert "selectedOption && selectedOption.assigned_actor_id" in javascript
    state = client.get("/api/state").get_json()
    moment = next(
        option
        for option in state["flow"]["zone_options"]
        if option["id"] == "mira_market_pickpocket_child"
    )
    assert moment["performer_mode"] == "fixed"


def test_location_selection_uses_image_tiles_with_board_color_frames() -> None:
    _html, javascript, stylesheet = _page_assets(_client())

    assert 'class="available-location-grid"' in javascript
    assert 'class="available-location-thumbnail"' in javascript
    assert "zone.image_url" in javascript
    assert "zone.color_rgb" in javascript
    assert "--location-frame-color" in javascript
    assert ".available-location-thumbnail" in stylesheet
    assert "border: 5px solid var(--location-frame-color" in stylesheet
    assert "Kliknij ponownie pole tej lokacji" in javascript
    assert "explorationNavigationCardBlocked" in javascript
    assert "&& !continuationPanelOpen" in javascript
    assert "system-exit-card" in javascript
    assert ".interaction-goal-card.system-exit-card" in stylesheet


def test_all_fourteen_character_moments_resolve_with_the_fixed_performer() -> None:
    cases = {
        "content/scenarios/village_square_mvp.json": (
            ("garran", "tavern", "garran_wounded_soldiers"),
            ("brakka", "elder_house", "brakka_bren_hard_truth"),
            ("mira", "market", "mira_market_pickpocket_child"),
            ("dagna", "tavern", "dagna_injured_caravaner"),
            ("lorian", "tavern", "lorian_soldiers_song"),
            ("nimra", "elder_house", "nimra_map_arcane_correction"),
            ("erynd", "forest_road", "erynd_old_patrol_sign"),
        ),
        "content/scenarios/abandoned_watchtower.json": (
            ("garran", "gate", "garran_gate_last_stand"),
            ("brakka", "barracks", "brakka_broken_manacles"),
            ("mira", "barracks", "mira_smugglers_mark"),
            ("dagna", "courtyard", "dagna_abandoned_wounded_signs"),
            ("lorian", "tower", "lorian_unfinished_watch_song"),
            ("nimra", "barracks", "nimra_arcane_burn"),
            ("erynd", "courtyard", "erynd_reconstructs_ambush"),
        ),
    }

    for scenario_path, scenario_cases in cases.items():
        for actor_id, zone_id, option_id in scenario_cases:
            session = ExplorationUiSession(scenario_path)
            session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
            first, *remaining = session.exploration.actors
            session.exploration = replace(
                session.exploration,
                actors=(
                    replace(first, id=ActorId(actor_id), name=actor_id.title()),
                    *remaining,
                ),
            )
            session.state = replace(
                session.state,
                party_position=PartyPosition(zone_id),
            )
            option = next(
                item
                for item in session.current_zone.options
                if item.id == option_id
            )

            pending = session.select_exploration_option(
                option_id,
                player_description="Bohater reaguje zgodnie ze swoją historią.",
            )
            assert pending["pending"]["check_plan"]["lead_actor_id"] == actor_id

            resolved = session.resolve_rolls({actor_id: 20})
            flags = {item["key"]: item["value"] for item in resolved["flags"]}
            assert option.success_flag is not None
            assert flags[option.success_flag] is True


def test_mvp_and_arena_instances_fit_seven_actions_plus_system_exit() -> None:
    hero_ids = ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd")
    scenario_paths = (
        "content/scenarios/village_square_mvp.json",
        "content/scenarios/abandoned_watchtower.json",
        "content/scenarios/mechanics_playground/scenario.json",
    )

    for scenario_path in scenario_paths:
        session = ExplorationUiSession(scenario_path)
        originals = session.exploration.actors
        session.exploration = replace(
            session.exploration,
            actors=tuple(
                replace(
                    originals[index % len(originals)],
                    id=ActorId(actor_id),
                    name=actor_id.title(),
                )
                for index, actor_id in enumerate(hero_ids)
            ),
        )
        session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
        for zone in session.state.zones:
            session.state = replace(
                session.state,
                party_position=PartyPosition(zone.id),
            )
            session.active_point_id = ""
            root_pads = session._board_interaction_pads()
            assert len(root_pads) <= min(8, len(zone.interaction_pad_positions))
            if zone.interaction_pad_positions:
                assert root_pads[-1].action_kind == "exit"
            for point in session.current_zone_points():
                session.active_point_id = point.id
                point_pads = session._board_interaction_pads()
                assert len(point_pads) <= min(8, len(zone.interaction_pad_positions))
                if zone.interaction_pad_positions:
                    assert point_pads[-1].action_kind == "exit"
            session.active_point_id = ""


def test_wrong_owner_cannot_use_personal_exploration_card() -> None:
    response = _client().post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v2:action:feature:intimidation:hero"},
    )

    assert response.status_code == 400
    assert "Karty eksploracji są obecnie wyłączone" in response.get_json()["error"]


def test_accept_card_applies_ready_start_and_instruction_setup_on_server() -> None:
    session = _session(active=False)
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")
    client = create_app(session).test_client()
    payload = {"payload": "dndbg:v1:action:universal:accept"}

    started = client.post("/api/physical-cards/scan", json=payload).get_json()
    assert started["applied"] is True
    assert started["effect"] == "start_session"
    assert started["state"]["flow"]["stage"] == "party_setup"

    setup_index = started["state"]["exploration_setup"]["current_index"]
    confirmed = client.post("/api/physical-cards/scan", json=payload).get_json()
    assert confirmed["applied"] is True
    assert confirmed["effect"] == "confirm_exploration_setup"
    assert confirmed["state"]["exploration_setup"]["current_index"] == setup_index + 1

    resolved_events = [
        event
        for event in client.get("/api/session-log").get_json()["events"]
        if event["event_type"] == "ui_physical_card_resolved"
    ]
    assert [event["payload"]["effect"] for event in resolved_events] == [
        "start_session",
        "confirm_exploration_setup",
    ]


def test_physical_card_route_accepts_keyboard_wedge_separator_translation() -> None:
    response = _client().post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg>v1>action>universal>accept"},
    )

    assert response.status_code == 200
    assert response.get_json()["action"] == "accept"
    assert response.get_json()["payload"] == "dndbg:v1:action:universal:accept"


def test_physical_control_card_scan_route_rejects_other_or_invalid_cards() -> None:
    client = _client()

    spell = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:eldritch_blast"},
    )
    malformed = client.post(
        "/api/physical-cards/scan",
        json={"payload": "not-a-card"},
    )

    assert spell.status_code == 400
    assert "wyłącznie podczas walki" in spell.get_json()["error"]
    assert malformed.status_code == 400


def test_actor_card_selects_performer_for_open_checked_zone_option() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg:v1:actor:rogue",
            "context": {"zone_option_id": "ask_for_rumors"},
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "actor_id": "rogue",
        "applied": False,
        "effect": "select_zone_option_actor",
        "label": "Łotrzyca",
        "payload": "dndbg:v1:actor:rogue",
    }
    events = client.get("/api/session-log").get_json()["events"]
    assert events[-1]["event_type"] == "ui_actor_card_zone_option_declared"
    assert events[-1]["payload"] == {
        "actor_id": "rogue",
        "zone_option_id": "ask_for_rumors",
    }


def test_actor_card_cannot_override_fixed_character_moment_performer() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.exploration = replace(
        session.exploration,
        actors=(
            replace(session.exploration.actors[0], id=ActorId("mira"), name="Mira"),
            *session.exploration.actors[1:],
        ),
    )
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg:v1:actor:rogue",
            "context": {"zone_option_id": "mira_market_pickpocket_child"},
        },
    )

    assert response.status_code == 400
    assert "przypisanego wykonawcę: Mira" in response.get_json()["error"]


def test_actor_card_rejects_zone_option_without_a_performer_check() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg:v1:actor:rogue",
            "context": {"zone_option_id": "read_notice_board"},
        },
    )

    assert response.status_code == 400
    assert "nie oczekuje" in response.get_json()["error"]


def test_spell_card_builds_a_custom_preparation_set_for_current_actor() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.SPELL_PREPARATION
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg:v1:action:spell:healing_word",
            "context": {
                "spell_preparation_mode": "custom",
                "spell_preparation_actor_id": "cleric",
            },
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["applied"] is False
    assert data["effect"] == "select_preparation_spell"
    assert data["actor_id"] == "cleric"
    assert data["spell_id"] == "healing_word"
    assert data["preparation_limit"] == 2
    cleric = next(actor for actor in session.exploration.actors if str(actor.id) == "cleric")
    assert cleric.spell_preparation is not None
    assert cleric.spell_preparation.confirmed is False
    events = client.get("/api/session-log").get_json()["events"]
    assert events[-1]["event_type"] == "ui_spell_preparation_card_declared"


def test_spell_card_requires_declining_default_preparation_first() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.SPELL_PREPARATION
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:healing_word"},
    )

    assert response.status_code == 400
    assert "Najpierw zeskanuj ODRZUĆ" in response.get_json()["error"]


def test_actor_card_selects_navigator_for_open_continuation_step() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "ready_for_watchtower", True),
    )
    session.travel_to("forest_road")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    client = create_app(session).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": "dndbg>v1>actor>hero",
            "context": {"continuation_stage": "navigator"},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["applied"] is False
    assert data["effect"] == "select_continuation_navigator"
    assert data["actor_id"] == "hero"
    assert data["navigation_dc"] == 12
    assert data["navigation_ability"] == "wisdom"
    assert data["navigation_skill"] == "survival"
    prompt = session._active_exploration_prompt()
    assert prompt.kind.value == "before_roll"
    assert prompt.interaction_id == "scenario_continuation"
    assert {"travel", "navigation", "survival"} <= set(prompt.tags)
    events = client.get("/api/session-log").get_json()["events"]
    assert events[-1]["event_type"] == "ui_continuation_navigator_declared"


def test_player_page_wires_hid_card_scans_to_primary_and_secondary_actions() -> None:
    html, javascript, stylesheet = _page_assets(_client())

    assert 'id="physical-card-status"' in html
    assert "const PHYSICAL_CARD_PREFIX = 'dndbg:';" in javascript
    assert "const PHYSICAL_CARD_RECENT_KEY_GAP_MS = 2000;" in javascript
    assert "|actor:[a-z][a-z0-9_]*" in javascript
    assert "(?::[a-z][a-z0-9_]*)?" in javascript
    assert "function normalizePhysicalCardScannerText(value)" in javascript
    assert "normalized.replaceAll('?', '_')" in javascript
    assert "data.effect === 'select_preparation_spell'" in javascript
    assert "data.effect === 'select_continuation_navigator'" in javascript
    assert "scanContext.continuation_stage = 'navigator'" in javascript
    assert "startCustomSpellPreparation()" in javascript
    assert "data-preparation-spell" not in javascript
    assert ".spell-preparation-card-tile" in stylesheet
    assert "data.feedback && data.feedback.message" in javascript
    assert "preserve-life-allocation" in javascript
    assert "option.trigger_event === 'damage_roll_revealed'" in javascript
    assert "normalized.replaceAll('>', ':')" in javascript
    assert "function physicalCardPayloadFromRecentKeys()" in javascript
    assert "const recentPayload = physicalCardPayloadFromRecentKeys();" in javascript
    assert "function acceptsEnterAsUniversalCard()" not in javascript
    assert "PHYSICAL_CARD_ACCEPT_PAYLOAD" not in javascript
    assert "lastPhysicalCardScanAt = Date.now();" in javascript
    assert "fetch('/api/physical-cards/scan'" in javascript
    assert "if (data.applied && data.state)" in javascript
    assert "const scanContext = selectedZoneOptionId" in javascript
    assert "data.effect === 'select_zone_option_actor'" in javascript
    assert "triggerPrimaryAction()" in javascript
    assert "triggerSecondaryAction()" in javascript
    assert "if (selectedZoneOptionId) { submitZoneOption(); return true; }" in javascript
    assert "if (selectedInteractionGoalId) { sendGoalAction(); return true; }" in javascript
    assert "boardInteraction.mode === 'navigation'" in javascript
    assert "scheduleAutomaticGoalAdvance" not in javascript
    assert "latestResultMessageSince(state, previousMessageCount)" in javascript
    assert "i >= firstNewMessage" in javascript
    assert "document.addEventListener('keydown', consumePhysicalCardKey, {capture: true})" in javascript
    assert ".physical-card-status" in stylesheet


def test_accept_prioritizes_start_and_setup_confirmation_over_optional_board_scan() -> None:
    _, javascript, _ = _page_assets(_client())
    primary_start = javascript.index("function triggerPrimaryAction()")
    primary_end = javascript.index("function cancelCurrentCombatStep()", primary_start)
    primary_action = javascript[primary_start:primary_end]

    assert primary_action.index("if (isVisible('flow-panel'))") < primary_action.index(
        "const scanButton = visiblePrimaryScanButton();"
    )
    assert "if (stage === 'ready_to_start') { startSession(); return true; }" in primary_action
    assert (
        "if (step.requires_board_assignment) scanBoard();\n"
        "      else confirmExplorationSetup();"
    ) in primary_action


def test_accept_uses_the_only_visible_forward_button_including_enemy_intent() -> None:
    _, javascript, _ = _page_assets(_client())
    primary_start = javascript.index("function triggerPrimaryAction()")
    primary_end = javascript.index("function cancelCurrentCombatStep()", primary_start)
    primary_action = javascript[primary_start:primary_end]

    assert "function visibleSingleAcceptButton()" in javascript
    assert "return candidates.length === 1 ? candidates[0] : null;" in javascript
    assert "data-card-action=\"accept\" onclick=\"resolveEnemyTurn()\"" in javascript
    assert primary_action.index("singleAcceptButton.click()") < primary_action.index(
        "if (combat.enemy_turn_preview) return false;"
    )


def test_combat_context_menu_confirm_route_forwards_loot_quantity() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def confirm(option_id: str = "", *, quantity: int | None = None):
        captured["option_id"] = option_id
        captured["quantity"] = quantity
        return session.state_payload()

    session.confirm_combat_context_menu = confirm
    client = create_app(session).test_client()

    response = client.post(
        "/api/combat/context-menu/confirm",
        json={"option_id": "loot-item:goblin:bolts", "quantity": 3},
    )

    assert response.status_code == 200
    assert captured == {
        "option_id": "loot-item:goblin:bolts",
        "quantity": 3,
    }

    invalid = client.post(
        "/api/combat/context-menu/confirm",
        json={"option_id": "loot-item:goblin:bolts", "quantity": 1.5},
    )
    assert invalid.status_code == 400
    assert "całkowitą" in invalid.get_json()["error"]


def test_combat_aura_preview_route_forwards_selected_effect_id() -> None:
    session = _session()
    session.set_combat_aura_preview = Mock(return_value=session.state_payload())
    client = create_app(session).test_client()

    response = client.post(
        "/api/combat/aura-preview",
        json={"aura_id": "bless-aura:dagna"},
    )

    assert response.status_code == 200
    session.set_combat_aura_preview.assert_called_once_with("bless-aura:dagna")


def test_concentration_routes_forward_cast_level_and_multiple_targets() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def start(action_id: str, cast_level: int | None = None):
        captured["action_id"] = action_id
        captured["cast_level"] = cast_level
        return session.state_payload()

    def confirm(
        *,
        target_id: str | None = None,
        target_ids: tuple[str, ...] = (),
    ):
        captured["target_id"] = target_id
        captured["target_ids"] = target_ids
        return session.state_payload()

    session.start_combat_concentration_action = start
    session.confirm_combat_concentration_action = confirm
    client = create_app(session).test_client()

    started = client.post(
        "/api/combat/concentration/start",
        json={"action_id": "bless_attack_bonus", "cast_level": 2},
    )
    confirmed = client.post(
        "/api/combat/concentration/confirm",
        json={"target_ids": ["cleric", "hero", "rogue"]},
    )

    assert started.status_code == 200
    assert confirmed.status_code == 200
    assert captured == {
        "action_id": "bless_attack_bonus",
        "cast_level": 2,
        "target_id": None,
        "target_ids": ("cleric", "hero", "rogue"),
    }


def test_summon_routes_forward_cast_level_and_position() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def start(action_id: str, cast_level: int | None = None):
        captured["action_id"] = action_id
        captured["cast_level"] = cast_level
        return session.state_payload()

    def confirm(*, col: int, row: int):
        captured["col"] = col
        captured["row"] = row
        return session.state_payload()

    session.start_summon = start
    session.confirm_summon = confirm
    client = create_app(session).test_client()

    started = client.post(
        "/api/combat/summon/start",
        json={"action_id": "call_guardian_spirit", "cast_level": 1},
    )
    confirmed = client.post(
        "/api/combat/summon/confirm",
        json={"col": 4, "row": 7},
    )

    assert started.status_code == 200
    assert confirmed.status_code == 200
    assert captured == {
        "action_id": "call_guardian_spirit",
        "cast_level": 1,
        "col": 4,
        "row": 7,
    }


def test_magic_movement_routes_forward_cast_level_and_target() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def start(action_id: str, cast_level: int | None = None):
        captured["action_id"] = action_id
        captured["cast_level"] = cast_level
        return session.state_payload()

    def confirm(
        *,
        col: int | None = None,
        row: int | None = None,
        target_id: str | None = None,
    ):
        captured["col"] = col
        captured["row"] = row
        captured["target_id"] = target_id
        return session.state_payload()

    session.start_magic_movement = start
    session.confirm_magic_movement = confirm
    client = create_app(session).test_client()

    started = client.post(
        "/api/combat/magic-movement/start",
        json={"action_id": "repelling_pulse", "cast_level": 1},
    )
    confirmed = client.post(
        "/api/combat/magic-movement/confirm",
        json={"target_id": "goblin_a"},
    )

    assert started.status_code == 200
    assert confirmed.status_code == 200
    assert captured == {
        "action_id": "repelling_pulse",
        "cast_level": 1,
        "col": None,
        "row": None,
        "target_id": "goblin_a",
    }


def test_spell_debuff_routes_forward_cast_level_and_target() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def start(action_id: str, cast_level: int | None = None):
        captured["action_id"] = action_id
        captured["cast_level"] = cast_level
        return session.state_payload()

    def confirm(*, target_id: str):
        captured["target_id"] = target_id
        return session.state_payload()

    session.start_spell_debuff = start
    session.confirm_spell_debuff = confirm
    client = create_app(session).test_client()

    started = client.post(
        "/api/combat/spell-debuff/start",
        json={"action_id": "weakening_miasma", "cast_level": 1},
    )
    confirmed = client.post(
        "/api/combat/spell-debuff/confirm",
        json={"target_id": "goblin_a"},
    )

    assert started.status_code == 200
    assert confirmed.status_code == 200
    assert captured == {
        "action_id": "weakening_miasma",
        "cast_level": 1,
        "target_id": "goblin_a",
    }


def test_spell_dispel_routes_forward_cast_level_target_and_check() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def start(action_id: str, cast_level: int | None = None):
        captured["action_id"] = action_id
        captured["cast_level"] = cast_level
        return session.state_payload()

    def confirm(*, target_id: str):
        captured["target_id"] = target_id
        return session.state_payload()

    def check(*, natural_roll: int):
        captured["natural_roll"] = natural_roll
        return session.state_payload()

    session.start_spell_dispel = start
    session.confirm_spell_dispel = confirm
    session.resolve_spell_dispel_check = check
    client = create_app(session).test_client()

    started = client.post(
        "/api/combat/spell-dispel/start",
        json={"action_id": "unravel_magic", "cast_level": 1},
    )
    confirmed = client.post(
        "/api/combat/spell-dispel/confirm",
        json={"target_id": "goblin_a"},
    )
    checked = client.post(
        "/api/combat/spell-dispel/check",
        json={"natural_roll": 17},
    )

    assert started.status_code == 200
    assert confirmed.status_code == 200
    assert checked.status_code == 200
    assert captured == {
        "action_id": "unravel_magic",
        "cast_level": 1,
        "target_id": "goblin_a",
        "natural_roll": 17,
    }


def test_trade_routes_forward_validated_transaction_payloads() -> None:
    session = _session()
    captured: list[tuple[str, dict[str, object]]] = []

    def buy(**payload):
        captured.append(("buy", payload))
        return session.state_payload()

    def sell(**payload):
        captured.append(("sell", payload))
        return session.state_payload()

    session.buy_merchant_item = buy
    session.sell_merchant_item = sell
    client = create_app(session).test_client()
    payload = {
        "merchant_id": "mira",
        "actor_id": "hero",
        "item_id": "crossbow_bolt",
        "quantity": 6,
    }

    assert client.post("/api/trade/buy", json=payload).status_code == 200
    assert client.post("/api/trade/sell", json=payload).status_code == 200
    assert captured == [
        ("buy", payload),
        ("sell", payload),
    ]

    invalid = client.post(
        "/api/trade/buy",
        json={**payload, "quantity": 1.5},
    )
    assert invalid.status_code == 400
    assert "całkowitą" in invalid.get_json()["error"]


def test_downtime_crafting_route_forwards_actor_and_recipe() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def complete(**payload):
        captured.update(payload)
        return session.state_payload()

    session.complete_downtime_crafting = complete
    response = create_app(session).test_client().post(
        "/api/downtime/crafting/complete",
        json={"actor_id": "hero", "recipe_id": "forge_dagger"},
    )

    assert response.status_code == 200
    assert captured == {
        "actor_id": "hero",
        "recipe_id": "forge_dagger",
    }


def test_armor_route_requires_boolean_equip_and_forwards_payload() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def change(**payload):
        captured.update(payload)
        return session.state_payload()

    session.change_actor_armor = change
    client = create_app(session).test_client()

    response = client.post(
        "/api/equipment/armor",
        json={"actor_id": "hero", "armor_id": "chain_mail", "equip": True},
    )

    assert response.status_code == 200
    assert captured == {
        "actor_id": "hero",
        "armor_id": "chain_mail",
        "equip": True,
    }
    invalid = client.post(
        "/api/equipment/armor",
        json={"actor_id": "hero", "armor_id": "chain_mail", "equip": "yes"},
    )
    assert invalid.status_code == 400
    assert "true albo false" in invalid.get_json()["error"]


def test_light_route_forwards_actor_item_and_action() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def change(**payload):
        captured.update(payload)
        return session.state_payload()

    session.change_actor_light = change
    response = create_app(session).test_client().post(
        "/api/equipment/light",
        json={"actor_id": "hero", "item_id": "candle", "action": "ignite"},
    )

    assert response.status_code == 200
    assert captured == {
        "actor_id": "hero",
        "item_id": "candle",
        "action": "ignite",
    }


def test_action_route_forwards_player_selected_social_skill() -> None:
    session = Mock()
    session.submit_action.return_value = {"ok": True}
    client = create_app(session).test_client()

    response = client.post(
        "/api/action",
        json={
            "text": "Przekonujemy zwiadowcę.",
            "selected_goal_id": "calm_scout",
            "check_participants": "single_actor",
            "participant_actor_ids": ["hero"],
            "selected_social_skill": "deception",
            "selected_action_source_id": "actor:hero:item:rope",
        },
    )

    assert response.status_code == 200
    session.submit_action.assert_called_once_with(
        "Przekonujemy zwiadowcę.",
        selected_goal_id="calm_scout",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
        selected_social_skill="deception",
        selected_action_source_id="actor:hero:item:rope",
        conversation_only=False,
    )


def test_exploration_option_route_forwards_actor_and_player_description() -> None:
    session = _session()
    captured: dict[str, object] = {}

    def select_option(
        option_id: str,
        *,
        actor_id: str | None = None,
        player_description: str = "",
    ):
        captured.update(
            {
                "option_id": option_id,
                "actor_id": actor_id,
                "player_description": player_description,
            }
        )
        return session.state_payload()

    session.select_exploration_option = select_option
    response = create_app(session).test_client().post(
        "/api/exploration/option",
        json={
            "option_id": "tavern_dice_game",
            "actor_id": "hero",
            "player_description": "Obserwuję dłonie przeciwnika przed pierwszym rzutem.",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "option_id": "tavern_dice_game",
        "actor_id": "hero",
        "player_description": "Obserwuję dłonie przeciwnika przed pierwszym rzutem.",
    }


def test_exploration_awareness_routes_forward_actor_id() -> None:
    session = _session()
    captured: list[tuple[str, str]] = []

    def search(actor_id):
        captured.append(("search", actor_id))
        return session.state_payload()

    def hide(actor_id):
        captured.append(("hide", actor_id))
        return session.state_payload()

    session.start_exploration_search = search
    session.start_exploration_hide = hide
    client = create_app(session).test_client()

    search_response = client.post(
        "/api/exploration/search/start",
        json={"actor_id": "rogue"},
    )
    hide_response = client.post(
        "/api/exploration/hide/start",
        json={"actor_id": "hero"},
    )

    assert search_response.status_code == 200
    assert hide_response.status_code == 200
    assert captured == [("search", "rogue"), ("hide", "hero")]


def test_exploration_fixture_routes_forward_typed_payloads() -> None:
    session = _session()
    captured: list[tuple[object, ...]] = []

    def action(**kwargs):
        captured.append(
            (
                "action",
                kwargs["actor_id"],
                kwargs["fixture_id"],
                kwargs["operation"],
            )
        )
        return session.state_payload()

    def damage(**kwargs):
        captured.append(
            (
                "damage",
                kwargs["actor_id"],
                kwargs["fixture_id"],
                kwargs["attack_total"],
                kwargs["damage"],
            )
        )
        return session.state_payload()

    session.start_exploration_fixture_action = action
    session.damage_exploration_fixture = damage
    client = create_app(session).test_client()

    action_response = client.post(
        "/api/exploration/fixture/action",
        json={
            "actor_id": "rogue",
            "fixture_id": "gate_supply_chest",
            "operation": "unlock",
        },
    )
    damage_response = client.post(
        "/api/exploration/fixture/damage",
        json={
            "actor_id": "hero",
            "fixture_id": "gate_supply_chest",
            "attack_total": 16,
            "damage": 7,
        },
    )

    assert action_response.status_code == 200
    assert damage_response.status_code == 200
    assert captured == [
        ("action", "rogue", "gate_supply_chest", "unlock"),
        ("damage", "hero", "gate_supply_chest", 16, 7),
    ]


def test_combat_ui_exposes_manual_enemy_saving_throw_endpoint() -> None:
    html, javascript, _stylesheet = _page_assets(_client())

    assert "/api/combat/enemy-saving-throw" in javascript
    assert "pending_enemy_saving_throw" in javascript
    assert "enemy-saving-throw-roll" in javascript
    assert "/static/exploration.js" in html


def test_combat_ui_renders_subtle_physical_card_reminders() -> None:
    _html, javascript, stylesheet = _page_assets(_client())

    assert "combatCardReminderHtml(combat, phase, isAllyTurn)" in javascript
    assert "Zeskanuj kartę albo kontynuuj bez niej." in javascript
    assert "wybrać zwykłą akcję na planszy" in javascript
    assert ".combat-card-reminder" in stylesheet


def test_courtyard_interaction_tile_images_are_served() -> None:
    client = _client()

    scout = client.get(
        "/scenario-assets/assets/courtyard_wounded_scout.png"
    )
    search = client.get("/scenario-assets/assets/courtyard_search.png")

    assert scout.status_code == 200
    assert scout.mimetype == "image/png"
    assert search.status_code == 200
    assert search.mimetype == "image/png"


def test_printable_paper_map_assets_are_served() -> None:
    client = _client()

    preview = client.get(
        "/game-assets/print_maps/village_watchtower/png/watchtower_overview.png"
    )
    pdf = client.get(
        "/game-assets/print_maps/village_watchtower/pdf/a4/watchtower_overview.pdf"
    )

    assert preview.status_code == 200
    assert preview.mimetype == "image/png"
    assert pdf.status_code == 200
    assert pdf.mimetype == "application/pdf"


def test_combat_ui_warns_about_area_spell_friendly_fire() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "function areaSpellFriendlyFireHtml" in javascript
    assert "Friendly fire:" in javascript
    assert "target_mode === 'all_creatures'" in javascript


def test_exploration_ui_renders_hazard_saving_throw_details() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "hazard_save" in javascript
    assert "Zagrożenie:" in javascript
    assert "Ryzyko obrażeń:" in javascript


def test_exploration_goal_ui_selects_participants_before_sending_method() -> None:
    html, javascript, stylesheet = _page_assets(_client())

    assert "function interactionParticipantPickerHtml" in javascript
    assert "function toggleInteractionActor" in javascript
    assert "function selectWholePartyForInteraction" in javascript
    assert "participant_actor_ids:" in javascript
    assert "check_participants: selectedCheckParticipants" in javascript
    assert "['no_actor', 'whole_party'].includes(selectedCheckParticipants)" in javascript
    assert "To wspólna decyzja drużyny. Wybór bohatera nie jest wymagany." in javascript
    assert "Wybierz numpadem postać, która wykona test." in javascript
    assert "Cała drużyna" in javascript
    assert 'id="goal-action"' in javascript
    assert "function sendGoalAction" in javascript
    assert "selected_social_skill:" in javascript
    assert "function interactionActionSourcePickerHtml" in javascript
    assert "selected_action_source_id:" in javascript
    assert "Źródło ustala legalne możliwości, właściciela i konsekwencje" in javascript
    assert "Gemini nie może go podmienić" in javascript
    assert "if (state.pending)" in javascript
    assert "Jak chcecie wpłynąć na NPC?" in javascript
    assert "Ten wybór należy do graczy" in javascript
    assert "function socialInteractionProgressHtml" in javascript
    assert "function interactionSocialApproachHtml" in javascript
    assert "function selectInteractionSocialSkill" in javascript
    assert "Przedstawcie szczere argumenty" in javascript
    assert "Zbudujcie wiarygodne kłamstwo" in javascript
    assert "Wywrzyjcie presję groźbą" in javascript
    assert "Przejdź do warunków testu" in javascript
    assert "if (goal.assigned_actor_id) return '';" in javascript
    assert "selectedInteractionActorIds = assigned ? [String(assigned.id)] : [];" in javascript
    assert "{text, conversation_only: true}" in javascript
    assert "Nie wybiera kafelka, nie deklaruje działania i nie uruchamia rzutu." in html
    assert ".interaction-actor-card.selected" in stylesheet
    assert ".social-approach-grid" in stylesheet
    assert "state.active_challenge.uses_progress" in javascript


def test_combat_ui_explains_empty_legal_target_list() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "function noLegalAttackTargetGuidance" in javascript
    assert "Brak celu w zasięgu wręcz" in javascript
    assert "zasięg lub linię widzenia" in javascript


def test_exploration_ui_exposes_downtime_crafting_preview_and_confirmation() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "function downtimePanelHtml" in javascript
    assert "Rzemiosło w downtime" in javascript
    assert "recipe.material_cost_cp" in javascript
    assert "recipe.time_cost_minutes" in javascript
    assert "window.confirm(prompt)" in javascript
    assert "/api/downtime/crafting/complete" in javascript


def test_interaction_screen_keeps_full_flow_in_chat_and_gm_composer_in_dialog() -> None:
    html, javascript, stylesheet = _page_assets(_client())

    assert "board-pad-grid" not in javascript
    assert "board-interaction-panel" not in javascript
    assert "auxiliaryPads" in javascript
    assert html.index('id="interaction-goals"') < html.index('id="chat-composer"')
    assert html.index('id="chat-utility-actions"') < html.index('id="interaction-goals"')
    assert 'id="gm-chat-dialog"' in html
    assert "function openGmChatDialog" in javascript
    assert "function closeGmChatDialog" in javascript
    assert "gmChatDialog.open" in javascript
    assert "function selectZoneOptionGoal" in javascript
    assert "function zoneOptionComposerHtml" in javascript
    assert "function submitZoneOption" in javascript
    assert "player_description: description" in javascript
    assert "Opis nie jest wymagany." in javascript
    assert "Opis może wpłynąć tylko na dozwolone przez scenę premie" in javascript
    assert "Na co zwróci uwagę MG:" in javascript
    assert "body.chat-instance-mode #action-panel" in stylesheet
    assert "overflow: hidden" in stylesheet
    assert "overflow-y: auto" in stylesheet
    assert "overscroll-behavior: contain" in stylesheet
    assert ".chat-flow-entry" in stylesheet
    assert ".gm-chat-dialog::backdrop" in stylesheet
    assert "object-fit: cover" in stylesheet
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in stylesheet


def test_interaction_workspace_splits_conversation_preview_and_eight_action_tiles() -> None:
    html, javascript, stylesheet = _page_assets(_client())

    assert 'class="interaction-workspace"' in html
    assert 'id="chat-conversation-scroll"' in html
    assert 'id="point-preview-pane"' in html
    assert 'id="interaction-actions-scroll"' in html
    assert 'id="actions-pane-title"' in html
    assert "function renderInteractionWorkspace" in javascript
    assert "function selectedPointPreview" in javascript
    assert "Pole ${esc(position[0])},${esc(position[1])} wskazane" in javascript
    assert "Wskazanie innego hotspotu zmieni podgląd" in javascript
    assert "Najnowsza odpowiedź" in javascript
    assert "const chatStream = document.getElementById('chat-conversation-scroll')" in javascript
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in stylesheet
    assert "grid-template-rows: repeat(2, minmax(0, 1fr))" in stylesheet
    assert "body.interaction-grid-mode .actions-workspace-scroll { overflow: hidden;" in stylesheet
    assert ".app-shell-context { display: none; }" in stylesheet
    assert ".party-summary-name { display: none; }" in stylesheet
    assert ".party-summary::-webkit-scrollbar { display: none; }" in stylesheet
    assert "flex: 1 1 0" in stylesheet
    assert "object-position: var(--interaction-image-position" in stylesheet
    assert "'nessa_portrait.png': variant === 'preview' ? '50% 9%' : '50% 14%'" in javascript
    assert "selectedZoneOption || selected || continuationPanelOpen ? ''" in javascript
    assert "continuationPanelOpen ? 'Wymarsz drużyny'" in javascript
    assert "simpleContinuationPanelHtml(continuation)" in javascript
    assert "Nie wymaga wyboru tempa ani rzutu podróży." in javascript


def test_interaction_goal_numpad_uses_stable_board_slots_and_readable_tiles() -> None:
    html, javascript, stylesheet = _page_assets(_client())

    assert 'data-numpad-key="0" onclick="leaveChatInstance()"' in html
    assert "^Numpad[0-9]$" in javascript
    assert "<kbd>0</kbd> zakończ rozmowę" in javascript
    assert 'leaveButton.innerHTML = `<kbd aria-hidden="true">0</kbd>' in javascript
    assert "numpadKey: /^[1-9]$/.test(stableSymbol)" in javascript
    assert "occupiedGoalNumpadKeys" in javascript
    assert "goalNumpadChoices.map(choice => choice.numpadKey)" in javascript
    assert "body.interaction-grid-mode .interaction-numpad-choice" in stylesheet
    assert "object-fit: contain" in stylesheet
    assert "grid-template-columns: minmax(310px, 38fr) minmax(0, 62fr)" in stylesheet
    assert "chat-instance-head .conversation-meta { display: none; }" in stylesheet


def test_description_free_interaction_goals_skip_redundant_confirmation() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "function interactionGoalExecutesImmediately" in javascript
    assert "function scheduleImmediateInteractionGoal" in javascript
    assert "if (interactionGoalExecutesImmediately(goal))" in javascript
    assert "scheduleImmediateInteractionGoal(goal);" in javascript
    assert "To działanie ma zdefiniowany sposób wykonania" not in javascript


def test_actor_portrait_ui_covers_party_tests_combat_and_messages() -> None:
    _html, javascript, stylesheet = _page_assets(_client())

    assert "function actorPortraitHtml" in javascript
    assert "actorPortraitHtml(actor, 'summary')" in javascript
    assert "actorPortraitHtml(actor, 'choice')" in javascript
    assert "actorPortraitHtml(entry, 'initiative')" in javascript
    assert "actorPortraitHtml(actor, 'turn')" in javascript
    assert "function messageCardHtml" in javascript
    assert "actorForMessage(message)" in javascript
    assert ".actor-portrait-choice" in stylesheet
    assert ".actor-portrait-message" in stylesheet


def test_encounter_stealth_ui_uses_defined_modifier_formatter() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "Modyfikator Stealth: ${signedNumber(Number(actor.modifier || 0))}" in javascript
    assert "Modyfikator Stealth: ${signed(Number(actor.modifier || 0))}" not in javascript


def test_area_attack_preview_exposes_confirm_and_back_controls() -> None:
    _html, javascript, _stylesheet = _page_assets(_client())

    assert "source.source_type === 'spell'" in javascript
    assert "Potwierdź atak" in javascript
    assert "Cofnij wybór obszaru" in javascript
    assert 'onclick="confirmAreaSpell()"' in javascript
    assert 'onclick="cancelAreaSpell()"' in javascript


def test_exploration_ui_page_includes_session_log_panel():
    client = _client()

    response = client.get("/play")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="session-log-panel"' in html
    assert 'id="session-log-filter"' in html
    javascript = client.get("/static/exploration.js").get_data(as_text=True)
    assert "/api/session-log" in javascript


def test_exploration_ui_page_uses_board_first_player_shell():
    html, javascript, stylesheet = _page_assets(_client())

    assert 'class="app-shell-header"' in html
    assert 'id="app-mode-label"' in html
    assert 'id="party-summary"' in html
    assert 'id="board-connection-indicator"' in html
    assert 'data-side-panel-tab="game"' in html
    assert 'data-side-panel-tab="party"' in html
    assert 'data-side-panel-tab="states"' in html
    assert 'data-side-panel-tab="spells"' in html
    assert 'data-side-panel-tab="inventory"' in html
    assert 'data-side-panel-tab="developer"' in html
    assert 'id="panel-actor-selector"' in html
    assert 'id="actor-states"' in html
    assert 'id="actor-spells"' in html
    assert 'id="actor-inventory"' in html
    assert 'id="board-disconnected-banner"' in html
    assert 'id="board-fallback-panel"' in html
    assert html.index('data-side-panel-content="developer"') < html.index('id="board-backend"')
    assert html.index('data-side-panel-content="developer"') < html.index('id="session-log-panel"')
    assert html.index('data-side-panel-content="developer"') < html.index('id="debug-payload"')
    assert "function setSidePanelTab" in javascript
    assert "function renderPartyShell" in javascript
    assert "partySummaryActorHtml(currentActorState(actor))" in javascript
    assert "function currentActorState" in javascript
    assert "party-summary-hp-value" in javascript
    assert "role=\"meter\"" in javascript
    assert ".party-summary-hp { display: block; height: 7px;" in stylesheet
    assert "function renderBoardConnectionIndicator" in javascript
    assert "function actorStatesHtml" in javascript
    assert "function actorSpellsHtml" in javascript
    assert "function actorInventoryPanelHtml" in javascript
    assert "function combatHudConditionChips" in javascript
    assert "chips.slice(0, 3)" in javascript
    assert "function handleSidePanelTabKeydown" in javascript
    assert "function cancelCurrentCombatStep" in javascript
    assert "function retryBoardConnection" in javascript
    assert "function toggleBoardFallback" in javascript
    assert "function manualBoardSelect" in javascript
    assert "'/api/board/select'" in javascript
    assert "Boolean(board.connected)" in javascript
    assert "--color-gold:" in stylesheet
    assert ".party-summary-actor" in stylesheet
    assert ".developer-warning" in stylesheet
    assert ".panel-info-card.spell" in stylesheet
    assert ".board-disconnected-banner" in stylesheet
    assert ".board-fallback-panel" in stylesheet


def test_exploration_ui_actor_payload_supports_on_demand_character_panels():
    actor = _client().get("/api/state").get_json()["actors"][0]

    assert actor["ac"] == 14
    assert actor["speed_feet"] == 30
    assert actor["temp_hp"] == 0
    assert actor["proficiency_bonus"] == 2
    assert actor["proficiencies"]["skills"] == ["athletics", "perception"]
    assert actor["hands"]["main_hand"]["item_name"] == "Miecz"
    assert actor["hands"]["off_hand"]["item_name"] == "Sztylet"


def test_debug_challenge_opens_gate_interaction_without_setup_flow():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(),
        debug_challenge_id="closed_gate",
    )

    state = session.state_payload()

    assert state["flow"]["stage"] == "location_active"
    assert state["active_challenge"]["id"] == "closed_gate"
    assert state["active_point"] is None
    assert state["exploration_setup"] is None


def test_exploration_ui_page_includes_spell_preparation_flow():
    client = _client(active=False)

    _html, javascript, _stylesheet = _page_assets(client)

    assert "Przygotowanie czarów" in javascript
    assert "spellPreparationCardHtml" in javascript
    assert "spellPreparationDraft" in javascript
    assert "spell.flavor_description" in javascript
    assert "spell.mechanical_description" in javascript
    assert "confirmSpellPreparation()" in javascript
    assert "/api/spell-preparation/confirm" in javascript
    assert "option.provider === 'class_feature'" in javascript
    assert "action.label || identifierLabel(actionId)" in javascript


def test_combat_targets_are_selected_on_board_not_by_internal_ids():
    client = _client(active=False)

    _html, javascript, _stylesheet = _page_assets(client)

    assert "Id celu" not in javascript
    assert 'name="combat-concentration-target"' not in javascript
    assert 'id="combat-stabilization-target"' not in javascript
    assert "data-twinned-attack-target" not in javascript
    assert "data-twinned-healing-target" not in javascript
    assert "data-sculpt-target" not in javascript
    assert "data-careful-target" not in javascript
    assert "data-heightened-target" not in javascript
    assert "/api/combat/class-feature/targeting" in javascript
    assert "Pokaż legalne cele" in javascript
    assert "Efekt w grze:" in javascript


def test_exploration_ui_page_exposes_level_up_after_experience_reward():
    client = _client()

    _html, javascript, _stylesheet = _page_assets(client)

    assert "Awans jest dostępny:" in javascript
    assert 'href="/characters/${encodeURIComponent(String(actor.id))}/level-up"' in javascript


def test_exploration_ui_page_includes_short_rest_flow():
    client = _client()

    html, javascript, stylesheet = _page_assets(client)

    assert 'id="short-rest-button"' not in html
    assert "'startShortRest()'" in javascript
    assert "Krótki odpoczynek" in javascript
    assert "spendShortRestHitDie" in javascript
    assert "data-short-rest-attunement" in javascript
    assert "/api/rest/short/start" in javascript


def test_exploration_ui_page_includes_filterable_slash_command_menu():
    client = _client()

    html, javascript, stylesheet = _page_assets(client)

    assert 'id="slash-command-menu"' in html
    assert "EXPLORATION_SLASH_COMMANDS" in html
    assert '"name": "zbuduj"' in html
    assert "slashCommandQuery" in javascript
    assert "startsWith(query)" in javascript
    assert "ArrowDown" in javascript
    assert "selectSlashCommand" in javascript
    assert ".slash-command-menu" in stylesheet
    assert "/api/rest/short/hit-die" in javascript


def test_exploration_ui_page_renders_graded_observation_conditions_in_chat():
    client = _client()

    _html, javascript, _stylesheet = _page_assets(client)

    assert "pending.kind === 'observation'" in javascript
    assert "Stopniowane informacje" in javascript
    assert "Warunki rozpoznania" in javascript
    assert "Porażka oznacza brak rozstrzygającej informacji" in javascript


def test_exploration_ui_page_exposes_crafting_confirmation_and_dismantling():
    client = _client()

    _html, javascript, _stylesheet = _page_assets(client)

    assert "Budowa:</b> bez rzutu" in javascript
    assert "Rozmontuj" in javascript
    assert "/api/crafting/dismantle" in javascript

    response = client.post("/api/crafting/dismantle", json={"item_id": "missing"})
    assert response.status_code == 400
    assert "Nieznana konstrukcja tymczasowa" in response.get_json()["error"]


def test_exploration_ui_page_is_fiction_first_and_accepts_questions():
    client = _client()

    html, javascript, stylesheet = _page_assets(client)

    assert html.index('id="scene-description-card"') < html.index('id="action-panel"')
    assert 'id="scene-conversation"' in html
    assert 'id="chat-stream"' in html
    assert 'id="interaction-state-card"' in html
    assert 'id="pending-title"' in html
    assert html.index('id="chat-stream"') < html.index('id="chat-utility-actions"') < html.index('id="pending-panel"')
    assert html.index('id="chat-stream"') < html.index('id="gm-chat-dialog"') < html.index('id="chat-composer"')
    assert html.index('id="pending-panel"') < html.index('id="roll-panel"') < html.index('id="result-panel"')
    assert html.count('conversation-system-card') == 3
    assert '<h3>Propozycja MG</h3>' not in html
    assert "Co robicie lub o co pytacie?" in html
    assert "Napisz wiadomość do MG" in html
    assert 'id="chat-typing"' in html
    assert 'id="chat-retry"' in html
    assert "Opuść interakcję" in html
    assert 'id="exploration-menu-panel"' not in html
    assert "Nie macie pomysłu? Zobaczcie inspiracje" not in javascript
    assert "Wskazówki MG i mechanika sceny" not in javascript
    assert "sceneConversationHtml" in javascript
    assert "sceneIntroMessageHtml" in javascript
    assert "conversationMetaHtml" in javascript
    assert "updateInteractionStateCard" in javascript
    assert "entries.splice(index, 1)" in javascript
    assert "scrollChatToBottom" in javascript
    assert "data-chat-scroll-bound" in javascript
    assert "waitingForGm" in javascript
    assert "retryLastGmRequest" in javascript
    assert "Odpowiedź trwa dłużej niż zwykle" in javascript
    assert "leaveChatInstance" in javascript
    assert "resolveNpcTransition" in javascript
    assert "/api/npc-transition/resolve" in javascript
    assert "/api/exploration/option" in javascript
    assert "boardChoiceToolbarHtml" in javascript
    assert "function simpleContinuationPanelHtml" in javascript
    assert "function advanceContinuationStep" in javascript
    assert "function retreatContinuationStep" in javascript
    assert "if (continuationPanelOpen) return advanceContinuationStep();" in javascript
    assert "if (continuationPanelOpen) return retreatContinuationStep();" in javascript
    assert "Przejście do kolejnej lokacji zajmie" in javascript
    assert "api('/api/scenario/continue', {}, 'Przygotowuję kolejną lokację...')" in javascript
    assert "Skutek podróży" in javascript
    assert "target_scenario_name" in javascript
    assert "Zdobyte i zabezpieczone rzeczy" in javascript
    assert "Rozpocznij ponownie" in javascript
    assert "window.prompt" not in javascript
    assert "'Menu lokacji'" in javascript
    assert "'Wróć do działań'" in javascript
    assert "navigationChoicesHtml" in javascript
    assert "synchronizeBoardSelection" in javascript
    assert "synchronizeBoardSelection({force: true})" in javascript
    assert "if (boardSelectionActivated) scrollChatToBottom(true)" in javascript
    assert "selection_revision" in javascript
    assert ".npc-transition-reactions" in stylesheet
    assert ".scene-image" in stylesheet
    assert ".conversation-entry" in stylesheet
    assert ".conversation-system-card" in stylesheet
    assert ".interaction-state-steps" in stylesheet
    assert ".conversation-context-chip" in stylesheet
    assert ".physical-roll-inputs" in stylesheet
    assert ".board-choice-toolbar" in stylesheet
    assert ".continuation-composer" in stylesheet
    assert ".continuation-pace-grid" in stylesheet
    assert ".continuation-pace-consequences" in stylesheet
    assert ".continuation-navigator-grid" in stylesheet
    assert ".continuation-steps" in stylesheet
    assert "body.chat-instance-mode { height: 100vh; overflow: hidden; }" in stylesheet
    assert "function pendingTitle" in javascript
    assert "if (proposal.player_narration) lines.push" not in javascript
    assert ".chat-typing" in stylesheet
    assert ".chat-retry" in stylesheet
    assert "body.chat-instance-mode" in stylesheet


def test_exploration_ui_page_includes_snapshot_controls():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)

    assert 'id="snapshot-save-button"' in html
    assert 'id="snapshot-load-button"' in html
    assert "/api/snapshot/save" in javascript
    assert "/api/snapshot/load" in javascript


def test_point_leave_route_clears_active_interaction_before_board_selection() -> None:
    session = _session()
    session.select_point = Mock(return_value=session.state_payload())
    client = create_app(session).test_client()

    response = client.post("/api/point/leave", json={})

    assert response.status_code == 200
    session.select_point.assert_called_once_with("")

    _html, javascript, _stylesheet = _page_assets(client)
    leave_start = javascript.index("async function leaveChatInstance()")
    leave_end = javascript.index("async function sendAction()", leave_start)
    leave_body = javascript[leave_start:leave_end]
    assert "/api/point/leave" in leave_body
    assert "await setBoardSelectionMode(true)" not in leave_body
    assert "setBoardSelectionMode(!navigationActive)" in leave_body
    assert "chatInstanceOpen = false" not in leave_body

    close_start = javascript.index("function closeCurrentExplorationInstance()")
    close_end = javascript.index("async function sendAction()", close_start)
    close_body = javascript[close_start:close_end]
    assert "flow.stage === 'interaction_result'" in close_body
    assert "finishInteraction()" in close_body
    assert "flow.stage === 'location_active'" in close_body
    assert "leaveChatInstance()" in close_body
    assert "state.pending_npc_transition" in close_body

    secondary_start = javascript.index("function triggerSecondaryAction()")
    secondary_end = javascript.index("function setPhysicalCardStatus", secondary_start)
    secondary_body = javascript[secondary_start:secondary_end]
    assert "if (closeCurrentExplorationInstance()) return true;" in secondary_body
    assert secondary_body.index("if (selectedZoneOptionId)") < secondary_body.index(
        "if (closeCurrentExplorationInstance())"
    )
    assert secondary_body.index("if (selectedInteractionGoalId)") < secondary_body.index(
        "if (closeCurrentExplorationInstance())"
    )


def test_exploration_ui_page_and_api_include_scenario_end_lifecycle():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)
    response = client.post("/api/scenario/finish", json={})

    assert 'id="active-effects"' in html
    assert 'id="finish-scenario-button"' in html
    assert "Źródło:" in javascript
    assert "/api/scenario/finish" in javascript
    assert "/api/scenario/continue" in javascript
    assert "/api/scenario/handoff/start" in javascript
    assert "Sukces z konsekwencją" in javascript
    assert "Niepowodzenie — historia toczy się dalej" in javascript
    assert "Podsumowanie celów" in javascript
    assert "zostaną przeniesione automatycznie" in javascript
    assert response.status_code == 200
    assert response.get_json()["flow"]["stage"] == "scenario_complete"


def test_scenario_continue_api_ignores_legacy_travel_choices():
    session = Mock()
    session.continue_scenario.return_value = {"ok": True}
    client = create_app(session).test_client()

    response = client.post(
        "/api/scenario/continue",
        json={
            "pace": "slow",
            "navigator_actor_id": "hero",
            "navigation_roll": {"natural_roll": 14, "natural_roll_2": 8},
            "forced_march_rolls": {
                "hero": [{"natural_roll": 12, "natural_roll_2": 4}],
            },
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    session.continue_scenario.assert_called_once_with()


def test_exploration_ui_short_rest_api_advances_time_and_returns_to_exploration():
    client = _client()

    preview = client.post("/api/rest/short/start", json={})
    completed = client.post("/api/rest/short/confirm", json={})
    finished = client.post("/api/rest/short/finish", json={})

    assert preview.status_code == 200
    assert preview.get_json()["flow"]["stage"] == "short_rest"
    assert completed.status_code == 200
    assert completed.get_json()["short_rest"]["elapsed_minutes"] == 60
    assert finished.status_code == 200
    assert finished.get_json()["flow"]["stage"] == "location_active"


def test_exploration_ui_short_rest_api_accepts_attunement_choice():
    client = _client()

    client.post("/api/rest/short/start", json={})
    completed = client.post(
        "/api/rest/short/confirm",
        json={
            "attunement_choices": [
                {
                    "actor_id": "cleric",
                    "item_id": "binding_wand",
                    "action": "attune",
                }
            ]
        },
    )

    assert completed.status_code == 200
    cleric = next(
        actor for actor in completed.get_json()["actors"]
        if actor["id"] == "cleric"
    )
    wand = next(item for item in cleric["inventory"] if item["id"] == "binding_wand")
    assert wand["attuned"] is True


def test_exploration_ui_long_rest_api_is_content_gated_and_advances_eight_hours():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, party_position=PartyPosition("tavern"))
    client = create_app(session).test_client()

    completed = client.post("/api/rest/long/complete", json={})

    assert completed.status_code == 200
    payload = completed.get_json()
    assert payload["long_rest"]["available"] is False
    assert session.state.elapsed_minutes == 480


def test_exploration_ui_page_includes_gm_decision_correction_controls():
    client = _client()

    html, javascript, stylesheet = _page_assets(client)

    assert (
        '<script src="/static/exploration.js?v=combat-hud-20260905-1"></script>'
        in html
    )
    assert "Popraw decyzję MG" in javascript
    assert "kliknij ponownie pole" in javascript
    assert "Mechanika:" in javascript
    assert "Mechanika pól" in javascript
    assert "decisionCorrectionHtml" in javascript
    assert "correction-roll-mode" in javascript
    assert "event.code === 'Numpad2'" in javascript
    assert "event.code === 'Numpad8'" in javascript
    assert "event.code === 'NumpadSubtract'" in javascript
    assert "event.code === 'NumpadSubtract'\n    && !typing" in javascript
    assert "event.code === 'NumpadEnter'" in javascript
    assert "function combatShortcutFromEvent(event)" in javascript
    assert "function triggerCombatActionShortcut(event)" in javascript
    assert "function triggerCombatActionShortcutKey(shortcut)" in javascript
    assert "event.repeat || event.ctrlKey || event.metaKey || event.altKey" in javascript
    assert "function triggerBufferedCombatShortcut(text, target)" in javascript
    assert "triggerBufferedCombatShortcut(text, target)" in javascript
    assert "triggerCombatActionShortcutKey('D')" in javascript
    assert "option.action_id === 'nimra_metamagic_cancel'" in javascript
    assert "event.key === 'Backspace'" in javascript
    assert "Wybierz akcję na karcie postaci" in javascript
    assert "Awaryjny wybór ekranowy" in javascript
    assert "Wszystkie skróty akcji aktywnego bohatera" in javascript
    assert "combat-keyboard-action-index-item" in javascript
    assert '<kbd>M</kbd> ruch' not in javascript
    assert "Numpad 8/2 zmienia pozycję listy" not in javascript
    assert "/api/combat/turn-actions/select" in javascript
    assert "flushCombatTurnActionMove" in javascript
    assert "applyOptimisticCombatTurnActionDelta" in javascript
    assert "updateCombatTurnActionSelectionDom" in javascript
    assert "data-action-index" in javascript
    assert ".combat-turn-action.selected')?.scrollIntoView" not in javascript
    assert "const obsoleteScanStop = boardScanInFlight" not in javascript
    assert "await obsoleteScanStop" not in javascript
    assert "settleCombatTurnActionMove" in javascript
    assert "selected_option_id || ''" in javascript
    assert "combatTurnActionMoveInFlight || combatTurnActionMoveTimer" in javascript
    assert "/api/combat/turn-actions/confirm" in javascript
    assert "/api/combat/turn-actions/cancel-preview" in javascript
    assert "/api/combat/item-target/confirm" in javascript
    assert "/api/combat/class-feature/targeting/confirm" in javascript
    assert "/api/combat/pending-board-selection/confirm" in javascript
    assert "/api/combat/aura-preview" in javascript
    assert "Pokaż zasięg" in javascript
    assert ".combat-aura-row" in stylesheet
    assert "option.group_label || combatMenuCategoryLabel" in javascript
    assert "combat-turn-command-layout" in javascript
    assert "combatTurnActorStatsHtml" in javascript
    assert "Ta akcja jest teraz niedostępna" in javascript
    assert 'id="combat-healing-roll"' in javascript
    assert "function initializeKeyboardRollWizard()" in javascript
    assert "function confirmKeyboardRollStep()" in javascript
    assert "function previousKeyboardRollStep()" in javascript
    assert "function submitKeyboardRollWizard()" in javascript
    assert "Największy możliwy wynik tego rzutu" in javascript
    assert 'data-roll-dice="${esc(dice)}"' in javascript
    assert 'data-roll-modifier="${esc(modifier)}"' in javascript
    assert ".keyboard-roll-wizard-card" in stylesheet
    assert ".combat-turn-command-layout" in stylesheet
    assert ".combat-turn-actor-stats" in stylesheet
    assert ".combat-action-unavailable" in stylesheet
    assert ".combat-keyboard-waiting" in stylesheet
    assert ".combat-keyboard-action-index" in stylesheet
    assert "data-numpad-key" in javascript
    assert "potwierdź aktualny podgląd Enterem" in javascript
    assert "correction-resource" in javascript
    assert "Zasób sceny" in javascript
    assert "zostanie zużyty po rzucie" in javascript
    assert "Modyfikatory sytuacyjne" in javascript
    assert "Improwizowane narzędzie" in javascript
    assert "improvised-tool-label" in javascript
    assert "/api/decision/correction" in javascript


def test_exploration_ui_combat_turn_controls_remain_available_during_board_scan():
    client = _client()

    html, javascript, stylesheet = _page_assets(client)
    html = "\n".join((html, javascript, stylesheet))

    assert 'data-allow-busy="true" onclick="finishCombatTurn()"' in html
    assert (
        'data-allow-busy="true" data-card-action="accept" '
        'onclick="resolveEnemyTurn()"'
    ) in html
    assert 'id="side-panel-toggle"' in html
    assert 'id="side-panel"' in html
    assert 'id="side-panel-scrim"' in html
    assert "toggleSidePanel()" in html
    assert "setSidePanelOpen(false)" in html
    assert "explorationSidePanelOpen" in html
    assert "side-panel-open" in html
    assert 'id="page-title"' in html
    assert 'id="encounter-title"' in html
    assert "state.combat) return combatStartHtml()" in html
    assert "function currentModeLabel()" in html
    assert "if (state.combat) return 'Walka'" in html
    assert "latestCombatMessageHtml()" in html
    assert "combatCurrentStepHtml" in html
    assert "combatPrimaryActionHtml" in html
    assert "combatActiveEffectsHtml" in html
    assert "combatAllEffectsHtml" in html
    assert "relevantCombatEffects" in html
    assert "combatEffectHtml" in html
    assert "statusChipsHtml" in html
    assert "actorEffectChips" in html
    assert "status-chip" in html
    assert "status_chips" in html
    assert "attackEffectsDetailsHtml" in html
    assert "combatActionDetailsHtml" in html
    assert "pendingCombatInteractionHtml" in html
    assert "/api/combat/interaction/confirm" in html
    assert "/api/combat/interaction/cancel" in html
    assert "/api/combat/retreat" in html
    assert "/api/combat/surrender" in html
    assert "retreatFromCombat()" in html
    assert "surrenderCombat()" in html
    assert "combatContextMenuHtml" in html
    assert "moveCombatContextMenu" in html
    assert "/api/combat/context-menu/select" in html
    assert "/api/combat/context-menu/confirm" in html
    assert "/api/combat/context-menu/cancel" in html
    assert "pendingCombatShoveHtml" in html
    assert "/api/combat/shove/resolve" in html
    assert "/api/combat/shove/cancel" in html
    assert "pendingOpportunityMovementHtml" in html
    assert "pendingOpportunityMovementDetailsHtml" in html
    assert "confirmOpportunityMovement()" in html
    assert "cancelOpportunityMovement()" in html
    assert "/api/combat/opportunity-movement/confirm" in html
    assert "/api/combat/opportunity-movement/cancel" in html
    assert "pendingEnemyOpportunityAttackHtml" in html
    assert "pendingEnemyOpportunityAttackDetailsHtml" in html
    assert "startEnemyOpportunityAttack()" in html
    assert "skipEnemyOpportunityAttack()" in html
    assert "submitEnemyOpportunityAttackRoll()" in html
    assert "submitEnemyOpportunityDamageRoll()" in html
    assert "/api/combat/enemy-opportunity/start" in html
    assert "/api/combat/enemy-opportunity/skip" in html
    assert "/api/combat/enemy-opportunity/roll" in html
    assert "/api/combat/enemy-opportunity/damage" in html
    assert "damageComponentPayload(pending, 'enemy-opportunity-damage')" in html
    assert "combatMainPromptHtml" in html
    assert "combatInstructionText" in html
    assert "combatActorStatusHtml" in html
    assert "actorHpLabel" in html
    assert "combat-current-step" in html
    assert "combat-mini-status" in html
    assert "combat-last-result" in html
    assert "combat-stage" in html
    assert "combat-action-card" in html
    assert "encounterProgressHtml" in html
    assert "encounter-transition-shell" in html
    assert "Przejście do walki" in html
    assert "Nadchodzi starcie" in html
    assert "combatInitiativeRibbonHtml" in html
    assert "combatTurnHudHtml" in html
    assert "combatHudConditionChips" in html
    assert "combatPresentationPhase" in html
    assert "combatPhaseStepsHtml" in html
    assert "combatInterruptPresentation" in html
    assert "initiative-ribbon" in html
    assert "combat-turn-hud" in html
    assert "combat-phase-steps" in html
    assert "combat-interrupt-dialog" in html
    assert "Pole walki, ostatni wynik i szczegóły" in html
    assert "Aktualny aktor" in html
    assert "Ostatni rezultat" in html
    assert "Aktywne efekty" in html
    assert "Wszystkie aktywne efekty" in html
    assert "Efekty ataku" in html
    assert "Szczegóły aktualnego kroku" in html
    assert "playerTurnDetailsHtml" in html
    assert "pendingPlayerAttackDetailsHtml" in html
    assert "enemyTurnDetailsHtml" in html
    assert "Tura gracza:" in html
    assert "Akcja:" in html
    assert "Bonus action:" in html
    assert "Reakcja:" in html
    assert "Ruch:" in html
    assert "wybrano cel" in html
    assert "wpisz obrażenia" in html
    assert "HP celu" in html
    assert "maybeAutoScanBoard" not in html
    assert "scanBoardAuto" not in html
    assert 'data-primary-scan="true" onclick="scanBoard()"' in html
    assert "visiblePrimaryScanButton()" in html
    assert "scheduleAutomaticBoardScan" in html
    assert "boardSelectionCanAutoArm" in html
    assert "boardSelectionStatusHtml" in html
    assert "boardScanInFlight" in html
    assert "boardScanPromise" in html
    assert "await pendingScan" in html
    assert "lastAttemptedBoardRevision = '';" in html
    assert "boardScanToken" in html
    assert "stopBoardScanLoop()" in html
    assert "lastAttemptedBoardRevision" in html
    assert "expected_revision" not in html
    assert "pendingPlayerAttackHtml" in html
    assert "Potwierdzenie ataku" in html
    assert "confirmPlayerAttackTarget()" in html
    assert "cancelPlayerAttackTarget()" in html
    assert "/api/combat/player-attack-confirm" in html
    assert "/api/combat/player-attack-cancel" in html
    assert "/api/combat/player-attack-roll" in html
    assert "d20RollInputsHtml" in html
    assert "d20RollPayload" in html
    assert "natural_roll_2" in html
    assert "attack_mode" in html
    assert "/api/combat/player-damage" in html
    assert "damageComponentPayload(pending, 'area-spell-damage')" in html
    assert "/api/combat/dash" in html
    assert "/api/combat/dodge" in html
    assert "/api/combat/disengage" in html
    assert "/api/combat/help/start" in html
    assert "/api/combat/help/confirm" in html
    assert "/api/combat/help/cancel" in html
    assert "/api/combat/concentration/start" in html
    assert "/api/combat/concentration/confirm" in html
    assert "/api/combat/concentration/cancel" in html
    assert "/api/combat/concentration-check" in html
    assert "pendingConcentrationCheckHtml" in html
    assert "pendingConcentrationCheckDetailsHtml" in html
    assert "submitConcentrationCheck()" in html
    assert "actorInventoryHtml" in html
    assert "Ten przedmiot został zużyty" in html
    assert "pending_concentration_check" in html
    assert "/api/combat/ready/start" in html
    assert "/api/combat/ready/confirm" in html
    assert "/api/combat/ready/cancel" in html
    assert "/api/combat/ready-attack/start" in html
    assert "/api/combat/ready-attack/skip" in html
    assert "/api/combat/ready-attack/roll" in html
    assert "/api/combat/ready-attack/damage" in html
    assert "/api/combat/defensive-spell/cast" in html
    assert "/api/combat/defensive-spell/skip" in html
    assert "damageComponentPayload(pending, 'ready-damage')" in html
    assert "useCombatDash()" in html
    assert "useCombatDodge()" in html
    assert "useInstinctiveDodgeReaction()" in html
    assert "skipInstinctiveDodgeReaction()" in html
    assert "/api/combat/instinctive-dodge/use" in html
    assert "/api/combat/instinctive-dodge/skip" in html
    assert "Premia +2 ze skazy nadal obowiązuje" in html
    assert "useCombatDisengage()" in html
    assert "startCombatHelp()" in html
    assert "confirmCombatHelp()" in html
    assert "cancelCombatHelp()" in html
    assert "pendingCombatHelpHtml" in html
    assert "pendingCombatHelpDetailsHtml" in html
    assert "pendingConcentrationActionHtml" in html
    assert "pendingConcentrationActionDetailsHtml" in html
    assert "startCombatReady()" in html
    assert "confirmCombatReady()" in html
    assert "cancelCombatReady()" in html
    assert "pendingCombatReadyHtml" in html
    assert "pendingReadyAttackHtml" in html
    assert "Atak okazyjny" in html
    assert "Wykonaj atak okazyjny" in html
    assert "Rozstrzygnij atak okazyjny i wykonaj ruch" in html
    assert "latestMessageWithTitle(state, 'Atak okazyjny')" in html
    assert "Atak został już rozstrzygnięty" in html
    assert "Przeczytałem — zakończ turę przeciwnika" in html
    assert "enemy-attack-summary" in html
    assert "Obrażenia: ${esc(damage)}" in html
    assert "HP ${esc(target)}:" in html
    assert "Przeczytałem — wróć do tury" in html
    assert 'id="result-ack-button"' in html
    assert "enemy-attack-result" in html
    assert "rangedThreatWarningHtml" in html
    assert "Przeciwnik nie musi być celem tego ataku" in html
    assert "PRZECIWNIK POKONANY" in html
    assert "Boolean(resultAck) && !state.combat" in html
    assert "resultAck || actionMenuStep ? '' : combatMainPromptHtml" in html
    assert "phase === 'result' && !resultAck" in html
    assert "enemyRollSummaryHtml" in html
    assert "enemyTurnIntentHtml" in html
    assert "Zamiar przeciwnika" in html
    assert "enemyTurnResultHtml" in html
    assert "confirmEnemyTurnResult()" in html
    assert "/api/combat/enemy-turn/confirm" in html
    assert "/api/combat/enemy-attack-roll" not in html
    assert "/api/combat/enemy-damage" not in html
    assert "confirmLocationPreview()" in html
    assert "/api/location/confirm-preview" in html
    assert "/api/exploration/board-selection" in html
    assert "setBoardSelectionMode(false)" in html
    assert "setBoardSelectionMode(!navigationActive)" in html
    assert "Kliknij ponownie pole tej lokacji" in html


def test_idle_player_turn_keeps_end_turn_next_to_board_scan_and_routes_other_actions_through_own_tile():
    client = _client()

    _html, javascript, _stylesheet = _page_assets(client)
    primary_action_source = javascript.split(
        "function combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn) {",
        1,
    )[1].split("function combatStabilizationHtml(combat) {", 1)[0]

    idle_turn_source = primary_action_source.split(
        "const movement = combat.movement || {remaining_feet: 0, destinations: []};",
        1,
    )[1]
    assert 'onclick="scanBoard()">Skanuj planszę</button>' in idle_turn_source
    assert "combatSourceButtonsHtml(combat)" not in idle_turn_source
    assert "startCombatReady()" not in idle_turn_source
    assert "startCombatHelp()" not in idle_turn_source
    assert "useCombatDash()" not in idle_turn_source
    assert "useCombatDodge()" not in idle_turn_source
    assert "useCombatDisengage()" not in idle_turn_source
    assert "finishCombatTurn()" in idle_turn_source
    assert "retreatFromCombat()" in idle_turn_source
    assert "surrenderCombat()" in idle_turn_source
    assert "Kliknij pole ${actor.name || 'aktywnego bohatera'}" in javascript
    assert "czary, akcje i ekwipunek" in javascript
    assert "Turę możesz zakończyć także przyciskiem obok skanowania" in javascript
    assert "Rzut obronny przeciwnika" in javascript
    assert "path === '/api/combat/player-attack-confirm'" in javascript
    assert "latestMessageWithTitleSince(state, 'Czar', previousMessageCount)" in javascript
    assert "function latestMessageWithTitleSince" in javascript
    assert "'Atak', 'Czar', 'Obrażenia'" in javascript
    assert "combat.context_menu.is_self_menu ? combatStabilizationHtml(combat)" in javascript
    assert "combat.targeting.kind === 'area'" in javascript
    assert "Pola ruchu są wyłączone" in javascript
    assert "Celowanie: <b>${esc(targeting.source_name || '-')}</b>" in javascript


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


def test_state_exposes_revisioned_automatic_board_selection_contract():
    session = _session()
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")
    state = create_app(session).test_client().get("/api/state").get_json()

    selection = state["board_selection"]
    assert selection["revision"]
    assert selection["mode"] == "interaction"
    assert selection["auto_arm"] is True
    assert selection["connected"] is True
    assert selection["confirmation_policy"] == "immediate"
    assert selection["legal_position_count"] == len(selection["legal_positions"])
    assert selection["legal_position_count"] > 0


def test_board_scan_ignores_stale_frontend_revision_without_consuming_click():
    session = _session()
    board = FakeBoardConnection(clicks=[(6, 1)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    response = client.post(
        "/api/board/scan",
        json={"revision": "stale-browser-state", "automatic": True},
    )

    assert response.status_code == 200
    assert board.clicks == [(6, 1)]
    events = client.get("/api/session-log").get_json()["events"]
    stale = [event for event in events if event["event_type"] == "ui_board_scan_stale_before_start"]
    assert stale[-1]["payload"]["automatic"] is True


def test_selected_force_gate_goal_skips_actor_selection_for_fixed_group_check():
    session = _session()
    board = FakeBoardConnection(clicks=[(6, 1)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    selected = client.post("/api/board/scan", json={}).get_json()

    assert selected["flow"]["board_interaction"]["selected_goal_id"] == "force_entry"
    actor_selection = selected["flow"]["board_interaction"]["actor_selection"]
    assert actor_selection["active"] is False
    assert actor_selection["pads"] == []
    assert selected["board_selection"]["mode"] == "interaction"
    assert selected["board_selection"]["auto_arm"] is False
    assert selected["board_selection"]["confirmation_policy"] == "screen_input"

    submitted = _submit_force_gate(client).get_json()

    assert submitted["flow"]["board_interaction"]["selected_goal_id"] is None
    assert submitted["pending"]["stage"] == "decision"
    assert submitted["board_selection"]["auto_arm"] is False


def test_party_identity_colors_follow_new_game_party_order():
    state = _session().state_payload()

    assert [
        (actor["id"], actor["party_slot"], actor["party_color"])
        for actor in state["actors"]
    ] == [
        ("hero", 1, "czerwony"),
        ("rogue", 2, "niebieski"),
        ("cleric", 3, "zielony"),
    ]


def test_screen_actor_selection_route_is_disabled():
    client = _client()

    response = client.post(
        "/api/exploration/actor-selection/select",
        json={
            "goal_id": "open_lock",
            "actor_id": "hero",
            "role": "lead",
        },
    )

    assert response.status_code == 409
    assert "wyłącznie przez fizyczną kartę" in response.get_json()["error"]


def test_helper_actor_card_selection_excludes_lead_and_uses_no_board_pads():
    session = _session()
    client = create_app(session).test_client()

    started = client.post(
        "/api/exploration/actor-selection/start",
        json={
            "goal_id": "force_entry",
            "role": "helper",
            "excluded_actor_ids": ["hero"],
        },
    ).get_json()

    selection = started["flow"]["board_interaction"]["actor_selection"]
    assert selection["pads"] == []
    assert started["board_selection"]["mode"] == "actor_card"
    assert started["board_selection"]["auto_arm"] is False

    selected = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:actor:rogue"},
    ).get_json()["state"]
    actor_selection = selected["flow"]["board_interaction"]["actor_selection"]
    assert actor_selection["selected_actor_id"] == "rogue"
    assert actor_selection["role"] == "helper"


def test_cancelled_screen_form_rearms_board_interaction_selection():
    session = _session()
    board = FakeBoardConnection(clicks=[(6, 1)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()
    selected = client.post("/api/board/scan", json={}).get_json()
    selected_revision = selected["board_selection"]["revision"]

    cleared = client.post("/api/board/clear-selection", json={}).get_json()

    assert cleared["flow"]["board_interaction"]["selected_goal_id"] is None
    assert cleared["board_selection"]["auto_arm"] is True
    assert cleared["board_selection"]["confirmation_policy"] == "immediate"
    assert cleared["board_selection"]["revision"] != selected_revision


def test_duplicate_board_scan_is_ignored_while_previous_scan_owns_hardware():
    session = _session()
    board = FakeBoardConnection(clicks=[(6, 1)])
    session.attach_board_connection(board, backend="simulator")
    session._board_scan_lock.acquire()
    try:
        state = session.scan_board_selection(
            expected_revision=session.state_payload()["board_selection"]["revision"],
            automatic=False,
        )
    finally:
        session._board_scan_lock.release()

    assert board.clicks == [(6, 1)]
    assert state["flow"]["board_interaction"]["selected_goal_id"] is None
    events = create_app(session).test_client().get("/api/session-log").get_json()["events"]
    assert events[-1]["event_type"] == "ui_board_scan_duplicate_ignored"


def test_gate_board_scan_selects_goal_and_records_activated_tile():
    session = _session()
    board = FakeBoardConnection(clicks=[(6, 1), (12, 3), (10, 4)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    interaction = client.get("/api/state").get_json()["flow"]["board_interaction"]
    assert [
        (pad["position"], pad["target_id"])
        for pad in interaction["pads"]
    ] == [
        ([6, 1], "force_entry"),
        ([12, 3], "open_lock"),
        ([10, 4], "look_around"),
        ([6, 3], "gate"),
    ]

    previous_revision = 0
    for goal_id in ("force_entry", "open_lock", "look_around"):
        selected = client.post("/api/board/scan", json={}).get_json()
        board_interaction = selected["flow"]["board_interaction"]
        assert board_interaction["selected_goal_id"] == goal_id
        assert board_interaction["selection_revision"] > previous_revision
        previous_revision = board_interaction["selection_revision"]
        if goal_id != "look_around":
            cleared = client.post("/api/board/clear-selection", json={}).get_json()
            previous_revision = cleared["flow"]["board_interaction"][
                "selection_revision"
            ]

    events = client.get("/api/session-log").get_json()["events"]
    activated = [
        event
        for event in events
        if event["event_type"] == "ui_board_interaction_pad_activated"
    ]
    assert [event["payload"]["target_id"] for event in activated] == [
        "force_entry",
        "open_lock",
        "look_around",
    ]
    revisions = [
        event["payload"]["selection_revision"] for event in activated
    ]
    assert revisions == sorted(revisions)
    assert len(set(revisions)) == 3


def test_exploration_ui_initial_payload_requires_spell_preparation_and_hides_actions():
    client = _client(active=False)

    data = client.get("/api/state").get_json()

    assert data["flow"]["stage"] == "waiting_for_board"
    assert data["flow"]["can_start"] is False
    assert data["spell_preparation"]["current_actor_id"] == "cleric"
    assert data["active_challenge"] is None
    assert data["current_zone"]["image_url"].endswith("/scenario-assets/assets/gate_preview.png")


def test_exploration_ui_serves_gate_preview_asset():
    client = _client(active=False)

    response = client.get("/scenario-assets/assets/gate_preview.png")

    assert response.status_code == 200
    assert response.content_type == "image/png"


def test_exploration_ui_serves_every_gate_goal_tile_image():
    client = _client(active=False)
    names = (
        "gate_force_entry.webp",
        "gate_wall_route.webp",
        "gate_lock.webp",
        "gate_look_around.webp",
        "gate_bolt.webp",
    )

    for name in names:
        response = client.get(f"/scenario-assets/assets/{name}")
        assert response.status_code == 200
        assert response.content_type == "image/webp"


def test_exploration_ui_serves_actor_portrait_and_exposes_its_url():
    client = _client(active=False)

    state = client.get("/api/state").get_json()
    hero = next(actor for actor in state["actors"] if actor["id"] == "hero")
    response = client.get(hero["portrait_url"])

    assert hero["portrait_url"] == "/game-assets/portraits/abandoned_watchtower/hero.webp"
    assert response.status_code == 200
    assert response.content_type == "image/webp"


def test_exploration_ui_prefills_board_settings_from_shared_config():
    client = _client()

    board = client.get("/api/state").get_json()["board"]

    assert board["configured_backend"] == "hardware"
    assert board["backend"] == "none"
    assert board["board_serial_port"] == "/dev/ttyUSB0"
    assert board["wled_url"] == "http://192.168.0.165"


def test_exploration_ui_state_keeps_gm_knowledge_behind_conversation_boundary():
    client = _client()

    response = client.get("/api/state")

    data = response.get_json()
    assert "Zarośnięta" in data["current_zone"]["description"]
    assert "stara drewniana brama" in data["current_zone"]["summary"]
    assert "available_materials" not in data["current_zone"]
    assert set(data["active_challenge"]) == {
        "id",
        "name",
        "progress_required",
        "current_progress",
        "noise",
        "completed",
        "complications",
        "goals",
        "uses_progress",
    }


def _finish_map_setup(client):
    while True:
        state = client.get("/api/state").get_json()
        if state["flow"]["stage"] != "party_setup" or state.get("exploration_setup") is None:
            return state
        client.post("/api/exploration/setup/confirm", json={})


def _confirm_fallen_gate_setup(client):
    state = client.get("/api/state").get_json()
    if state["flow"]["stage"] == "interaction_result":
        state = client.post("/api/interaction/finish", json={}).get_json()
    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["label"] == "przewrócona brama"
    return client.post("/api/exploration/setup/confirm", json={}).get_json()


def _resolve_encounter_opening(client):
    response = client.post("/api/encounter/opening/resolve", json={})
    assert response.status_code == 200
    state = response.get_json()
    assert state["pending_encounter"]["opening"]["resolved"] is True
    return state


def _advance_encounter_setup(client, board):
    state = client.get("/api/state").get_json()
    setup = state["encounter_setup"]
    if setup["status"] == "completed":
        return state
    step = setup["current_step"]
    if step.get("requires_board_assignment"):
        position = tuple(step["available_positions"][0])
        board.clicks.append(position)
        return client.post("/api/board/scan", json={}).get_json()
    return client.post("/api/encounter/setup/confirm", json={}).get_json()


def _resolve_enemy_turn_from_ui(client, board):
    state = client.post("/api/combat/enemy-turn", json={}).get_json()
    if state["combat"]["enemy_turn_intent"] is not None:
        state = client.post("/api/combat/enemy-turn", json={}).get_json()
    preview = state["combat"]["enemy_turn_preview"]
    if preview is None:
        return state

    if preview["kind"] == "movement":
        board.clicks.append(tuple(preview["destination"]))
    else:
        board.clicks.append(tuple(preview["target_position"]))

    result = client.post("/api/board/scan", json={}).get_json()
    assert result["combat"]["enemy_turn_result"] is not None
    return client.post("/api/combat/enemy-turn/confirm", json={}).get_json()


def test_exploration_ui_start_preview_location_and_confirm_from_ui_updates_leds():
    session = _session(active=False)
    board = FakeBoardConnection(clicks=[(9, 2), (9, 2)])
    session.attach_board_connection(board, backend="simulator")
    app = create_app(session)
    client = app.test_client()

    ready = client.get("/api/state").get_json()
    assert ready["flow"]["stage"] == "ready_to_start"

    started = client.post("/api/start", json={}).get_json()
    assert started["flow"]["stage"] == "party_setup"

    started = _finish_map_setup(client)
    assert started["flow"]["stage"] == "spell_preparation"
    started = client.post(
        "/api/spell-preparation/confirm",
        json={"actor_id": "cleric", "spell_ids": ["healing_word", "bless_attack_bonus"]},
    ).get_json()
    assert started["flow"]["stage"] == "location_preview"
    assert started["flow"]["preview_zone"] is None
    assert [zone["id"] for zone in started["flow"]["available_locations"]] == ["gate", "courtyard", "tower"]
    assert [zone["available"] for zone in started["flow"]["available_locations"]] == [True, False, False]

    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "gate"
    assert preview["active_challenge"] is None

    repeated_preview = client.post("/api/board/scan", json={}).get_json()
    assert repeated_preview["flow"]["stage"] == "location_active"
    assert repeated_preview["flow"]["preview_zone"] is None
    assert repeated_preview["active_challenge"]["id"] == "closed_gate"


def test_exploration_ui_blocked_visible_location_shows_locked_preview():
    session = _session(active=False)
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    client.post("/api/start", json={})
    setup = _finish_map_setup(client)
    assert setup["flow"]["stage"] == "spell_preparation"
    client.post(
        "/api/spell-preparation/confirm",
        json={"actor_id": "cleric", "spell_ids": ["healing_word", "bless_attack_bonus"]},
    )
    preview = client.post("/api/board/scan", json={}).get_json()

    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "courtyard"
    assert preview["flow"]["preview_zone"]["available"] is False
    assert "Najpierw trzeba otworzyć bramę" in preview["flow"]["preview_zone"]["locked_reason"]
    assert preview["active_challenge"] is None

    revision = preview["board_selection"]["revision"]
    board.clicks.append((9, 10))
    repeated = client.post("/api/board/scan", json={}).get_json()

    assert repeated["flow"]["stage"] == "location_preview"
    assert repeated["flow"]["preview_zone"]["id"] == "courtyard"
    assert repeated["board_selection"]["revision"] != revision
    assert "ponowne kliknięcie nie otworzy" in repeated["board"]["message"]


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

    action_response = _submit_force_gate(client)
    assert action_response.status_code == 200
    assert action_response.get_json()["pending"]["stage"] == "decision"

    decision_response = client.post("/api/decision", json={"decision": "accept"})
    assert decision_response.status_code == 200
    assert decision_response.get_json()["required_rolls"][0]["actor_id"] == "hero"

    rolls_response = client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    assert rolls_response.status_code == 200
    data = rolls_response.get_json()
    assert data["flow"]["stage"] == "interaction_result"
    assert data["flow"]["interaction_result"]["next_instruction"]
    assert data["exploration_setup"] is None
    assert data["active_challenge"] is None
    assert data["pending_encounter"] is None

    setup = client.post("/api/interaction/finish", json={}).get_json()
    assert setup["flow"]["stage"] == "party_setup"
    assert setup["exploration_setup"]["current_step"]["label"] == "przewrócona brama"

    data = client.post("/api/exploration/setup/confirm", json={}).get_json()

    assert data["travel_options"][0]["id"] == "courtyard"
    assert {"label": "Brama", "value": "otwarta"} in data["scene_status"]
    assert data["pending_encounter"]["trigger_id"] == "gate_open_skirmish"


def test_exploration_ui_accept_queues_rolls_for_the_whole_party():
    client = _client()

    _submit_force_gate(client)
    response = client.post("/api/decision", json={"decision": "accept"})

    assert response.status_code == 200
    assert [roll["actor_id"] for roll in response.get_json()["required_rolls"]] == [
        "hero",
        "rogue",
        "cleric",
    ]


def test_exploration_ui_decision_correction_endpoint_updates_pending_option():
    client = _client()

    _submit_force_gate(
        client,
        "Wyważamy bramę z pomocą.",
    )
    response = client.post(
        "/api/decision/correction",
        json={
            "mechanic_id": "group_check",
            "check_participants": "whole_party",
            "check_aggregation": "any_success",
            "lead_actor_id": "hero",
            "helper_actor_id": None,
            "ability": "dexterity",
            "skill": "acrobatics",
            "dc": 13,
            "roll_mode": "normal",
            "situational_modifiers": [
                {
                    "label": "Mokra lina",
                    "modifier": -1,
                    "source": "interaction_object",
                    "reason": "Opis obiektu wskazuje mokrą linę.",
                    "roll_mode": "disadvantage",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["selected_lead_actor_id"] == "hero"
    assert data["selected_helper_actor_id"] is None
    assert data["pending"]["option"]["mechanic"]["id"] == "group_check"
    assert data["pending"]["option"]["check_participants"] == "whole_party"
    assert data["pending"]["option"]["ability"] == "dexterity"
    assert data["pending"]["option"]["skill"] == "acrobatics"
    assert data["pending"]["option"]["dc"] == 13
    assert data["pending"]["option"]["roll_mode"] == "disadvantage"
    assert data["pending"]["option"]["situational_modifiers"][0]["label"] == "Mokra lina"


def test_exploration_ui_decision_correction_cannot_replace_authored_group_model():
    client = _client()

    _submit_force_gate(client, "Używam starej deski jak dźwigni.")
    response = client.post(
        "/api/decision/correction",
        json={
            "mechanic_id": "improvised_tool_check",
            "check_participants": "single_actor",
            "check_aggregation": "lead_result",
            "lead_actor_id": "hero",
            "ability": "strength",
            "skill": "athletics",
            "dc": 15,
            "roll_mode": "normal",
            "situational_modifiers": [],
            "improvised_tool": {
                "label": "Stara deska",
                "source": "interaction_object",
                "source_detail": "rumowisko przy bramie",
                "effect_modifier": 1,
                "risk": "może pęknąć przy krytycznej porażce",
                "reason": "Opis sceny zawiera stare deski.",
            },
        },
    )

    assert response.status_code == 400
    assert "przypisane do wybranego kafelka" in response.get_json()["error"]


def test_exploration_ui_reset_endpoint_restores_state():
    client = _client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})

    response = client.post("/api/reset", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "waiting_for_board"
    assert data["active_challenge"] is None


def test_exploration_ui_confirms_spell_preparation_through_api():
    session = _session(active=False)
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")
    session.start_session()
    while session.exploration_setup_flow is not None:
        session.confirm_exploration_setup_step()
    client = create_app(session).test_client()

    response = client.post(
        "/api/spell-preparation/confirm",
        json={
            "actor_id": "cleric",
            "spell_ids": ["radiant_line", "healing_word"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "location_preview"
    cleric = data["spell_preparation"]["actors"][0]
    assert cleric["confirmed"] is True
    assert {
        spell["id"]
        for spell in cleric["spells"]
        if spell["prepared"] and not spell["always_prepared"]
    } == {"radiant_line", "healing_word"}


def test_exploration_ui_shows_and_handles_travel_after_completed_challenge():
    client = _client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    completed = client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}}).get_json()

    assert completed["active_challenge"] is None
    assert completed["flow"]["stage"] == "interaction_result"

    completed = _confirm_fallen_gate_setup(client)

    assert completed["travel_options"][0]["id"] == "courtyard"

    response = client.post("/api/travel", json={"zone_id": "courtyard"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["exploration_setup"] is None
    assert data["current_zone"]["id"] == "courtyard"
    assert data["active_challenge"]["id"] == "courtyard_search"


def test_exploration_ui_finish_interaction_returns_to_location_selection():
    client = _client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    completed = client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}}).get_json()
    assert completed["flow"]["stage"] == "interaction_result"

    response = client.post("/api/interaction/finish", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "party_setup"
    assert data["exploration_setup"]["current_step"]["label"] == "przewrócona brama"

    data = client.post("/api/exploration/setup/confirm", json={}).get_json()
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"] is None
    assert [zone["id"] for zone in data["flow"]["available_locations"]] == ["gate", "courtyard", "tower"]
    assert [zone["color"] for zone in data["flow"]["available_locations"]] == ["żółty", "niebieski", "pomarańczowy"]


def test_exploration_ui_can_cancel_location_preview():
    session = _session()
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    session.resolved_encounter_trigger_ids.add("gate_open_skirmish")
    session.pending_encounter = None
    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "courtyard"

    response = client.post("/api/location/cancel-preview", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"] is None


def test_exploration_ui_reveals_selects_and_resolves_npc_point():
    session = _session()
    client = create_app(session).test_client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
    client.post("/api/travel", json={"zone_id": "courtyard"})
    client.post("/api/exploration/setup/confirm", json={})
    client.post("/api/board/select", json={"col": 8, "row": 8})

    point_response = client.post("/api/point", json={"point_id": "wounded_scout"})
    assert point_response.status_code == 200
    point_state = point_response.get_json()
    assert point_state["active_point"]["id"] == "wounded_scout"
    assert point_state["active_point"]["npc"]["name"] == "Ranny zwiadowca"
    assert point_state["active_point"]["npc"]["goals"][0]["id"] == "calm_scout"
    assert point_state["active_point"]["npc"]["goals"][0]["social_skill_options"] == [
        "persuasion",
        "deception",
        "intimidation",
    ]
    assert {"label": "Ranny zwiadowca", "value": "odkryty, ranny"} in point_state["scene_status"]

    action_response = client.post("/api/action", json={"text": "Uspokajamy zwiadowcę."})
    assert action_response.status_code == 200
    assert action_response.get_json()["pending"]["kind"] == "npc"

    roll_pending = client.post("/api/decision", json={"decision": "accept"}).get_json()
    assert roll_pending["pending"]["check_plan"]["dc"] == 10
    accepted = client.post("/api/rolls", json={"rolls": {"hero": 20}}).get_json()
    assert {"key": "scout_calmed", "value": True} in accepted["flags"]
    assert {"label": "Ranny zwiadowca", "value": "uspokojony"} in accepted["scene_status"]


def test_exploration_ui_applies_authored_npc_key_issue_without_roll():
    session = _session()
    client = create_app(session).test_client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
    client.post("/api/travel", json={"zone_id": "courtyard"})
    client.post("/api/exploration/setup/confirm", json={})
    client.post("/api/board/select", json={"col": 8, "row": 8})
    client.post("/api/point", json={"point_id": "wounded_scout"})

    response = client.post(
        "/api/action",
        json={
            "text": "Dajemy słowo, że dostarczymy meldunki.",
            "selected_goal_id": "calm_scout",
            "check_participants": "single_actor",
            "participant_actor_ids": ["cleric"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["pending"] is None
    assert {"key": "scout_calmed", "value": True} in data["flags"]
    assert {"key": "scout_trusts_party", "value": True} in data["flags"]
    assert data["conversation"]["entries"][-1]["title"] == "Ranny zwiadowca"
    assert "Meldunki muszą dotrzeć" in data["conversation"]["entries"][-1]["body"]
    assert {goal["id"] for goal in data["active_point"]["npc"]["goals"]} == {
        "help_scout",
        "ask_scout",
        "pressure_scout",
    }


def test_exploration_ui_points_are_board_first_and_text_redirects_to_point_led():
    session = _session()
    client = create_app(session).test_client()
    _submit_force_gate(client)
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
    client.post("/api/travel", json={"zone_id": "courtyard"})
    setup = client.get("/api/state").get_json()
    assert setup["flow"]["stage"] == "party_setup"
    assert setup["exploration_setup"]["current_step"]["assignment_point_id"] == "wounded_scout"
    client.post("/api/board/select", json={"col": 8, "row": 8})

    state = client.get("/api/state").get_json()
    wounded = next(point for point in state["current_zone_points"] if point["id"] == "wounded_scout")
    assert wounded["color"] == "fioletowy"
    assert wounded["positions"] == [[8, 8]]

    response = client.post("/api/action", json={"text": "Chcemy zbadać rannego zwiadowcę."})

    assert response.status_code == 200
    data = response.get_json()
    assert data["pending"] is None
    assert "podświetlone na fioletowy" in data["messages"][-1]["body"]


def test_exploration_ui_sets_pending_gate_skirmish_after_gate_opens():
    client = _client()
    _submit_force_gate(client, "Hałasujemy przy bramie.")
    client.post("/api/decision", json={"decision": "accept"})
    data = client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}}).get_json()

    assert data["pending_encounter"] is None
    data = _confirm_fallen_gate_setup(client)

    assert data["pending_encounter"]["trigger_id"] == "gate_open_skirmish"
    assert data["pending_encounter"]["encounter_scenario"] == "content/scenarios/gate_skirmish.json"
    assert {"label": "Encounter", "value": "Gobliny za bramą"} in data["scene_status"]


def test_exploration_ui_runs_guided_encounter_setup_after_trigger():
    session = _session()
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()
    _submit_force_gate(client, "Hałasujemy przy bramie.")
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    opening = _resolve_encounter_opening(client)

    assert opening["pending_encounter"]["opening"]["outcome"] == "no_surprise"

    setup_started = client.post("/api/encounter/setup/start").get_json()
    setup = setup_started["encounter_setup"]
    assert setup["scenario_id"] == "gate_skirmish"
    assert setup["status"] == "active"
    assert setup["current_step"]["label"] == "Start walki"
    assert setup["step_count"] >= 3

    next_step = client.post("/api/encounter/setup/confirm").get_json()["encounter_setup"]
    assert next_step["current_step"]["label"] == "pola startowe bohaterów"
    assert next_step["current_step"]["positions"] == [[7, 6], [8, 6], [9, 6]]
    assert next_step["current_step"]["requires_board_assignment"] is True
    assert next_step["current_step"]["assignment_actor_id"] == "hero"

    board.clicks.append((8, 6))
    rogue_step = client.post("/api/board/scan").get_json()["encounter_setup"]
    assert rogue_step["current_step"]["label"] == "pola startowe bohaterów"
    assert rogue_step["current_step"]["assignment_actor_id"] == "rogue"
    assert rogue_step["current_step"]["available_positions"] == [[7, 6], [9, 6]]

    board.clicks.append((9, 6))
    cleric_step = client.post("/api/board/scan").get_json()["encounter_setup"]
    assert cleric_step["current_step"]["label"] == "pola startowe bohaterów"
    assert cleric_step["current_step"]["assignment_actor_id"] == "cleric"
    assert cleric_step["current_step"]["available_positions"] == [[7, 6]]

    board.clicks.append((7, 6))
    enemy_state = client.post("/api/board/scan").get_json()
    enemy_step = enemy_state["encounter_setup"]
    assert enemy_step["current_step"]["label"] == "jawnych przeciwników i NPC"
    assert enemy_step["current_step"]["positions"] == [[7, 9], [11, 7]]
    assert enemy_state["board_selection"]["legal_position_count"] == 0
    assert enemy_state["board_selection"]["auto_arm"] is False

    while True:
        state = _advance_encounter_setup(client, board)
        setup = state["encounter_setup"]
        if setup["status"] == "completed":
            break

    assert setup["current_step"] is None
    assert any(message["title"] == "Setup zakończony" for message in state["messages"])


def test_exploration_ui_can_assign_player_start_from_ui_position_buttons():
    session = _session()
    client = create_app(session).test_client()
    _submit_force_gate(client, "Hałasujemy przy bramie.")
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    _resolve_encounter_opening(client)

    client.post("/api/encounter/setup/start")
    client.post("/api/encounter/setup/confirm")

    rogue_step = client.post("/api/board/select", json={"col": 8, "row": 6}).get_json()["encounter_setup"]
    assert rogue_step["current_step"]["label"] == "pola startowe bohaterów"
    assert rogue_step["current_step"]["assignment_actor_id"] == "rogue"
    assert rogue_step["current_step"]["available_positions"] == [[7, 6], [9, 6]]

    cleric_step = client.post("/api/board/select", json={"col": 9, "row": 6}).get_json()["encounter_setup"]
    assert cleric_step["current_step"]["label"] == "pola startowe bohaterów"
    assert cleric_step["current_step"]["assignment_actor_id"] == "cleric"
    assert cleric_step["current_step"]["available_positions"] == [[7, 6]]

    enemy_step = client.post("/api/board/select", json={"col": 7, "row": 6}).get_json()["encounter_setup"]
    assert enemy_step["current_step"]["label"] == "jawnych przeciwników i NPC"
    assert enemy_step["current_step"]["positions"] == [[7, 9], [11, 7]]


def test_exploration_ui_starts_combat_after_setup_and_initiative():
    session = _session()
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()
    _submit_force_gate(client, "Hałasujemy przy bramie.")
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    _resolve_encounter_opening(client)
    client.post("/api/encounter/setup/start")
    while True:
        setup_state = _advance_encounter_setup(client, board)
        if setup_state["encounter_setup"]["status"] == "completed":
            break

    initiative_state = client.post("/api/encounter/initiative/start").get_json()
    assert initiative_state["encounter_initiative"]["current_prompt"]["actor_id"] == "hero"

    after_hero = client.post("/api/encounter/initiative/roll", json={"natural_roll": 14}).get_json()
    assert after_hero["encounter_initiative"]["current_prompt"]["actor_id"] == "rogue"

    after_rogue = client.post("/api/encounter/initiative/roll", json={"natural_roll": 10}).get_json()
    assert after_rogue["encounter_initiative"]["current_prompt"]["actor_id"] == "cleric"

    after_cleric = client.post("/api/encounter/initiative/roll", json={"natural_roll": 8}).get_json()
    initiative = after_cleric["encounter_initiative"]
    combat = after_cleric["combat"]

    assert initiative["status"] == "completed"
    assert [entry["actor_id"] for entry in initiative["order"]] == [
        combat["current_actor"]["id"],
        *[entry["actor_id"] for entry in initiative["order"][1:]],
    ]
    assert combat["status"] == "active"
    assert combat["round_number"] == 1
    assert len(combat["actors"]) == 5
    assert any(message["title"] == "Kolejność inicjatywy" for message in after_cleric["messages"])


def test_exploration_ui_happy_path_returns_to_player_after_enemy_turns():
    session = _session(active=False)
    board = FakeBoardConnection(clicks=[(9, 2)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    ready = client.get("/api/state").get_json()
    assert ready["flow"]["stage"] == "ready_to_start"

    started = client.post("/api/start", json={}).get_json()
    assert started["flow"]["stage"] == "party_setup"

    preview_ready = _finish_map_setup(client)
    assert preview_ready["flow"]["stage"] == "spell_preparation"
    preview_ready = client.post(
        "/api/spell-preparation/confirm",
        json={"actor_id": "cleric", "spell_ids": ["healing_word", "bless_attack_bonus"]},
    ).get_json()
    assert preview_ready["flow"]["stage"] == "location_preview"

    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["preview_zone"]["id"] == "gate"
    assert preview["active_challenge"] is None

    active = client.post("/api/location/confirm-preview", json={}).get_json()
    assert active["flow"]["stage"] == "location_active"
    assert active["active_challenge"]["id"] == "closed_gate"

    action = _submit_force_gate(client, "Hałasujemy przy bramie.").get_json()
    assert action["pending"]["stage"] == "decision"

    accepted = client.post("/api/decision", json={"decision": "accept"}).get_json()
    assert accepted["required_rolls"][0]["actor_id"] == "hero"
    assert accepted["required_rolls"][0]["actor_name"] == "Bohater"
    assert accepted["required_rolls"][0]["die_sides"] == 20

    resolved = client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}}).get_json()
    assert resolved["flow"]["stage"] == "interaction_result"

    setup_ready = _confirm_fallen_gate_setup(client)
    assert setup_ready["pending_encounter"]["trigger_id"] == "gate_open_skirmish"
    _resolve_encounter_opening(client)

    setup_started = client.post("/api/encounter/setup/start", json={}).get_json()
    assert setup_started["encounter_setup"]["status"] == "active"
    while True:
        setup_state = _advance_encounter_setup(client, board)
        if setup_state["encounter_setup"]["status"] == "completed":
            break

    initiative = client.post("/api/encounter/initiative/start", json={}).get_json()
    assert initiative["encounter_initiative"]["current_prompt"]["actor_id"] == "hero"

    client.post("/api/encounter/initiative/roll", json={"natural_roll": 20})
    client.post("/api/encounter/initiative/roll", json={"natural_roll": 19})
    combat_started = client.post("/api/encounter/initiative/roll", json={"natural_roll": 18}).get_json()
    combat = combat_started["combat"]
    first_player_id = combat["current_actor"]["id"]
    assert combat["status"] == "active"
    assert combat["current_actor"]["faction"] == "ally"
    assert first_player_id == "rogue"

    move_destination = next(tile for tile in combat["movement"]["destinations"] if tile["cost_feet"] == 5)
    moved = client.post(
        "/api/combat/move",
        json={"col": move_destination["col"], "row": move_destination["row"]},
    ).get_json()
    assert moved["combat"]["current_actor"]["id"] == first_player_id
    assert moved["combat"]["movement"]["remaining_feet"] == 25
    assert moved["combat"]["turn_action"]["action_use"] == "action_available"

    attack_option = next(
        option
        for option in moved["combat"]["turn_action_menu"]["options"]
        if option["action"] == "select_attack_source"
    )
    targeting = client.post(
        "/api/combat/turn-actions/confirm",
        json={"option_id": attack_option["id"]},
    ).get_json()
    target = targeting["combat"]["legal_targets"][0]
    selected = client.post(
        "/api/board/select",
        json={"col": target["position"][0], "row": target["position"][1]},
    ).get_json()
    assert selected["combat"]["pending_player_attack"]["stage"] == "confirm_attack"
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert selected["combat"]["turn_action"]["action_use"] == "action_available"

    confirmed = client.post("/api/combat/player-attack-confirm", json={}).get_json()
    assert confirmed["combat"]["pending_player_attack"]["stage"] == "attack_roll"

    attack_roll = client.post("/api/combat/player-attack-roll", json={"natural_roll": 20}).get_json()
    assert attack_roll["combat"]["pending_player_attack"]["stage"] == "damage_roll"

    damaged = client.post("/api/combat/player-damage", json={"damage": 5}).get_json()
    assert damaged["combat"]["pending_player_attack"] is None
    assert damaged["combat"]["turn_action"]["action_use"] == "action_used"

    state = client.post("/api/combat/end-turn", json={}).get_json()
    while state["combat"]["current_actor"]["faction"] == "ally":
        state = client.post("/api/combat/end-turn", json={}).get_json()

    assert state["combat"]["current_actor"]["faction"] == "enemy"
    assert state["combat"]["round_number"] == 1

    while state["combat"]["current_actor"]["faction"] == "enemy":
        state = _resolve_enemy_turn_from_ui(client, board)

    assert state["combat"]["current_actor"]["faction"] == "ally"
    assert state["combat"]["round_number"] == 2
    assert state["combat"]["enemy_turn_preview"] is None
    assert state["combat"]["enemy_turn_result"] is None
    assert any(message["title"] == "Tura przeciwnika" for message in state["messages"])


def test_exploration_ui_board_scan_selects_travel_zone_and_updates_leds():
    session = _session()
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    app = create_app(session)
    client = app.test_client()

    _submit_force_gate(client, "Wyważamy bramę głośno.")
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16, "rogue": 1, "cleric": 1}})
    _confirm_fallen_gate_setup(client)
    session.resolved_encounter_trigger_ids.add("gate_open_skirmish")
    session.pending_encounter = None

    assert board.led_calls

    response = client.post("/api/board/scan")
    data = response.get_json()

    assert response.status_code == 200
    assert data["current_zone"]["id"] == "gate"
    assert data["board"]["connected"] is True
    assert data["flow"]["stage"] == "location_preview"
    assert data["flow"]["preview_zone"]["id"] == "courtyard"
    assert "Dziedziniec" in data["board"]["message"]
