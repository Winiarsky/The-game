from __future__ import annotations

from dataclasses import dataclass

from .base_shield import BaseShield


@dataclass
class StandardShield(BaseShield):
    item_id: str = "standard_shield"
    name: str = "Tarcza stalowa"
    description: str = "Standardowa tarcza stalowa."
    price_cp: int = 200
    bulk: str | int = 1
    traits: tuple[str, ...] = ("shield_block",)
    ac_bonus: int = 2
    take_cover_ac_bonus: int = 2
    hardness: int = 5
    max_hp: int = 20
    broken_threshold: int = 10
