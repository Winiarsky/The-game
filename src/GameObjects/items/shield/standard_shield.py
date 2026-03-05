from __future__ import annotations

from dataclasses import dataclass

from .base_shield import BaseShield


@dataclass
class StandardShield(BaseShield):
    item_id: str = "standard_shield"
    name: str = "Steel Shield"
    description: str = "Standardowa stalowa tarcza."
    traits: tuple[str, ...] = ("shield_block",)
    ac_bonus: int = 2
    hardness: int = 5
    max_hp: int = 20
    broken_threshold: int = 10
