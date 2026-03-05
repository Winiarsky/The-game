from __future__ import annotations

from statuses.base import Status

ELVEN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: longbow, composite longbow, longsword, rapier, shortbow, "
    "composite shortbow.\n"
    "Dla broni z tagiem elf: martial -> simple, advanced -> martial "
    "(do wyliczania biegłości).\n"
    "Dodatkowo zyskujesz dostęp do uncommon elf weapons.\n"
    "Przykład: broń z tagami [elf, advanced] liczona jest jak martial."
)


def ElvenWeaponFamiliarityStatus() -> Status:
    """Feat: Elven Weapon Familiarity."""
    return Status(
        id="elven_weapon_familiarity",
        label="Elven Weapon Familiarity",
        data={
            "ui_description": ELVEN_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "longbow": "trained",
                "composite_longbow": "trained",
                "longsword": "trained",
                "rapier": "trained",
                "shortbow": "trained",
                "composite_shortbow": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "elf", "from": "advanced", "to": "martial"},
                {"required_tag": "elf", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["elf"],
        },
    )


ELVEN_WEAPON_FAMILIARITY_STATUS = ElvenWeaponFamiliarityStatus()

__all__ = [
    "ElvenWeaponFamiliarityStatus",
    "ELVEN_WEAPON_FAMILIARITY_STATUS",
    "ELVEN_WEAPON_FAMILIARITY_DESCRIPTION",
]
