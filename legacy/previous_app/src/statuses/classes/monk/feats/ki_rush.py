from __future__ import annotations

from statuses.base import Status

KI_RUSH_DESCRIPTION = (
    "Ki Rush (Focus 1): dwa ruchy (Stride/Step) i concealed do początku następnej tury."
)


def KiRushStatus() -> Status:
    return Status(
        id="ki_rush",
        label="Ki Rush",
        data={
            "ui_description": KI_RUSH_DESCRIPTION,
            "ui_prompt": KI_RUSH_DESCRIPTION,
            "set_actor_attrs": {"focus_point": 1},
        },
    )


KI_RUSH_STATUS = KiRushStatus()

__all__ = ["KiRushStatus", "KI_RUSH_STATUS", "KI_RUSH_DESCRIPTION"]
