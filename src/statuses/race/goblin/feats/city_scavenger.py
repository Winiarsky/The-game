from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

CITY_SCAVENGER_DESCRIPTION = (
    "Umiesz zdobywać zasoby i zarobek, żerując na miejskich okazjach.\n"
    "Kiedy: testy Subsist w settlement (Society albo Survival) oraz testy Earn Income "
    "podczas Subsist w city.\n"
    "Efekt: +1 circumstance do wskazanych testów; możesz używać Society/Survival do Subsist "
    "w settlement i wykonywać równoległe Earn Income podczas Subsist w city. "
    "Jeśli masz heritage Irongut Goblin, bonus rośnie do +2."
)


def CityScavengerStatus(*, bonus: int = 1) -> Status:
    """Feat: City Scavenger."""
    final_bonus = max(1, int(bonus or 1))
    return Status(
        id="city_scavenger",
        label="City Scavenger",
        data={
            "ui_description": CITY_SCAVENGER_DESCRIPTION,
            "city_scavenger_bonus": final_bonus,
            "city_scavenger_bonus_if_irongut": 2,
            "city_scavenger_subsist_skills": [Skill.SOCIETY.value, Skill.SURVIVAL.value],
            "city_scavenger_earn_income_skills": [Skill.SOCIETY.value, Skill.SURVIVAL.value],
            "city_scavenger_allows_parallel_earn_income_in_city": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.SOCIETY.value, Skill.SURVIVAL.value],
                tags_required=["subsist", "settlement"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=final_bonus,
                        tag=Skill.SOCIETY.value,
                        source="status:city_scavenger",
                        label=f"city scavenger +{final_bonus}",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=final_bonus,
                        tag=Skill.SURVIVAL.value,
                        source="status:city_scavenger",
                        label=f"city scavenger +{final_bonus}",
                    ),
                ],
                prompt_notes=[
                    f"City Scavenger: +{final_bonus} do Subsist (Society/Survival) w settlement."
                ],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.SOCIETY.value, Skill.SURVIVAL.value],
                tags_required=["earn_income", "subsist", "city"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=final_bonus,
                        tag=Skill.SOCIETY.value,
                        source="status:city_scavenger",
                        label=f"city scavenger +{final_bonus}",
                    ),
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=final_bonus,
                        tag=Skill.SURVIVAL.value,
                        source="status:city_scavenger",
                        label=f"city scavenger +{final_bonus}",
                    ),
                ],
                prompt_notes=[
                    f"City Scavenger: +{final_bonus} do Earn Income (Society/Survival) podczas Subsist w city."
                ],
            ),
        ],
    )


CITY_SCAVENGER_STATUS = CityScavengerStatus()

__all__ = ["CityScavengerStatus", "CITY_SCAVENGER_STATUS", "CITY_SCAVENGER_DESCRIPTION"]
