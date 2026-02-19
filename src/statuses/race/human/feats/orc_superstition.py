from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ORC_SUPERSTITION_DESCRIPTION = (
    "+1 circumstance do rzutow obronnych przeciwko magii (tag magic)."
)


def OrcSuperstitionStatus() -> Status:
    """Feat: Orc Superstition."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.WILL.value,
            source="status:orc_superstition",
            label="orc superstition +1",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.REFLEX.value,
            source="status:orc_superstition",
            label="orc superstition +1",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.FORTITUDE.value,
            source="status:orc_superstition",
            label="orc superstition +1",
        ),
    ]
    return Status(
        id="orc_superstition",
        label="Orc Superstition",
        data={"ui_description": ORC_SUPERSTITION_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.WILL.value,
                    Skill.REFLEX.value,
                    Skill.FORTITUDE.value,
                ],
                tags_required=["magic"],
                bonus_effects=bonus_effects,
                prompt_notes=["Orc Superstition: +1 vs magic."],
            )
        ],
    )


ORC_SUPERSTITION_STATUS = OrcSuperstitionStatus()

__all__ = [
    "OrcSuperstitionStatus",
    "ORC_SUPERSTITION_STATUS",
    "ORC_SUPERSTITION_DESCRIPTION",
]
