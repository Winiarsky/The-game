from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

STRONG_BLOODED_DESCRIPTION = (
    "Odporność na poison: 1 na 2 poziomy (min 1).\n"
    "Po udanym save vs poison: stage -2 (virulent: -1).\n"
    "Po krytycznym sukcesie: stage -3 (virulent: -2).\n"
    "Przykład: jad na stage 3, zwykły sukces -> stage 1."
)


def StrongBloodedDwarfStatus() -> Status:
    """Heritage: Strong-Blooded Dwarf."""
    return Status(
        id="strong_blooded_dwarf",
        label="Strong-Blooded Dwarf",
        data={
            "ui_description": STRONG_BLOODED_DESCRIPTION,
            "damage_resistance": {
                DamageType.POISON.value: {"per_2_levels": 1, "minimum": 1}
            },
            "poison_stage_reduction_on_success": 2,
            "poison_stage_reduction_on_success_virulent": 1,
            "poison_stage_reduction_on_critical_success": 3,
            "poison_stage_reduction_on_critical_success_virulent": 2,
        },
    )


STRONG_BLOODED_DWARF_STATUS = StrongBloodedDwarfStatus()

__all__ = [
    "StrongBloodedDwarfStatus",
    "STRONG_BLOODED_DWARF_STATUS",
    "STRONG_BLOODED_DESCRIPTION",
]
