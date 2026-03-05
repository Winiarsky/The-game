from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect


def BlindedStatus() -> Status:
    """Status: oślepiony – -4 do wybranych testów umiejętności."""
    penalty = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=4,
        tag="",
        source="status:blinded",
        label="oślepiony -4",
        is_penalty=True,
    )
    effects = []
    for skill in (Skill.THIEVERY, Skill.MEDICINE, Skill.CRAFTING, Skill.ACROBATICS):
        effects.append(
            CheckEffect(
                applies_to="source",
                skills=[skill.value],
                bonus_effects=[
                    BonusEffect(
                        type=penalty.type,
                        value=penalty.value,
                        tag=skill.value,
                        source=penalty.source,
                        label=penalty.label,
                        is_penalty=True,
                    )
                ],
            )
        )
    return Status(
        id="blinded",
        label="Blinded",
        data={"effect_tags": ["blinded", "visual"], "vision_checks_auto_fail": True},
        check_effects=effects,
    )


BLINDED_STATUS = BlindedStatus()

__all__ = ["BlindedStatus", "BLINDED_STATUS"]
