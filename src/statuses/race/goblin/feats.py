from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_GOBLIN_FEAT_DATA = {"ancestry": "goblin", "feat": True, "traits": ["goblin", "feat"]}


def BurnItStatus() -> Status:
    """Info: ogniste czary i alchemia zadają +1 obrażenia."""
    return Status(
        id="feat_burn_it",
        label="Burn It!",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": [
                "Twoje czary i alchemiczne przedmioty zadające obrażenia od ognia zadają +1 obrażeń."
            ],
        },
    )


BURN_IT_STATUS = BurnItStatus()


def CityScavengerStatus() -> Status:
    """+1 circumstance do testów Society/Survival (miejskie znaleziska)."""
    bonus_society = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=Skill.SOCIETY.value,
        source="feat:city_scavenger",
        label="+1 Society (City Scavenger)",
    )
    bonus_survival = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=Skill.SURVIVAL.value,
        source="feat:city_scavenger",
        label="+1 Survival (City Scavenger)",
    )
    return Status(
        id="feat_city_scavenger",
        label="City Scavenger",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": [
                "Premia okoliczności +1 do testów Society lub Survival podczas miejskich przeszukiwań/zadań."
            ],
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.SOCIETY.value],
                bonus_effects=[bonus_society],
                prompt_notes=["City Scavenger: +1 circumstance do Society na eventach typu scavenging."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.SURVIVAL.value],
                bonus_effects=[bonus_survival],
                prompt_notes=["City Scavenger: +1 circumstance do Survival na eventach typu scavenging."],
            ),
        ],
    )


CITY_SCAVENGER_STATUS = CityScavengerStatus()


def GoblinLoreStatus() -> Status:
    """Info: trained w Nature i Stealth."""
    return Status(
        id="feat_goblin_lore",
        label="Goblin Lore",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": ["Masz poziom trained w Nature i Stealth."],
        },
    )


GOBLIN_LORE_STATUS = GoblinLoreStatus()


def GoblinScuttleStatus() -> Status:
    """Info: 1/turn darmowy Step przy sojuszniku obok."""
    return Status(
        id="feat_goblin_scuttle",
        label="Goblin Scuttle",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": [
                "Raz na turę w walce możesz wykonać darmową akcję Step, jeśli stoisz obok sojusznika."
            ],
        },
    )


GOBLIN_SCUTTLE_STATUS = GoblinScuttleStatus()


def GoblinWeaponFamiliarityStatus() -> Status:
    """Info: biegłość w dogslicer i horsechopper."""
    return Status(
        id="feat_goblin_weapon_familiarity",
        label="Goblin Weapon Familiarity",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": [
                "Jesteś trained w broniach dogslicer i horsechopper; pamiętaj o kartach broni."
            ],
        },
    )


GOBLIN_WEAPON_FAMILIARITY_STATUS = GoblinWeaponFamiliarityStatus()


def JunkTinkerStatus() -> Status:
    """+2 circumstance do Crafting przy improwizacji złomu."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.CRAFTING.value,
        source="feat:junk_tinker",
        label="+2 Crafting (Junk Tinker)",
    )
    return Status(
        id="feat_junk_tinker",
        label="Junk Tinker",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": ["+2 circumstance do testów Crafting przy tworzeniu/improwizacji ze złomu."],
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.CRAFTING.value],
                bonus_effects=[bonus],
                prompt_notes=["Junk Tinker: +2 circumstance do Crafting na eventach związanych z tworzeniem/tinkering."],
            )
        ],
    )


JUNK_TINKER_STATUS = JunkTinkerStatus()


def VerySneakyStatus() -> Status:
    """Info: Stealth Move o 1 pole dalej."""
    return Status(
        id="feat_very_sneaky",
        label="Very Sneaky",
        data={
            **_GOBLIN_FEAT_DATA,
            "prompt_notes": ["Poruszając się w trybie Stealth możesz zrobić o jeden krok dalej."],
        },
    )


VERY_SNEAKY_STATUS = VerySneakyStatus()


__all__ = [
    "BurnItStatus",
    "BURN_IT_STATUS",
    "CityScavengerStatus",
    "CITY_SCAVENGER_STATUS",
    "GoblinLoreStatus",
    "GOBLIN_LORE_STATUS",
    "GoblinScuttleStatus",
    "GOBLIN_SCUTTLE_STATUS",
    "GoblinWeaponFamiliarityStatus",
    "GOBLIN_WEAPON_FAMILIARITY_STATUS",
    "JunkTinkerStatus",
    "JUNK_TINKER_STATUS",
    "VerySneakyStatus",
    "VERY_SNEAKY_STATUS",
]
