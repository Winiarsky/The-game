from __future__ import annotations

from statuses.base import Status

GNOME_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Lepiej rozumiesz bronie tradycyjnie uzywane przez gnomy.\n"
    "Kiedy: po wybraniu featu oraz przy wyliczaniu bieglosci broni z tagiem gnome.\n"
    "Efekt: dostajesz trained z glaive i kukri; zyskujesz dostep do kukri i "
    "uncommon gnome weapons; przy wyliczaniu bieglosci dla broni z tagiem gnome "
    "kategorie sa obnizane o 1 stopien (advanced->martial, martial->simple)."
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
