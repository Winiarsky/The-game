from __future__ import annotations

from dataclasses import dataclass

from GameObjects.items.base_item import BaseItem


@dataclass
class BaseWeapon(BaseItem):
    category: str = "weapon"
    event_name: str = "unarmed"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = "bludgeoning"
    proficiency_category: str = "simple"
    weapon_group: str = "brawling"
    hands_required: int = 1
    ranged: bool = False
    range_increment_ft: int = 0
    reload: int = 0

    def ui_description(self) -> str:
        hand_label = "2H" if int(self.hands_required or 1) >= 2 else "1H"
        ranged_label = "dystansowa" if self.ranged else "wręcz"
        traits = ", ".join(self.traits) if self.traits else "brak"
        prof_label = str(getattr(self, "proficiency_category", "simple") or "simple")
        group_label = str(getattr(self, "weapon_group", "brawling") or "brawling")
        lines: list[str] = [
            f"{self.name}",
            f"- Atak: {self.damage_prompt} ({self.damage_type})",
            f"- Chwyt: {hand_label}",
            f"- Typ: {ranged_label}",
            f"- Biegłość: {prof_label}",
            f"- Grupa: {group_label}",
            f"- Cena: {self._price_label(int(getattr(self, 'price_cp', 0) or 0))}",
            f"- Bulk: {self._bulk_label(getattr(self, 'bulk', '-'))}",
        ]
        if self.ranged and int(self.range_increment_ft or 0) > 0:
            lines.append(f"- Przyrost zasięgu: {int(self.range_increment_ft)} ft")
            lines.append(f"- Przeładowanie: {int(self.reload)}")
        lines.append(f"- Cechy: {traits}")
        return "\n".join(lines)


__all__ = [
    "BaseWeapon",
]
