from __future__ import annotations

from dataclasses import dataclass

from .base_item import BaseItem


@dataclass
class GoodberryItem(BaseItem):
    item_id: str = "goodberry"
    name: str = "Goodberry"
    category: str = "potion"
    description: str = "Magiczna jagoda, która leczy po zjedzeniu."
    traits: tuple[str, ...] = ("consumable", "healing", "druid", "focus")
    cast_rank: int = 1

    def ui_description(self) -> str:
        return (
            f"{self.name}\n"
            "Aktywacja: Ekwipunek -> 5\n"
            "Efekt: automatyczne leczenie 1d6+4 (zużywa jagodę).\n"
            f"Ranga rzucenia: {max(1, int(self.cast_rank or 1))}"
        )


def is_goodberry_item(item) -> bool:
    return str(getattr(item, "item_id", "") or "").strip().lower() == "goodberry"


__all__ = [
    "GoodberryItem",
    "is_goodberry_item",
]
