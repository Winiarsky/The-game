from __future__ import annotations

from .base import Status
from .check_effects import CheckEffect
from skills import Skill

# Status: uparty cel – obniża sukcesy o 1 stopień
STUBBORN_STATUS = Status(
    id="stubborn",
    label="Uparty",
    check_effects=[
        CheckEffect(
            applies_to="target",
            skills=[Skill.DIPLOMACY.value],
            demote=1,
            prompt_notes=["Rozmówca jest wyjątkowo oporny."],
        )
    ],
)

__all__ = ["STUBBORN_STATUS"]
