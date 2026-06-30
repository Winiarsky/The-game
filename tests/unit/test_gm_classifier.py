import pytest
from pydantic import ValidationError

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import ExplorationState
from dnd_board_game.llm import (
    GeminiGmClassifierClient,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    GmDeclarationThreadEntry,
    GmClassifierProposal,
    GmPreparationEffect,
    GmProposalValidationError,
    GroqGmClassifierClient,
    build_gm_classifier_request,
    challenge_option_from_validated_proposal,
    validate_gm_classifier_proposal,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    return exploration, ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )


def _proposal(**overrides):
    data = {
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
        "consequences": [
            {"trigger": "failure", "type": "add_noise", "value": 1},
            {"trigger": "critical_failure", "type": "add_complication", "value": "minor_injury"},
        ],
        "success_message": "Wchodzicie górą.",
        "failure_message": "Przęsła są śliskie, ale robicie postęp.",
        "critical_failure_message": "Ktoś boleśnie spada.",
        "player_narration": "Lina może pomóc wejść po zniszczonych przęsłach.",
    }
    data.update(overrides)
    return GmClassifierProposal.model_validate(data)


def test_gm_classifier_validates_owned_resource_with_matching_tag():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną.",
    )

    validated = validate_gm_classifier_proposal(_proposal(), request)

    assert [resource.id for resource in validated.resources] == ["rope"]


def test_gm_classifier_rejects_resource_without_matching_tag():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używamy liny do podważenia mechanizmu.",
    )
    proposal = _proposal(approach_tags=["lever"], used_resource_ids=["rope"])

    with pytest.raises(GmProposalValidationError, match="nie pasuje tagami"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_resource_not_in_inventory():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używamy starej piły.",
    )
    proposal = _proposal(approach_tags=["saw"], used_resource_ids=["saw"])

    with pytest.raises(GmProposalValidationError, match="Drużyna nie ma zasobu"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_request_payload_contains_active_preparation_effects():
    exploration, state = _state()
    effect = GmPreparationEffect.model_validate(
        {
            "type": "modifier",
            "label": "Lina przygotowana na przęsłach",
            "target_tags": ["climbing"],
            "value": 2,
            "duration": "next_attempt",
            "source": "test",
        }
    )
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wchodzimy górą.",
        active_preparation_effects=(effect,),
    )

    payload = request.to_prompt_payload()

    assert payload["active_preparation_effects"][0]["label"] == "Lina przygotowana na przęsłach"


