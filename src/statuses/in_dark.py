from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect


def InDarkStatus() -> Status:
    """Status ciemności – informacja o +10 circumstance do Stealth (manualnie)."""
    return Status(
        id="in_dark",
        label="In Dark",
        data={"effect_tags": ["darkness"]},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.STEALTH.value],
                tags_required=["try_stealth"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=10,
                        tag=Skill.STEALTH.value,
                        source="status:in_dark",
                        label="ciemność +10",
                    )
                ],
                prompt_notes=["Ciemność: +10 circumstance do Stealth."],
            )
        ],
    )


IN_DARK_STATUS = InDarkStatus()

__all__ = ["InDarkStatus", "IN_DARK_STATUS"]
