from __future__ import annotations

from statuses.base import Status

POWERFUL_FIST_DESCRIPTION = (
    "Powerful Fist: bazowy fist ma 1k6 zamiast 1k4. "
    "W tym uproszczeniu kara do lethal z nonlethal jest tylko przypomnieniem UI."
)


def PowerfulFistStatus() -> Status:
    return Status(
        id="powerful_fist",
        label="Powerful Fist",
        data={
            "ui_description": POWERFUL_FIST_DESCRIPTION,
            "ui_prompt": POWERFUL_FIST_DESCRIPTION,
        },
    )


POWERFUL_FIST_STATUS = PowerfulFistStatus()

__all__ = ["PowerfulFistStatus", "POWERFUL_FIST_STATUS", "POWERFUL_FIST_DESCRIPTION"]
