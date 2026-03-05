from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

IRONGUT_GOBLIN_DESCRIPTION = (
    "Możesz żywić się zepsutym jedzeniem i jeść/pić nawet gdy jesteś sickened.\n"
    "Masz +2 circumstance do save przeciw afflictions od rzeczy spożytych, "
    "przeciw uzyskaniu sickened z rzeczy spożytych oraz przy próbie usunięcia "
    "sickened z rzeczy spożytych.\n"
    "Dla Fortitude save: success -> critical success (gdy dotyczy ingested)."
)


def IrongutGoblinStatus() -> Status:
    """Heritage: Irongut Goblin."""
    return Status(
        id="irongut_goblin",
        label="Irongut Goblin",
        data={
            "ui_description": IRONGUT_GOBLIN_DESCRIPTION,
            "can_subsist_on_garbage_in_settlement": True,
            "can_eat_while_sickened": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value],
                tags_required=["ingested"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.FORTITUDE.value,
                        source="status:irongut_goblin",
                        label="irongut",
                    )
                ],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Irongut Goblin"],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.WILL.value, Skill.REFLEX.value],
                tags_required=["ingested"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.WILL.value,
                        source="status:irongut_goblin",
                        label="irongut",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.REFLEX.value,
                        source="status:irongut_goblin",
                        label="irongut",
                    ),
                ],
                prompt_notes=["Irongut Goblin: +2 vs ingested affliction/sickened checks."],
            ),
        ],
    )


IRONGUT_GOBLIN_STATUS = IrongutGoblinStatus()

__all__ = [
    "IrongutGoblinStatus",
    "IRONGUT_GOBLIN_STATUS",
    "IRONGUT_GOBLIN_DESCRIPTION",
]
