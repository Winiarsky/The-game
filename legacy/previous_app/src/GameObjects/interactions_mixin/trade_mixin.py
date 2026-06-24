from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradeItem:
    item_id: str
    name: str
    price: int  # cena bazowa w cp
    kind: str = "auto"  # auto|weapon|armor|shield|equipment|alchemical|service
    description: str = ""
    stock: int = -1  # -1 = bez limitu
    min_tier: str = "novice"  # novice|adept|master


@dataclass
class TradeMixin:
    inventory: list[TradeItem] = None
    base_price_modifier: float = 1.0

    def price_multiplier(self, attitude: int) -> float:
        """Prosty mnożnik ceny zależny od nastawienia."""
        table = {
            -2: 1.6,
            -1: 1.3,
            0: 1.0,
            1: 0.9,
            2: 0.85,
        }
        return table.get(attitude, 1.0) * self.base_price_modifier
