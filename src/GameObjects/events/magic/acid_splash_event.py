from __future__ import annotations

import logging

from damage_types import DamageType
from statuses import make_persistent_damage, inspire_courage_damage_bonus
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note

from ..base import EventContext, EventResult
from ..registry import register_event
from .base_attack_magic_event import BaseMagicAttackEvent
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


@register_event
class AcidSplashEvent(BaseMagicAttackEvent):
    name = "acidsplash"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["acid", "cantrip", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]

    prompt = "Acid Splash – wystrzel bryzg kwasu w zasięgu 30 stóp."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        dmg = self._prompt_damage()
        dmg += int(inspire_courage_damage_bonus(ctx.actor) or 0)
        defeated = self._apply_damage(target, dmg, DamageType.ACID.value)

        persistent_value = None
        if critical:
            persistent_value = self._prompt_persistent(ctx.actor, DamageType.ACID.value)
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
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            "Acid Splash – podaj obrażenia kwasowe:",
            source="game",
            layout="damage",
            answer_placeholder="Obrażenia kwasowe",
        )
        return int(val or 0)

    def _prompt_persistent(self, actor, damage_type: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        note = burn_it_prompt_note(actor, damage_type, persistent=True)
        val = ui.prompt_roll(
            "Krytyk! Podaj wartość persistent acid:",
            source="game",
            layout="damage",
            answer_placeholder="Persistent acid",
            prompt_long=note,
        )
        bonus = burn_it_bonus(actor, damage_type, persistent=True)
        return int(val or 0) + int(bonus)

    def _apply_damage(self, target, amount: int, damage_type: str) -> bool:
        defeated = False
        apply = getattr(target, "apply_damage", None)
        if callable(apply):
            try:
                _, defeated = apply(max(0, int(amount)), damage_type)
            except Exception as exc:
                logger.error("Nie udało się zadać obrażeń acid splash: %s", exc)
        return defeated
