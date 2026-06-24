from __future__ import annotations

from statuses.base import Status

ORC_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Mechanika: zyskujesz trained w falchion i greataxe.\n"
    "Mechanika: dostep do wszystkich uncommon broni z tagiem orc.\n"
    "Mechanika biegosci: bron [orc, martial] liczysz jak simple, a [orc, advanced] jak martial."
)


def OrcWeaponFamiliarityStatus() -> Status:
    """Feat: Orc Weapon Familiarity."""
    return Status(
        id="orc_weapon_familiarity",
        label="Orcza znajomosc broni",
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
