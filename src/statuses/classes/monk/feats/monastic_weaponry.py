from __future__ import annotations

from statuses.base import Status

MONASTIC_WEAPONRY_DESCRIPTION = (
    "Monastic Weaponry: bronie z traitem monk traktujesz jak proste do biegłości, "
    "a melee monk weapons mozesz wykorzystywac z Flurry of Blows i Ki Strike, "
    "o ile nie ogranicza cie aktywna stance."
)

MONASTIC_WEAPONRY_WEAPON_IDS = [
    "bo_staff",
    "kama",
    "katar",
    "nunchaku",
    "sai",
    "shuriken",
    "temple_sword",
]


def MonasticWeaponryStatus() -> Status:
    return Status(
        id="monastic_weaponry",
        label="Monastic Weaponry",
        data={
            "ui_description": MONASTIC_WEAPONRY_DESCRIPTION,
            "ui_prompt": MONASTIC_WEAPONRY_DESCRIPTION,
            "weapon_category_adjustments": [
                {
                    "required_tag": "monk",
                    "from": "martial",
                    "to": "simple",
                }
            ],
            "monastic_weapon_required_trait": "monk",
            "monastic_weapon_melee_only": True,
            "monastic_weapon_ids": list(MONASTIC_WEAPONRY_WEAPON_IDS),
        },
    )


MONASTIC_WEAPONRY_STATUS = MonasticWeaponryStatus()

__all__ = [
    "MonasticWeaponryStatus",
    "MONASTIC_WEAPONRY_STATUS",
    "MONASTIC_WEAPONRY_DESCRIPTION",
    "MONASTIC_WEAPONRY_WEAPON_IDS",
]
