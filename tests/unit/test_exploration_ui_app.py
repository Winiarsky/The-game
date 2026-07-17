from dnd_board_game.llm import GmClassifierProposal, GmDeclarationAnalysis, GmDeclarationAnalysisType, NpcInteractionProposal
from dnd_board_game.exploration import reveal_exploration_points
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
    return session


def _page_assets(client) -> tuple[str, str, str]:
    html = client.get("/").get_data(as_text=True)
    javascript = client.get("/static/exploration.js").get_data(as_text=True)
    stylesheet = client.get("/static/exploration.css").get_data(as_text=True)
    return html, javascript, stylesheet


def test_combat_ui_exposes_manual_enemy_saving_throw_endpoint() -> None:
    html, javascript, _stylesheet = _page_assets(_client())

    assert "/api/combat/enemy-saving-throw" in javascript
    assert "pending_enemy_saving_throw" in javascript
    assert "enemy-saving-throw-roll" in javascript
    assert "/static/exploration.js" in html


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


def test_exploration_ui_page_includes_session_log_panel():
    client = _client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="session-log-panel"' in html
    assert 'id="session-log-filter"' in html
    javascript = client.get("/static/exploration.js").get_data(as_text=True)
    assert "/api/session-log" in javascript


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
    assert "data-preparation-spell" in javascript
    assert "confirmSpellPreparation()" in javascript
    assert "/api/spell-preparation/confirm" in javascript


def test_exploration_ui_page_includes_short_rest_flow():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)

    assert 'id="short-rest-button"' in html
    assert "Krótki odpoczynek" in javascript
    assert "spendShortRestHitDie" in javascript
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
    assert 'id="pending-title"' in html
    assert html.index('id="chat-stream"') < html.index('id="pending-panel"') < html.index('id="chat-composer"')
    assert '<h3>Propozycja MG</h3>' not in html
    assert "Co robicie lub o co pytacie?" in html
    assert "Napisz wiadomość do MG" in html
    assert 'id="chat-typing"' in html
    assert "Opuść interakcję" in html
    assert 'id="exploration-menu-panel"' in html
    assert "Nie macie pomysłu? Zobaczcie inspiracje" not in javascript
    assert "Wskazówki MG i mechanika sceny" not in javascript
    assert "sceneConversationHtml" in javascript
    assert "sceneIntroMessageHtml" in javascript
    assert "waitingForGm" in javascript
    assert "leaveChatInstance" in javascript
    assert "resolveNpcTransition" in javascript
    assert "/api/npc-transition/resolve" in javascript
    assert ".npc-transition-reactions" in stylesheet
    assert ".scene-image" in stylesheet
    assert ".conversation-entry" in stylesheet
    assert ".conversation-system-card" in stylesheet
    assert "function pendingTitle" in javascript
    assert "if (proposal.player_narration) lines.push" not in javascript
    assert ".chat-typing" in stylesheet
    assert "body.chat-instance-mode" in stylesheet


def test_exploration_ui_page_includes_snapshot_controls():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)

    assert 'id="snapshot-save-button"' in html
    assert 'id="snapshot-load-button"' in html
    assert "/api/snapshot/save" in javascript
    assert "/api/snapshot/load" in javascript


def test_exploration_ui_page_and_api_include_scenario_end_lifecycle():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)
    response = client.post("/api/scenario/finish", json={})

    assert 'id="active-effects"' in html
    assert 'id="finish-scenario-button"' in html
    assert "Źródło:" in javascript
    assert "/api/scenario/finish" in javascript
    assert response.status_code == 200
    assert response.get_json()["flow"]["stage"] == "scenario_complete"


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


def test_exploration_ui_page_includes_gm_decision_correction_controls():
    client = _client()

    html, javascript, _stylesheet = _page_assets(client)

    assert '<script src="/static/exploration.js"></script>' in html
    assert "Popraw decyzję MG" in javascript
    assert "decisionCorrectionHtml" in javascript
    assert "correction-roll-mode" in javascript
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
    assert 'data-allow-busy="true" onclick="resolveEnemyTurn()"' in html
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
    assert "inCombat ? 'Walka' : 'Eksploracja'" in html
    assert "latestCombatMessageHtml()" in html
    assert "combatCurrentStepHtml" in html
    assert "combatPrimaryActionHtml" in html
    assert "combatLastResultHtml" in html
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
    assert "combatMainPromptHtml" in html
    assert "combatInstructionText" in html
    assert "combatActorStatusHtml" in html
    assert "actorHpLabel" in html
    assert "combat-current-step" in html
    assert "combat-mini-status" in html
    assert "combat-last-result" in html
    assert "combat-stage" in html
    assert "combat-action-card" in html
    assert "Szczegóły walki" in html
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
    assert "playerTurnScanLoop" in html
    assert "boardScanInFlight" in html
    assert "boardScanToken" in html
    assert "stopBoardScanLoop()" in html
    assert "playerTurnScanLoop = false;" in html
    assert "isAllyCombatTurnActive()" in html
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
    assert "useCombatDash()" in html
    assert "useCombatDodge()" in html
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
    assert ">Ready<" in html
    assert ">Help<" in html
    assert ">Dash<" in html
    assert ">Unik<" in html
    assert ">Odwrót<" in html
    assert "Atak okazyjny" in html
    assert "Wykonaj atak okazyjny" in html
    assert "Potwierdź ruch mimo ryzyka" in html
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
    assert "drugim kliknięciem" not in html


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


