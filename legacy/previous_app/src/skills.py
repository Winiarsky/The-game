from __future__ import annotations

from enum import Enum


class Skill(str, Enum):
    """Central list of supported skill identifiers."""

    FORTITUDE = "fortitude"
    REFLEX = "reflex"
    WILL = "will"
    THIEVERY = "thievery"
    DIPLOMACY = "diplomacy"
    STEALTH = "stealth"
    PERCEPTION = "perception"
    ATHLETICS = "athletics"
    ACROBATICS = "acrobatics"
    ARCANA = "arcana"
    NATURE = "nature"
    RELIGION = "religion"
    CRAFTING = "crafting"
    DECEPTION = "deception"
    INTIMIDATION = "intimidation"
    LORE = "lore"
    MEDICINE = "medicine"
    PERFORMANCE = "performance"
    OCCULTISM = "occultism"
    SOCIETY = "society"
    SURVIVAL = "survival"