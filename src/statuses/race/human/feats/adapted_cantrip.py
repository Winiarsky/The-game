from __future__ import annotations

from statuses.base import Status

ADAPTED_CANTRIP_DESCRIPTION = (
    "Wybierz cantrip z innej tradycji; traktujesz go jako swój. (UI only)"
)


def AdaptedCantripStatus() -> Status:
    """Feat: Adapted Cantrip (UI prompt)."""
    return Status(
        id="adapted_cantrip",
        label="Adapted Cantrip",
        data={
            "ui_description": ADAPTED_CANTRIP_DESCRIPTION,
            "adapted_cantrip": None,
            "adapted_tradition": None,
            "replaced_cantrip": None,
        },
    )


ADAPTED_CANTRIP_STATUS = AdaptedCantripStatus()

__all__ = ["AdaptedCantripStatus", "ADAPTED_CANTRIP_STATUS", "ADAPTED_CANTRIP_DESCRIPTION"]
