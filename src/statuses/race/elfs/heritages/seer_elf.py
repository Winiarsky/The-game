from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

SEER_ELF_DESCRIPTION = (
    "Mozesz rzucac czar Detect Magic, otrzymujesz rowniez premie +1 "
    "Circumstance do testow Arcana, Occultism i Religion"
)


def SeerElfStatus() -> Status:
    """Heritage: Seer Elf."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.ARCANA.value,
            source="status:seer_elf",
            label="seer elf",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.OCCULTISM.value,
            source="status:seer_elf",
            label="seer elf",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.RELIGION.value,
            source="status:seer_elf",
            label="seer elf",
        ),
    ]
    return Status(
        id="seer_elf",
        label="Seer Elf",
        data={"ui_description": SEER_ELF_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.ARCANA.value,
                    Skill.OCCULTISM.value,
                    Skill.RELIGION.value,
                ],
                bonus_effects=bonus_effects,
                prompt_notes=["Seer Elf"],
            )
        ],
    )


SEER_ELF_STATUS = SeerElfStatus()

__all__ = ["SeerElfStatus", "SEER_ELF_STATUS", "SEER_ELF_DESCRIPTION"]
