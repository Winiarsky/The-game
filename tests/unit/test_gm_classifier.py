import pytest
from pydantic import ValidationError

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import ExplorationState
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmProposalValidationError,
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
        "dc": 13,
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


def test_gm_classifier_ignores_extra_llm_fields_but_rejects_zero_success_progress():
    proposal = _proposal(messages=[], progress_on_success=0)
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcemy zrobić podkop.",
    )

    with pytest.raises(GmProposalValidationError, match="co najmniej 1 punkt postępu"):
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
        approach_tags=["crafting"],
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
    assert option.ability_check.dc == 13
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
    assert "lina nie pozwala latać" in payload["zone_context"]["forbidden_assumptions"]
    assert "przelot na linie bez magii" in payload["challenge"]["context"]["impossible_approaches"]
    assert "szybki podkop pod kamienną bramą bez odpowiednich narzędzi i czasu" in payload["challenge"]["context"]["impossible_approaches"]
    assert payload["dynamic_state"]["challenge_progress"]["current"] == 0
    assert payload["dynamic_state"]["inventory_resource_ids"] == ["rope", "wedge"]


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
