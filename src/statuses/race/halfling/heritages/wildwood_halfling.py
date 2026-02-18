from __future__ import annotations

from statuses.base import Status

WILDWOOD_HALFLING_DESCRIPTION = (
    "Ignorujesz trudny teren z drzew, gęstwiny i podszytu (np. bushes)."
)


def WildwoodHalflingStatus() -> Status:
    """Heritage: Wildwood Halfling."""
    return Status(
        id="wildwood_halfling",
        label="Wildwood Halfling",
        data={
            "ui_description": WILDWOOD_HALFLING_DESCRIPTION,
            "ignore_move_cost_terrain_tags": ["bushes", "forest"],
        },
    )


WILDWOOD_HALFLING_STATUS = WildwoodHalflingStatus()

__all__ = ["WildwoodHalflingStatus", "WILDWOOD_HALFLING_STATUS", "WILDWOOD_HALFLING_DESCRIPTION"]
