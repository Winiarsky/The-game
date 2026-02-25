from __future__ import annotations

from statuses.base import Status

RAGING_THROWER_PROMPT = (
    "Raging Thrower: dodajesz bonus z Rage do obrażeń broni rzucanych (thrown)."
)


def RagingThrowerStatus() -> Status:
    """Feat: Raging Thrower."""
    return Status(
        id="raging_thrower",
        label="Raging Thrower",
        data={"ui_prompt": RAGING_THROWER_PROMPT},
    )


RAGING_THROWER_STATUS = RagingThrowerStatus()

__all__ = ["RagingThrowerStatus", "RAGING_THROWER_STATUS", "RAGING_THROWER_PROMPT"]
