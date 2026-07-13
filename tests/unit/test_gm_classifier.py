from dataclasses import replace

import pytest
from pydantic import ValidationError

from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import ExplorationState, set_party_zone
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
from dnd_board_game.llm.content_config import load_freeform_grounding_terms, load_llm_core_rules, load_llm_intent_catalog
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
        actors=exploration.actors,
    )

    validated = validate_gm_classifier_proposal(_proposal(), request)

    assert [resource.id for resource in validated.resources] == ["rope"]


def test_gm_classifier_preserves_selected_mechanic_on_generated_option():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Łotrzyca wspina się, a Bohater ją asekuruje.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        selected_mechanic="lead_with_help_check",
        check_participants="lead_with_help",
        check_aggregation="lead_result",
        consequence_targets=["lead_actor", "helper_actor", "scene"],
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert option.mechanic_id == "lead_with_help_check"
    assert option.check_participants.value == "lead_with_help"


def test_gm_classifier_preserves_situational_modifiers_on_generated_option():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="W deszczu wspinam się po mokrej linie.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        roll_mode="normal",
        situational_modifiers=[
            {
                "label": "Mokra lina",
                "modifier": -1,
                "source": "interaction_object",
                "reason": "Opis obiektu i deklaracja wskazują mokrą linę.",
                "roll_mode": "disadvantage",
            }
        ],
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert option.roll_mode.value == "disadvantage"
    assert option.situational_modifiers[0].label == "Mokra lina"
    assert option.situational_modifiers[0].modifier == -1
    assert option.situational_modifiers[0].source.value == "interaction_object"


def test_gm_classifier_preserves_improvised_tool_on_generated_option():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Biorę starą deskę z rumowiska i używam jej jak dźwigni.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        selected_mechanic="improvised_tool_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        approach_label="Dźwignia ze starej deski",
        approach_tags=["lever"],
        ability="strength",
        skill="athletics",
        used_resource_ids=[],
        player_narration="Używasz starej deski z rumowiska jako prowizorycznej dźwigni.",
        improvised_tool={
            "label": "Stara deska",
            "source": "interaction_object",
            "source_detail": "stare deski przy bramie",
            "effect_modifier": 1,
            "risk": "może pęknąć przy krytycznej porażce",
            "reason": "Opis obiektu zawiera stare deski, które mogą działać jak prowizoryczna dźwignia.",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert option.mechanic_id == "improvised_tool_check"
    assert option.improvised_tool is not None
    assert option.improvised_tool.label == "Stara deska"
    assert option.improvised_tool.effect_modifier == 1


def test_gm_classifier_requires_improvised_tool_for_improvised_tool_check():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używam starej deski jak narzędzia.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        selected_mechanic="improvised_tool_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        approach_tags=["lever"],
        used_resource_ids=[],
    )

    with pytest.raises(GmProposalValidationError, match="improvised_tool"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_improvised_tool_on_non_improvised_mechanic():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wspinam się.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        selected_mechanic="single_actor_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        improvised_tool={
            "label": "Stara deska",
            "source": "interaction_object",
            "source_detail": "stare deski przy bramie",
            "effect_modifier": 1,
            "reason": "To powinno wymagać improvised_tool_check.",
        },
    )

    with pytest.raises(GmProposalValidationError, match="tylko dla improvised_tool_check"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_rejects_empty_situational_modifier():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wspinam się.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        situational_modifiers=[
            {
                "label": "Opis bez efektu",
                "modifier": 0,
                "source": "gm",
                "reason": "Nie zmienia rzutu.",
                "roll_mode": "normal",
            }
        ],
    )

    with pytest.raises(GmProposalValidationError, match="nie zmienia rzutu"):
        validate_gm_classifier_proposal(proposal, request)


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


