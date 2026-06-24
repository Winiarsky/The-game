from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

BREATH_CONTROL_DESCRIPTION = (
    "Potrafisz wstrzymac oddech 25x dluzej (opisowo). "
    "+1 circumstance do rzutow obronnych przeciwko inhalowanym zagrozeniom; "
    "sukces staje sie krytycznym sukcesem. "
    "W praktyce dziala na tagu poison (uprostrzenie)."
)


def BreathControlStatus() -> Status:
    """Feat: Breath Control."""
    return Status(
        id="breath_control",
        label="Breath Control",
        data={"ui_description": BREATH_CONTROL_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value],
                tags_required=["poison"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.FORTITUDE.value,
                        source="status:breath_control",
                        label="breath control +1",
                    )
                ],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Breath Control: +1 vs poison, sukces -> krytyczny sukces."],
            )
        ],
    )


BREATH_CONTROL_STATUS = BreathControlStatus()

__all__ = [
    "BreathControlStatus",
    "BREATH_CONTROL_STATUS",
    "BREATH_CONTROL_DESCRIPTION",
]