def test_gm_classifier_accepts_modifier_preparation_without_roll():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Owijamy linę, żeby łatwiej wejść później.",
    )
    proposal = _proposal(
        approach_label="Przygotowanie liny",
        approach_tags=["climbing"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "modifier",
            "label": "Lina stabilizuje wspinaczkę",
            "target_tags": ["climbing"],
            "value": 2,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.value == 2


def test_gm_classifier_rejects_preparation_modifier_outside_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Przygotowujemy bardzo mocny bonus.",
    )
    proposal = _proposal(
        approach_label="Przesadne przygotowanie",
        approach_tags=["climbing"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "modifier",
            "label": "Przesadny bonus",
            "target_tags": ["climbing"],
            "value": 5,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    with pytest.raises(GmProposalValidationError, match="Modyfikator przygotowania jest poza zakresem policy"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_accepts_combined_preparation_and_attempt():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Owijamy linę i od razu wchodzimy górą.",
    )
    proposal = _proposal(
        action_flow="combined",
        requires_roll_now=True,
        preparation_effect={
            "type": "modifier",
            "label": "Lina stabilizuje wspinaczkę",
            "target_tags": ["climbing"],
            "value": 2,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.action_flow.value == "combined"


def test_gm_classifier_rejects_unknown_skill_and_bad_dc():
    with pytest.raises(ValidationError):
        _proposal(dc=30)

    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Robimy coś dziwnego.",
    )
    proposal = _proposal(skill="alchemy")
    with pytest.raises(GmProposalValidationError, match="Nieobsługiwana umiejętność"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_tag_outside_challenge_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy przekupić bramę.",
    )
    proposal = _proposal(approach_tags=["bribe"], used_resource_ids=())

    with pytest.raises(GmProposalValidationError, match="Nieobsługiwane tagi podejścia"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_dc_outside_challenge_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą.",
    )
    proposal = _proposal(dc=20, used_resource_ids=())

    with pytest.raises(GmProposalValidationError, match="nie zgadza się z dc_policy"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_dc_that_does_not_match_difficulty_tier():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą.",
    )
    proposal = _proposal(difficulty_tier="medium", dc=12, used_resource_ids=())

    with pytest.raises(GmProposalValidationError, match="nie zgadza się z dc_policy"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_unknown_difficulty_tier():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą.",
    )
    proposal = _proposal(difficulty_tier="legendary", dc=15, used_resource_ids=())

    with pytest.raises(GmProposalValidationError, match="nie jest dozwolony"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_too_many_resources_for_challenge_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną i klinem.",
    )
    proposal = _proposal(approach_tags=["climbing", "lever"], used_resource_ids=["rope", "wedge"])

    with pytest.raises(GmProposalValidationError, match="maksymalnie 1 zasobów"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_ignores_extra_llm_fields_but_rejects_success_progress_outside_policy():
    proposal = _proposal(messages=[], progress_on_success=0)
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcemy zrobić podkop.",
    )

    with pytest.raises(GmProposalValidationError, match="Postęp przy sukcesie jest poza zakresem policy"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_unowned_declared_resource():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcemy zrobić podkop łopatą.",
    )
    proposal = _proposal(
        approach_label="Podkop pod bramą",
        approach_tags=["lever"],
        ability="strength",
        skill="athletics",
        used_resource_ids=["shovel"],
    )

    with pytest.raises(GmProposalValidationError, match="Drużyna nie ma zasobu: shovel"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_environment_search_error_uses_player_narration():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Rozglądamy się za śladami.",
    )
    proposal = GmClassifierProposal.model_validate(
        {
            "intent_type": "environment_search",
            "player_narration": "To brzmi jak rozglądanie się po okolicy, a nie konkretna próba sforsowania bramy.",
        }
    )

    with pytest.raises(GmProposalValidationError, match="rozglądanie się po okolicy"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_narration_that_conflicts_with_technical_approach():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcemy wyważyć bramę z rozbiegu.",
    )
    proposal = _proposal(
        approach_label="Wyważenie bramy",
        approach_tags=["heavy_force", "noise"],
        ability="strength",
        skill="athletics",
        used_resource_ids=[],
        player_narration="Najlepszym podejściem jest podważenie mechanizmu klinem, które będzie testowane.",
    )

    with pytest.raises(GmProposalValidationError, match="inne podejście niż techniczne pola testu"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_builds_temporary_challenge_option():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną.",
    )

    validated = validate_gm_classifier_proposal(_proposal(), request)
    option = challenge_option_from_validated_proposal(validated)

    assert option.id == "gm_generated"
    assert option.ability_check.ability == "dexterity"
    assert option.ability_check.skill == "acrobatics"
    assert option.ability_check.dc == 15
    assert option.progress_on_success == 2
    assert option.progress_on_failure == 1
    assert option.failure_noise == 1
    assert option.critical_failure_complication == "minor_injury"


def test_gm_classifier_request_payload_contains_context_layers_and_dynamic_state():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną.",
    )

    payload = request.to_prompt_payload()

    assert "brak działającego mechanizmu lotu" in payload["scenario_context"]["forbidden_assumptions"]
    assert payload["challenge"]["llm_policy"]["dc_policy"]["tiers"][1]["id"] == "medium"
    assert payload["challenge"]["llm_policy"]["dc_policy"]["tiers"][1]["dc"] == 15
    assert "lina nie pozwala latać" in payload["zone_context"]["forbidden_assumptions"]
    assert "przelot na linie bez magii" in payload["challenge"]["context"]["impossible_approaches"]
    assert "szybki podkop pod kamienną bramą bez odpowiednich narzędzi i czasu" in payload["challenge"]["context"]["impossible_approaches"]
    assert payload["challenge"]["llm_policy"]["dc_range"] == [8, 18]
    assert payload["challenge"]["llm_policy"]["max_resources_per_attempt"] == 1
    assert "heavy_force" in payload["allowed_tags"]
    assert "bribe" not in payload["allowed_tags"]
    assert "crafting" in payload["allowed_skills"]
    assert payload["dynamic_state"]["challenge_progress"]["current"] == 0
    assert payload["dynamic_state"]["inventory_resource_ids"] == ["rope", "wedge"]
    assert payload["dynamic_state"]["attempt_history"] == []


def test_gm_classifier_request_payload_contains_declaration_thread():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Dobra, to bez butów.",
        declaration_thread=(
            GmDeclarationThreadEntry("player", "Przeskakuję w skocznych butach.", "Odrzucono: brak takiego zasobu."),
            GmDeclarationThreadEntry("system", "Drużyna nie ma skocznych butów."),
        ),
    )

    payload = request.to_prompt_payload()

    assert payload["declaration_thread"][0]["content"] == "Przeskakuję w skocznych butach."
    assert payload["declaration_thread"][0]["outcome"] == "Odrzucono: brak takiego zasobu."
    assert payload["player_action"] == "Dobra, to bez butów."


def test_gm_classifier_request_payload_contains_attempt_history_after_roll():
    exploration, state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "break_picket")
    from dnd_board_game.exploration import resolve_challenge_option
    from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll

    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 10))
    result = resolve_challenge_option(state, challenge, option, roll)
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=result.state,
        player_action="Próbujemy dalej podważać sztachety.",
    )

    history = request.to_prompt_payload()["dynamic_state"]["attempt_history"]
    assert history[0]["option_id"] == "break_picket"
    assert history[0]["progress_added"] == 1


