from __future__ import annotations

from statuses.base import Status
from statuses.familiar import FAMILIAR_OWNER_STATUS

ANIMAL_ACCOMPLICE_DESCRIPTION = (
    "Nawiazujesz magiczna wiez z drobnym zwierzeciem-pomocnikiem.\n"
    "Kiedy: po wybraniu featu.\n"
    "Efekt: otrzymujesz status familiara (FAMILIAR_OWNER_STATUS) i dostep "
    "do akcji/zdarzen zwiazanych z familiara zgodnie z aktualna implementacja silnika."
)


def AnimalAccompliceStatus() -> Status:
    """Feat: Animal Accomplice (opis do UI)."""
    return Status(
        id="animal_accomplice",
        label="Animal Accomplice",
        data={
            "ui_description": ANIMAL_ACCOMPLICE_DESCRIPTION,
            "grants_statuses": [FAMILIAR_OWNER_STATUS],
        },
    )


ANIMAL_ACCOMPLICE_STATUS = AnimalAccompliceStatus()

__all__ = [
    "AnimalAccompliceStatus",
    "ANIMAL_ACCOMPLICE_STATUS",
    "ANIMAL_ACCOMPLICE_DESCRIPTION",
]
