from __future__ import annotations

from bonuses import BonusEffect, BonusType
from .base import Status
from .check_effects import CheckEffect
from skills import Skill

# Status: szlachetne obycie – premia okoliczności +2 do Diplomacy z tagiem noble
NOBLE_PERSON_STATUS = Status(
    id="noble_person",
    label="Szlachcic",
    check_effects=[
        CheckEffect(
            applies_to="source",
            skills=[Skill.DIPLOMACY.value],
            tags_required=["noble"],
            bonus_effects=[
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag="diplomacy",
                    source="status:noble_person",
                    label="+2 szlacheckie obycie",
                )
            ],
        )
    ],
)

__all__ = ["NOBLE_PERSON_STATUS"]
