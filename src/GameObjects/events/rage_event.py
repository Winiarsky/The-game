from __future__ import annotations

import logging
from dataclasses import replace

from bonuses import BonusEffect, BonusType
from statuses.darkvision import DARKVISION_STATUS
from statuses.rage import RageStatus, RAGE_DURATION_TURNS, RAGE_DEFAULT_AC_PENALTY
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class RageEvent(GameEvent):
    name = "rage"
    default_tags = ["rage", "stance"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Rage dostępne tylko w walce.")

        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Rage.")

        has_status = getattr(actor, "has_status", None)
        if callable(has_status) and has_status("rage"):
            return EventResult.cancelled(message="Rage już aktywne.")

        remover_status = getattr(actor, "remove_status", None)
        if callable(remover_status):
            try:
                remover_status("rage")
            except Exception:
                pass

        remover_bonus = getattr(actor, "remove_bonuses_by_source", None)
        if callable(remover_bonus):
            try:
                remover_bonus("rage")
            except Exception:
                pass

        adder_status = getattr(actor, "add_status", None)
        if not callable(adder_status):
            return EventResult.cancelled(message="Bohater nie obsługuje statusów.")

        duration = RAGE_DURATION_TURNS
        try:
            adder_status(RageStatus(duration=duration))
        except Exception as exc:
            logger.error("Nie udało się dodać statusu Rage: %s", exc)
            return EventResult.cancelled(message="Nie udało się aktywować Rage.")

        has_status = getattr(actor, "has_status", None)
        has_darkvision = False
        if callable(has_status):
            try:
                has_darkvision = has_status("darkvision")
            except Exception:
                has_darkvision = False
        else:
            for item in getattr(actor, "statuses", []) or []:
                if getattr(item, "id", None) == "darkvision" or item == "darkvision":
                    has_darkvision = True
                    break
        if (callable(has_status) and has_status("cute_vision")) or (
            not callable(has_status)
            and any(getattr(s, "id", None) == "cute_vision" or s == "cute_vision" for s in getattr(actor, "statuses", []) or [])
        ):
            if not has_darkvision:
                data = dict(getattr(DARKVISION_STATUS, "data", None) or {})
                data["source_tag"] = "rage"
                try:
                    adder_status(
                        replace(
                            DARKVISION_STATUS,
                            duration=duration,
                            source="rage",
                            data=data,
                        )
                    )
                except Exception:
                    pass

        adder_bonus = getattr(actor, "add_bonus", None)
        if callable(adder_bonus):
            adder_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=int(RAGE_DEFAULT_AC_PENALTY),
                    tag="ac",
                    source="rage",
                    label="rage",
                    is_penalty=True,
                    duration_turns=duration,
                )
            )

        try:
            ctx.game.ui_log(
                "Rage aktywne: tymczasowe HP = poziom + modyfikator z Kondycji (opisowo), "
                f"-{RAGE_DEFAULT_AC_PENALTY} AC, +2 dmg wręcz."
            )
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Rage aktywne.")
