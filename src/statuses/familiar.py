from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from .base import Status
from .check_effects import CheckEffect

FAMILIAR_OWNER_STATUS = Status(
    id="FamiliarOwner",
    label="Familiar Owner",
    data={"ui_description": "Posiadasz familiara i możesz go komenderować."},
)


def FamiliarScoutStatus() -> Status:
    return Status(
        id="familiar_scout",
        label="Familiar: Scout",
        data={"consume_on_use": True},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="familiar:scout",
                        label="familiar scout +2",
                    )
                ],
                prompt_notes=["Familiar Scout: +2 do Perception (jednorazowo)."],
            )
        ],
    )


def FamiliarGuidanceStatus(skill_id: str) -> Status:
    return Status(
        id=f"familiar_guidance_{skill_id}",
        label="Familiar: Guidance",
        data={"consume_on_use": True, "skill_id": skill_id},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[skill_id],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=skill_id,
                        source="familiar:guidance",
                        label="familiar guidance +1",
                    )
                ],
                prompt_notes=["Familiar Guidance: +1 (jednorazowo)."],
            )
        ],
    )


FAMILIAR_DISTRACT_STATUS = Status(
    id="familiar_distract",
    label="Familiar: Distract",
)


FAMILIAR_TOUCH_DELIVERY_STATUS = Status(
    id="familiar_touch_delivery",
    label="Familiar: Touch Delivery",
)


__all__ = [
    "FAMILIAR_OWNER_STATUS",
    "FamiliarScoutStatus",
    "FamiliarGuidanceStatus",
    "FAMILIAR_DISTRACT_STATUS",
    "FAMILIAR_TOUCH_DELIVERY_STATUS",
]
