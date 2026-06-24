from __future__ import annotations

from statuses.base import Status

POWER_ATTACK_DESCRIPTION = (
    "Power Attack (Flourish): 2 akcje, melee Strike z dodatkową kością obrażeń. "
    "Atak liczy się jako 2 ataki do MAP."
)


def PowerAttackStatus() -> Status:
    return Status(
        id="power_attack",
        label="Power Attack",
        data={"ui_description": POWER_ATTACK_DESCRIPTION, "ui_prompt": POWER_ATTACK_DESCRIPTION},
    )


POWER_ATTACK_STATUS = PowerAttackStatus()

__all__ = ["PowerAttackStatus", "POWER_ATTACK_STATUS", "POWER_ATTACK_DESCRIPTION"]
