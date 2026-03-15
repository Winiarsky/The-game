from __future__ import annotations

import logging

from GameObjects.items.shield import get_equipped_shield
from bonuses import BonusEffect, BonusType
from statuses import SpeedPenaltyStatus
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _clear_raise_shield_speed_penalties(actor) -> None:
    statuses = list(getattr(actor, "statuses", []) or [])
    if not statuses:
        return
    kept = []
    for status in statuses:
        status_id = str(getattr(status, "id", "") or "").strip().lower()
        source = str(getattr(status, "source", "") or "")
        if status_id == "speed_penalty" and source.startswith("raise_shield:"):
            continue
        kept.append(status)
    try:
        setattr(actor, "statuses", kept)
    except Exception:
        pass


def _apply_tower_shield_speed_penalty(actor, *, source_tag: str, shield) -> None:
    penalty = max(0, int(getattr(shield, "speed_penalty_feet", 0) or 0))
    if penalty <= 0:
        return
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return
    actor_id = str(getattr(actor, "object_id", "") or "").strip() or None
    try:
        adder(
            SpeedPenaltyStatus(
                penalty_feet=penalty,
                source=source_tag,
                source_id=actor_id,
                source_turns_left=1,
                duration=1,
                label=f"raise shield: -{penalty} ft",
            )
        )
    except Exception:
        return


def _is_tower_shield(shield) -> bool:
    traits = {str(item or "").strip().lower() for item in (getattr(shield, "traits", ()) or ())}
    return "tower_shield" in traits


@register_event
class RaiseShieldEvent(GameEvent):
    """Podniesienie tarczy – circumstance AC bonus z tarczy do początku kolejnej tury bohatera."""

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
        shield = get_equipped_shield(hero, create_default=False)
        if shield is None:
            return EventResult.cancelled(message="Raise Shield: brak wyposazonej tarczy.")
        if bool(getattr(shield, "is_destroyed", False)):
            return EventResult.cancelled(message="Raise Shield: twoja tarcza jest zniszczona.")
        if getattr(hero, "has_status", lambda _s: False)("prone"):
            return EventResult.cancelled(message="Nie możesz podnieść tarczy będąc prone.")

        # wyczyść wcześniejsze podniesienia tarczy
        remover = getattr(hero, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("raise_shield:")
            except Exception:
                pass
        _clear_raise_shield_speed_penalties(hero)

        round_idx = getattr(getattr(ctx.game, "state", None), "round_index", None)
        source_tag = f"raise_shield:round{round_idx}" if round_idx is not None else "raise_shield"
        try:
            shield_ac_bonus = max(0, int(getattr(shield, "ac_bonus", 2) or 2))
        except Exception:
            shield_ac_bonus = 2

        adder = getattr(hero, "add_bonus", None)
        if not callable(adder):
            return EventResult(success=False, consumed_action=False, message="Bohater nie obsługuje bonusów.")

        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=shield_ac_bonus,
                tag="ac",
                source=source_tag,
                label="tarcza w górze",
                duration_turns=1,
            )
        )
        _apply_tower_shield_speed_penalty(hero, source_tag=source_tag, shield=shield)

        logger.info("Bohater podnosi tarczę: +%s AC circumstance do początku kolejnej tury.", shield_ac_bonus)
        try:
            ctx.game.ui_log(f"Podnosisz tarczę: +{shield_ac_bonus} AC (circumstance) do początku następnej tury.")
            if _is_tower_shield(shield):
                take_cover_bonus = max(shield_ac_bonus, int(getattr(shield, "take_cover_ac_bonus", shield_ac_bonus) or shield_ac_bonus))
                if take_cover_bonus > shield_ac_bonus:
                    ctx.game.ui_log(
                        f"Tarcza wieżowa: samo Raise Shield daje +{shield_ac_bonus} AC. "
                        f"Użyj Take Cover, aby mieć greater cover (+{take_cover_bonus} AC)."
                    )
        except Exception:
            pass
        try:
            ui_hero = getattr(ctx.game, "ui_hero", None)
            if callable(ui_hero):
                ui_hero(hero)
        except Exception:
            pass

        return EventResult(success=True, consumed_action=True, message=f"Tarcza podniesiona (+{shield_ac_bonus} AC).")
