from __future__ import annotations

import logging

from board import consts
from actions.specials.magic_missile import magic_missile_ability

from ..base import EventContext, EventResult
from ..registry import register_event
from .magic_event import MagicEvent
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


@register_event
class MagicMissileEvent(MagicEvent):
    name = "magic_missile"
    default_tags = ["cast", "attack_ranged", "magic"]
    consumes_action = True
    actions_cost = 1
    spell_tradition = SpellTradition.ARCANA
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.OCCULT)
    prompt = "Magic Missile – wystrzel pociski energii w cel w zasięgu."

    def execute(self, ctx: EventContext) -> EventResult:
        hero = ctx.actor or self._choose_hero(ctx)
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        success = bool(magic_missile_ability(hero, ctx))
        return EventResult(
            success=success,
            consumed_action=self.consumes_action,
            message="Magic Missile zakończone." if success else "Magic Missile nie powiodło się.",
        )

    def _choose_hero(self, ctx: EventContext):
        heroes_positions = [h.position for h in getattr(ctx.game, "heroes", []) if getattr(h, "position", None) is not None]
        if not heroes_positions:
            logger.info("Brak bohaterów na planszy.")
            return None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        try:
            pos = ctx.game.conn.scan_board(heroes_positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        return ctx.game.board.occupant_at(pos)
