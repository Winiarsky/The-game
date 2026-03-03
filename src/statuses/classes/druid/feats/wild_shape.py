from __future__ import annotations

from statuses.base import Status

WILD_SHAPE_DESCRIPTION = (
    "Wild Shape: zyskujesz dostep do order spell Wild Shape (mechanika form bedzie "
    "rozszerzana kolejnymi featami)."
)


def WildShapeStatus() -> Status:
    return Status(
        id="wild_shape",
        label="Wild Shape",
        data={
            "ui_description": WILD_SHAPE_DESCRIPTION,
            "ui_prompt": WILD_SHAPE_DESCRIPTION,
            "requires_druid_order": "wild",
            "granted_order_spell": "wild_shape",
        },
    )


WILD_SHAPE_STATUS = WildShapeStatus()

__all__ = [
    "WILD_SHAPE_DESCRIPTION",
    "WildShapeStatus",
    "WILD_SHAPE_STATUS",
]
