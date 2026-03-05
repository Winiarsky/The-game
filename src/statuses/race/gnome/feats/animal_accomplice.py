from __future__ import annotations

from statuses.base import Status
from statuses.familiar import FAMILIAR_OWNER_STATUS

ANIMAL_ACCOMPLICE_DESCRIPTION = (
    "Budujesz magiczną więź ze zwierzęciem i zyskujesz familiara "
    "(zgodnie z zasadami familiara)."
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
