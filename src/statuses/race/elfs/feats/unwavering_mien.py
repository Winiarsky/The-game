from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

UNWAVERING_MIEN_DESCRIPTION = (
    "otrzymujesz bonus +1 do testow Will, Fortitude i Reflex gdy test ma tag "
    "mental; dodatkowo podnosisz wynik o jeden stopien"
)


def UnwaveringMienStatus() -> Status:
    """Feat: Unwavering Mien."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.WILL.value,
            source="status:unwavering_mien",
            label="unwavering mien",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.FORTITUDE.value,
            source="status:unwavering_mien",
            label="unwavering mien",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.REFLEX.value,
            source="status:unwavering_mien",
            label="unwavering mien",
        ),
    ]
    return Status(
        id="unwavering_mien",
        label="Unwavering Mien",
        data={"ui_description": UNWAVERING_MIEN_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.WILL.value,
                    Skill.FORTITUDE.value,
                    Skill.REFLEX.value,
                ],
                tags_required=["mental"],
                bonus_effects=bonus_effects,
                promote=1,
                prompt_notes=["Unwavering Mien"],
            )
        ],
    )


UNWAVERING_MIEN_STATUS = UnwaveringMienStatus()

__all__ = [
    "UnwaveringMienStatus",
    "UNWAVERING_MIEN_STATUS",
    "UNWAVERING_MIEN_DESCRIPTION",
]