def test_exploration_ui_initial_payload_requires_spell_preparation_and_hides_actions():
    client = _client(active=False)

    data = client.get("/api/state").get_json()

    assert data["flow"]["stage"] == "spell_preparation"
    assert data["flow"]["can_start"] is False
    assert data["spell_preparation"]["current_actor_id"] == "cleric"
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
    session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("healing_word", "bless_attack_bonus"),
    )
    board = FakeBoardConnection(clicks=[(9, 2), (9, 2)])
    session.attach_board_connection(board, backend="simulator")
    app = create_app(session)
    client = app.test_client()

    ready = client.get("/api/state").get_json()
    assert ready["flow"]["stage"] == "ready_to_start"

    started = client.post("/api/start", json={}).get_json()
    assert started["flow"]["stage"] == "party_setup"

    started = _finish_map_setup(client)
    assert started["flow"]["stage"] == "location_preview"
    assert started["flow"]["preview_zone"] is None
    assert [zone["id"] for zone in started["flow"]["available_locations"]] == ["gate", "courtyard", "tower"]
    assert [zone["available"] for zone in started["flow"]["available_locations"]] == [True, False, False]

    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["stage"] == "location_preview"
    assert preview["flow"]["preview_zone"]["id"] == "gate"
    assert preview["active_challenge"] is None

    repeated_preview = client.post("/api/board/scan", json={}).get_json()
    assert repeated_preview["flow"]["stage"] == "location_preview"
    assert repeated_preview["flow"]["preview_zone"]["id"] == "gate"
    assert repeated_preview["active_challenge"] is None

    active = client.post("/api/location/confirm-preview", json={}).get_json()
    assert active["flow"]["stage"] == "location_active"
    assert active["active_challenge"]["id"] == "closed_gate"


