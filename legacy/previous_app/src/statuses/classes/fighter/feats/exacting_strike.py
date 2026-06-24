from __future__ import annotations

from statuses.base import Status

EXACTING_STRIKE_DESCRIPTION = (
    "Exacting Strike (Press): wykonujesz Strike. "
    "Na failure atak nie zwiększa MAP."
)


def ExactingStrikeStatus() -> Status:
    return Status(
        id="exacting_strike",
        label="Exacting Strike",
        data={"ui_description": EXACTING_STRIKE_DESCRIPTION, "ui_prompt": EXACTING_STRIKE_DESCRIPTION},
    )


EXACTING_STRIKE_STATUS = ExactingStrikeStatus()

__all__ = ["ExactingStrikeStatus", "EXACTING_STRIKE_STATUS", "EXACTING_STRIKE_DESCRIPTION"]
