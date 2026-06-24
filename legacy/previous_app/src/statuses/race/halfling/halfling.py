from __future__ import annotations

from statuses.base import Status
from .keen_eyes import KEEN_EYES_STATUS

HALFLING_DESCRIPTION = (
    "Punkty Zycia: 6\n"
    "Rozmiar: Maly\n"
    "Predkosc: 25 stop\n"
    "Boosty atrybutow: Zrecznosc, Madrosc, Dowolna\n"
    "Wada atrybutu: Sila\n"
    "Jezyki: Common, Halfling\n"
    "Dodatkowe jezyki: Dwarven, Elven, Gnomish, Goblin.\n"
    "Cechy: Halfling, Humanoid.\n"
    "Keen Eyes: latwiej wykrywasz cele ukryte i namierzasz concealed/hidden."
)


def HalflingStatus() -> Status:
    """Status rasy: halfling."""
    return Status(
        id="halfling",
        label="Halfling",
        data={
            "ui_description": HALFLING_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 25,
            "size": "small",
            "ancestry_traits": ["halfling", "humanoid"],
            "ancestry_languages": ["common", "halfling"],
            "ancestry_bonus_languages": [
                "dwarven",
                "elven",
                "gnomish",
                "goblin",
            ],
            "ability_boosts": ["dexterity", "wisdom", "free"],
            "ability_flaw": "strength",
            "grants_statuses": [KEEN_EYES_STATUS],
        },
    )


HALFLING_STATUS = HalflingStatus()

__all__ = ["HalflingStatus", "HALFLING_STATUS", "HALFLING_DESCRIPTION"]
