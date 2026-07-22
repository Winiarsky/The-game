from dataclasses import replace

import pytest
from pydantic import ValidationError

from dnd_board_game.actions import PlayerIntentHint
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import ExplorationState, FixtureOperation, set_party_zone
from dnd_board_game.llm import (
    GeminiGmClassifierClient,
    GmActionFlow,
    GmConversationResponseKind,
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
    validate_gm_declaration_analysis,
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


def test_fixture_action_mechanics_are_grounded_from_fixture_policy():
    exploration, state = _state()
    source_id = "zone:gate:fixture:gate_corroded_hinges"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Odrywam skorodowane zawiasy.",
        actors=exploration.actors,
        explicit_player_intent_hint=PlayerIntentHint.ACTION,
        referenced_crafting_source_ids=(source_id,),
        selected_fixture_source_id=source_id,
        selected_fixture_operation=FixtureOperation.DETACH,
    )
    proposal = _proposal(
        approach_label="Oderwanie skorodowanych zawiasów",
        approach_tags=["rusted_hinge", "lever"],
        ability="dexterity",
        skill="acrobatics",
        difficulty_tier="hard",
        difficulty_reason="LLM zaproponował własne parametry.",
        dc=18,
        progress_on_success=1,
        progress_on_failure=1,
        used_resource_ids=[],
        consequences=[],
        player_narration="Bohater próbuje siłą oderwać skorodowane zawiasy od bramy.",
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert option.ability_check.ability == "strength"
    assert option.ability_check.skill == "athletics"
    assert option.ability_check.dc == 12
    assert option.progress_on_success == 2
    assert option.progress_on_failure == 0
    assert option.success_noise == 1
    assert option.failure_noise == 1
    assert option.failure_complication == "jammed_gate"


def test_declaration_analysis_validates_grounded_fixture_operation():
    exploration, state = _state()
    source_id = "zone:gate:fixture:gate_corroded_hinges"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Odrywam skorodowane zawiasy.",
        actors=exploration.actors,
        player_intent_hint=PlayerIntentHint.ACTION,
        explicit_player_intent_hint=PlayerIntentHint.ACTION,
        referenced_crafting_source_ids=(source_id,),
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "normalized_intent": "Oderwanie skorodowanych zawiasów.",
            "action_target_source_id": source_id,
            "fixture_operation": "detach",
        }
    )

    validated = validate_gm_declaration_analysis(analysis, request)

    assert validated.action_target_source_id == source_id
    assert validated.fixture_operation.value == "detach"


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


def test_gm_classifier_binds_improvised_use_to_selected_scene_source():
    exploration, state = _state()
    source_id = "zone:gate:item:gate_rotten_planks"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używam znalezionej deski jako dźwigni.",
        actors=exploration.actors,
        referenced_crafting_source_ids=(source_id,),
        selected_use_source_id=source_id,
    )
    proposal = _proposal(
        selected_mechanic="improvised_tool_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        approach_label="Użycie znalezionej deski",
        approach_tags=["lever"],
        used_resource_ids=[],
        player_narration="Używasz znalezionej drewnianej deski jako prowizorycznej dźwigni.",
        improvised_tool={
            "label": "Drewniana deska",
            "source": "interaction_object",
            "source_detail": "znaleziona drewniana deska",
            "source_id": source_id,
            "effect_modifier": -1,
            "risk": "spróchniałe drewno może pęknąć",
            "reason": "Deska jest długa i sztywna, ale krucha.",
        },
    )

    option = challenge_option_from_validated_proposal(
        validate_gm_classifier_proposal(proposal, request)
    )

    assert option.improvised_tool is not None
    assert option.improvised_tool.source_id == source_id


