from __future__ import annotations

from statuses.base import Status

DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: battle axe, pick, warhammer.\n"
    "Dla broni z tagiem dwarf: martial -> simple, advanced -> martial (do wyliczania biegłości).\n"
    "Przykład: jeśli broń ma tagi [dwarf, advanced], liczysz ją jak martial."
)


def DwarvenWeaponFamiliarityStatus() -> Status:
    """Feat: Dwarven Weapon Familiarity (opis do UI)."""
    return Status(
        id="dwarven_weapon_familiarity",
        label="Dwarven Weapon Familiarity",
        data={
            "ui_description": DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "battle_axe": "trained",
                "pick": "trained",
                "warhammer": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "dwarf", "from": "advanced", "to": "martial"},
                {"required_tag": "dwarf", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["dwarf"],
        },
    )


DWARVEN_WEAPON_FAMILIARITY_STATUS = DwarvenWeaponFamiliarityStatus()

__all__ = [
    "DwarvenWeaponFamiliarityStatus",
    "DWARVEN_WEAPON_FAMILIARITY_STATUS",
    "DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION",
]
