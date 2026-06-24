from __future__ import annotations

from statuses.base import Status

FEY_TOUCHED_GNOME_DESCRIPTION = (
    "Magia fey przenika twoje dziedzictwo od urodzenia.\n"
    "Kiedy: po wybraniu heritage wybierasz 1 cantrip z listy Fey-touched.\n"
    "Efekt: dostajesz trait fey (ancestry_extra_traits), wybrany cantrip jako "
    "innate spell at-will (granted_cantrips, tradycja primal), oraz mozliwosc "
    "zmiany cantripa po 10 minutach dziennej medytacji (reselect_cantrip_daily_minutes)."
)


def FeyTouchedGnomeStatus() -> Status:
    """Heritage: Fey-touched Gnome."""
    return Status(
        id="fey_touched_gnome",
        label="Fey-touched Gnome",
        data={
            "ui_description": FEY_TOUCHED_GNOME_DESCRIPTION,
            "ui_choice_kind": "fey_touched_gnome",
            "ancestry_extra_traits": ["fey"],
            "fey_touched_cantrip_choices": [
                "detect_magic",
                "guidance",
                "ray_of_frost",
                "produce_flame",
                "light",
                "tanglefoot",
                "shield",
                "ghost_sound",
                "stabilize",
                "daze",
            ],
            "fey_touched_cantrip": None,
            "granted_cantrips": [],
            "innate_magic_tradition": "primal",
            "reselect_cantrip_daily_minutes": 10,
        },
    )


FEY_TOUCHED_GNOME_STATUS = FeyTouchedGnomeStatus()

__all__ = [
    "FeyTouchedGnomeStatus",
    "FEY_TOUCHED_GNOME_STATUS",
    "FEY_TOUCHED_GNOME_DESCRIPTION",
]
