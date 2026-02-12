from __future__ import annotations

import logging

from damage_types import DamageType
from statuses import make_persistent_damage

from ..base import EventContext, EventResult
from ..registry import register_event
from .base_attack_magic_event import BaseMagicAttackEvent
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


@register_event
class AcidSplashEvent(BaseMagicAttackEvent):
    name = "acidcplash"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["acid", "cantrip", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]

    prompt = "Acid Splash – wystrzel bryzg kwasu w zasięgu 30 stóp."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        dmg = self._prompt_damage()
        defeated = self._apply_damage(target, dmg, DamageType.ACID.value)

        persistent_value = None
        if critical:
            persistent_value = self._prompt_persistent()
            if persistent_value and persistent_value > 0:
                try:
                    target.add_status(make_persistent_damage(persistent_value, DamageType.ACID.value, source=self.name))
                except Exception as exc:
                    logger.debug("Nie udało się dodać persistent acid: %s", exc)

        message = f"Acid Splash trafia za {dmg} acid."
        if critical:
            message = f"Acid Splash – krytyk! {dmg} acid."
            if persistent_value:
                message += f" Persistent acid {persistent_value}."
        if defeated:
            message += " Cel pokonany."

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=message,
            data={
                "critical": critical,
                "damage": dmg,
                "damage_type": DamageType.ACID.value,
                "persistent_damage": persistent_value,
            },
        )

    def _prompt_damage(self) -> int:
        from GameObjects.interactions_mixin import prompt_for_roll

        try:
            return int(prompt_for_roll("Acid Splash – podaj obrażenia kwasowe: "))
        except Exception:
            return 0

    def _prompt_persistent(self) -> int:
        from GameObjects.interactions_mixin import prompt_for_roll

        try:
            return int(prompt_for_roll("Krytyk! Podaj wartość persistent acid: "))
        except Exception:
            return 0

    def _apply_damage(self, target, amount: int, damage_type: str) -> bool:
        defeated = False
        apply = getattr(target, "apply_damage", None)
        if callable(apply):
            try:
                _, defeated = apply(max(0, int(amount)), damage_type)
            except Exception as exc:
                logger.error("Nie udało się zadać obrażeń acid splash: %s", exc)
        return defeated
