from __future__ import annotations

import logging
from typing import Iterable, Optional

from bonuses import BonusEffect, compute_total_modifier
from combat import effective_ac

from ..base import GameEvent

logger = logging.getLogger(__name__)


class AttackEventBase(GameEvent):
    """Wspólne helpery dla wszystkich eventów ataku (wręcz i dystans)."""

    def _ac_with_bonuses(
        self,
        target,
        *,
        attacker=None,
        extra_bonuses: Optional[Iterable[BonusEffect]] = None,
    ) -> tuple[int, int, int]:
        """Zwraca (target_ac, base_ac, modifier) z uwzględnieniem tymczasowych bonusów (np. osłony).

        base_ac – pochodzi z atrybutu celu lub effective_ac (które uwzględnia np. flat-footed).
        modifier – suma najlepszych bonusów/kar z listy bonusów celu + extra_bonuses pod tagiem "ac".
        """

        base_ac = getattr(target, "ac", effective_ac(target))
        bonuses = list(getattr(target, "bonuses", [])) if hasattr(target, "bonuses") else []
        if extra_bonuses:
            bonuses.extend(list(extra_bonuses))

        modifier = compute_total_modifier(bonuses, "ac", getattr(attacker, "object_id", None)) if bonuses else 0
        target_ac = base_ac + modifier
        return target_ac, base_ac, modifier

    def _attacker_modifier(self, attacker, action_tag: str, target=None) -> int:
        """Oblicz modyfikator atakującego dla podanego tagu (np. prone = -2)."""

        compute = getattr(attacker, "compute_modifier", None)
        if callable(compute):
            try:
                return int(compute(action_tag, target=target))
            except Exception:
                logger.debug("Nie udało się policzyć compute_modifier dla %s", action_tag, exc_info=True)
        return 0

    def _format_bonus_info(self, attacker, action_tag: str, target=None) -> str:
        """Opis modyfikatorów do wyświetlenia w promptcie (z BonusMixin.format_prompt)."""

        formatter = getattr(attacker, "format_prompt", None)
        if not callable(formatter):
            return ""
        try:
            formatted = formatter(action_tag, target=target)
            return f"\nModyfikatory ({action_tag}):\n{formatted}\n" if formatted else ""
        except Exception:
            logger.debug("format_prompt nie powiódł się dla %s", action_tag, exc_info=True)
            return ""

    def _maybe_prompt_vengeful_hatred(self, attacker, target) -> None:
        """Pokaż informację o +1 do obrażeń vs wybrany typ przeciwnika (bez naliczania)."""
        getter = getattr(attacker, "get_status_data", None)
        if callable(getter):
            enemy_type = getter("vengeful_hatred", "enemy_type", None)
            bonus = getter("vengeful_hatred", "damage_bonus", 1)
        else:
            enemy_type = None
            bonus = 1
            for status in getattr(attacker, "statuses", []) or []:
                if getattr(status, "id", None) != "vengeful_hatred":
                    continue
                data = getattr(status, "data", {}) or {}
                enemy_type = data.get("enemy_type")
                bonus = data.get("damage_bonus", 1)
                break
        if not enemy_type:
            return
        target_type = getattr(target, "enemy_type", None)
        if target_type is None:
            return
        enemy_type_norm = getattr(enemy_type, "value", enemy_type)
        target_type_norm = getattr(target_type, "value", target_type)
        if enemy_type_norm != target_type_norm:
            return
        try:
            from ui_client import get_ui_client

            get_ui_client().prompt_info(
                "Vengeful Hatred",
                prompt_long=(
                    f"Bonus do obrazen +{int(bonus)} vs {enemy_type_norm}. "
                    "Dodaj recznie do wyniku."
                ),
                source="vengeful_hatred",
            )
        except Exception:
            return
