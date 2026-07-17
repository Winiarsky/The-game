import pytest

from dnd_board_game.exploration import (
    NpcAttitude,
    SocialRequestRisk,
    plan_social_interaction,
)


@pytest.mark.parametrize(
    ("attitude", "risk", "possible", "requires_roll", "dc"),
    [
        (NpcAttitude.FRIENDLY, SocialRequestRisk.NO_RISK, True, False, None),
        (NpcAttitude.FRIENDLY, SocialRequestRisk.MINOR_RISK, True, True, 10),
        (NpcAttitude.FRIENDLY, SocialRequestRisk.SIGNIFICANT_RISK, True, True, 20),
        (NpcAttitude.INDIFFERENT, SocialRequestRisk.NO_RISK, True, True, 10),
        (NpcAttitude.INDIFFERENT, SocialRequestRisk.MINOR_RISK, True, True, 20),
        (NpcAttitude.INDIFFERENT, SocialRequestRisk.SIGNIFICANT_RISK, False, False, None),
        (NpcAttitude.HOSTILE, SocialRequestRisk.NO_RISK, True, True, 20),
        (NpcAttitude.HOSTILE, SocialRequestRisk.MINOR_RISK, False, False, None),
        (NpcAttitude.HOSTILE, SocialRequestRisk.SIGNIFICANT_RISK, False, False, None),
    ],
)
def test_social_interaction_plan_matches_2014_reaction_table(
    attitude: NpcAttitude,
    risk: SocialRequestRisk,
    possible: bool,
    requires_roll: bool,
    dc: int | None,
) -> None:
    plan = plan_social_interaction(attitude, risk)

    assert plan.possible is possible
    assert plan.requires_roll is requires_roll
    assert plan.dc == dc
