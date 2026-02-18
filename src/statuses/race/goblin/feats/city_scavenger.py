from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

CITY_SCAVENGER_DESCRIPTION = (
    "+1 circumstance do testów Society lub Survival. Dla Survivalu wynik testu podbity o 1 stopień."
)


def CityScavengerStatus() -> Status:
    """Feat: City Scavenger."""
    return Status(
        id="city_scavenger",
        label="City Scavenger",
        data={"ui_description": CITY_SCAVENGER_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.SOCIETY.value, Skill.SURVIVAL.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.SOCIETY.value,
                        source="status:city_scavenger",
                        label="city scavenger +1",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.SURVIVAL.value,
                        source="status:city_scavenger",
                        label="city scavenger +1",
                    ),
                ],
                prompt_notes=["City Scavenger: +1 circumstance do Society/Survival."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.SURVIVAL.value],
                promote=1,
                prompt_notes=["City Scavenger: wynik Survival podbity o 1 stopień."],
            ),
        ],
    )


CITY_SCAVENGER_STATUS = CityScavengerStatus()

__all__ = ["CityScavengerStatus", "CITY_SCAVENGER_STATUS", "CITY_SCAVENGER_DESCRIPTION"]
