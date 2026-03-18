from __future__ import annotations

from statuses.base import Status

HUNTED_SHOT_DESCRIPTION = (
    "Strzal na cel (Flourish): wykonaj 2 Strikes dystansowe przeciw oznaczonej ofierze. "
    "Jesli oba trafiaja ten sam cel, obrazenia sa scalane dla resist/weakness."
)


def HuntedShotStatus() -> Status:
    return Status(
        id="hunted_shot",
        label="Strzal na cel",
        data={
            "ui_description": HUNTED_SHOT_DESCRIPTION,
            "ui_prompt": HUNTED_SHOT_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


HUNTED_SHOT_STATUS = HuntedShotStatus()

__all__ = ["HUNTED_SHOT_DESCRIPTION", "HuntedShotStatus", "HUNTED_SHOT_STATUS"]
