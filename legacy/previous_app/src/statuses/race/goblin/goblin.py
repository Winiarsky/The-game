from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

GOBLIN_DESCRIPTION = (
    "Punkty Zycia: 6\n"
    "Rozmiar: Maly\n"
    "Predkosc: 25 stop\n"
    "Boosty atrybutow: Zrecznosc, Charyzma, Dowolna\n"
    "Wada atrybutu: Madrosc\n"
    "Jezyki: Common, Goblin\n"
    "Dodatkowe jezyki: Draconic, Dwarven, Gnoll, Gnomish, Halfling, Orcish.\n"
    "Cechy: Goblin, Humanoid.\n"
    "Darkvision: w ciemnosci i slabym swietle widzisz jak w jasnym "
    "(ciemnosc w odcieniach szarosci)."
)


def GoblinStatus() -> Status:
    """Status rasy: goblin."""
    return Status(
        id="goblin",
        label="Goblin",
        data={
            "ui_description": GOBLIN_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 25,
            "size": "small",
            "ancestry_traits": ["goblin", "humanoid"],
            "ancestry_languages": ["common", "goblin"],
            "ancestry_bonus_languages": [
                "draconic",
                "dwarven",
                "gnoll",
                "gnomish",
                "halfling",
                "orcish",
            ],
            "ability_boosts": ["dexterity", "charisma", "free"],
            "ability_flaw": "wisdom",
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


GOBLIN_STATUS = GoblinStatus()

__all__ = ["GoblinStatus", "GOBLIN_STATUS", "GOBLIN_DESCRIPTION"]
