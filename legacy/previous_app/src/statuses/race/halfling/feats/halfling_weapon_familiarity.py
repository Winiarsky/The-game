from __future__ import annotations

from statuses.base import Status

HALFLING_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Fluff: Niziolki od dziecka ucza sie korzystac z lekkiej broni, proc i sprytnego uzbrojenia swojej kultury.\n"
    "Mechanika:\n"
    "- Kiedy: Po wybraniu tej opcji.\n"
    "- Efekt:\n"
    "  - Otrzymujesz trained z sling, halfling sling staff i shortsword.\n"
    "  - Zyskujesz dostep do wszystkich uncommon halfling weapons.\n"
    "  - Przy liczeniu bieglosci bron z tagiem halfling liczy sie o 1 kategorie latwiej: martial jako simple, a advanced jako martial.\n"
    "  - Przykład: jesli klasa daje ci trained w martial weapons, halfling advanced weapon liczysz jak martial i mozesz uzywac jej bez bycia untrained."
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
