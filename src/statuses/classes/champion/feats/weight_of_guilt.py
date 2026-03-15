from __future__ import annotations

from statuses.base import Status

WEIGHT_OF_GUILT_DESCRIPTION = (
    "Weight of Guilt: gdy cel zignoruje Glimpse of Redemption, "
    "mozesz nadac mu stupefied 2 zamiast enfeebled 2 (do konca jego nastepnej tury)."
)


def WeightOfGuiltStatus() -> Status:
    return Status(
        id="weight_of_guilt",
        label="Weight of Guilt",
        data={
            "ui_description": WEIGHT_OF_GUILT_DESCRIPTION,
            "ui_prompt": WEIGHT_OF_GUILT_DESCRIPTION,
            "requires_champion_cause": "redeemer",
        },
    )


WEIGHT_OF_GUILT_STATUS = WeightOfGuiltStatus()

__all__ = [
    "WEIGHT_OF_GUILT_DESCRIPTION",
    "WeightOfGuiltStatus",
    "WEIGHT_OF_GUILT_STATUS",
]
