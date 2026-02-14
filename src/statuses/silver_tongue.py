from __future__ import annotations

from .base import Status
from .check_effects import CheckEffect
from skills import Skill

# Status: srebrny język – podnosi wynik o 1 stopień, nota o przewadze na kości
SILVER_TONGUE_STATUS = Status(
    id="silver_tongue",
    label="Srebrny język",
    check_effects=[
        CheckEffect(
            applies_to="source",
            skills=[Skill.DIPLOMACY.value],
            promote=1,
            prompt_notes=["Rzuć 2k20, wybierz wyższy wynik (tylko informacja)."],
        )
    ],
)

__all__ = ["SILVER_TONGUE_STATUS"]
