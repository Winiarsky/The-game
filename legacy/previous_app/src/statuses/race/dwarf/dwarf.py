from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

DWARF_DESCRIPTION = (
    "Punkty Zycia: 10\n"
    "Rozmiar: Sredni\n"
    "Predkosc: 20 stop\n"
    "Boosty atrybutow: Kondycja, Madrosc, Dowolna\n"
    "Wada atrybutu: Charyzma\n"
    "Jezyki: Common, Dwarven\n"
    "Dodatkowe jezyki: liczba rowna modyfikatorowi Inteligencji (jesli dodatni): "
    "Gnomish, Goblin, Jotun, Orcish, Terran, Undercommon lub inne dostepne regionalnie.\n"
    "Cechy: Dwarf, Humanoid\n"
    "Darkvision: widzisz w ciemnosci i slabym swietle jak w jasnym swietle "
    "(ciemnosc w odcieniach szarosci).\n"
    "Clan Dagger: otrzymujesz darmowy clan dagger."
)


def DwarfStatus() -> Status:
    """Status rasy: dwarf."""
    return Status(
        id="dwarf",
        label="Dwarf",
        data={
            "ui_description": DWARF_DESCRIPTION,
            "ancestry_hp": 10,
            "base_speed_feet": 20,
            "size": "medium",
            "ancestry_traits": ["dwarf", "humanoid"],
            "ancestry_languages": ["common", "dwarven"],
            "ancestry_bonus_languages": [
                "gnomish",
                "goblin",
                "jotun",
                "orcish",
                "terran",
                "undercommon",
            ],
            "ability_boosts": ["constitution", "wisdom", "free"],
            "ability_flaw": "charisma",
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


DWARF_STATUS = DwarfStatus()

__all__ = ["DwarfStatus", "DWARF_STATUS", "DWARF_DESCRIPTION"]