def test_gm_classifier_rejects_different_improvised_source_than_player_selected():
    exploration, state = _state()
    source_id = "zone:gate:item:gate_rotten_planks"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używam znalezionej deski jako dźwigni.",
        actors=exploration.actors,
        referenced_crafting_source_ids=(source_id,),
        selected_use_source_id=source_id,
    )
    proposal = _proposal(
        selected_mechanic="improvised_tool_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        approach_tags=["lever"],
        used_resource_ids=[],
        player_narration="Używasz wskazanego elementu jako prowizorycznej dźwigni.",
        improvised_tool={
            "label": "Inny element",
            "source": "interaction_object",
            "source_detail": "inny element sceny",
            "source_id": "zone:gate:fixture:gate_corroded_hinges",
            "effect_modifier": -1,
            "reason": "Błędnie wybrane źródło.",
        },
    )

    with pytest.raises(GmProposalValidationError, match="source_id"):
        validate_gm_classifier_proposal(proposal, request)


def test_declaration_analyzer_accepts_planned_dynamic_construction_name():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcę zbudować prowizoryczny taran.",
        declaration_thread=(
            GmDeclarationThreadEntry(
                "gm",
                "Ze starych desek i metalowych okuć możecie stworzyć prowizoryczny taran.",
                "player_question",
            ),
        ),
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.BUILD,
        explicit_player_intent_hint=PlayerIntentHint.BUILD,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "action_flow": "preparation",
            "player_message": "Możecie spróbować.",
            "normalized_intent": "Składam prowizoryczny taran do późniejszego użycia.",
            "reason": "Materiały są obecne w scenie.",
            "confidence": 0.9,
            "declared_resources": ["prowizoryczny taran"],
            "assumed_new_facts": ["prowizoryczny taran z desek i metalowych elementów"],
        }
    )

    validate_gm_declaration_analysis(analysis, request)


def test_gate_policy_has_no_predefined_temporary_item_templates():
    exploration, state = _state()
    challenge = next(item for item in state.challenges if item.id == "closed_gate")

    assert challenge.llm_policy.temporary_item_templates == ()


def test_gm_classifier_exposes_property_based_crafting_to_llm():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Buduję prowizoryczną drabinę z desek i liny.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )

    crafting = request.to_prompt_payload()["crafting"]

    assert {purpose["id"] for purpose in crafting["purposes"]} == {
        "heavy_force",
        "climbing_aid",
        "leverage",
        "precision_tool",
    }
    sources = {source["id"]: source for source in crafting["available_sources"]}
    assert sources["zone:gate:item:gate_rotten_planks"]["quantity"] == 4
    assert "long" in sources["zone:gate:item:gate_rotten_planks"]["properties"]
    assert "resource:rope" in sources
    assert sources["zone:gate:fixture:gate_corroded_hinges"]["requires_detachment"] is True
    assert crafting["rules"]["requires_build_roll_by_default"] is False
    assert crafting["rules"]["detachable_fixtures_can_be_acquired_during_crafting"] is True


def test_explicit_build_is_grounded_to_dynamic_preparation_and_engine_selected_components():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcę zbudować drabinę, żeby później wejść na mur.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.BUILD,
        explicit_player_intent_hint=PlayerIntentHint.BUILD,
    )
    proposal = _proposal(
        action_flow="challenge_attempt",
        requires_roll_now=True,
        selected_mechanic="single_actor_check",
        approach_label="Budowa prowizorycznej drabiny",
        approach_tags=["climbing"],
        ability="intelligence",
        skill="crafting",
        dc=15,
        difficulty_tier="medium",
        progress_on_success=2,
        progress_on_failure=0,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczna drabina",
            "target_tags": ["climbing"],
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.action_flow == GmActionFlow.PREPARATION
    assert validated.proposal.requires_roll_now is False
    assert validated.proposal.preparation_effect.crafting_draft is not None
    assert validated.proposal.preparation_effect.temporary_item_template_id is None
    assert validated.crafting_plan is not None
    assert validated.crafting_plan.draft.auto_select_missing_components is True
    assert {
        component.source_id for component in validated.crafting_plan.component_uses
    } == {
        "zone:gate:item:gate_rotten_planks",
        "resource:rope",
    }


def test_gm_classifier_validates_dynamic_crafting_without_template_id():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Buduję prowizoryczną drabinę z desek i liny.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    proposal = _proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznej drabiny",
        approach_tags=["climbing"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczna drabina",
            "target_tags": ["climbing"],
            "crafting_draft": {
                "label": "Prowizoryczna drabina",
                "description": "Dwie długie deski związane liną.",
                "purpose_id": "climbing_aid",
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 2},
                    {"source_id": "resource:rope", "quantity": 1},
                ],
            },
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.crafting_plan is not None
    assert validated.crafting_plan.purpose.id == "climbing_aid"
    assert validated.crafting_plan.purpose.time_cost_minutes == 15
    assert validated.proposal.preparation_effect.temporary_item_template_id is None