def test_exploration_ui_blocked_visible_location_shows_locked_preview():
    session = _session(active=False)
    session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("healing_word", "bless_attack_bonus"),
    )
    board = FakeBoardConnection(clicks=[(9, 10)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    client.post("/api/start", json={})
    _finish_map_setup(client)
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


def test_exploration_ui_accept_can_select_lead_actor():
    client = _client()

    client.post("/api/action", json={"text": "Wyważamy bramę."})
    response = client.post("/api/decision", json={"decision": "accept", "lead_actor_id": "rogue"})

    assert response.status_code == 200
    roll = response.get_json()["required_rolls"][0]
    assert roll["actor_id"] == "rogue"
    assert roll["actor_name"] == "Łotrzyca"
    assert roll["die_sides"] == 20
    assert roll["label"] == "d20"


def test_exploration_ui_decision_correction_endpoint_updates_pending_option():
    client = _client()

    client.post("/api/action", json={"text": "Wyważamy bramę z pomocą."})
    response = client.post(
        "/api/decision/correction",
        json={
            "mechanic_id": "lead_with_help_check",
            "check_participants": "lead_with_help",
            "check_aggregation": "lead_result",
            "lead_actor_id": "rogue",
            "helper_actor_id": "hero",
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
    assert data["selected_lead_actor_id"] == "rogue"
    assert data["selected_helper_actor_id"] == "hero"
    assert data["pending"]["option"]["mechanic"]["id"] == "lead_with_help_check"
    assert data["pending"]["option"]["check_participants"] == "lead_with_help"
    assert data["pending"]["option"]["ability"] == "dexterity"
    assert data["pending"]["option"]["skill"] == "acrobatics"
    assert data["pending"]["option"]["dc"] == 13
    assert data["pending"]["option"]["roll_mode"] == "disadvantage"
    assert data["pending"]["option"]["situational_modifiers"][0]["label"] == "Mokra lina"


def test_exploration_ui_decision_correction_endpoint_updates_improvised_tool():
    client = _client()

    client.post("/api/action", json={"text": "Używam starej deski jak dźwigni."})
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

    assert response.status_code == 200
    data = response.get_json()
    assert data["pending"]["option"]["mechanic"]["id"] == "improvised_tool_check"
    assert data["pending"]["option"]["improvised_tool"]["label"] == "Stara deska"
    assert data["pending"]["option"]["improvised_tool"]["effect_modifier"] == 1


def test_exploration_ui_reset_endpoint_restores_state():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})

    response = client.post("/api/reset", json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "spell_preparation"
    assert data["active_challenge"] is None


def test_exploration_ui_confirms_spell_preparation_through_api():
    client = _client(active=False)

    response = client.post(
        "/api/spell-preparation/confirm",
        json={
            "actor_id": "cleric",
            "spell_ids": ["radiant_line", "healing_word"],
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"]["stage"] == "waiting_for_board"
    cleric = data["spell_preparation"]["actors"][0]
    assert cleric["confirmed"] is True
    assert {
        spell["id"]
        for spell in cleric["spells"]
        if spell["prepared"] and not spell["always_prepared"]
    } == {"radiant_line", "healing_word"}


def test_exploration_ui_shows_and_handles_travel_after_completed_challenge():
    client = _client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    completed = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()

    assert completed["active_challenge"] is None
    assert completed["flow"]["stage"] == "interaction_result"

    completed = _confirm_fallen_gate_setup(client)

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
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
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
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    _confirm_fallen_gate_setup(client)
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
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

    roll_pending = client.post("/api/decision", json={"decision": "accept"}).get_json()
    assert roll_pending["pending"]["check_plan"]["dc"] == 10
    accepted = client.post("/api/rolls", json={"rolls": {"hero": 20}}).get_json()
    assert {"key": "scout_calmed", "value": True} in accepted["flags"]
    assert {"label": "Ranny zwiadowca", "value": "uspokojony"} in accepted["scene_status"]


def test_exploration_ui_points_are_board_first_and_text_redirects_to_point_led():
    session = _session()
    client = create_app(session).test_client()
    client.post("/api/action", json={"text": "Wyważamy bramę."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
    _confirm_fallen_gate_setup(client)
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
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


def test_exploration_ui_sets_pending_gate_skirmish_after_gate_opens():
    client = _client()
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    data = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()

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
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
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
    enemy_step = client.post("/api/board/scan").get_json()["encounter_setup"]
    assert enemy_step["current_step"]["label"] == "jawnych przeciwników i NPC"
    assert enemy_step["current_step"]["positions"] == [[7, 9], [11, 7]]

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
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
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
    client.post("/api/action", json={"text": "Hałasujemy przy bramie."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
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
    session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("healing_word", "bless_attack_bonus"),
    )
    board = FakeBoardConnection(clicks=[(9, 2)])
    session.attach_board_connection(board, backend="simulator")
    client = create_app(session).test_client()

    ready = client.get("/api/state").get_json()
    assert ready["flow"]["stage"] == "ready_to_start"

    started = client.post("/api/start", json={}).get_json()
    assert started["flow"]["stage"] == "party_setup"

    preview_ready = _finish_map_setup(client)
    assert preview_ready["flow"]["stage"] == "location_preview"

    preview = client.post("/api/board/scan", json={}).get_json()
    assert preview["flow"]["preview_zone"]["id"] == "gate"
    assert preview["active_challenge"] is None

    active = client.post("/api/location/confirm-preview", json={}).get_json()
    assert active["flow"]["stage"] == "location_active"
    assert active["active_challenge"]["id"] == "closed_gate"

    action = client.post("/api/action", json={"text": "Hałasujemy przy bramie."}).get_json()
    assert action["pending"]["stage"] == "decision"

    accepted = client.post("/api/decision", json={"decision": "accept"}).get_json()
    assert accepted["required_rolls"][0]["actor_id"] == "hero"
    assert accepted["required_rolls"][0]["actor_name"] == "Bohater"
    assert accepted["required_rolls"][0]["die_sides"] == 20

    resolved = client.post("/api/rolls", json={"rolls": {"hero": 16}}).get_json()
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

    target = moved["combat"]["legal_targets"][0]
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

    client.post("/api/action", json={"text": "Wyważamy bramę głośno."})
    client.post("/api/decision", json={"decision": "accept"})
    client.post("/api/rolls", json={"rolls": {"hero": 16}})
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
