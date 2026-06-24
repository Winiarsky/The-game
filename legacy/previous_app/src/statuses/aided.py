from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from .base import Status
from .check_effects import CheckEffect


def AidedStatus(*, bonus: int = 1, skill_id: str | None = None) -> Status:
    """Jednorazowy bonus do najbliższego testu umiejętności."""
    bonus = int(bonus)
    if skill_id:
        skills = [skill_id]
    else:
        skills = [skill.value for skill in Skill]
    effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=bonus,
            tag=skill_id,
            source="status:aided",
            label=f"aided +{bonus}",
        )
        for skill_id in skills
    ]
    return Status(
        id="aided",
        label="Aided",
        data={"consume_on_use": True, "bonus": bonus, "skill_id": skill_id},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=skills,
                tags_required=["roll"],
                bonus_effects=effects,
                prompt_notes=[f"Aided: +{bonus} do najbliższego testu (jednorazowo)."],
            )
        ],
    )


__all__ = ["AidedStatus"]
