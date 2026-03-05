from __future__ import annotations

from statuses.base import Status
from statuses.classes.alchemist.alchemist_research_field import ALCHEMIST_RESEARCH_FIELD_STATUS
from statuses.classes.alchemist.feats.advanced_alchemy import ADVANCED_ALCHEMY_STATUS
from statuses.classes.alchemist.feats.quick_alchemy_allow import QUICK_ALCHEMY_ALLOW_STATUS

ALCHEMIST_PROMPT = (
    "Ability boost: Intelligence\n"
    "Hitpoints: +8 + Condition modifier\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Trained in Perception\n"
    "SAVING THROWS\n"
    "Expert in Fortitude\n"
    "Expert in Reflex\n"
    "Trained in Will\n"
    "SKILLS\n"
    "Trained in Crafting\n"
    "Trained in a number of additional skills equal to 3 plus your Intelligence modifier\n"
    "ATTACKS\n"
    "Trained in simple weapons\n"
    "Trained in alchemical bombs\n"
    "Trained in unarmed attacks\n"
    "DEFENSES\n"
    "Trained in light armor\n"
    "Trained in medium armor\n"
    "Trained in unarmored defense"
    "Alchemia:"
    "Na poczatku scenariusza wytwarzasz alchemiczne skladniki w ilosci poziom + modyfikator z intelektu"
    "Kazdy jeden skladnik moze posluzyc na wytworzenie 2 takichsamych alchemicznych przedmiotow, na poczatku scenariusza"
    "lub mozesz zostawic skladniki i uzyc ich juz podczas scenariusza wykorzystujac, lecz wtedy za jeden skladnik wytwarzasz 1 przedmiot"
    "musisz posiadac przepis w swojej ksedze alchemicznej zeby moc wytworzyc dany przedmiot"
    "czegoly w podreczniku"
)


def AlchemistStatus() -> Status:
    """Class: Alchemist (opis do UI prompta)."""
    return Status(
        id="alchemist",
        label="Alchemist",
        data={
            "ui_prompt": ALCHEMIST_PROMPT,
            "class_hp": 8,
            "set_actor_attrs": {"class_name": "alchemist"},
            "grants_statuses": [
                ALCHEMIST_RESEARCH_FIELD_STATUS,
                QUICK_ALCHEMY_ALLOW_STATUS,
                ADVANCED_ALCHEMY_STATUS,
            ],
        },
    )


ALCHEMIST_STATUS = AlchemistStatus()

__all__ = [
    "ALCHEMIST_PROMPT",
    "AlchemistStatus",
    "ALCHEMIST_STATUS",
]
