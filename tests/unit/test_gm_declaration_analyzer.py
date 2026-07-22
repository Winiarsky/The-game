import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import ExplorationState
from dnd_board_game.llm import (
    GmActionFlow,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    GmProposalValidationError,
    PromptId,
    build_gm_classifier_request,
    load_prompt,
    validate_gm_declaration_analysis,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def test_declaration_analyzer_prompt_is_centralized():
    prompt = load_prompt(PromptId.GM_DECLARATION_ANALYZER)

    assert "pistoletem laserowym" in prompt
    assert "sikam na mur i krzyczę" in prompt
    assert "player_question" in prompt
    assert "world_action" in prompt
    assert "immediate_effects" in prompt
    assert "declared_resources" in prompt
    assert "action_flow" in prompt


def test_declaration_analysis_accepts_unsupported_fantasy_breaking_action():
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "unsupported",
            "player_message": "Laserowy pistolet nie pasuje do tej sceny fantasy i nie ma go w zasobach drużyny.",
            "normalized_intent": "Użycie broni technologicznej spoza sceny.",
            "reason": "Deklaracja łamie założenia gatunku i dostępne zasoby.",
            "confidence": 0.95,
        }
    )

    assert analysis.analysis_type == GmDeclarationAnalysisType.UNSUPPORTED


def test_declaration_analysis_accepts_plausible_climbing_interpretation():
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "player_message": "Rozumiem to jako próbę przejścia górą po uszkodzonych przęsłach.",
            "normalized_intent": "Wspinaczka po bramie na drugą stronę.",
            "reason": "Deklaracja pasuje do aktywnego wyzwania i lokalnego kontekstu.",
            "confidence": 0.78,
        }
    )

    assert analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
    assert analysis.action_flow == GmActionFlow.CHALLENGE_ATTEMPT


def test_world_action_accepts_only_policy_grounded_immediate_consequences():
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
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Sikam na mur i wrzeszczę na gobliny.",
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "world_action",
            "player_message": "Mur pozostaje niewzruszony, ale gobliny zdecydowanie już nie śpią.",
            "immediate_effects": [
                {
                    "type": "add_noise",
                    "parameters": {"challenge_id": "closed_gate", "value": 3},
                },
                {
                    "type": "add_complication",
                    "parameters": {
                        "challenge_id": "closed_gate",
                        "value": "alarm_w_strażnicy",
                    },
                },
            ],
        }
    )

    validated = validate_gm_declaration_analysis(analysis, request)

    assert validated.action_flow == GmActionFlow.WORLD_ACTION


def test_world_action_rejects_effect_outside_active_challenge_policy():
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
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Ogłaszam się właścicielem strażnicy.",
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "world_action",
            "player_message": "Strażnica nie uznaje tej procedury sukcesji.",
            "immediate_effects": [
                {
                    "type": "set_flag",
                    "parameters": {"key": "owns_watchtower", "value": True},
                }
            ],
        }
    )

    with pytest.raises(GmProposalValidationError, match="nie jest dozwolona"):
        validate_gm_declaration_analysis(analysis, request)


def test_declaration_analysis_rejects_missing_declared_resource_when_plausible():
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
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wyciągam słoik z kwasem i polewam zawiasy.",
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "action_flow": "challenge_attempt",
            "declared_resources": ["słoik z kwasem"],
            "player_message": "",
            "normalized_intent": "Użycie kwasu na zawiasach.",
            "reason": "Test.",
            "confidence": 0.8,
        }
    )

    with pytest.raises(GmProposalValidationError, match="Drużyna nie ma zadeklarowanych zasobów"):
        validate_gm_declaration_analysis(analysis, request)


def test_declaration_analysis_allows_unsupported_missing_resource_message():
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
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wyciągam słoik z kwasem.",
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "unsupported",
            "action_flow": "unsupported",
            "declared_resources": ["słoik z kwasem"],
            "player_message": "Drużyna nie ma takiego zasobu.",
            "normalized_intent": "Nieposiadany zasób.",
            "reason": "Test.",
            "confidence": 0.9,
        }
    )

    validate_gm_declaration_analysis(analysis, request)
