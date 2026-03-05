from __future__ import annotations

from dataclasses import dataclass

from GameObjects.items.base_item import BaseItem


@dataclass
class BaseArmor(BaseItem):
    category: str = "armor"
    armor_category: str = "light"
    ac_bonus: int = 0
    dex_cap: int = 5
    strength_requirement: int = 10
    check_penalty: int = 0
    speed_penalty_feet: int = 0
    bulwark_reflex_floor: int | None = None

    def ui_description(self) -> str:
        traits = ", ".join(self.traits) if self.traits else "brak"
        speed_penalty = ""
        if int(self.speed_penalty_feet or 0) > 0:
            speed_penalty = f"\nSpeed Penalty: -{int(self.speed_penalty_feet)} ft"
        return (
            f"{self.name}\n"
            f"Armor: {self.armor_category}\n"
            f"AC Bonus: +{int(self.ac_bonus)} | DEX Cap: +{int(self.dex_cap)} | STR: {int(self.strength_requirement)}\n"
            f"Check Penalty: -{int(self.check_penalty)}"
            f"{speed_penalty}\n"
            f"Traits: {traits}"
        )


__all__ = [
    "BaseArmor",
]
