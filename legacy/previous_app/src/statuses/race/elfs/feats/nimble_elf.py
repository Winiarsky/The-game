from __future__ import annotations

from statuses.base import Status

NIMBLE_ELF_DESCRIPTION = (
    "Twoja bazowa prędkość rośnie o 5 stóp.\n"
    "Przykład: elf 30 ft -> 35 ft."
)


def NimbleElfStatus() -> Status:
    """Feat: Nimble Elf."""
    return Status(
        id="nimble_elf",
        label="Nimble Elf",
        data={
            "ui_description": NIMBLE_ELF_DESCRIPTION,
            "base_speed_bonus_feet": 5,
        },
    )


NIMBLE_ELF_STATUS = NimbleElfStatus()

__all__ = ["NimbleElfStatus", "NIMBLE_ELF_STATUS", "NIMBLE_ELF_DESCRIPTION"]
