from __future__ import annotations

from statuses.base import Status

STORM_BORN_DESCRIPTION = (
    "Storm Born: ignorujesz weather penalties do ranged spell attack i Perception. "
    "Targeted spells ignoruja concealment z pogody."
)


def StormBornStatus() -> Status:
    return Status(
        id="storm_born",
        label="Storm Born",
        data={
            "ui_description": STORM_BORN_DESCRIPTION,
            "ui_prompt": STORM_BORN_DESCRIPTION,
            "requires_druid_order": "storm",
            "ignore_weather_ranged_spell_penalty": True,
            "ignore_weather_perception_penalty": True,
            "ignore_weather_concealment_flat_check": True,
        },
    )


STORM_BORN_STATUS = StormBornStatus()

__all__ = [
    "STORM_BORN_DESCRIPTION",
    "StormBornStatus",
    "STORM_BORN_STATUS",
]
