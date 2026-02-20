from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

TRICK_MAGIC_ITEM_DESCRIPTION = (
    "+2 circumstance do testu z tagiem magic_item (Arcana/Nature/Occultism/Religion)."
)


def TrickMagicItemStatus() -> Status:
    """Feat: Trick Magic Item (opis do UI)."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.ARCANA.value,
            source="status:trick_magic_item",
            label="trick magic +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.NATURE.value,
            source="status:trick_magic_item",
            label="trick magic +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.OCCULTISM.value,
            source="status:trick_magic_item",
            label="trick magic +2",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.RELIGION.value,
            source="status:trick_magic_item",
            label="trick magic +2",
        ),
    ]
    return Status(
        id="trick_magic_item",
        label="Trick Magic Item",
        data={"ui_description": TRICK_MAGIC_ITEM_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.ARCANA.value,
                    Skill.NATURE.value,
                    Skill.OCCULTISM.value,
                    Skill.RELIGION.value,
                ],
                tags_required=["magic_item"],
                bonus_effects=bonus_effects,
                prompt_notes=["Trick Magic Item: +2 (magic_item)."],
            )
        ],
    )


TRICK_MAGIC_ITEM_STATUS = TrickMagicItemStatus()

__all__ = [
    "TrickMagicItemStatus",
    "TRICK_MAGIC_ITEM_STATUS",
    "TRICK_MAGIC_ITEM_DESCRIPTION",
]
