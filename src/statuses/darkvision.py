from __future__ import annotations

from statuses.base import Status
from statuses.check_effects import CheckEffect
from skills import Skill


def DarkVisionStatus() -> Status:
    """Status darkvision – blokuje efekty ciemności."""
    return Status(
        id="darkvision",
        label="Darkvision",
        data={
            "immune_status_ids": ["blinded"],
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                prompt_notes=["Ignorujesz efekty naturalnej ciemnosci."],
            )
        ],
    )


DARKVISION_STATUS = DarkVisionStatus()

__all__ = ["DarkVisionStatus", "DARKVISION_STATUS"]
