from __future__ import annotations

import logging
from dataclasses import replace

from bonuses import BonusEffect, BonusType
from statuses.darkvision import DARKVISION_STATUS
from statuses.rage import RageStatus, RAGE_DURATION_TURNS, RAGE_DEFAULT_AC_PENALTY
from statuses.classes.barbarian.instincts.animal_instinct import AnimalInstinctActiveStatus
from statuses.classes.barbarian.instincts.dragon_instinct import DragonInstinctActiveStatus
from statuses.classes.barbarian.instincts.giant_instinct import GiantInstinctActiveStatus
from statuses.classes.barbarian.instincts.spirit_instinct import SpiritInstinctActiveStatus
from statuses.clumsy import ClumsyStatus
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

        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            profile = getter("animal_instinct", "animal_instinct_profile", None)
        else:
            profile = None
            for s in getattr(actor, "statuses", []) or []:
                if getattr(s, "id", None) != "animal_instinct":
                    continue
                data = getattr(s, "data", None) or {}
                profile = data.get("animal_instinct_profile")
                break
        if profile:
            remover_status = getattr(actor, "remove_status", None)
            if callable(remover_status):
                try:
                    remover_status("animal_instinct_active")
                except Exception:
                    pass
            try:
                adder_status(AnimalInstinctActiveStatus(profile=profile, duration=duration))
            except Exception:
                pass

        if callable(getter):
            dragon_type = getter("dragon_instinct", "dragon_instinct_type", None)
        else:
            dragon_type = None
            for s in getattr(actor, "statuses", []) or []:
                if getattr(s, "id", None) != "dragon_instinct":
                    continue
                data = getattr(s, "data", None) or {}
                dragon_type = data.get("dragon_instinct_type")
                break
        if dragon_type:
            remover_status = getattr(actor, "remove_status", None)
            if callable(remover_status):
                try:
                    remover_status("dragon_instinct_active")
                except Exception:
                    pass
            try:
                adder_status(DragonInstinctActiveStatus(dragon_type=str(dragon_type), duration=duration))
            except Exception:
                pass

        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                has_giant = bool(has_status("giant_instinct"))
            except Exception:
                has_giant = False
        else:
            has_giant = False
            for s in getattr(actor, "statuses", []) or []:
                if getattr(s, "id", None) == "giant_instinct":
                    has_giant = True
                    break
        if has_giant:
            remover_status = getattr(actor, "remove_status", None)
            if callable(remover_status):
                try:
                    remover_status("giant_instinct_active")
                except Exception:
                    pass
                try:
                    remover_status("clumsy")
                except Exception:
                    pass
            try:
                adder_status(GiantInstinctActiveStatus(duration=duration))
                adder_status(ClumsyStatus(ac_penalty=1, duration=duration, source="giant_instinct", label="Clumsy (giant)"))
            except Exception:
                pass

        if callable(getter):
            spirit_type = getter("spirit_instinct", "spirit_instinct_type", None)
        else:
            spirit_type = None
            for s in getattr(actor, "statuses", []) or []:
                if getattr(s, "id", None) != "spirit_instinct":
                    continue
                data = getattr(s, "data", None) or {}
                spirit_type = data.get("spirit_instinct_type")
                break
        if spirit_type:
            remover_status = getattr(actor, "remove_status", None)
            if callable(remover_status):
                try:
                    remover_status("spirit_instinct_active")
                except Exception:
                    pass
            try:
                adder_status(SpiritInstinctActiveStatus(spirit_type=str(spirit_type), duration=duration))
            except Exception:
                pass


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
