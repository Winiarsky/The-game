from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from interactions_mixin.skill_checks import resolve_skill_check


@dataclass
class PickpocketMixin:
    pickpocket_dc: int = 16
    pickpocket_loot: list[str] = None
    pickpocket_fail_attitude_delta: int = -1

    def resolve_pickpocket(self, roll: int) -> tuple[str, Optional[str]]:
        """Zwraca (outcome, zdobyty_przedmiot_lub_None)."""
        outcome = resolve_skill_check(self.pickpocket_dc, roll)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["sakiewka"])[0]
            return outcome, loot
        return outcome, None
