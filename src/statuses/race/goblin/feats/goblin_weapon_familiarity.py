from __future__ import annotations

from statuses.base import Status

GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: dogslicer i horsechopper.\n"
    "Dostęp: wszystkie uncommon goblin weapons.\n"
    "Dla broni z tagiem goblin: martial -> simple, advanced -> martial "
    "(do wyliczania biegłości).\n"
    "Przykład: broń [goblin, advanced] liczysz jak martial."
)


def GoblinWeaponFamiliarityStatus() -> Status:
    """Feat: Goblin Weapon Familiarity (opis do UI)."""
    return Status(
        id="goblin_weapon_familiarity",
        label="Goblin Weapon Familiarity",
        data={
            "ui_description": GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "dogslicer": "trained",
                "horsechopper": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "goblin", "from": "advanced", "to": "martial"},
                {"required_tag": "goblin", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["goblin"],
        },
    )


GOBLIN_WEAPON_FAMILIARITY_STATUS = GoblinWeaponFamiliarityStatus()

__all__ = [
    "GoblinWeaponFamiliarityStatus",
    "GOBLIN_WEAPON_FAMILIARITY_STATUS",
    "GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION",
]
