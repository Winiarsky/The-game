from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

CAVERN_ELF_DESCRIPTION = (
    "Zyskujesz Darkvision.\n"
    "Dziedzictwo zastępuje bazowe Low-Light Vision elfa."
)


def CavernElfStatus() -> Status:
    """Heritage: Cavern Elf."""
    return Status(
        id="cavern_elf",
        label="Cavern Elf",
        data={
            "ui_description": CAVERN_ELF_DESCRIPTION,
            "remove_statuses": [DIM_LIGHT_VISION_STATUS],
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


CAVERN_ELF_STATUS = CavernElfStatus()

__all__ = ["CavernElfStatus", "CAVERN_ELF_STATUS", "CAVERN_ELF_DESCRIPTION"]
