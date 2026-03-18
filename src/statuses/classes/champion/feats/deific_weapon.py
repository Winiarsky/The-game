from __future__ import annotations

from statuses.base import Status

DEIFIC_WEAPON_CHOICES = [
    "sword",
    "dagger",
    "longbow",
    "unarmed",
    "razortooth_jaws",
]

DEIFIC_WEAPON_DESCRIPTION = (
    "Boska bron: bron jest powiazana z ulubiona bronia wybranego bostwa "
    "(dla custom deity wybierasz recznie). "
    "Przy ataku tą bronią zwiększasz kość obrażeń o jeden stopień."
)


def DeificWeaponStatus() -> Status:
    return Status(
        id="deific_weapon",
        label="Boska bron",
        data={
            "ui_description": DEIFIC_WEAPON_DESCRIPTION,
            "ui_choice_kind": "deific_weapon",
            "deific_weapon_choices": list(DEIFIC_WEAPON_CHOICES),
            "deific_weapon_type": None,
        },
    )


DEIFIC_WEAPON_STATUS = DeificWeaponStatus()

__all__ = [
    "DEIFIC_WEAPON_CHOICES",
    "DEIFIC_WEAPON_DESCRIPTION",
    "DeificWeaponStatus",
    "DEIFIC_WEAPON_STATUS",
]
