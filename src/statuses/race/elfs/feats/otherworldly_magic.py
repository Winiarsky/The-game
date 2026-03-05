from __future__ import annotations

from statuses.base import Status

OTHERWORLDLY_MAGIC_DESCRIPTION = (
    "Wybierz 1 arcane cantrip, który możesz rzucać jako innate spell at-will.\n"
    "W tym silniku wybór cantripa zapisywany jest na statusie."
)


def OtherworldlyMagicStatus() -> Status:
    """Feat: Otherworldly Magic."""
    return Status(
        id="otherworldly_magic",
        label="Otherworldly Magic",
        data={
            "ui_description": OTHERWORLDLY_MAGIC_DESCRIPTION,
            "ui_choice_kind": "otherworldly_magic",
            "otherworldly_magic_choices": [
                "detect_magic",
                "daze",
                "light",
                "mage_hand",
                "shield",
                "ray_of_frost",
                "telekinetic_projectile",
                "produce_flame",
                "ghost_sound",
                "message",
            ],
            "otherworldly_magic_cantrip": None,
            "granted_cantrips": [],
            "innate_magic_tradition": "arcane",
        },
    )


OTHERWORLDLY_MAGIC_STATUS = OtherworldlyMagicStatus()

__all__ = [
    "OtherworldlyMagicStatus",
    "OTHERWORLDLY_MAGIC_STATUS",
    "OTHERWORLDLY_MAGIC_DESCRIPTION",
]
