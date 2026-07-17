from dataclasses import replace

import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import ExplorationState, resolve_npc_runtime_interaction
from dnd_board_game.llm import NpcInteractionProposal, build_npc_interaction_request, validate_npc_interaction_proposal
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _request():
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
    point = next(item for item in exploration.points if item.id == "wounded_scout")
    zone = next(item for item in exploration.zones if item.id == point.zone_id)
    return build_npc_interaction_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action="Uspokajamy zwiadowcę.",
    )


def test_npc_interaction_accepts_allowed_success_effect():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_stabilized", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_trusts_party", "value": True}},
            ],
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.proposal.effects_on_success[0].type == "set_flag"
    assert validated.proposal.requires_roll is True
    assert validated.proposal.ability == "charisma"
    assert validated.proposal.skill == "persuasion"
    assert validated.proposal.dc == 10
    assert validated.social_plan is not None
    assert validated.attempt_plan is not None
    assert validated.attempt_plan.available is True
    assert validated.attempt_plan.attempt_id == "scout_build_trust"


def test_npc_interaction_requires_risk_for_social_reaction_intent():
    proposal = NpcInteractionProposal.model_validate(
        {"action_type": "social", "requires_roll": False}
    )

    with pytest.raises(ValueError, match="requires request_risk"):
        validate_npc_interaction_proposal(proposal, _request())


def test_npc_interaction_marks_too_risky_request_as_refusal_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "significant_risk",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "persuasion",
            "dc": 15,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.social_plan is not None
    assert validated.social_plan.possible is False
    assert validated.proposal.requires_roll is False
    assert validated.proposal.dc is None


def test_npc_interaction_returns_natural_retry_block_instead_of_validation_error():
    request = _request()
    first = resolve_npc_runtime_interaction(
        request.state,
        npc_id="wounded_scout",
        intent="social",
        success=False,
        summary="Zwiadowca nadal nie ufa drużynie.",
        attempt_id="scout_build_trust",
    )
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(
        proposal,
        replace(request, state=first.state),
    )

    assert validated.attempt_plan is not None
    assert validated.attempt_plan.available is False
    assert "Najpierw pokażcie czynami" in validated.attempt_plan.blocked_reason


def test_npc_interaction_rejects_effect_flag_outside_policy():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "dragon_summoned", "value": True}},
            ],
        }
    )

    with pytest.raises(ValueError, match="effect flag is not allowed"):
        validate_npc_interaction_proposal(proposal, _request())


def test_npc_interaction_locked_intent_can_be_unlocked_by_success_effect():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_stabilized", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_trusts_party", "value": True}},
            ],
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.proposal.action_type == "information"


def test_npc_interaction_uses_content_check_and_outcomes_for_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "quantity": 1,
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.action_plan is not None
    assert validated.action_plan.target.label == "Torba z meldunkami"
    assert validated.proposal.requires_roll is True
    assert validated.proposal.ability == "dexterity"
    assert validated.proposal.skill == "sleight_of_hand"
    assert validated.proposal.dc == 14


def test_npc_interaction_rejects_unknown_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "imaginary_gold",
            "requires_roll": True,
            "ability": "dexterity",
            "skill": "sleight_of_hand",
            "dc": 10,
        }
    )

    with pytest.raises(ValueError, match="has no target"):
        validate_npc_interaction_proposal(proposal, _request())


def test_npc_interaction_rejects_llm_effects_for_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "requires_roll": True,
            "ability": "dexterity",
            "skill": "sleight_of_hand",
            "dc": 10,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_dead", "value": True}},
            ],
        }
    )

    with pytest.raises(ValueError, match="cannot define LLM-owned outcomes"):
        validate_npc_interaction_proposal(proposal, _request())


def test_structured_social_target_combines_reaction_table_with_content_outcomes():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "intimidation",
            "request_risk": "minor_risk",
            "target_id": "scout_information",
            "requires_roll": False,
            "skill": "intimidation",
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.social_plan is not None
    assert validated.social_plan.dc == 20
    assert validated.action_plan is not None
    assert validated.action_plan.target.reward_label == "Trop o bestii"
    assert validated.attempt_plan is not None
    assert validated.attempt_plan.max_attempts == 1
    assert validated.proposal.ability == "charisma"
    assert validated.proposal.skill == "intimidation"
