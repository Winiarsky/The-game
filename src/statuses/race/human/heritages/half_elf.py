from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

HALF_ELF_DESCRIPTION = (
    "Either one of your parents was an elf, or one or both were\n"
    "half-elves. You have pointed ears and other telltale signs\n"
    "of elf heritage. You gain the elf trait, the half-elf trait,\n"
    "and low-light vision. In addition, you can select elf,\n"
    "half-elf, and human feats whenever you gain an ancestry feat."
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
