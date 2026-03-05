from __future__ import annotations

from statuses.base import Status

UNCONVENTIONAL_WEAPONRY_DESCRIPTION = (
    "Wybierasz uncommon broń powiązaną z inną ancestry lub kulturą.\n"
    "Zyskujesz do niej dostęp.\n"
    "Do wyliczania biegłości traktujesz ją jako simple weapon "
    "(albo jako martial, jeśli wybierasz uncommon advanced weapon i masz "
    "trained we wszystkich martial weapons).\n"
    "W tym silniku wybór i kategoria są zapisywane na statusie."
)


def UnconventionalWeaponryStatus() -> Status:
    """Feat: Unconventional Weaponry."""
    return Status(
        id="unconventional_weaponry",
        label="Unconventional Weaponry",
        data={
            "ui_description": UNCONVENTIONAL_WEAPONRY_DESCRIPTION,
            "ui_choice_kind": "unconventional_weaponry",
            "unconventional_weaponry_choices": [
                "dogslicer",
                "horsechopper",
                "kukri",
                "falchion",
                "greataxe",
                "halfling_sling_staff",
                "composite_longbow",
                "composite_shortbow",
            ],
            "weapon_name": None,
            "counts_as": "simple",
            "weapon_proficiency_overrides": {},
            "weapon_access_names": [],
        },
    )


UNCONVENTIONAL_WEAPONRY_STATUS = UnconventionalWeaponryStatus()

__all__ = [
    "UnconventionalWeaponryStatus",
    "UNCONVENTIONAL_WEAPONRY_STATUS",
    "UNCONVENTIONAL_WEAPONRY_DESCRIPTION",
]
