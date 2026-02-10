from __future__ import annotations

from bonuses import BonusEffect, BonusType
from .base import Status
from .check_effects import CheckEffect

# Status: szlachetne obycie – premia okoliczności +2 do Diplomacy z tagiem noble
NOBLE_PERSON_STATUS = Status(
    id="noble_person",
    label="Szlachcic",
    check_effects=[
        CheckEffect(
            applies_to="source",
            skills=["diplomacy"],
            tags_required=["noble"],
            bonus_effects=[
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag="diplomacy",
                    source="status:noble_person",
                    label="+2 szlacheckie obycie",
                )
            ],
        )
    ],
)

# Status: srebrny język – podnosi wynik o 1 stopień, nota o przewadze na kości
SILVER_TONGUE_STATUS = Status(
    id="silver_tongue",
    label="Srebrny język",
    check_effects=[
        CheckEffect(
            applies_to="source",
            skills=["diplomacy"],
            promote=1,
            prompt_notes=["Rzuć 2k20, wybierz wyższy wynik (tylko informacja)."],
        )
    ],
)

# Status: uparty cel – obniża sukcesy o 1 stopień
STUBBORN_STATUS = Status(
    id="stubborn",
    label="Uparty",
    check_effects=[
        CheckEffect(
            applies_to="target",
            skills=["diplomacy"],
            demote=1,
            prompt_notes=["Rozmówca jest wyjątkowo oporny."],
        )
    ],
)

__all__ = [
    "NOBLE_PERSON_STATUS",
    "SILVER_TONGUE_STATUS",
    "STUBBORN_STATUS",
]
