from __future__ import annotations

from enum import StrEnum


class ActionUse(StrEnum):
    ACTION_AVAILABLE = "action_available"
    ACTION_USED = "action_used"


def consume_action(state: ActionUse) -> ActionUse:
    if state == ActionUse.ACTION_USED:
        raise ValueError("Action has already been used.")
    return ActionUse.ACTION_USED
