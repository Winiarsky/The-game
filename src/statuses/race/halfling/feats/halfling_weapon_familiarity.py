from __future__ import annotations

from statuses.base import Status

HALFLING_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: sling, halfling sling staff i shortsword.\n"
    "Dostęp: wszystkie uncommon halfling weapons.\n"
    "Dla broni z tagiem halfling: martial -> simple, advanced -> martial "
    "(do wyliczania biegłości).\n"
    "Przykład: broń [halfling, advanced] liczysz jak martial."
)


def HalflingWeaponFamiliarityStatus() -> Status:
    """Feat: Halfling Weapon Familiarity."""
    return Status(
        id="halfling_weapon_familiarity",
        label="Halfling Weapon Familiarity",
        data={
            "ui_description": HALFLING_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "sling": "trained",
                "halfling_sling_staff": "trained",
                "shortsword": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "halfling", "from": "advanced", "to": "martial"},
                {"required_tag": "halfling", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["halfling"],
        },
    )


HALFLING_WEAPON_FAMILIARITY_STATUS = HalflingWeaponFamiliarityStatus()

__all__ = [
    "HalflingWeaponFamiliarityStatus",
    "HALFLING_WEAPON_FAMILIARITY_STATUS",
    "HALFLING_WEAPON_FAMILIARITY_DESCRIPTION",
]
