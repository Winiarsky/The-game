from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ANCIENT_BLOODED_DESCRIPTION = (
    "Otrzymujesz akcje specjalna \"Starozytna krew\", jej wykonanie wzmacnia "
    "pierwszy rzut obronny przeciwko czarom - circumstance bonus +1"
)


def AncientBloodedDwarfStatus() -> Status:
    """Heritage: Ancient-Blooded Dwarf (opis do UI)."""
    return Status(
        id="ancient_blooded_dwarf",
        label="Ancient-Blooded Dwarf",
        data={"ui_description": ANCIENT_BLOODED_DESCRIPTION},
    )


def AncientBloodStatus() -> Status:
    """Status tymczasowy: Ancient Blood (1 tura, jednorazowy)."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.WILL.value,
            source="status:ancient_blood",
            label="ancient blood",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.REFLEX.value,
            source="status:ancient_blood",
            label="ancient blood",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.FORTITUDE.value,
            source="status:ancient_blood",
            label="ancient blood",
        ),
    ]
    return Status(
        id="ancient_blood",
        label="Ancient Blood",
        duration=1,
        data={"consume_on_use": True},
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
                prompt_notes=["Ancient Blood"],
            )
        ],
    )


ANCIENT_BLOODED_DWARF_STATUS = AncientBloodedDwarfStatus()
ANCIENT_BLOOD_STATUS = AncientBloodStatus()

__all__ = [
    "AncientBloodedDwarfStatus",
    "ANCIENT_BLOODED_DWARF_STATUS",
    "AncientBloodStatus",
    "ANCIENT_BLOOD_STATUS",
    "ANCIENT_BLOODED_DESCRIPTION",
]
