from __future__ import annotations

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_GOBLIN_HERITAGE_DATA = {"ancestry": "goblin", "heritage": True, "traits": ["goblin", "heritage"]}


def _heritage_data_with_resistance(resistance: dict[str, int] | None = None) -> dict[str, object]:
    """Kopia bazowych danych heritage z opcjonalną redukcją obrażeń."""
    data = dict(_GOBLIN_HERITAGE_DATA)
    if resistance:
        data["damage_resistance"] = resistance
    return data


def CharhideGoblinStatus() -> Status:
    """Redukcja obrażeń fire o 1 (min 0)."""
    return Status(
        id="heritage_charhide_goblin",
        label="Charhide Goblin",
        data=_heritage_data_with_resistance({DamageType.FIRE.value: 1}),
    )


CHARHIDE_GOBLIN_STATUS = CharhideGoblinStatus()


def IrongutGoblinStatus() -> Status:
    """+2 circumstance do Fortitude vs fire; sukces -> krytyk."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.FORTITUDE.value,
        source="heritage:irongut_goblin",
        label="+2 Fortitude vs fire",
    )
    return Status(
        id="heritage_irongut_goblin",
        label="Irongut Goblin",
        data=_GOBLIN_HERITAGE_DATA,
        check_effects=[
            CheckEffect(
                applies_to="target",
                skills=[Skill.FORTITUDE.value],
                tags_required=["fire"],
                bonus_effects=[bonus],
                promote=1,
                promote_on=["success"],
                prompt_notes=[
                    "+2 circumstance do rzutów Fortitude przeciw efektom z tagiem fire.",
                    "Sukces takiego rzutu staje się krytycznym sukcesem.",
                ],
            )
        ],
    )


IRONGUT_GOBLIN_STATUS = IrongutGoblinStatus()


def RazortoothGoblinStatus() -> Status:
    """Informacja o karcie broni 'Ostre Zęby' (niezaimplementowane)."""
    return Status(
        id="heritage_razortooth_goblin",
        label="Razortooth Goblin",
        data={
            **_GOBLIN_HERITAGE_DATA,
            "prompt_notes": ["Weź kartę broni 'Ostre Zęby' (jeszcze niezaimplementowane w systemie)."],
        },
    )


RAZORTOOTH_GOBLIN_STATUS = RazortoothGoblinStatus()


def SnowGoblinStatus() -> Status:
    """Redukcja obrażeń cold/ice o 1 (min 0)."""
    return Status(
        id="heritage_snow_goblin",
        label="Snow Goblin",
        data=_heritage_data_with_resistance({DamageType.COLD.value: 1}),
    )


SNOW_GOBLIN_STATUS = SnowGoblinStatus()


def UnbreakableGoblinStatus() -> Status:
    """Informacja: startowe HP 10 zamiast 8."""
    return Status(
        id="heritage_unbreakable_goblin",
        label="Unbreakable Goblin",
        data={
            **_GOBLIN_HERITAGE_DATA,
            "prompt_notes": ["Masz 10 zamiast 8 bazowych HP (pamiętaj przy tworzeniu bohatera)."],
        },
    )


UNBREAKABLE_GOBLIN_STATUS = UnbreakableGoblinStatus()


__all__ = [
    "CharhideGoblinStatus",
    "CHARHIDE_GOBLIN_STATUS",
    "IrongutGoblinStatus",
    "IRONGUT_GOBLIN_STATUS",
    "RazortoothGoblinStatus",
    "RAZORTOOTH_GOBLIN_STATUS",
    "SnowGoblinStatus",
    "SNOW_GOBLIN_STATUS",
    "UnbreakableGoblinStatus",
    "UNBREAKABLE_GOBLIN_STATUS",
]