def test_gm_classifier_rejects_dynamic_crafting_with_unsuitable_components():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Układam drabinę z samych kamieni.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    proposal = _proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Kamienna drabina",
        approach_tags=["climbing"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Kamienna drabina",
            "target_tags": ["climbing"],
            "crafting_draft": {
                "label": "Kamienna drabina",
                "description": "Luźne kamienie ułożone jeden na drugim.",
                "purpose_id": "climbing_aid",
                "auto_select_missing_components": False,
                "components": [
                    {"source_id": "zone:gate:item:gate_loose_stones", "quantity": 3}
                ],
            },
        },
    )

    with pytest.raises(GmProposalValidationError, match="Konstrukcja wymaga komponentów"):
        validate_gm_classifier_proposal(proposal, request)


def test_gm_classifier_accepts_precision_tool_from_detachable_fixture():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Robię prowizoryczny wytrych z metalowego elementu bramy.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    proposal = _proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Wykonanie prowizorycznego wytrycha",
        approach_tags=["lockpicking"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny wytrych",
            "target_tags": ["lockpicking"],
            "crafting_draft": {
                "label": "Prowizoryczny wytrych",
                "description": "Odgięty fragment skorodowanego metalowego zawiasu.",
                "purpose_id": "precision_tool",
                "components": [
                    {"source_id": "zone:gate:fixture:gate_corroded_hinges", "quantity": 1}
                ],
            },
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.crafting_plan is not None
    assert validated.crafting_plan.purpose.id == "precision_tool"
    assert validated.crafting_plan.purpose.modifier == -1


def test_explicit_build_replaces_legacy_shaped_effect_with_dynamic_draft():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcę zrobić prowizoryczny taran.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.BUILD,
        explicit_player_intent_hint=PlayerIntentHint.BUILD,
    )
    proposal = _proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznego taranu",
        approach_tags=["heavy_force"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny taran",
            "target_tags": ["heavy_force"],
            "source_materials": ["spróchniałe deski", "metalowe elementy"],
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.temporary_item_template_id is None
    assert validated.proposal.preparation_effect.crafting_draft is not None
    assert validated.crafting_plan is not None
    assert validated.crafting_plan.purpose.id == "heavy_force"
    assert {component.source_id for component in validated.crafting_plan.component_uses} == {
        "zone:gate:item:gate_rotten_planks",
        "zone:gate:item:gate_loose_stones",
    }


def test_dynamic_build_can_request_exact_components_without_automatic_completion():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Chcę zrobić prowizoryczny taran.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    proposal = _proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznego taranu",
        approach_tags=["heavy_force"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        used_resource_ids=[],
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny taran",
            "target_tags": ["heavy_force"],
            "crafting_draft": {
                "label": "Prowizoryczny taran",
                "description": "Długa deska obciążona kamieniem.",
                "purpose_id": "heavy_force",
                "auto_select_missing_components": False,
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 1},
                    {"source_id": "zone:gate:item:gate_loose_stones", "quantity": 1},
                ],
            },
        },
    )

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.preparation_effect is not None
    assert validated.proposal.preparation_effect.temporary_item_template_id is None
    assert validated.crafting_plan is not None
    assert validated.crafting_plan.draft.auto_select_missing_components is False


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


