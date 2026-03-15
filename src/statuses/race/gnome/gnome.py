from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

GNOME_DESCRIPTION = (
    "Punkty Zycia: 8\n"
    "Rozmiar: Maly\n"
    "Predkosc: 25 stop\n"
    "Boosty atrybutow: Kondycja, Charyzma, Dowolna\n"
    "Wada atrybutu: Sila\n"
    "Jezyki: Common, Gnomish, Sylvan\n"
    "Dodatkowe jezyki: Draconic, Dwarven, Elven, Goblin, Jotun, Orcish.\n"
    "Cechy: Gnome, Humanoid.\n"
    "Low-Light Vision: w slabym swietle widzisz jak w jasnym i ignorujesz concealed z dim light."
)


def GnomeStatus() -> Status:
    """Status rasy: gnome."""
    return Status(
        id="gnome",
        label="Gnome",
        data={
            "ui_description": GNOME_DESCRIPTION,
            "ancestry_hp": 8,
            "base_speed_feet": 25,
            "size": "small",
            "ancestry_traits": ["gnome", "humanoid"],
            "ancestry_languages": ["common", "gnomish", "sylvan"],
            "ancestry_bonus_languages": [
                "draconic",
                "dwarven",
                "elven",
                "goblin",
                "jotun",
                "orcish",
            ],
            "ability_boosts": ["constitution", "charisma", "free"],
            "ability_flaw": "strength",
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


GNOME_STATUS = GnomeStatus()

__all__ = ["GnomeStatus", "GNOME_STATUS", "GNOME_DESCRIPTION"]
