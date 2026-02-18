from __future__ import annotations

from statuses.base import Status

NIMBLE_ELF_DESCRIPTION = "Twoja predkosc zwieksza sie o 5 stop"


def NimbleElfStatus() -> Status:
    """Feat: Nimble Elf (opis do UI)."""
    return Status(
        id="nimble_elf",
        label="Nimble Elf",
        data={"ui_description": NIMBLE_ELF_DESCRIPTION},
    )


NIMBLE_ELF_STATUS = NimbleElfStatus()

__all__ = ["NimbleElfStatus", "NIMBLE_ELF_STATUS", "NIMBLE_ELF_DESCRIPTION"]