def test_gm_classifier_drops_empty_situational_modifier():
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

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert validated.proposal.situational_modifiers == ()
    assert option.situational_modifiers == ()


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


def test_gm_classifier_grounds_dc_to_selected_difficulty_tier():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą.",
    )
    proposal = _proposal(dc=20, used_resource_ids=())

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.dc == 15


def test_gm_classifier_uses_content_dc_instead_of_llm_number():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Próbujemy wejść górą.",
    )
    proposal = _proposal(difficulty_tier="medium", dc=12, used_resource_ids=())

    validated = validate_gm_classifier_proposal(proposal, request)

    assert validated.proposal.dc == 15


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


def test_gm_classifier_accepts_actor_inventory_item_and_restricts_option_owner():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Łotrzyca otwiera zamek narzędziami złodziejskimi.",
        actors=exploration.actors,
    )
    proposal = _proposal(
        approach_label="Otwieranie zatartego zamka",
        approach_tags=["lockpicking", "rusted_lock", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        used_resource_ids=["thieves_tools"],
        selected_mechanic="use_item_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        player_narration="Łotrzyca ostrożnie pracuje narzędziami przy zatartym zamku.",
        success_message="Zamek ustępuje pod precyzyjnym naciskiem narzędzi.",
        failure_message="Zatarty mechanizm nadal stawia opór.",
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)

    assert validated.resources == ()
    assert validated.required_actor_item_ids == ("thieves_tools",)
    assert option.requires_item_ids == ("thieves_tools",)


def test_gm_classifier_normalizes_selected_actor_inventory_source_id():
    exploration, state = _state()
    source_id = "actor:rogue:item:thieves_tools"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Używam narzędzi złodziejskich i otwieram zamek.",
        actors=exploration.actors,
        referenced_crafting_source_ids=(source_id,),
        selected_use_source_id=source_id,
    )
    proposal = _proposal(
        approach_label="Otwieranie zatartego zamka",
        approach_tags=["lockpicking", "rusted_lock", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        used_resource_ids=[source_id],
        selected_mechanic="use_item_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        player_narration="Łotrzyca ostrożnie otwiera zamek swoimi narzędziami.",
        success_message="Zamek ustępuje.",
        failure_message="Zamek nadal stawia opór.",
    )

    validated = validate_gm_classifier_proposal(proposal, request)
    option = challenge_option_from_validated_proposal(validated)
    grounded_source = request.to_prompt_payload()["player_grounded_sources"][0]

    assert validated.resources == ()
    assert validated.required_actor_item_ids == ("thieves_tools",)
    assert option.requires_item_ids == ("thieves_tools",)
    assert grounded_source["id"] == source_id
    assert grounded_source["reference_id"] == "thieves_tools"


def test_declaration_analysis_accepts_conversation_source_fact_ids_as_grounded():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Wykorzystuję wskazane deski i zawiasy do zrobienia narzędzia.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "action_flow": "preparation",
            "normalized_intent": "Budowa narzędzia z dostępnych elementów sceny.",
            "declared_resources": [
                "source:zone:gate:fixture:gate_corroded_hinges",
                "source:zone:gate:item:gate_rotten_planks",
            ],
        }
    )

    validate_gm_declaration_analysis(analysis, request)


def test_declaration_analysis_grounds_player_term_mapped_to_visible_scene_source():
    exploration, state = _state()
    plank_source_id = "zone:gate:item:gate_rotten_planks"
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukam kija, którym mógłbym zdjąć rygiel przez szparę.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.USE,
        referenced_crafting_source_ids=(plank_source_id,),
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "action_flow": "challenge_attempt",
            "normalized_intent": "Użycie prowizorycznego kija do manipulacji ryglem.",
            "assumed_new_facts": ["prowizoryczny kij do manipulacji ryglem"],
        }
    )

    validate_gm_declaration_analysis(analysis, request)

    grounded_source = request.to_prompt_payload()["player_grounded_sources"][0]
    assert grounded_source["id"] == plank_source_id
    assert grounded_source["label"] == "Drewniana deska"


