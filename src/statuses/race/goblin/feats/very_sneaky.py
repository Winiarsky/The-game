from __future__ import annotations

from statuses.base import Status

VERY_SNEAKY_DESCRIPTION = (
    "Podczas akcji Sneak możesz poruszyć się o 5 stóp więcej (do pełnej Speed).\n"
    "Dodatkowo przy kontynuowaniu Sneak i udanych testach możesz pozostać "
    "niezauważony do końca tury nawet bez cover/concealed na końcu pojedynczej akcji.\n"
    "W tym silniku działa hook dodatkowych 5 stóp dla Sneak."
)


def VerySneakyStatus() -> Status:
    """Feat: Very Sneaky (opis do UI)."""
    return Status(
        id="very_sneaky",
        label="Very Sneaky",
        data={
            "ui_description": VERY_SNEAKY_DESCRIPTION,
            "sneak_bonus_feet": 5,
            "very_sneaky_end_of_turn_visibility_rule": True,
        },
    )


VERY_SNEAKY_STATUS = VerySneakyStatus()

__all__ = ["VerySneakyStatus", "VERY_SNEAKY_STATUS", "VERY_SNEAKY_DESCRIPTION"]
