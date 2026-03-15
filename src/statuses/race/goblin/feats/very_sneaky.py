from __future__ import annotations

from statuses.base import Status

VERY_SNEAKY_DESCRIPTION = (
    "Poruszasz się w ukryciu szybciej niż inni.\n"
    "Kiedy: wykonujesz ruch skradaniem (Sneak).\n"
    "Efekt: bazowo Sneak używa połowy twojej Speed; ten feat dodaje +5 stóp do limitu "
    "ruchu skradaniem (maksymalnie do pełnej Speed). Dodatkowo obowiązuje reguła "
    "utrzymania ukrycia do końca tury zgodnie z logiką Very Sneaky."
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
