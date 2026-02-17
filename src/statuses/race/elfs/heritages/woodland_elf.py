from __future__ import annotations

from statuses.base import Status

WOODLAND_ELF_DESCRIPTION = (
    "teren typu forest daje Ci mozliwosc uzycia akcji take_cover nawet jesli "
    "nie stoisz kolo obiektu kotry by to umozliwil. ponadto ignorujesz kary "
    "za trudny teren typu krzaki"
)


def WoodlandElfStatus() -> Status:
    """Heritage: Woodland Elf."""
    return Status(
        id="woodland_elf",
        label="Woodland Elf",
        data={
            "ui_description": WOODLAND_ELF_DESCRIPTION,
            "allow_take_cover_terrain_tags": ["forest"],
            "ignore_move_cost_terrain_tags": ["bushes"],
        },
    )


WOODLAND_ELF_STATUS = WoodlandElfStatus()

__all__ = ["WoodlandElfStatus", "WOODLAND_ELF_STATUS", "WOODLAND_ELF_DESCRIPTION"]
