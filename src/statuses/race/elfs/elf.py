from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

ELF_DESCRIPTION = (
    "Punkty Zycia: 6\n"
    "Rozmiar: Sredni\n"
    "Predkosc: 30 stop\n"
    "Boosty atrybutow: Zrecznosc, Inteligencja, Dowolna\n"
    "Wada atrybutu: Kondycja\n"
    "Jezyki: Common, Elven\n"
    "Dodatkowe jezyki rowne modyfikatorowi Inteligencji: "
    "Celestial, Draconic, Gnoll, Gnomish, Goblin, Orcish, Sylvan (lub regionalne).\n"
    "Cechy: Elf, Humanoid\n"
    "Low-Light Vision: w slabym swietle widzisz jak w jasnym i ignorujesz concealed z dim light."
)


def ElfStatus() -> Status:
    """Status rasy: elf."""
    return Status(
        id="elf",
        label="Elf",
        data={
            "ui_description": ELF_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 30,
            "size": "medium",
            "ancestry_traits": ["elf", "humanoid"],
            "ancestry_languages": ["common", "elven"],
            "ancestry_bonus_languages": [
                "celestial",
                "draconic",
                "gnoll",
                "gnomish",
                "goblin",
                "orcish",
                "sylvan",
            ],
            "ability_boosts": ["dexterity", "intelligence", "free"],
            "ability_flaw": "constitution",
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


ELF_STATUS = ElfStatus()

__all__ = ["ElfStatus", "ELF_STATUS", "ELF_DESCRIPTION"]
