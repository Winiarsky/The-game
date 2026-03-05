from __future__ import annotations

from statuses.base import Status

ORC_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: falchion i greataxe.\n"
    "Dostęp: wszystkie uncommon orc weapons.\n"
    "Dla broni z tagiem orc: martial -> simple, advanced -> martial "
    "(do wyliczania biegłości).\n"
    "Przykład: broń [orc, advanced] liczysz jak martial."
)


def OrcWeaponFamiliarityStatus() -> Status:
    """Feat: Orc Weapon Familiarity."""
    return Status(
        id="orc_weapon_familiarity",
        label="Orc Weapon Familiarity",
        data={
            "ui_description": ORC_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "falchion": "trained",
                "greataxe": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "orc", "from": "advanced", "to": "martial"},
                {"required_tag": "orc", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["orc"],
        },
    )


ORC_WEAPON_FAMILIARITY_STATUS = OrcWeaponFamiliarityStatus()

__all__ = [
    "OrcWeaponFamiliarityStatus",
    "ORC_WEAPON_FAMILIARITY_STATUS",
    "ORC_WEAPON_FAMILIARITY_DESCRIPTION",
]