def test_declaration_analyzer_receives_data_driven_source_property_vocabulary():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukam czegoś, czym dosięgnę rygla.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )

    property_ids = request.to_prompt_payload()["crafting"]["available_property_ids"]

    assert "long" in property_ids
    assert "rigid" in property_ids
    assert property_ids == sorted(property_ids)


def test_declaration_analysis_rejects_source_query_property_outside_catalog():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Szukam czegoś telepatycznego.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "source_query": {
                "purpose": "telepatyczne narzędzie",
                "required_properties": ["telepathic"],
            },
        }
    )

    with pytest.raises(GmProposalValidationError, match="telepathic"):
        validate_gm_declaration_analysis(analysis, request)


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
    guidance = {fact["id"]: fact for fact in payload["challenge"]["context"]["guidance_facts"]}
    assert guidance["gate.no_rope_flight"]["kind"] == "constraint"
    assert guidance["gate.no_quick_tunnel"]["visibility"] == "obvious"
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


def test_gm_question_payload_separates_visible_facts_from_progressive_hints():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Czy leżą tu jakieś kamienie?",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )

    payload = request.to_prompt_payload()
    facts = {fact["id"]: fact for fact in payload["conversation_knowledge"]["facts"]}

    stone_id = "source:zone:gate:item:gate_loose_stones"
    assert facts[stone_id]["kind"] == "visible_source"
    assert facts[stone_id]["minimum_hint_level"] == 0
    assert any(fact["kind"] == "gm_hint" for fact in facts.values())
    assert facts["fact:gate.force_is_loud"]["minimum_hint_level"] == 1
    assert facts["fact:gate.force_is_loud"]["revealed"] is True
    assert facts["fact:gate.noise_affects_scout"]["revealed"] is False
    assert facts["fact:gate.rotten_wood"]["minimum_hint_level"] == 0
    assert payload["conversation_policy"]["next_hint_level"] == 1
    assert payload["conversation_policy"]["hidden_facts_must_not_be_revealed"] is True


def test_gm_question_validation_accepts_grounded_visible_observation():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Czy leżą tu jakieś kamienie?",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Tak. Przy murze leżą luźne, ciężkie kamienie.",
            "reason": "Odpowiedź oparta na widocznym źródle sceny.",
            "confidence": 1.0,
            "response_kind": "observation",
            "grounded_fact_ids": ["source:zone:gate:item:gate_loose_stones"],
            "hint_level": 0,
            "requires_check": False,
        }
    )

    validate_gm_declaration_analysis(analysis, request)


@pytest.mark.parametrize(
    ("player_action", "hint_level"),
    (
        ("chce sprawdzić czy bramę można wyważyć", 1),
        ("jaki jest stan bramy, można ją wyważyć?", 0),
    ),
)
def test_question_normalizes_approach_fact_to_gentle_hint(player_action, hint_level):
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action=player_action,
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.QUESTION,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Stare skrzydła wyglądają na możliwe do wyważenia siłą.",
            "response_kind": "observation",
            "grounded_fact_ids": ["fact:gate.force_possible"],
            "hint_level": hint_level,
        }
    )

    normalized = validate_gm_declaration_analysis(analysis, request)

    assert normalized.response_kind == GmConversationResponseKind.GENTLE_HINT
    assert normalized.hint_level == 1


def test_question_downgrades_level_two_risk_to_matching_level_one_affordance():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="czy można wspinać się po bramie?",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
        player_intent_hint=PlayerIntentHint.QUESTION,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Tak, ale wspinaczka grozi upadkiem.",
            "response_kind": "observation",
            "grounded_fact_ids": ["fact:gate.climb_is_dangerous"],
            "hint_level": 0,
        }
    )

    normalized = validate_gm_declaration_analysis(analysis, request)

    assert normalized.response_kind == GmConversationResponseKind.GENTLE_HINT
    assert normalized.hint_level == 1
    assert normalized.grounded_fact_ids == ("fact:gate.climb_possible",)
    assert normalized.player_message.startswith("Można próbować przejść górą")


