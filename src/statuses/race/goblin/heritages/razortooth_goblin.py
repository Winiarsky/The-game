from __future__ import annotations

from statuses.base import Status

RAZORTOOTH_GOBLIN_DESCRIPTION = (
    "Twoje szczęki są naturalną bronią.\n"
    "Zyskujesz atak nieuzbrojony Szczeki: 1d6 piercing, grupa brawling, cechy finesse i unarmed."
)


def RazortoothGoblinStatus() -> Status:
    """Heritage: Razortooth Goblin."""
    return Status(
        id="razortooth_goblin",
        label="Razortooth Goblin",
        data={
            "ui_description": RAZORTOOTH_GOBLIN_DESCRIPTION,
            "ui_prompt": "Razortooth Goblin: masz nową akcję 'Razortooth Jaws' (1d6 piercing, finesse, unarmed).",
            "granted_unarmed_attacks": [
                {
                    "id": "razortooth_jaws",
                    "damage_dice": "1d6",
                    "damage_type": "piercing",
                    "weapon_group": "brawling",
                    "traits": ["finesse", "unarmed"],
                }
            ],
        },
    )


RAZORTOOTH_GOBLIN_STATUS = RazortoothGoblinStatus()

__all__ = [
    "RazortoothGoblinStatus",
    "RAZORTOOTH_GOBLIN_STATUS",
    "RAZORTOOTH_GOBLIN_DESCRIPTION",
]
