from __future__ import annotations

from statuses.base import Status

WILDWOOD_HALFLING_DESCRIPTION = (
    "Wykorzystujesz mały rozmiar, by przeciskać się przez las i dżunglę.\n"
    "Ignorujesz utrudniony teren pochodzacy z drzew, listowia i podszytu."
)


def WildwoodHalflingStatus() -> Status:
    """Heritage: Wildwood Halfling."""
    return Status(
        id="wildwood_halfling",
        label="Wildwood Halfling",
        data={
            "ui_description": WILDWOOD_HALFLING_DESCRIPTION,
            "ignore_move_cost_terrain_tags": [
                "trees",
                "foliage",
                "undergrowth",
                "bushes",
                "forest",
                "jungle",
            ],
        },
    )


WILDWOOD_HALFLING_STATUS = WildwoodHalflingStatus()

__all__ = ["WildwoodHalflingStatus", "WILDWOOD_HALFLING_STATUS", "WILDWOOD_HALFLING_DESCRIPTION"]
