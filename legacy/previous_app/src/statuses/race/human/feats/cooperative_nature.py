from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

COOPERATIVE_NATURE_DESCRIPTION = (
    "Masz +4 circumstance bonus do checks to Aid."
)


def CooperativeNatureStatus() -> Status:
    """Feat: Cooperative Nature."""
    bonus_effects = []
    for skill in Skill:
        bonus_effects.append(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=4,
                tag=skill.value,
                source="status:cooperative_nature",
                label="cooperative nature +4",
            )
        )
    return Status(
        id="cooperative_nature",
        label="Cooperative Nature",
        data={
            "ui_description": COOPERATIVE_NATURE_DESCRIPTION,
            "aid_check_bonus": 4,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                tags_required=["aid"],
                bonus_effects=bonus_effects,
                prompt_notes=["Cooperative Nature: +4 circumstance do check to Aid."],
            )
        ],
    )


COOPERATIVE_NATURE_STATUS = CooperativeNatureStatus()

__all__ = [
    "CooperativeNatureStatus",
    "COOPERATIVE_NATURE_STATUS",
    "COOPERATIVE_NATURE_DESCRIPTION",
]
