from __future__ import annotations

from statuses.base import Status

HUMAN_DESCRIPTION = (
    "Punkty Zycia: 8\n"
    "Rozmiar: Sredni\n"
    "Predkosc: 25 stop\n"
    "Boosty atrybutow: Dwa dowolne boosty\n"
    "Jezyki: Common\n"
    "Dodatkowe jezyki: 1 + modyfikator Inteligencji (jesli dodatni), "
    "z listy jezykow powszechnych i regionalnych.\n"
    "Cechy: Human, Humanoid."
)


def HumanStatus() -> Status:
    """Status rasy: human."""
    return Status(
        id="human",
        label="Human",
        data={
            "ui_description": HUMAN_DESCRIPTION,
            "ancestry_hp": 8,
            "base_speed_feet": 25,
            "size": "medium",
            "ancestry_traits": ["human", "humanoid"],
            "ancestry_languages": ["common"],
            "ancestry_bonus_languages_base": 1,
            "ancestry_bonus_languages_source": "int_modifier_positive",
            "ability_boosts": ["free", "free"],
        },
    )


HUMAN_STATUS = HumanStatus()

__all__ = ["HumanStatus", "HUMAN_STATUS", "HUMAN_DESCRIPTION"]
