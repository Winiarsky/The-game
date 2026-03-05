from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ROCK_DWARF_DESCRIPTION = (
    "+2 circumstance bonus do testow, gdy bohater jest celem shove/trip "
    "(Reflex lub Fortitude), +2 vs efekty przewracające oraz redukcja forced movement.\n"
    "Mechanika: forced movement 10+ ft jest zmniejszany o połowę.\n"
    "Przykład: krytyczny Shove przesuwa o 10 ft -> Rock Dwarf przesuwa się o 5 ft."
)


def RockDwarfStatus() -> Status:
    """Heritage: Rock Dwarf."""
    effects = []
    for tag in ("shove", "trip"):
        effects.append(
            CheckEffect(
                applies_to="target",
                skills=[Skill.REFLEX.value, Skill.FORTITUDE.value],
                tags_required=[tag],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.REFLEX.value,
                        source="status:rock_dwarf",
                        label="rock dwarf",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.FORTITUDE.value,
                        source="status:rock_dwarf",
                        label="rock dwarf",
                    ),
                ],
                prompt_notes=["Rock Dwarf"],
            )
        )
    effects.append(
        CheckEffect(
            applies_to="target",
            skills=[Skill.REFLEX.value, Skill.FORTITUDE.value],
            tags_required=["prone"],
            bonus_effects=[
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag=Skill.REFLEX.value,
                    source="status:rock_dwarf",
                    label="rock dwarf",
                ),
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag=Skill.FORTITUDE.value,
                    source="status:rock_dwarf",
                    label="rock dwarf",
                ),
            ],
            prompt_notes=["Rock Dwarf: +2 vs prone effects"],
        )
    )

    return Status(
        id="rock_dwarf",
        label="Rock Dwarf",
        data={
            "ui_description": ROCK_DWARF_DESCRIPTION,
            "forced_movement_multiplier": 0.5,
            "forced_movement_threshold_feet": 10,
            "defensive_effect_tags": ["shove", "trip", "prone"],
        },
        check_effects=effects,
    )


ROCK_DWARF_STATUS = RockDwarfStatus()

__all__ = ["RockDwarfStatus", "ROCK_DWARF_STATUS", "ROCK_DWARF_DESCRIPTION"]