def test_gm_classifier_accepts_advantage_preparation_for_allowed_tag():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Mocujemy linę tak, żeby wejść pewniej.",
    )
    proposal = _proposal(
        approach_label="Przygotowanie przewagi",
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
            "type": "advantage",
            "label": "Lina daje stabilne punkty podparcia",
            "target_tags": ["climbing"],
            "value": 1,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.type.value == "advantage"


def test_gm_classifier_rejects_preparation_with_tag_outside_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Przygotowujemy kosmiczny manewr.",
    )
    proposal = _proposal(
        approach_label="Niepasujące przygotowanie",
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
            "type": "advantage",
            "label": "Kosmiczny bonus",
            "target_tags": ["spaceflight"],
            "value": 1,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    with pytest.raises(GmProposalValidationError, match="nieobsługiwane target_tags"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_accepts_grant_resource_from_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukamy narzędzia do przecięcia spróchniałych desek.",
    )
    proposal = _proposal(
        approach_label="Znalezienie starej piły",
        approach_tags=["scouting", "saw"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "grant_resource",
            "label": "Stare narzędzie w obozowisku",
            "target_tags": ["saw", "picket"],
            "value": 1,
            "duration": "next_attempt",
            "source": "freeform",
            "resource_id": "saw",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.resource_id == "saw"


def test_gm_classifier_rejects_grant_resource_outside_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukamy łomu.",
    )
    proposal = _proposal(
        approach_label="Znalezienie łomu",
        approach_tags=["lever"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "grant_resource",
            "label": "Łom",
            "target_tags": ["lever"],
            "value": 1,
            "duration": "next_attempt",
            "source": "freeform",
            "resource_id": "crowbar",
        },
    )

    with pytest.raises(GmProposalValidationError, match="nie może być przyznany"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_accepts_unlock_option_from_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukamy słabego miejsca w sztachetach.",
    )
    proposal = _proposal(
        approach_label="Odkrycie nacięcia",
        approach_tags=["scouting", "picket"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "unlock_option",
            "label": "Słabe miejsce w sztachetach",
            "target_tags": ["picket"],
            "value": 1,
            "duration": "next_attempt",
            "source": "freeform",
            "option_id": "saw_picket",
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.option_id == "saw_picket"


def test_gm_classifier_rejects_effect_boost_outside_policy():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Przygotowujemy duży efekt.",
    )
    proposal = _proposal(
        approach_label="Przesadny boost",
        approach_tags=["lever"],
        ability=None,
        skill=None,
        dc=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        action_flow="preparation",
        requires_roll_now=False,
        preparation_effect={
            "type": "effect_boost",
            "label": "Przesadna dźwignia",
            "target_tags": ["lever"],
            "value": 3,
            "duration": "next_attempt",
            "source": "freeform",
        },
    )

    with pytest.raises(GmProposalValidationError, match="Wzmocnienie efektu jest poza zakresem policy"):
        validate_gm_classifier_proposal(proposal, request)


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
        actors=exploration.actors,
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
        actors=exploration.actors,
    )

    payload = request.to_prompt_payload()

    assert "brak działającego mechanizmu lotu" in payload["scenario_context"]["forbidden_assumptions"]
    assert payload["challenge"]["llm_policy"]["dc_policy"]["tiers"][1]["id"] == "medium"
    assert payload["challenge"]["llm_policy"]["dc_policy"]["tiers"][1]["dc"] == 15
    assert "lina nie pozwala latać" in payload["zone_context"]["forbidden_assumptions"]
    assert "przelot na linie bez magii" in payload["challenge"]["context"]["impossible_approaches"]
    assert "szybki podkop pod bramą przez twarde kamienne albo betonowe podłoże" in payload["challenge"]["context"]["impossible_approaches"]
    assert payload["challenge"]["llm_policy"]["dc_range"] == [8, 18]
    assert payload["challenge"]["llm_policy"]["allowed_grant_resource_ids"] == ["saw"]
    assert payload["challenge"]["llm_policy"]["allowed_unlock_option_ids"] == ["saw_picket"]
    assert payload["challenge"]["llm_policy"]["effect_boost_range"] == [1, 1]
    assert payload["challenge"]["llm_policy"]["max_resources_per_attempt"] == 1
    assert "heavy_force" in payload["allowed_tags"]
    assert "bribe" not in payload["allowed_tags"]
    assert "crafting" in payload["allowed_skills"]
    assert "athletics" in load_llm_core_rules().skills
    assert payload["dynamic_state"]["challenge_progress"]["current"] == 0
    assert payload["dynamic_state"]["inventory_resource_ids"] == ["rope", "wedge"]
    assert payload["dynamic_state"]["attempt_history"] == []
    party_actors = {actor["id"]: actor for actor in payload["party_actors"]}
    assert "thieves_tools" in {item["id"] for item in party_actors["rogue"]["inventory"]}
    assert "sacred_flame" in party_actors["cleric"]["spell_ids"]
    assert "lead_with_help_check" in {mechanic["id"] for mechanic in payload["allowed_mechanics"]}
    options = {option["id"]: option for option in payload["challenge"]["available_options"]}
    assert options["lockpick_gate"]["requirements"]["item_ids"] == ["thieves_tools"]
    assert options["lockpick_gate"]["mechanic"]["id"] == "use_item_check"
    assert options["reveal_bolt_with_flame"]["requirements"]["spell_ids"] == ["sacred_flame"]
    assert options["reveal_bolt_with_flame"]["mechanic"]["id"] == "use_spell_check"


def test_gm_classifier_request_uses_active_zone_challenge_policy():
    exploration, state = _state()
    courtyard = next(zone for zone in state.zones if zone.id == "courtyard")
    state = set_party_zone(state, courtyard)
    state = replace(state, flags=set_scene_flag(state.flags, "gate_passed", True))

    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Nasłuchujemy i sprawdzamy ślady na dziedzińcu.",
    )

    payload = request.to_prompt_payload()
    assert payload["challenge"]["id"] == "courtyard_search"
    assert "listening" in payload["allowed_tags"]
    assert "heavy_force" not in payload["allowed_tags"]
    assert payload["challenge"]["llm_policy"]["dc_policy"]["tiers"][1]["dc"] == 15


def test_gm_classifier_rejects_gate_style_tag_for_courtyard_challenge():
    exploration, state = _state()
    courtyard = next(zone for zone in state.zones if zone.id == "courtyard")
    state = set_party_zone(state, courtyard)
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Rozwalamy dziedziniec siłą.",
    )
    proposal = _proposal(
        target_challenge_id="courtyard_search",
        approach_label="Siłowe przeszukanie dziedzińca",
        approach_tags=["heavy_force"],
        ability="strength",
        skill="athletics",
        used_resource_ids=[],
    )

    with pytest.raises(GmProposalValidationError, match="Nieobsługiwane tagi"):
        validate_gm_classifier_proposal(proposal, request)


def test_llm_content_config_loads_general_rules_and_grounding_terms():
    rules = load_llm_core_rules()
    grounding = load_freeform_grounding_terms()
    intent_catalog = load_llm_intent_catalog()

    assert "strength" in rules.abilities
    assert "athletics" in rules.skills
    assert any(mention.label == "kwas" for mention in grounding.guarded_resource_mentions)
    assert "social" in intent_catalog.ids
    assert "theft" in intent_catalog.ids


def test_gm_classifier_rejects_unknown_check_aggregation():
    data = _proposal().model_dump(mode="json")
    data["check_aggregation"] = "best_vibes"

    with pytest.raises(ValidationError):
        GmClassifierProposal.model_validate(data)


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
