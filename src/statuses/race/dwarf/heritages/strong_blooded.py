from __future__ import annotations

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

STRONG_BLOODED_DESCRIPTION = (
    "Redukuje obrazenia typu poison o 1 na 2 poziomy (min 1) "
    "i daje +1 do Fortitude vs poison."
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
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value],
                tags_required=["poison"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.FORTITUDE.value,
                        source="status:strong_blooded_dwarf",
                        label="strong-blooded",
                    )
                ],
                prompt_notes=["Strong-Blooded"],
            )
        ],
    )


STRONG_BLOODED_DWARF_STATUS = StrongBloodedDwarfStatus()

__all__ = [
    "StrongBloodedDwarfStatus",
    "STRONG_BLOODED_DWARF_STATUS",
    "STRONG_BLOODED_DESCRIPTION",
]
