import pytest

from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    NpcIntentPermission,
    NpcIntentTarget,
    NpcOutcomeBranch,
    NpcOutcomeTier,
    PartyPosition,
    npc_outcome_for_check,
    plan_npc_intent_action,
    resolve_npc_outcome,
)


def _target() -> NpcIntentTarget:
    return NpcIntentTarget(
        id="reports",
        label="Reports",
        description="Steal the reports.",
        max_quantity=1,
        ability="dexterity",
        skill="sleight_of_hand",
        dc=14,
        outcome_branches=tuple(
            NpcOutcomeBranch(
                outcome,
                f"Outcome: {outcome.value}",
                effects=(
                    {
                        "type": "set_flag",
                        "parameters": {"key": f"outcome:{outcome.value}", "value": True},
                    },
                ),
            )
            for outcome in NpcOutcomeTier
        ),
    )


def test_npc_outcome_tier_uses_natural_extremes_only_with_matching_result() -> None:
    assert npc_outcome_for_check(success=True, natural_roll=20) == NpcOutcomeTier.CRITICAL_SUCCESS
    assert npc_outcome_for_check(success=True, natural_roll=1) == NpcOutcomeTier.SUCCESS
    assert npc_outcome_for_check(success=False, natural_roll=20) == NpcOutcomeTier.FAILURE
    assert npc_outcome_for_check(success=False, natural_roll=1) == NpcOutcomeTier.CRITICAL_FAILURE


def test_npc_outcome_plan_validates_target_and_executes_only_selected_branch() -> None:
    state = ExplorationState((), (), PartyPosition("courtyard"), SceneFlags())
    permission = NpcIntentPermission("theft", "allowed", targets=(_target(),))
    plan = plan_npc_intent_action(
        state,
        permission=permission,
        target_id="reports",
        quantity=1,
    )

    resolution = resolve_npc_outcome(state, plan, NpcOutcomeTier.FAILURE)

    assert resolution.branch.message == "Outcome: failure"
    assert scene_flag(resolution.state.flags, "outcome:failure", False) is True
    assert scene_flag(resolution.state.flags, "outcome:success", False) is False


def test_npc_outcome_plan_rejects_unknown_target_and_quantity_above_limit() -> None:
    state = ExplorationState((), (), PartyPosition("courtyard"), SceneFlags())
    permission = NpcIntentPermission("theft", "allowed", targets=(_target(),))

    with pytest.raises(ValueError, match="has no target"):
        plan_npc_intent_action(state, permission=permission, target_id="gold", quantity=1)

    with pytest.raises(ValueError, match=r"range 1\.\.1"):
        plan_npc_intent_action(state, permission=permission, target_id="reports", quantity=2)
