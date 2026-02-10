from __future__ import annotations

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_DWARF_HERITAGE_DATA = {"ancestry": "dwarf", "heritage": True, "traits": ["dwarf", "heritage"]}


def _heritage_data_with_resistance(resistance: dict[str, int] | None = None) -> dict[str, object]:
    """Kopia bazowych danych heritage z opcjonalną redukcją obrażeń."""
    data = dict(_DWARF_HERITAGE_DATA)
    if resistance:
        data["damage_resistance"] = resistance
    return data


def AncientBloodedDwarfStatus() -> Status:
    """Reakcja przeciw efektom magicznym – informacja do promptu."""
    return Status(
        id="heritage_ancient_blooded_dwarf",
        label="Ancient-Blooded Dwarf",
        data=_DWARF_HERITAGE_DATA,
        check_effects=[
            CheckEffect(
                applies_to="target",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["magic", "saving_throw"],
                prompt_notes=[
                    "Możesz wydać reakcję, by dodać +1 do wyniku tego rzutu (nieautomatyczne)."
                ],
            )
        ],
    )


ANCIENT_BLOODED_DWARF_STATUS = AncientBloodedDwarfStatus()


def DeathWardenDwarfStatus() -> Status:
    """Sukces przeciw nekromancji podbijany do krytyka."""
    return Status(
        id="heritage_death_warden_dwarf",
        label="Death Warden Dwarf",
        data=_DWARF_HERITAGE_DATA,
        check_effects=[
            CheckEffect(
                applies_to="target",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["necromancy", "saving_throw"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Sukces przeciw efektowi nekromancji staje się krytycznym sukcesem."],
            )
        ],
    )


DEATH_WARDEN_DWARF_STATUS = DeathWardenDwarfStatus()


def ForgeDwarfStatus() -> Status:
    """Redukcja obrażeń ognia o 1 (min 0)."""
    return Status(
        id="heritage_forge_dwarf",
        label="Forge Dwarf",
        data=_heritage_data_with_resistance({DamageType.FIRE.value: 1}),
    )


FORGE_DWARF_STATUS = ForgeDwarfStatus()


def RockDwarfStatus() -> Status:
    """Premia okoliczności +2 do Fort/Ref vs shove/trip/prone (info w promptcie)."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.FORTITUDE.value,
            source="heritage:rock_dwarf",
            label="+2 vs shove/trip/prone (Fortitude)",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag=Skill.REFLEX.value,
            source="heritage:rock_dwarf",
            label="+2 vs shove/trip/prone (Reflex)",
        ),
    ]
    return Status(
        id="heritage_rock_dwarf",
        label="Rock Dwarf",
        data=_DWARF_HERITAGE_DATA,
        check_effects=[
            CheckEffect(applies_to="target", skills=[Skill.FORTITUDE.value, Skill.REFLEX.value], tags_required=["shove"], bonus_effects=bonus_effects),
            CheckEffect(applies_to="target", skills=[Skill.FORTITUDE.value, Skill.REFLEX.value], tags_required=["trip"], bonus_effects=bonus_effects),
            CheckEffect(applies_to="target", skills=[Skill.FORTITUDE.value, Skill.REFLEX.value], tags_required=["prone"], bonus_effects=bonus_effects),
        ],
    )


ROCK_DWARF_STATUS = RockDwarfStatus()


def StrongBloodedDwarfStatus() -> Status:
    """Ochrona przed trucizną: -1 dmg, sukces podbijany do krytyka."""
    return Status(
        id="heritage_strong_blooded_dwarf",
        label="Strong-Blooded Dwarf",
        data=_heritage_data_with_resistance({DamageType.POISON.value: 1}),
        check_effects=[
            CheckEffect(
                applies_to="target",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["saving_throw", "poison"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Sukces przeciw efektowi trucizny jest traktowany jak krytyczny sukces. Pamiętaj: obrażenia poison -1 (min 0)."],
            )
        ],
    )


STRONG_BLOODED_DWARF_STATUS = StrongBloodedDwarfStatus()


__all__ = [
    "AncientBloodedDwarfStatus",
    "ANCIENT_BLOODED_DWARF_STATUS",
    "DeathWardenDwarfStatus",
    "DEATH_WARDEN_DWARF_STATUS",
    "ForgeDwarfStatus",
    "FORGE_DWARF_STATUS",
    "RockDwarfStatus",
    "ROCK_DWARF_STATUS",
    "StrongBloodedDwarfStatus",
    "STRONG_BLOODED_DWARF_STATUS",
]
