from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

HALF_ELF_DESCRIPTION = (
    "Co najmniej jedno z twoich rodzicow jest elfem lub polelfem.\n"
    "Masz wyrazne cechy elfiego pochodzenia, jak ostre uszy.\n"
    "Zyskujesz cechy elf i half-elf oraz widzenie w polmroku.\n"
    "Dodatkowo przy wyborze ancestry featow mozesz wybierac featy\n"
    "z listy elf, half-elf i human."
)


def HalfElfStatus() -> Status:
    """Heritage: Half-Elf."""
    return Status(
        id="half_elf",
        label="Half-Elf",
        data={
            "ui_description": HALF_ELF_DESCRIPTION,
            "ancestry_extra_traits": ["elf", "half_elf"],
            "ancestry_feat_access": ["elf", "half_elf", "human"],
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


HALF_ELF_STATUS = HalfElfStatus()

__all__ = ["HalfElfStatus", "HALF_ELF_STATUS", "HALF_ELF_DESCRIPTION"]