def test_gm_declaration_analysis_model_accepts_player_question():
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Najciszej wygląda manipulowanie mechanizmem albo szukanie obejścia.",
            "normalized_intent": "Pytanie o ciche podejście.",
            "reason": "Gracz pyta o ryzyko, nie deklaruje działania.",
            "confidence": 0.9,
        }
    )

    assert analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION


def test_groq_client_retries_429_then_parses_response(monkeypatch):
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną.",
    )
    responses = [
        _FakeHttpResponse(429, {"Retry-After": "0"}),
        _FakeHttpResponse(
            200,
            {},
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"analysis_type":"plausible","player_message":"","normalized_intent":"wspinaczka","reason":"","confidence":0.8}'
                        }
                    }
                ]
            },
        ),
    ]

    monkeypatch.setattr("dnd_board_game.llm.gm_classifier.requests.post", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr("dnd_board_game.llm.gm_classifier.time.sleep", lambda _seconds: None)

    client = GroqGmClassifierClient(api_key="test", max_retries=1)

    analysis = client.analyze(request)

    assert analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE


def test_gemini_client_retries_429_then_parses_response(monkeypatch):
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą z liną.",
    )
    responses = [
        _FakeHttpResponse(429, {"Retry-After": "0"}),
        _FakeHttpResponse(
            200,
            {},
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"analysis_type":"plausible","player_message":"","normalized_intent":"wspinaczka","reason":"","confidence":0.8}'
                                }
                            ]
                        }
                    }
                ]
            },
        ),
    ]
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return responses.pop(0)

    monkeypatch.setattr("dnd_board_game.llm.gm_classifier.requests.post", fake_post)
    monkeypatch.setattr("dnd_board_game.llm.gm_classifier.time.sleep", lambda _seconds: None)

    client = GeminiGmClassifierClient(api_key="test", model="gemini-test", max_retries=1)

    analysis = client.analyze(request)

    assert analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
    assert calls[0][0][0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
    assert calls[0][1]["headers"]["x-goog-api-key"] == "test"
    assert calls[0][1]["json"]["generation_config"]["response_mime_type"] == "application/json"


class _FakeHttpResponse:
    def __init__(self, status_code, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        return self._payload


def test_gm_classifier_rejects_technical_use_of_forbidden_context():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wsiadam na linę i przelatuję nad bramą.",
    )
    proposal = _proposal(
        approach_label="przelot na linie bez magii",
        approach_tags=["climbing"],
        used_resource_ids=["rope"],
    )

    with pytest.raises(GmProposalValidationError, match="zakazanego założenia"):
        validate_gm_classifier_proposal(proposal, request)
