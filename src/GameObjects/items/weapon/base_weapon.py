from __future__ import annotations

from dataclasses import dataclass

from GameObjects.items.base_item import BaseItem


@dataclass
class BaseWeapon(BaseItem):
    category: str = "weapon"
    event_name: str = "unarmed"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = "bludgeoning"
    hands_required: int = 1
    ranged: bool = False

    def ui_description(self) -> str:
        hand_label = "2H" if int(self.hands_required or 1) >= 2 else "1H"
        ranged_label = "ranged" if self.ranged else "melee"
        traits = ", ".join(self.traits) if self.traits else "brak"
        return (
            f"{self.name}\n"
            f"Attack: {self.damage_prompt} ({self.damage_type})\n"
            f"Hands: {hand_label} | Type: {ranged_label}\n"
            f"Traits: {traits}"
        )


__all__ = [
    "BaseWeapon",
]
