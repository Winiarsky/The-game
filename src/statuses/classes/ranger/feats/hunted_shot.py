from __future__ import annotations

from statuses.base import Status

HUNTED_SHOT_DESCRIPTION = (
    "Hunted Shot (Flourish): wykonaj 2 Strikes ranged przeciw hunted prey. "
    "Jeśli oba trafiają ten sam cel, obrażenia są scalane dla resist/weakness."
)


def HuntedShotStatus() -> Status:
    return Status(
        id="hunted_shot",
        label="Hunted Shot",
        data={
            "ui_description": HUNTED_SHOT_DESCRIPTION,
            "ui_prompt": HUNTED_SHOT_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


HUNTED_SHOT_STATUS = HuntedShotStatus()

__all__ = ["HUNTED_SHOT_DESCRIPTION", "HuntedShotStatus", "HUNTED_SHOT_STATUS"]