def test_gm_question_validation_rejects_unknown_fact_and_premature_strong_hint():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Potrzebujemy podpowiedzi.",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    unknown = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Za bramą leży magiczny klucz.",
            "response_kind": "observation",
            "grounded_fact_ids": ["hidden:magic_key"],
        }
    )
    too_strong = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Zbudujcie taran i uderzcie w bramę.",
            "response_kind": "strong_hint",
            "grounded_fact_ids": ["fact:gate.force_possible"],
            "hint_level": 3,
        }
    )

    with pytest.raises(GmProposalValidationError, match="fakty spoza sceny"):
        validate_gm_declaration_analysis(unknown, request)
    with pytest.raises(GmProposalValidationError, match="zbyt silną podpowiedź"):
        validate_gm_declaration_analysis(too_strong, request)


def test_gm_question_validation_requires_followup_for_uncertain_observation():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="Czy ktoś stoi za bramą?",
        actors=exploration.actors,
        crafting_policy=exploration.crafting_policy,
    )
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Z tej pozycji nie możecie tego stwierdzić.",
            "response_kind": "requires_check",
            "requires_check": True,
            "suggested_followup": "Nasłuchujemy przy szczelinie w bramie.",
        }
    )

    validate_gm_declaration_analysis(analysis, request)


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


def test_gm_classifier_request_payload_contains_explicit_player_intent_hint():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="czy zawiasy są luźne?",
        player_intent_hint=PlayerIntentHint.QUESTION,
    )

    assert request.to_prompt_payload()["player_intent_hint"] == "question"


def test_gm_classifier_exposes_active_graded_observation_without_revealing_facts():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="zaglądam przez szczelinę",
        observations=exploration.observations,
    )

    observation = next(
        item
        for item in request.to_prompt_payload()["available_observations"]
        if item["id"] == "look_through_gate_gap"
    )

    assert observation["id"] == "look_through_gate_gap"
    assert observation["base_dc"] == 10
    assert [fact["minimum_total"] for fact in observation["facts"]] == [10, 15, 20]
    assert all(fact["revealed"] is False for fact in observation["facts"])


def test_gm_classifier_accepts_observation_check_but_rejects_hidden_result_before_roll():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="zaglądam przez szczelinę",
        observations=exploration.observations,
    )
    proposed_check = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "player_question",
            "player_message": "Przez szczelinę widać tylko fragment dziedzińca. Dokładna obserwacja wymaga testu.",
            "response_kind": "requires_check",
            "requires_check": True,
            "suggested_followup": "Przyglądam się przez szczelinę i szukam ruchu.",
            "observation_id": "look_through_gate_gap",
        }
    )
    leaked_result = proposed_check.model_copy(
        update={
            "player_message": "Za bramą stoją dwa gobliny.",
            "grounded_fact_ids": (
                "observation:look_through_gate_gap:fact:gate_goblins_spotted",
            ),
        }
    )

    validate_gm_declaration_analysis(proposed_check, request)
    with pytest.raises(GmProposalValidationError, match="najpierw rozstrzygnięcia obserwacji"):
        validate_gm_declaration_analysis(leaked_result, request)


def test_explicit_question_intent_cannot_be_changed_into_action():
    exploration, state = _state()
    request = build_gm_classifier_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        scenario_context=exploration.llm_context,
        state=state,
        player_action="czy zawiasy są luźne?",
        player_intent_hint=PlayerIntentHint.QUESTION,
    )
    analysis = GmDeclarationAnalysis(
        analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
        player_message="",
        normalized_intent="Badanie zawiasów.",
        reason="test",
        confidence=1.0,
    )

    with pytest.raises(GmProposalValidationError, match="Jawna komenda rozmowy"):
        validate_gm_declaration_analysis(analysis, request)


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
