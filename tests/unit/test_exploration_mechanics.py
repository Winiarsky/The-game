import pytest

from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ExplorationMechanicId,
    infer_mechanic_id,
    mechanic_payload_for_option,
    validate_mechanic_selection,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def test_infer_mechanic_id_from_participants_and_option_requirements():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    gate = next(challenge for challenge in exploration.challenges if challenge.id == "closed_gate")
    lockpick = next(option for option in gate.options if option.id == "lockpick_gate")
    flame = next(option for option in gate.options if option.id == "reveal_bolt_with_flame")

    assert (
        infer_mechanic_id(
            participants=CheckParticipants.SINGLE_ACTOR,
            aggregation=CheckAggregation.LEAD_RESULT,
        )
        == ExplorationMechanicId.SINGLE_ACTOR_CHECK
    )
    assert (
        infer_mechanic_id(
            participants=CheckParticipants.LEAD_WITH_HELP,
            aggregation=CheckAggregation.LEAD_RESULT,
        )
        == ExplorationMechanicId.LEAD_WITH_HELP_CHECK
    )
    assert (
        infer_mechanic_id(
            participants=CheckParticipants.WHOLE_PARTY,
            aggregation=CheckAggregation.MAJORITY,
        )
        == ExplorationMechanicId.GROUP_CHECK
    )
    assert mechanic_payload_for_option(lockpick)["id"] == "use_item_check"
    assert mechanic_payload_for_option(flame)["id"] == "use_spell_check"


def test_validate_mechanic_selection_rejects_incompatible_shape():
    validate_mechanic_selection(
        ExplorationMechanicId.GROUP_CHECK,
        participants=CheckParticipants.SELECTED_ACTORS,
        aggregation=CheckAggregation.HIGHEST,
    )

    with pytest.raises(ValueError, match="nie pasuje"):
        validate_mechanic_selection(
            ExplorationMechanicId.LEAD_WITH_HELP_CHECK,
            participants=CheckParticipants.WHOLE_PARTY,
            aggregation=CheckAggregation.LEAD_RESULT,
        )

    with pytest.raises(ValueError, match="nie obsługuje"):
        validate_mechanic_selection(
            ExplorationMechanicId.SINGLE_ACTOR_CHECK,
            participants=CheckParticipants.SINGLE_ACTOR,
            aggregation=CheckAggregation.HIGHEST,
        )
