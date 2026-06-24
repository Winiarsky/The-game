from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

UNWAVERING_MIEN_DESCRIPTION = (
    "Gdy mental effect trwa co najmniej 2 rundy, możesz skrócić go o 1 rundę.\n"
    "Dodatkowo save przeciw efektom usypiającym traktujesz o 1 stopień lepiej."
)


def UnwaveringMienStatus() -> Status:
    """Feat: Unwavering Mien."""
    return Status(
        id="unwavering_mien",
        label="Unwavering Mien",
        data={
            "ui_description": UNWAVERING_MIEN_DESCRIPTION,
            "reduce_mental_effect_duration_rounds": 1,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.WILL.value,
                    Skill.FORTITUDE.value,
                    Skill.REFLEX.value,
                ],
                tags_required=["sleep"],
                promote=1,
                prompt_notes=["Unwavering Mien: save vs sleep o 1 stopień lepiej."],
            )
        ],
    )


UNWAVERING_MIEN_STATUS = UnwaveringMienStatus()

__all__ = [
    "UnwaveringMienStatus",
    "UNWAVERING_MIEN_STATUS",
    "UNWAVERING_MIEN_DESCRIPTION",
]
