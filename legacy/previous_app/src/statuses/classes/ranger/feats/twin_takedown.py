from __future__ import annotations

from statuses.base import Status

TWIN_TAKEDOWN_DESCRIPTION = (
    "Twin Takedown (Flourish): wykonaj 2 Strikes melee (dwie bronie 1H) przeciw hunted prey. "
    "Jeśli oba trafiają, obrażenia są scalane dla resist/weakness."
)


def TwinTakedownStatus() -> Status:
    return Status(
        id="twin_takedown",
        label="Twin Takedown",
        data={
            "ui_description": TWIN_TAKEDOWN_DESCRIPTION,
            "ui_prompt": TWIN_TAKEDOWN_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


TWIN_TAKEDOWN_STATUS = TwinTakedownStatus()

__all__ = ["TWIN_TAKEDOWN_DESCRIPTION", "TwinTakedownStatus", "TWIN_TAKEDOWN_STATUS"]
