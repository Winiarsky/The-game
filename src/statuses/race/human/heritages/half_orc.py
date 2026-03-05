from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

HALF_ORC_DESCRIPTION = (
    "One of your parents was an orc, or one or both were\n"
    "half-orcs. You have a green tinge to your skin and other\n"
    "indicators of orc heritage. You gain the orc trait, the\n"
    "half-orc trait, and low-light vision. In addition, you can\n"
    "select orc, half-orc, and human feats whenever you gain\n"
    "an ancestry feat."
)


def HalfOrcStatus() -> Status:
    """Heritage: Half-Orc."""
    return Status(
        id="half_orc",
        label="Half-Orc",
        data={
            "ui_description": HALF_ORC_DESCRIPTION,
            "ancestry_extra_traits": ["orc", "half_orc"],
            "ancestry_feat_access": ["orc", "half_orc", "human"],
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


HALF_ORC_STATUS = HalfOrcStatus()

__all__ = ["HalfOrcStatus", "HALF_ORC_STATUS", "HALF_ORC_DESCRIPTION"]
