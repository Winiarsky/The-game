import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import ExplorationState
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


def test_npc_interaction_rejects_effect_flag_outside_policy():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
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
