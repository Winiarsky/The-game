from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DestructibleMixin:
    ac: int
    hp: int
    hardness: int
    destroyed: bool = False

    def apply_damage(self, roll: int, damage: int) -> tuple[bool, int, str]:
        """Zwraca (trafienie, dmg_po_hardness, komunikat)."""
        if self.destroyed:
            return False, 0, "Obiekt już zniszczony."
        if roll < self.ac:
            return False, 0, f"Atak ({roll}) nie trafia (AC {self.ac})."
        effective = max(0, damage - self.hardness)
        self.hp -= effective
        if self.hp <= 0:
            self.destroyed = True
            return True, effective, f"Obiekt rozsypuje się (zadano {effective})."
        return True, effective, f"Trafienie. Zadajesz {effective} (HP pozostalo: {self.hp})."
