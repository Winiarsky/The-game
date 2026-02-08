from __future__ import annotations

import logging

from bonuses import BonusEffect, BonusType
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class RaiseShieldEvent(GameEvent):
    """Podniesienie tarczy – +2 circumstance do AC do początku kolejnej tury bohatera."""

    name = "shield"
    default_tags = ["raise_shield", "defense"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            msg = "Podniesienie tarczy dostępne tylko w walce."
            logger.info(msg)
            return EventResult(success=False, consumed_action=False, message=msg)

        hero = ctx.actor
        if hero is None:
            return EventResult(success=False, consumed_action=False, message="Brak wybranego bohatera.")
        if getattr(hero, "has_status", lambda _s: False)("prone"):
            return EventResult.cancelled(message="Nie możesz podnieść tarczy będąc prone.")

        # wyczyść wcześniejsze podniesienia tarczy
        remover = getattr(hero, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("raise_shield:")
            except Exception:
                pass

        round_idx = getattr(getattr(ctx.game, "state", None), "round_index", None)
        source_tag = f"raise_shield:round{round_idx}" if round_idx is not None else "raise_shield"

        adder = getattr(hero, "add_bonus", None)
        if not callable(adder):
            return EventResult(success=False, consumed_action=False, message="Bohater nie obsługuje bonusów.")

        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=2,
                tag="ac",
                source=source_tag,
                label="tarcza w górze",
                duration_turns=1,
            )
        )

        logger.info("Bohater podnosi tarczę: +2 AC circumstance do początku kolejnej tury.")
        try:
            ctx.game.ui_log("Podnosisz tarczę: +2 AC (circumstance) do początku następnej tury.")
        except Exception:
            pass

        return EventResult(success=True, consumed_action=True, message="Tarcza podniesiona (+2 AC).")
