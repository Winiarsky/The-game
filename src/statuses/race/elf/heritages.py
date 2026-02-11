from __future__ import annotations

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_ELF_HERITAGE_DATA = {"ancestry": "elf", "heritage": True, "traits": ["elf", "heritage"]}


def _heritage_data_with_resistance(resistance: dict[str, int] | None = None) -> dict[str, object]:
    """Kopia bazowych danych heritage z opcjonalną redukcją obrażeń."""
    data = dict(_ELF_HERITAGE_DATA)
    if resistance:
        data["damage_resistance"] = resistance
    return data


def ArcticElfStatus() -> Status:
    """Redukcja obrażeń cold o 1 (min 0)."""
    return Status(
        id="heritage_arctic_elf",
        label="Arctic Elf",
        data=_heritage_data_with_resistance({DamageType.COLD.value: 1}),
    )


ARCTIC_ELF_STATUS = ArcticElfStatus()


def CavernElfStatus() -> Status:
    """Ignoruje efekty/eventy z tagiem dark (informacja do logiki)."""
    return Status(
        id="heritage_cavern_elf",
        label="Cavern Elf",
        data={
            **_ELF_HERITAGE_DATA,
            "ignore_effect_tags": ["dark"],
            "prompt_notes": ["Ignorujesz efekty i eventy z tagiem dark (np. darkness)."],
        },
    )


CAVERN_ELF_STATUS = CavernElfStatus()


def SeerElfStatus() -> Status:
    """+1 circumstance do testów z tagiem identify_magic lub decipher_writing; info o Detect Magic."""
    def _bonus(tag: str) -> BonusEffect:
        return BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=tag,
            source="heritage:seer_elf",
            label="+1 identify/decipher magic",
        )

    check_effects = []
    identify_skills = [Skill.ARCANA.value, Skill.OCCULTISM.value, Skill.RELIGION.value, Skill.NATURE.value]
    decipher_skills = [Skill.ARCANA.value, Skill.OCCULTISM.value, Skill.SOCIETY.value, Skill.RELIGION.value]

    check_effects.extend(
        [
            CheckEffect(
                applies_to="source",
                skills=[skill],
                tags_required=["identify_magic"],
                bonus_effects=[_bonus(skill)],
                prompt_notes=["Posiadasz czar Detect Magic (info)."],
            )
            for skill in identify_skills
        ]
    )
    check_effects.extend(
        [
            CheckEffect(
                applies_to="source",
                skills=[skill],
                tags_required=["decipher_writing"],
                bonus_effects=[_bonus(skill)],
                prompt_notes=["Posiadasz czar Detect Magic (info)."],
            )
            for skill in decipher_skills
        ]
    )
    return Status(
        id="heritage_seer_elf",
        label="Seer Elf",
        data={**_ELF_HERITAGE_DATA, "prompt_notes": ["Masz czar Detect Magic (jeszcze niezaimplementowany)."]},
        check_effects=check_effects,
    )


SEER_ELF_STATUS = SeerElfStatus()


def WhispererElfStatus() -> Status:
    """+2 circumstance bonus do akcji Seek."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.PERCEPTION.value,
        source="heritage:whisperer_elf",
        label="+2 Seek (Perception)",
    )
    return Status(
        id="heritage_whisperer_elf",
        label="Whisperer Elf",
        data=_ELF_HERITAGE_DATA,
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["seek"],
                bonus_effects=[bonus],
                prompt_notes=["+2 circumstance do akcji Seek."],
            )
        ],
    )


WHISPERER_ELF_STATUS = WhispererElfStatus()


def WoodlandElfStatus() -> Status:
    """Las: take cover bez obiektu; las nie spowalnia (informacja)."""
    return Status(
        id="heritage_woodland_elf",
        label="Woodland Elf",
        data={
            **_ELF_HERITAGE_DATA,
            "forest_take_cover": True,
            "forest_ignore_slow": True,
            "prompt_notes": [
                "W lesie możesz użyć Take Cover bez pobliskiego obiektu.",
                "Teren forest nie spowalnia twojego ruchu.",
            ],
        },
    )


WOODLAND_ELF_STATUS = WoodlandElfStatus()


__all__ = [
    "ArcticElfStatus",
    "ARCTIC_ELF_STATUS",
    "CavernElfStatus",
    "CAVERN_ELF_STATUS",
    "SeerElfStatus",
    "SEER_ELF_STATUS",
    "WhispererElfStatus",
    "WHISPERER_ELF_STATUS",
    "WoodlandElfStatus",
    "WOODLAND_ELF_STATUS",
]
