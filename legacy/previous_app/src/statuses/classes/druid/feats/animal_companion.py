from __future__ import annotations

from GameObjects.companions import animal_companion_type_ids
from statuses.base import Status

ANIMAL_COMPANION_DESCRIPTION = (
    "Zwierzecy towarzysz: zyskujesz mlodego zwierzecego towarzysza. "
    "W walce towarzysz pojawia sie jako osobny obiekt i dziala przez komende wlasciciela."
)


def AnimalCompanionStatus() -> Status:
    choices = animal_companion_type_ids()
    return Status(
        id="animal_companion",
        label="Zwierzecy towarzysz",
        data={
            "ui_description": ANIMAL_COMPANION_DESCRIPTION,
            "ui_prompt": ANIMAL_COMPANION_DESCRIPTION,
            "requires_druid_order": "animal",
            "ui_choice_kind": "animal_companion_type",
            "animal_companion_type_choices": list(choices),
            "animal_companion_type": choices[0] if choices else "wolf",
        },
    )


ANIMAL_COMPANION_STATUS = AnimalCompanionStatus()

__all__ = [
    "ANIMAL_COMPANION_DESCRIPTION",
    "AnimalCompanionStatus",
    "ANIMAL_COMPANION_STATUS",
]
