from __future__ import annotations

from bonuses import BonusEffect, BonusType
from statuses.base import Status
from statuses.check_effects import CheckEffect
from skills import Skill

_GNOME_HERITAGE_DATA = {"ancestry": "gnome", "heritage": True, "traits": ["gnome", "heritage"]}


def ChameleonGnomeStatus() -> Status:
    """+2 circumstance do testów z tagiem try_stealth."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.STEALTH.value,
        source="heritage:chameleon_gnome",
        label="Chameleon +2 Stealth",
    )
    return Status(
        id="heritage_chameleon_gnome",
        label="Chameleon Gnome",
        data=_GNOME_HERITAGE_DATA,
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.STEALTH.value],
                tags_required=["try_stealth"],
                bonus_effects=[bonus],
                prompt_notes=["+2 circumstance do testów Stealth z tagiem try_stealth."],
            )
        ],
    )


CHAMELEON_GNOME_STATUS = ChameleonGnomeStatus()


def FeyTouchedGnomeStatus() -> Status:
    """Informacja o wyborze cantripu z listy primal."""
    return Status(
        id="heritage_fey_touched_gnome",
        label="Fey Touched Gnome",
        data={
            **_GNOME_HERITAGE_DATA,
            "prompt_notes": [
                "Na początku scenariusza wybierz dowolny cantrip z listy primal; możesz go używać przez scenariusz.",
            ],
        },
    )


FEY_TOUCHED_GNOME_STATUS = FeyTouchedGnomeStatus()


def SensateGnomeStatus() -> Status:
    """+2 circumstance bonus do akcji Seek."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.PERCEPTION.value,
        source="heritage:sensate_gnome",
        label="Sensate +2 Seek",
    )
    return Status(
        id="heritage_sensate_gnome",
        label="Sensate Gnome",
        data=_GNOME_HERITAGE_DATA,
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


SENSATE_GNOME_STATUS = SensateGnomeStatus()


def UmbralGnomeStatus() -> Status:
    """Ignoruje efekty/eventy z tagiem dark (jak Cavern Elf)."""
    return Status(
        id="heritage_umbral_gnome",
        label="Umbral Gnome",
        data={
            **_GNOME_HERITAGE_DATA,
            "ignore_effect_tags": ["dark"],
            "prompt_notes": ["Ignorujesz efekty i eventy z tagiem dark (np. darkness)."],
        },
    )


UMBRAL_GNOME_STATUS = UmbralGnomeStatus()


def WellspringGnomeStatus() -> Status:
    """Informacja o wyborze cantripu arcane/divine/occult."""
    return Status(
        id="heritage_wellspring_gnome",
        label="Wellspring Gnome",
        data={
            **_GNOME_HERITAGE_DATA,
            "prompt_notes": [
                "Na początku scenariusza wybierz cantrip z listy arcane, divine albo occult; możesz go używać przez scenariusz.",
            ],
        },
    )


WELLSPRING_GNOME_STATUS = WellspringGnomeStatus()


__all__ = [
    "ChameleonGnomeStatus",
    "CHAMELEON_GNOME_STATUS",
    "FeyTouchedGnomeStatus",
    "FEY_TOUCHED_GNOME_STATUS",
    "SensateGnomeStatus",
    "SENSATE_GNOME_STATUS",
    "UmbralGnomeStatus",
    "UMBRAL_GNOME_STATUS",
    "WellspringGnomeStatus",
    "WELLSPRING_GNOME_STATUS",
]
