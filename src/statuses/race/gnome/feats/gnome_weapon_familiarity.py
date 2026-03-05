from __future__ import annotations

from statuses.base import Status

GNOME_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Trained: glaive i kukri.\n"
    "Dostęp: kukri i uncommon gnome weapons.\n"
    "Dla broni z tagiem gnome: martial -> simple, advanced -> martial "
    "(do wyliczania biegłości).\n"
    "Przykład: broń [gnome, advanced] liczysz jak martial."
)


def GnomeWeaponFamiliarityStatus() -> Status:
    """Feat: Gnome Weapon Familiarity (opis do UI)."""
    return Status(
        id="gnome_weapon_familiarity",
        label="Gnome Weapon Familiarity",
        data={
            "ui_description": GNOME_WEAPON_FAMILIARITY_DESCRIPTION,
            "weapon_proficiency_overrides": {
                "glaive": "trained",
                "kukri": "trained",
            },
            "weapon_category_adjustments": [
                {"required_tag": "gnome", "from": "advanced", "to": "martial"},
                {"required_tag": "gnome", "from": "martial", "to": "simple"},
            ],
            "weapon_access_tags": ["gnome"],
            "weapon_access_names": ["kukri"],
        },
    )


GNOME_WEAPON_FAMILIARITY_STATUS = GnomeWeaponFamiliarityStatus()

__all__ = [
    "GnomeWeaponFamiliarityStatus",
    "GNOME_WEAPON_FAMILIARITY_STATUS",
    "GNOME_WEAPON_FAMILIARITY_DESCRIPTION",
]
