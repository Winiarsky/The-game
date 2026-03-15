from __future__ import annotations

from statuses.base import Status

SHIELD_BLOCK_DESCRIPTION = (
    "Reakcja: gdy masz podniesiona tarcze i otrzymujesz obrazenia fizyczne, "
    "tarcza pochlania obrazenia do Hardness (wdrozone mechanicznie przez reakcje)."
)


def ShieldBlockStatus() -> Status:
    """Feat: Shield Block."""
    return Status(
        id="shield_block",
        label="Shield Block",
        data={"ui_description": SHIELD_BLOCK_DESCRIPTION},
    )


SHIELD_BLOCK_STATUS = ShieldBlockStatus()

__all__ = ["ShieldBlockStatus", "SHIELD_BLOCK_STATUS", "SHIELD_BLOCK_DESCRIPTION"]
