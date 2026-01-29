from __future__ import annotations

from dataclasses import dataclass

from interactions_mixin.skill_checks import resolve_skill_check


@dataclass
class HiddenMixin:
    hidden: bool = False
    revealed: bool = False
    reveal_dc: int = 18
    seekable: bool = True

    def try_reveal(self, roll: int) -> tuple[str, str]:
        if not self.hidden:
            return "info", "Tu nic nie jest ukryte."
        if self.revealed:
            return "info", "Sekret już odkryty."
        outcome = resolve_skill_check(self.reveal_dc, roll)
        if outcome in ("success", "critical_success"):
            self.revealed = True
            return outcome, "Zauważasz ukryty element."
        return outcome, "Nie dostrzegasz niczego niezwykłego."
