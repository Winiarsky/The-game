from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

FORLORN_DESCRIPTION = (
    "Masz +1 circumstance do save przeciw efektom emotion.\n"
    "Na sukces przeciw emotion otrzymujesz krytyczny sukces."
)


def ForlornStatus() -> Status:
    """Feat: Forlorn."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.FORTITUDE.value,
            source="status:forlorn",
            label="forlorn +1",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.REFLEX.value,
            source="status:forlorn",
            label="forlorn +1",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.WILL.value,
            source="status:forlorn",
            label="forlorn +1",
        ),
    ]
    return Status(
        id="forlorn",
        label="Forlorn",
        data={"ui_description": FORLORN_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["emotion"],
                bonus_effects=bonus_effects,
                promote=1,
                promote_on=["success"],
                prompt_notes=["Forlorn: +1 vs emotion, success -> critical success."],
            )
        ],
    )


FORLORN_STATUS = ForlornStatus()

__all__ = ["ForlornStatus", "FORLORN_STATUS", "FORLORN_DESCRIPTION"]
